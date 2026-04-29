"""
FastAPI 애플리케이션 - 속마음 말하기 AI 채팅 API
"""

import logging
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

from agents.orchestrator import orchestrator
from config import settings
from utils import DataValidator, ErrorHandler

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 앱 설정
app = FastAPI(
    title="속마음 말하기 - AI 공감 채팅 API",
    description="멀티 에이전트 AI 시스템을 통한 공감형 채팅 애플리케이션",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 요청/응답 모델 정의
class PersonaSetup(BaseModel):
    """페르소나 설정 모델"""
    relationship: str = Field(..., description="관계: 연인, 친구, 부모, 직장상사, 교수, 기타")
    emotion: str = Field(..., description="기대 감정: 분노, 슬픔, 후회, 감사, 미련, 복잡함")
    desired_response: str = Field(..., description="원하는 반응: 사과, 위로, 공감, 무시, 솔직한 피드백, 책임 인정")
    intensity: str = Field(..., description="반응 강도: 부드럽게, 중간, 강하게")
    tone: str = Field(..., description="말투: 다정, 무뚝뚝함, 차가움, 유머러스함, 보통")
    profanity_allowed: Optional[bool] = Field(False, description="욕설 허용 여부")
    
    @validator("relationship", "emotion", "desired_response", "intensity", "tone")
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("필수 필드는 빈 값이 될 수 없습니다.")
        return v


class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    session_id: str = Field(..., description="세션 ID")
    message: str = Field(..., description="사용자 메시지", min_length=1, max_length=5000)
    
    @validator("message")
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError("메시지는 빈 문자열이 될 수 없습니다.")
        return v.strip()


class SessionResponse(BaseModel):
    """세션 응답 모델"""
    success: bool
    session_id: Optional[str] = None
    message: Optional[str] = None
    persona: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    success: bool
    session_id: Optional[str] = None
    reply: Optional[str] = None
    analyst_comment: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    strategy: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


# API 엔드포인트

@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """헬스 체크"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": "0.1.0"
    }


@app.post("/session/setup", response_model=SessionResponse, tags=["Session"])
async def setup_session(persona: PersonaSetup) -> SessionResponse:
    """
    새 세션 설정
    
    페르소나 설정을 통해 새로운 채팅 세션을 초기화합니다.
    """
    logger.info("새 세션 설정 요청 수신")
    
    try:
        # 페르소나 데이터 딕셔너리로 변환
        persona_dict = persona.dict()
        
        # 오케스트레이터를 통해 세션 설정
        result = orchestrator.setup_session(persona_dict)
        
        if result.get("success"):
            return SessionResponse(
                success=True,
                session_id=result.get("session_id"),
                message=result.get("message"),
                persona=result.get("persona")
            )
        else:
            error = result.get("error", {})
            raise HTTPException(
                status_code=Status.HTTP_400_BAD_REQUEST,
                detail=str(error.get("message", "세션 설정 실패"))
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 설정 중 오류: {e}")
        raise HTTPException(
            status_code=Status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="세션 설정 중 오류가 발생했습니다."
        )


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def send_message(request: ChatRequest) -> ChatResponse:
    """
    메시지 전송 및 AI 응답
    
    사용자 메시지를 전송하고 멀티 에이전트 시스템을 통해 처리합니다.
    """
    logger.info(f"채팅 요청 수신: {request.session_id}")
    
    try:
        # 파이프라인 실행
        result = orchestrator.run_pipeline(request.session_id, request.message)
        
        if result.get("success"):
            return ChatResponse(
                success=True,
                session_id=result.get("session_id"),
                reply=result.get("reply"),
                analyst_comment=result.get("analyst_comment"),
                analysis=result.get("analysis"),
                strategy=result.get("strategy")
            )
        else:
            error = result.get("error", {})
            raise HTTPException(
                status_code=Status.HTTP_400_BAD_REQUEST,
                detail=str(error.get("message", "메시지 처리 실패"))
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"메시지 처리 중 오류: {e}")
        raise HTTPException(
            status_code=Status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="메시지 처리 중 오류가 발생했습니다."
        )


@app.get("/session/{session_id}", tags=["Session"])
async def get_session_info(session_id: str) -> Dict[str, Any]:
    """
    세션 정보 조회
    
    특정 세션의 정보와 채팅 히스토리를 조회합니다.
    """
    logger.info(f"세션 정보 조회: {session_id}")
    
    try:
        result = orchestrator.get_session_info(session_id)
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(
                status_code=Status.HTTP_404_NOT_FOUND,
                detail=result.get("error", {}).get("message", "세션을 찾을 수 없습니다.")
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 조회 중 오류: {e}")
        raise HTTPException(
            status_code=Status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="세션 조회 중 오류가 발생했습니다."
        )


@app.get("/rag/statistics", tags=["RAG"])
async def get_rag_stats() -> Dict[str, Any]:
    """
    RAG 인덱서 통계 조회
    
    불러온 지식 베이스 문서의 통계 정보를 조회합니다.
    """
    logger.info("RAG 통계 조회")
    
    try:
        from agents.retriever import retriever_agent
        stats = retriever_agent.get_rag_statistics()
        
        return {
            "success": True,
            "statistics": stats
        }
    
    except Exception as e:
        logger.error(f"RAG 통계 조회 중 오류: {e}")
        raise HTTPException(
            status_code=Status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG 통계 조회 중 오류가 발생했습니다."
        )


@app.get("/rag/search", tags=["RAG"])
async def rag_search(
    emotion: Optional[str] = None,
    relationship: Optional[str] = None,
    tone: Optional[str] = None,
    query: Optional[str] = None
) -> Dict[str, Any]:
    """
    RAG 직접 검색 (디버깅/테스트용)
    
    감정, 관계, 말투, 또는 텍스트 쿼리로 지식 베이스를 검색합니다.
    
    쿼리 파라미터:
    - emotion: 감정 (예: "분노", "슬픔")
    - relationship: 관계 (예: "연인", "친구")
    - tone: 말투 (예: "다정함", "무뚝뚝함")
    - query: 텍스트 검색 쿼리
    """
    logger.info(f"RAG 검색: emotion={emotion}, relationship={relationship}, tone={tone}")
    
    try:
        from agents.retriever import retriever_agent
        
        results = retriever_agent.search_direct(
            emotion=emotion,
            relationship=relationship,
            tone=tone,
            query=query
        )
        
        return {
            "success": True,
            "query": {
                "emotion": emotion,
                "relationship": relationship,
                "tone": tone,
                "text_query": query
            },
            "results_count": len(results),
            "results": results
        }
    
    except Exception as e:
        logger.error(f"RAG 검색 중 오류: {e}")
        raise HTTPException(
            status_code=Status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG 검색 중 오류가 발생했습니다."
        )


@app.get("/", tags=["Info"])
async def root() -> Dict[str, str]:
    """API 정보"""
    return {
        "name": "속마음 말하기 AI 채팅 API",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


# 에러 처리
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 예외 처리"""
    return {
        "success": False,
        "error": {
            "status_code": exc.status_code,
            "message": exc.detail,
            "type": "HTTPException"
        }
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """일반 예외 처리"""
    logger.error(f"처리되지 않은 예외: {exc}", exc_info=True)
    return {
        "success": False,
        "error": {
            "type": "InternalServerError",
            "message": "예상하지 못한 오류가 발생했습니다."
        }
    }


# 애플리케이션 이벤트
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작시"""
    logger.info("="*50)
    logger.info("속마음 말하기 API 서버 시작")
    logger.info(f"환경: {settings.environment}")
    logger.info(f"로그 레벨: {settings.log_level}")
    logger.info(f"API 주소: http://{settings.api_host}:{settings.api_port}")
    logger.info(f"문서: http://{settings.api_host}:{settings.api_port}/docs")
    logger.info("="*50)


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료시"""
    logger.info("="*50)
    logger.info("속마음 말하기 API 서버 종료")
    logger.info("="*50)


# 서버 실행
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )