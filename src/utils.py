"""
유틸리티 함수 모음 - 세션, 데이터 검증, 로깅 등
"""

import uuid
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class Emotion(str, Enum):
    """감정 카테고리 정의"""
    SADNESS = "슬픔"  # Sadness & Loss
    ANGER = "분노"  # Anger & Frustration
    REGRET = "후회"  # Regret & Lingering
    ANXIETY = "불안"  # Anxiety & Fear
    GUILT = "죄책감"  # Guilt & Shame
    STRESS = "스트레스"  # Burnout & Stress


class Relationship(str, Enum):
    """관계 카테고리 정의"""
    ROMANTIC = "연인"
    FRIEND = "친구"
    PARENT = "부모"
    SUPERIOR = "직장상사"
    PROFESSOR = "교수"
    OTHER = "기타"


class Intensity(str, Enum):
    """상황 강도"""
    LOW = "낮음"
    MEDIUM = "중간"
    HIGH = "높음"


class Tone(str, Enum):
    """말투 설정"""
    TENDER = "다정함"
    BLUNT = "무뚝뚝함"
    COLD = "차가움"
    HUMOROUS = "유머러스함"
    NORMAL = "보통"


@dataclass
class SessionData:
    """세션 데이터 모델"""
    session_id: str
    created_at: str
    persona: Dict[str, Any]
    chat_history: List[Dict[str, str]]
    analysis_results: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionData":
        """딕셔너리에서 생성"""
        return cls(**data)


@dataclass
class PersonaConfig:
    """페르소나 설정 데이터 모델"""
    relationship: str
    emotion: str
    desired_response: str
    intensity: str
    tone: str
    profanity_allowed: bool = False
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaConfig":
        """딕셔너리에서 생성"""
        return cls(**data)


@dataclass
class AnalysisResult:
    """감정 분석 결과 모델"""
    category: str
    situation_type: str
    sentiment_score: int  # 1-10 스케일
    summary: str
    key_emotions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisResult":
        """딕셔너리에서 생성"""
        return cls(**data)


class SessionManager:
    """세션 관리 유틸리티"""
    
    _sessions: Dict[str, SessionData] = {}
    _session_ttl: int = 3600  # 1시간
    
    @staticmethod
    def generate_session_id() -> str:
        """고유한 세션 ID 생성"""
        return f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    @classmethod
    def create_session(cls, persona: Dict[str, Any]) -> str:
        """새 세션 생성"""
        session_id = cls.generate_session_id()
        session_data = SessionData(
            session_id=session_id,
            created_at=datetime.now().isoformat(),
            persona=persona,
            chat_history=[]
        )
        cls._sessions[session_id] = session_data
        logger.info(f"세션 생성: {session_id}")
        return session_id
    
    @classmethod
    def get_session(cls, session_id: str) -> Optional[SessionData]:
        """세션 조회"""
        if session_id not in cls._sessions:
            logger.warning(f"세션을 찾을 수 없음: {session_id}")
            return None
        return cls._sessions[session_id]
    
    @classmethod
    def add_chat_message(
        cls, 
        session_id: str, 
        user_message: str, 
        ai_response: str, 
        analysis: Optional[Dict[str, Any]] = None
    ) -> bool:
        """채팅 메시지 추가"""
        session = cls.get_session(session_id)
        if not session:
            return False
        
        message_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user_message,
            "assistant": ai_response,
            "analysis": analysis
        }
        
        session.chat_history.append(message_entry)
        
        # 최근 20개 메시지만 유지
        if len(session.chat_history) > 20:
            session.chat_history = session.chat_history[-20:]
        
        logger.debug(f"메시지 추가: {session_id} ({len(session.chat_history)}개)")
        return True
    
    @classmethod
    def get_chat_history(cls, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """채팅 히스토리 조회"""
        session = cls.get_session(session_id)
        if not session:
            return []
        return session.chat_history[-limit:]
    
    @classmethod
    def delete_session(cls, session_id: str) -> bool:
        """세션 삭제"""
        if session_id in cls._sessions:
            del cls._sessions[session_id]
            logger.info(f"세션 삭제: {session_id}")
            return True
        return False
    
    @classmethod
    def get_all_sessions(cls) -> List[str]:
        """모든 활성 세션 ID 조회"""
        return list(cls._sessions.keys())


class DataValidator:
    """데이터 검증 유틸리티"""
    
    @staticmethod
    def validate_persona_config(persona: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """페르소나 설정 검증"""
        required_fields = [
            "relationship", "emotion", "desired_response", 
            "intensity", "tone"
        ]
        
        for field in required_fields:
            if field not in persona or not persona[field]:
                return False, f"필수 필드 '{field}'이 누락되었습니다."
        
        # 유효한 값 확인
        valid_relationships = [r.value for r in Relationship]
        if persona["relationship"] not in valid_relationships:
            return False, f"잘못된 관계 설정: {persona['relationship']}"
        
        valid_emotions = [e.value for e in Emotion]
        if persona["emotion"] not in valid_emotions:
            return False, f"잘못된 감정 설정: {persona['emotion']}"
        
        valid_intensities = [i.value for i in Intensity]
        if persona["intensity"] not in valid_intensities:
            return False, f"잘못된 강도 설정: {persona['intensity']}"
        
        valid_tones = [t.value for t in Tone]
        if persona["tone"] not in valid_tones:
            return False, f"잘못된 말투 설정: {persona['tone']}"
        
        return True, None
    
    @staticmethod
    def validate_message(message: str, max_length: int = 5000) -> tuple[bool, Optional[str]]:
        """메시지 검증"""
        if not message or not isinstance(message, str):
            return False, "메시지는 문자열이어야 합니다."
        
        message = message.strip()
        if not message:
            return False, "빈 메시지는 전송할 수 없습니다."
        
        if len(message) > max_length:
            return False, f"메시지는 {max_length}자 이내여야 합니다."
        
        return True, None
    
    @staticmethod
    def validate_session_id(session_id: str) -> tuple[bool, Optional[str]]:
        """세션 ID 검증"""
        if not session_id or not isinstance(session_id, str):
            return False, "유효하지 않은 세션 ID입니다."
        
        if not session_id.startswith("session_"):
            return False, "세션 ID 형식이 잘못되었습니다."
        
        return True, None


class PromptBuilder:
    """프롬프트 생성 유틸리티"""
    
    @staticmethod
    def build_analyst_prompt(
        user_message: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Analyst 에이전트용 프롬프트 생성"""
        history_text = ""
        if chat_history and len(chat_history) > 0:
            history_text = "\n[이전 대화]\n"
            for msg in chat_history[-3:]:  # 최근 3개 메시지
                history_text += f"사용자: {msg.get('user', '')}\n"
                history_text += f"응답: {msg.get('assistant', '')}\n"
        
        return f"""다음 사용자의 메시지를 분석해주세요.

{history_text}

[현재 메시지]
사용자: {user_message}

이 메시지에서 드러나는 감정, 상황, 강도를 분석하세요."""
    
    @staticmethod
    def build_retriever_prompt(
        analysis_result: Dict[str, Any]
    ) -> str:
        """Retriever 에이전트용 프롬프트 생성"""
        return f"""다음 감정 분석 결과에 맞는 공감 전략과 응답 구조를 제시하세요.

[분석 결과]
- 감정 카테고리: {analysis_result.get('category', '')}
- 상황 유형: {analysis_result.get('situation_type', '')}
- 강도: {analysis_result.get('sentiment_score', 0)}/10
- 요약: {analysis_result.get('summary', '')}

이에 맞는 심리학적 공감 전략, 답변 구조, 구체적인 예시를 제공하세요."""
    
    @staticmethod
    def build_listener_prompt(
        user_message: str,
        persona: Dict[str, Any],
        rag_strategy: Dict[str, Any],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Listener 에이전트용 프롬프트 생성"""
        history_text = ""
        if chat_history and len(chat_history) > 0:
            history_text = "\n[이전 대화]\n"
            for msg in chat_history[-3:]:
                history_text += f"사용자: {msg.get('user', '')}\n"
                history_text += f"응답: {msg.get('assistant', '')}\n"
        
        return f"""당신의 역할:
- 관계: {persona.get('relationship', '')}
- 말투: {persona.get('tone', '')}
- 강도: {persona.get('intensity', '')}

[RAG 공감 전략 가이드]
- 핵심 전략: {rag_strategy.get('strategy', '')}
- 답변 구조: {rag_strategy.get('structure', '')}
- 참고 예시: {rag_strategy.get('examples', '')}

{history_text}

[사용자 메시지]
{user_message}

위 역할을 완벽히 수행하면서 RAG 전략을 따라 자연스럽고 따뜻한 응답을 생성하세요.
마지막에는 사용자에게 전하는 심리학적 조언을 덧붙이세요."""


class ErrorHandler:
    """에러 처리 유틸리티"""
    
    @staticmethod
    def handle_api_error(error: Exception, context: Optional[str] = None) -> Dict[str, Any]:
        """API 에러 처리"""
        error_message = str(error)
        logger.error(f"API 에러 ({context}): {error_message}")
        
        return {
            "success": False,
            "error": {
                "type": type(error).__name__,
                "message": error_message,
                "context": context,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    @staticmethod
    def create_error_response(
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """표준 에러 응답 생성"""
        return {
            "success": False,
            "error": {
                "type": error_type,
                "message": message,
                "details": details or {},
                "timestamp": datetime.now().isoformat()
            }
        }


class TextProcessor:
    """텍스트 처리 유틸리티"""
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """텍스트 길이 제한"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + suffix
    
    @staticmethod
    def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
        """텍스트에서 JSON 추출"""
        try:
            # 마크다운 코드 블록 제거
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning(f"JSON 추출 실패: {e}")
            return None
    
    @staticmethod
    def clean_text(text: str) -> str:
        """텍스트 정제"""
        # 불필요한 공백 제거
        text = " ".join(text.split())
        # 앞뒤 공백 제거
        return text.strip()
