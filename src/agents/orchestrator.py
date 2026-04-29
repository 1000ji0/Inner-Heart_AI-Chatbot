"""
오케스트레이터 에이전트 - 전체 파이프라인 제어 및 에이전트 조율
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .analyst import AnalystAgent
from .retriever import RetrieverAgent
from .listener import ListenerAgent
from utils import (
    SessionManager, DataValidator, PromptBuilder, ErrorHandler, TextProcessor
)

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    멀티 에이전트 시스템의 중앙 관리자
    
    파이프라인:
    1. 페르소나 설정 (Setup)
    2. 사용자 메시지 수신
    3. Analyst: 감정 분석
    4. Retriever: RAG 검색으로 전략 제공
    5. Listener: 페르소나 기반 최종 응답 생성
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.analyst = AnalystAgent()
        self.retriever = RetrieverAgent()
        self.listener = ListenerAgent()
    
    def setup_session(self, persona: Dict[str, Any]) -> Dict[str, Any]:
        """
        새 세션 설정
        
        Args:
            persona: 페르소나 설정 데이터
            - relationship: 관계 (연인, 친구, 부모, 직장상사, 교수, 기타)
            - emotion: 기대 감정 (분노, 슬픔, 후회, 감사, 미련, 복잡함)
            - desired_response: 원하는 반응 (사과, 위로, 공감, 무시, 솔직한 피드백, 책임 인정)
            - intensity: 반응 강도 (부드럽게, 중간, 강하게)
            - tone: 말투 (다정, 무뚝뚝함, 차가움, 유머러스함, 보통)
            - profanity_allowed: 욕설 허용 여부 (선택사항)
            
        Returns:
            세션 생성 결과 또는 에러
        """
        self.logger.info("="*50)
        self.logger.info("새 세션 설정 시작")
        self.logger.info("="*50)
        
        # 페르소나 검증
        is_valid, error_msg = DataValidator.validate_persona_config(persona)
        if not is_valid:
            self.logger.error(f"페르소나 검증 실패: {error_msg}")
            return ErrorHandler.create_error_response(
                "VALIDATION_ERROR",
                error_msg,
                {"persona": persona}
            )
        
        try:
            # 세션 생성
            session_id = SessionManager.create_session(persona)
            
            self.logger.info(f"세션 생성 성공: {session_id}")
            self.logger.info(f"페르소나: {persona}")
            
            return {
                "success": True,
                "session_id": session_id,
                "message": "세션이 설정되었습니다.",
                "persona": persona
            }
        
        except Exception as e:
            self.logger.error(f"세션 설정 중 오류: {e}")
            return ErrorHandler.handle_api_error(e, "setup_session")
    
    def run_pipeline(
        self,
        session_id: str,
        user_message: str
    ) -> Dict[str, Any]:
        """
        전체 파이프라인 실행: 분석 -> 검색 -> 응답 생성
        
        Args:
            session_id: 세션 ID
            user_message: 사용자 메시지
            
        Returns:
            최종 응답 및 분석 결과
        """
        self.logger.info("-"*50)
        self.logger.info(f"파이프라인 시작 - 세션: {session_id}")
        self.logger.info("-"*50)
        
        # 1. 입력 검증
        is_valid, error_msg = DataValidator.validate_session_id(session_id)
        if not is_valid:
            self.logger.error(f"세션 ID 검증 실패: {error_msg}")
            return ErrorHandler.create_error_response(
                "INVALID_SESSION",
                error_msg
            )
        
        is_valid, error_msg = DataValidator.validate_message(user_message)
        if not is_valid:
            self.logger.error(f"메시지 검증 실패: {error_msg}")
            return ErrorHandler.create_error_response(
                "INVALID_MESSAGE",
                error_msg
            )
        
        # 2. 세션 조회
        session = SessionManager.get_session(session_id)
        if not session:
            self.logger.error(f"세션을 찾을 수 없음: {session_id}")
            return ErrorHandler.create_error_response(
                "SESSION_NOT_FOUND",
                f"세션을 찾을 수 없습니다: {session_id}"
            )
        
        try:
            # 3. Step 1: Analyst 에이전트 - 감정 분석
            self.logger.info("[Step 1] Analyst 에이전트 - 감정 분석 시작")
            analysis_result = self._step_analyze(
                user_message,
                SessionManager.get_chat_history(session_id)
            )
            
            if not analysis_result.get("success"):
                self.logger.error(f"감정 분석 실패: {analysis_result}")
                return analysis_result
            
            analysis_data = analysis_result.get("analysis", {})
            self.logger.info(f"감정 분석 완료: {analysis_data.get('category')}")
            
            # 4. Step 2: Retriever 에이전트 - RAG 검색
            self.logger.info("[Step 2] Retriever 에이전트 - 공감 전략 검색 시작")
            retrieval_result = self._step_retrieve(
                analysis_data,
                session.persona
            )
            
            if not retrieval_result.get("success"):
                self.logger.error(f"전략 검색 실패: {retrieval_result}")
                return retrieval_result
            
            rag_strategy = retrieval_result.get("strategy", {})
            self.logger.info(f"전략 검색 완료: {rag_strategy.get('strategy_name')}")
            
            # 5. Step 3: Listener 에이전트 - 최종 응답 생성
            self.logger.info("[Step 3] Listener 에이전트 - 최종 응답 생성 시작")
            response_result = self._step_generate_response(
                user_message,
                session.persona,
                rag_strategy,
                SessionManager.get_chat_history(session_id)
            )
            
            if not response_result.get("success"):
                self.logger.error(f"응답 생성 실패: {response_result}")
                return response_result
            
            ai_response = response_result.get("response", "")
            analyst_comment = response_result.get("insight", "")
            self.logger.info("응답 생성 완료")
            
            # 6. 채팅 히스토리 저장
            SessionManager.add_chat_message(
                session_id,
                user_message,
                ai_response,
                analysis=analysis_data
            )
            
            # 7. 최종 응답 구성
            final_response = {
                "success": True,
                "session_id": session_id,
                "reply": ai_response,
                "analyst_comment": analyst_comment,
                "analysis": {
                    "category": analysis_data.get("category"),
                    "sentiment_score": analysis_data.get("sentiment_score"),
                    "summary": analysis_data.get("summary"),
                    "key_emotions": analysis_data.get("key_emotions", [])
                },
                "strategy": {
                    "name": rag_strategy.get("strategy_name"),
                    "approach": rag_strategy.get("strategy")
                },
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info("="*50)
            self.logger.info("파이프라인 완료 (성공)")
            self.logger.info("="*50)
            
            return final_response
        
        except Exception as e:
            self.logger.error(f"파이프라인 실행 중 예상치 못한 오류: {e}", exc_info=True)
            return ErrorHandler.handle_api_error(e, "run_pipeline")
    
    def _step_analyze(
        self,
        user_message: str,
        chat_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Analyst 에이전트 실행"""
        try:
            return self.analyst.analyze(user_message, chat_history)
        except Exception as e:
            self.logger.error(f"Analyst 에이전트 오류: {e}")
            return ErrorHandler.handle_api_error(e, "_step_analyze")
    
    def _step_retrieve(
        self,
        analysis_data: Dict[str, Any],
        persona: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Retriever 에이전트 실행"""
        try:
            return self.retriever.retrieve_strategy(analysis_data, persona)
        except Exception as e:
            self.logger.error(f"Retriever 에이전트 오류: {e}")
            return ErrorHandler.handle_api_error(e, "_step_retrieve")
    
    def _step_generate_response(
        self,
        user_message: str,
        persona: Dict[str, Any],
        rag_strategy: Dict[str, Any],
        chat_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Listener 에이전트 실행"""
        try:
            return self.listener.generate_response(
                user_message,
                persona,
                rag_strategy,
                chat_history
            )
        except Exception as e:
            self.logger.error(f"Listener 에이전트 오류: {e}")
            return ErrorHandler.handle_api_error(e, "_step_generate_response")
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """세션 정보 조회"""
        is_valid, error_msg = DataValidator.validate_session_id(session_id)
        if not is_valid:
            return ErrorHandler.create_error_response(
                "INVALID_SESSION",
                error_msg
            )
        
        session = SessionManager.get_session(session_id)
        if not session:
            return ErrorHandler.create_error_response(
                "SESSION_NOT_FOUND",
                f"세션을 찾을 수 없습니다: {session_id}"
            )
        
        return {
            "success": True,
            "session_id": session_id,
            "created_at": session.created_at,
            "persona": session.persona,
            "message_count": len(session.chat_history),
            "recent_messages": SessionManager.get_chat_history(session_id, limit=5)
        }
    
    def close_session(self, session_id: str) -> Dict[str, Any]:
        """세션 종료"""
        is_valid, error_msg = DataValidator.validate_session_id(session_id)
        if not is_valid:
            return ErrorHandler.create_error_response(
                "INVALID_SESSION",
                error_msg
            )
        
        if SessionManager.delete_session(session_id):
            return {
                "success": True,
                "message": f"세션이 종료되었습니다: {session_id}"
            }
        
        return ErrorHandler.create_error_response(
            "SESSION_NOT_FOUND",
            f"세션을 찾을 수 없습니다: {session_id}"
        )


# 전역 인스턴스
orchestrator = Orchestrator()