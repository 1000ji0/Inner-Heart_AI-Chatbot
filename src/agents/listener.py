"""
리스너 에이전트 (Listener) - 페르소나 기반 최종 응답 생성
"""

import logging
from typing import Dict, Any, List, Optional

from config import api_client
from utils import PromptBuilder, ErrorHandler, TextProcessor

logger = logging.getLogger(__name__)


class ListenerAgent:
    """
    검색된 전략에 '페르소나(관계, 말투)'라는 옷을 입혀 
    최종 답변을 완성하는 작가 역할
    
    주요 기능:
    1. 페르소나에 따른 캐릭터 몰입
    2. 공감 메시지 생성
    3. 심리학적 조언 추가
    4. 자연스러운 대화 톤 유지
    """
    
    # 말투별 톤 설정
    TONE_PROFILES = {
        "다정함": {
            "warmth": "high",
            "formality": "low",
            "emojis": True,
            "affection": "high",
            "keywords": ["정말", "너무", "꼭", "귀여운", "고마워"]
        },
        "무뚝뚝함": {
            "warmth": "medium",
            "formality": "medium",
            "emojis": False,
            "affection": "low",
            "keywords": ["그래", "맞다", "음", "있잖아"]
        },
        "차가움": {
            "warmth": "low",
            "formality": "high",
            "emojis": False,
            "affection": "very_low",
            "keywords": ["그것이", "잘 알겠습니다", "논리적으로"]
        },
        "유머러스함": {
            "warmth": "high",
            "formality": "low",
            "emojis": True,
            "affection": "medium",
            "keywords": ["ㅋㅋ", "헉", "웃음", "농담"]
        },
        "보통": {
            "warmth": "medium",
            "formality": "medium",
            "emojis": False,
            "affection": "medium",
            "keywords": ["그렇구나", "이해해", "그래도"]
        }
    }
    
    # 관계별 호칭과 톤
    RELATIONSHIP_PROFILES = {
        "연인": {
            "personal_level": "very_high",
            "intimacy": "high",
            "formality": "very_low",
            "example_phrases": ["사랑해", "정말 고마워", "앞으로도 함께"]
        },
        "친구": {
            "personal_level": "high",
            "intimacy": "medium",
            "formality": "low",
            "example_phrases": ["우리 잘 지낼 수 있어", "너 너무 좋은 친구야", "항상 옆에 있을게"]
        },
        "부모": {
            "personal_level": "high",
            "intimacy": "medium",
            "formality": "medium",
            "example_phrases": ["엄마/아빠 입장에서", "너의 안전이 최우선", "충분히 잘했어"]
        },
        "직장상사": {
            "personal_level": "medium",
            "intimacy": "low",
            "formality": "high",
            "example_phrases": ["훌륭한 성과입니다", "충분히 노력하고 있습니다", "함께 해결해봅시다"]
        },
        "교수": {
            "personal_level": "low",
            "intimacy": "very_low",
            "formality": "very_high",
            "example_phrases": ["학문적으로", "지속적인 노력이", "훌륭한 잠재력"]
        },
        "기타": {
            "personal_level": "medium",
            "intimacy": "medium",
            "formality": "medium",
            "example_phrases": ["이해합니다", "함께 생각해봅시다", "응원합니다"]
        }
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_client = api_client
    
    def generate_response(
        self,
        user_message: str,
        persona: Dict[str, Any],
        rag_strategy: Dict[str, Any],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        최종 공감 응답 생성
        
        Args:
            user_message: 원래 사용자 메시지
            persona: 페르소나 설정 (관계, 말투, 강도)
            rag_strategy: Retriever에서 제공한 공감 전략
            chat_history: 이전 채팅 히스토리
            
        Returns:
            생성된 응답 및 심리 조언
        """
        self.logger.info(f"응답 생성 시작: {persona.get('relationship')} / {persona.get('tone')}")
        
        try:
            # 1. 시스템 지시사항 구성
            system_instruction = self._build_system_instruction(persona, rag_strategy)
            
            # 2. 프롬프트 구성
            prompt = self._build_prompt(
                user_message,
                persona,
                rag_strategy,
                chat_history
            )
            
            self.logger.debug(f"프롬프트: {prompt[:100]}")
            
            # 3. Gemini API 호출
            api_response = self.api_client.call_gemini(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.8  # 창의성 필요 (응답 다양성)
            )
            
            self.logger.debug(f"API 응답: {api_response}")
            
            # 4. 응답 검증 및 정규화
            response_data = self._validate_and_normalize_response(api_response)
            
            self.logger.info("응답 생성 완료")
            
            return {
                "success": True,
                "response": response_data.get("reply"),
                "insight": response_data.get("analyst_comment"),
                "tone_applied": persona.get("tone"),
                "relationship_context": persona.get("relationship")
            }
        
        except Exception as e:
            self.logger.error(f"응답 생성 중 오류: {e}")
            return ErrorHandler.handle_api_error(e, "ListenerAgent.generate_response")
    
    def _build_system_instruction(
        self,
        persona: Dict[str, Any],
        rag_strategy: Dict[str, Any]
    ) -> str:
        """시스템 지시사항 생성"""
        relationship = persona.get("relationship", "친구")
        tone = persona.get("tone", "보통")
        intensity = persona.get("intensity", "중간")
        
        relationship_profile = self.RELATIONSHIP_PROFILES.get(
            relationship, 
            self.RELATIONSHIP_PROFILES["기타"]
        )
        tone_profile = self.TONE_PROFILES.get(tone, self.TONE_PROFILES["보통"])
        
        # 강도별 지침
        intensity_guide = {
            "낮음": "부드럽고 조심스럽게 접근하며, 사용자의 감정을 가볍게 받아들이세요.",
            "중간": "자연스럽고 따뜻하게 공감하며, 사용자의 감정을 존중하세요.",
            "높음": "깊이 있게 공감하고, 사용자의 감정을 충분히 인정해주세요."
        }
        
        return f"""당신의 역할과 성격:
- 관계: {relationship} (친밀도: {relationship_profile['intimacy']})
- 말투: {tone}
- 반응 강도: {intensity}

[말투 가이드]
{json.dumps(tone_profile, ensure_ascii=False)}

[관계 가이드]
{json.dumps(relationship_profile, ensure_ascii=False)}

[공감 전략]
- 핵심 전략: {rag_strategy.get('strategy')}
- 답변 구조: {rag_strategy.get('structure')}
- 금지사항: {', '.join(rag_strategy.get('dont_s', []))}

[응답 강도 가이드]
{intensity_guide.get(intensity, intensity_guide['중간'])}

당신은 이 관계의 사람이 되어 정말로 그 사람이 말하는 방식으로 응답해야 합니다.
부자연스럽지 않으면서도 진정성 있는 공감을 제공하세요.

반드시 다음 JSON 형식으로만 응답하세요:
{{
  "reply": "생성된 공감 답변 (자연스럽고 따뜻한 톤)",
  "analyst_comment": "사용자에게 전하는 심리학적 조언 한 줄",
  "tone_markers": ["적용된 톤 요소 1", "적용된 톤 요소 2"],
  "empathy_level": "낮음/중간/높음"
}}"""
    
    def _build_prompt(
        self,
        user_message: str,
        persona: Dict[str, Any],
        rag_strategy: Dict[str, Any],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """프롬프트 생성"""
        return PromptBuilder.build_listener_prompt(
            user_message,
            persona,
            rag_strategy,
            chat_history
        )
    
    def _validate_and_normalize_response(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """API 응답 검증 및 정규화"""
        required_fields = ["reply", "analyst_comment"]
        
        for field in required_fields:
            if field not in api_response:
                raise ValueError(f"필수 필드 '{field}'이 누락되었습니다.")
        
        reply = api_response.get("reply", "").strip()
        analyst_comment = api_response.get("analyst_comment", "").strip()
        
        if not reply:
            raise ValueError("응답 내용이 비어있습니다.")
        
        if not analyst_comment:
            analyst_comment = self._generate_default_insight()
        
        return {
            "reply": reply,
            "analyst_comment": analyst_comment,
            "tone_markers": api_response.get("tone_markers", []),
            "empathy_level": api_response.get("empathy_level", "중간")
        }
    
    def _generate_default_insight(self) -> str:
        """기본 심리 조언 생성"""
        insights = [
            "당신의 감정을 느끼는 것은 매우 자연스러운 일입니다.",
            "이 순간을 통해 자신에 대해 더 알아갈 수 있을 거예요.",
            "당신이 느끼는 감정은 유효하고 중요합니다.",
            "가끔은 힘들어도 괜찮습니다. 그런 날도 있으니까요.",
            "앞으로 나아갈 수 있는 작은 힘을 얻기 바랍니다."
        ]
        
        import random
        return random.choice(insights)
    
    def apply_tone_to_text(self, text: str, tone: str) -> str:
        """텍스트에 톤 적용"""
        tone_profile = self.TONE_PROFILES.get(tone, self.TONE_PROFILES["보통"])
        
        # 키워드 추가 (간단한 톤 적용)
        modified_text = text
        
        if tone_profile.get("warmth") == "high" and tone_profile.get("affection") == "high":
            # 다정함 추가
            if "정말" not in modified_text and len(modified_text) > 20:
                modified_text = f"정말 {modified_text}"
        
        if tone_profile.get("emojis"):
            # 이모지 추가 (선택사항)
            if tone == "유머러스함":
                modified_text += " ㅋㅋ"
            elif tone == "다정함":
                modified_text += " 💙"
        
        return modified_text
    
    def generate_followup_questions(
        self,
        user_message: str,
        persona: Dict[str, Any]
    ) -> List[str]:
        """후속 질문 생성 (선택사항)"""
        prompt = f"""사용자의 메시지에 대해 {persona.get('relationship')}인 당신이 
더 깊이 있는 대화를 위해 물어볼 수 있는 3가지 자연스러운 후속 질문을 생성하세요.

사용자 메시지: {user_message}

질문들은 리스트 형식으로만 제시하세요."""
        
        try:
            response = self.api_client.call_gemini_text(
                prompt=prompt,
                system_instruction=f"당신은 {persona.get('relationship')}입니다. 자연스러운 후속 질문만 생성하세요."
            )
            
            # 응답 파싱
            lines = response.split("\n")
            questions = [line.strip("- •").strip() for line in lines if line.strip()]
            return questions[:3]
        
        except Exception as e:
            self.logger.warning(f"후속 질문 생성 실패: {e}")
            return []


# 필수 임포트
import json

# 전역 인스턴스
listener_agent = ListenerAgent()