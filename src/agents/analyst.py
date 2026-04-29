"""
분석 에이전트 - 사용자 메시지의 감정, 상황, 강도 분석
"""

import logging
from typing import Dict, Any, List, Optional

from config import api_client
from utils import PromptBuilder, ErrorHandler, Emotion

logger = logging.getLogger(__name__)


class AnalystAgent:
    """
    사용자의 텍스트 뒤에 숨겨진 '의도와 감정'을 읽어내는 전문가
    
    주요 기능:
    1. 감정 테마 분류 (6가지 핵심 감정)
    2. 상황 요약 및 핵심 파악
    3. 감정 강도 수치화 (1~10)
    4. 주요 감정 키워드 추출
    """
    
    # 감정 카테고리 정의
    EMOTION_CATEGORIES = {
        "슬픔": {
            "keywords": ["슬프", "우울", "힘들", "외로", "고독", "상실", "아프", "절망"],
            "description": "Sadness & Loss"
        },
        "분노": {
            "keywords": ["화", "분노", "짜증", "화난", "억울", "불의", "배신", "무시"],
            "description": "Anger & Frustration"
        },
        "후회": {
            "keywords": ["후회", "미련", "아쉬움", "그럼 좋았을", "다시", "못한", "너무"],
            "description": "Regret & Lingering"
        },
        "불안": {
            "keywords": ["불안", "두렵", "걱정", "불확실", "위험", "떨려", "공포", "불안감"],
            "description": "Anxiety & Fear"
        },
        "죄책감": {
            "keywords": ["죄책감", "미안", "죄송", "내 탓", "책임", "부끄러", "낭패", "미움"],
            "description": "Guilt & Shame"
        },
        "스트레스": {
            "keywords": ["스트레스", "바쁜", "힘들", "지친", "과로", "힘겨운", "번아웃"],
            "description": "Burnout & Stress"
        }
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_client = api_client
    
    def analyze(
        self,
        user_message: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        사용자 메시지 분석
        
        Args:
            user_message: 사용자 메시지
            chat_history: 이전 채팅 히스토리
            
        Returns:
            감정 분석 결과
        """
        self.logger.info(f"감정 분석 시작: {user_message[:50]}")
        
        try:
            # 1. 시스템 지시사항 구성
            system_instruction = self._build_system_instruction()
            
            # 2. 프롬프트 구성
            prompt = PromptBuilder.build_analyst_prompt(user_message, chat_history)
            
            self.logger.debug(f"프롬프트: {prompt[:100]}")
            
            # 3. Gemini API 호출
            api_response = self.api_client.call_gemini(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.6  # 분석이므로 좀 더 낮은 온도
            )
            
            self.logger.debug(f"API 응답: {api_response}")
            
            # 4. 응답 검증 및 정규화
            analysis_result = self._validate_and_normalize_response(api_response)
            
            self.logger.info(f"분석 완료: {analysis_result.get('category')}")
            
            return {
                "success": True,
                "analysis": analysis_result
            }
        
        except Exception as e:
            self.logger.error(f"분석 중 오류: {e}")
            return ErrorHandler.handle_api_error(e, "AnalystAgent.analyze")
    
    def _build_system_instruction(self) -> str:
        """시스템 지시사항 생성"""
        emotion_list = ", ".join([f"{k} ({v['description']})" 
                                 for k, v in self.EMOTION_CATEGORIES.items()])
        
        return f"""당신은 고도로 훈련된 심리 분석 에이전트입니다.
사용자의 메시지를 깊이 있게 분석하여 다음을 수행하세요:

1. **감정 카테고리 선택**: 다음 6가지 중 가장 적합한 하나를 선택
   {emotion_list}

2. **상황 유형 파악**: 구체적인 상황 유형 (예: 약속 파기, 무시, 배신 등)

3. **감정 강도 측정**: 1~10 사이의 수값
   - 1~3: 약함 (가벼운 불만)
   - 4~6: 중간 (명확한 감정)
   - 7~10: 강함 (깊은 감정)

4. **핵심 요약**: 사용자의 가장 중요한 고민/감정을 한 두 문장으로 요약

5. **주요 감정 키워드 추출**: 메시지에서 나타나는 3~5가지 감정 키워드

반드시 다음 JSON 형식으로만 응답하세요:
{{
  "category": "감정 카테고리 이름",
  "situation_type": "구체적인 상황 유형",
  "sentiment_score": 1~10의 정수,
  "summary": "핵심 상황 요약 (2문장 이내)",
  "key_emotions": ["감정1", "감정2", "감정3"],
  "reasoning": "분석 근거 (간단히)"
}}

주의사항:
- 사용자의 감정을 판단하지 말고 이해하세요
- 상대방 입장이 아닌 사용자 감정에 집중하세요
- 정확하고 공감적인 분석을 제공하세요"""
    
    def _validate_and_normalize_response(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """API 응답 검증 및 정규화"""
        required_fields = [
            "category", "situation_type", "sentiment_score",
            "summary", "key_emotions"
        ]
        
        for field in required_fields:
            if field not in api_response:
                raise ValueError(f"필수 필드 '{field}'이 누락되었습니다.")
        
        # 감정 강도 검증
        sentiment_score = api_response.get("sentiment_score", 5)
        if not isinstance(sentiment_score, int) or sentiment_score < 1 or sentiment_score > 10:
            sentiment_score = 5
            self.logger.warning(f"감정 강도가 유효하지 않음, 기본값 5로 설정")
        
        # 카테고리 검증
        category = api_response.get("category", "")
        valid_categories = list(self.EMOTION_CATEGORIES.keys())
        if category not in valid_categories:
            category = self._infer_category_from_keywords(api_response.get("key_emotions", []))
            self.logger.warning(f"카테고리가 유효하지 않음, 추론된 값 사용: {category}")
        
        return {
            "category": category,
            "situation_type": api_response.get("situation_type", "일반적인 상황"),
            "sentiment_score": sentiment_score,
            "summary": api_response.get("summary", "사용자가 감정적 고민을 공유했습니다."),
            "key_emotions": api_response.get("key_emotions", []),
            "reasoning": api_response.get("reasoning", ""),
            "analysis_timestamp": self._get_timestamp()
        }
    
    def _infer_category_from_keywords(self, keywords: List[str]) -> str:
        """키워드에서 감정 카테고리 추론"""
        if not keywords:
            return "스트레스"
        
        # 각 카테고리별 스코어 계산
        scores = {}
        for category, info in self.EMOTION_CATEGORIES.items():
            score = sum(1 for kw in keywords if any(
                cat_kw in kw.lower() for cat_kw in info["keywords"]
            ))
            scores[category] = score
        
        # 가장 높은 스코어 카테고리 선택
        best_category = max(scores, key=scores.get)
        
        if scores[best_category] == 0:
            return "스트레스"  # 기본값
        
        return best_category
    
    def _get_timestamp(self) -> str:
        """현재 시간 반환"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def extract_emotional_context(self, message: str) -> Dict[str, Any]:
        """
        메시지에서 감정 맥락 추출 (보조 함수)
        
        Args:
            message: 사용자 메시지
            
        Returns:
            감정 맥락 정보
        """
        context = {
            "message_length": len(message),
            "has_punctuation": any(p in message for p in "!?..."),
            "emotional_intensity_markers": [],
            "possible_emotions": []
        }
        
        # 강조 표시 확인
        if "!!!" in message or "???" in message:
            context["emotional_intensity_markers"].append("강조 표시")
        
        if "..." in message:
            context["emotional_intensity_markers"].append("생각의 끝남")
        
        # 가능한 감정 추론
        message_lower = message.lower()
        for category, info in self.EMOTION_CATEGORIES.items():
            for keyword in info["keywords"]:
                if keyword in message_lower:
                    context["possible_emotions"].append(category)
                    break
        
        return context
