import os
import json
import logging
from typing import Optional, Dict, Any
from functools import lru_cache
from datetime import datetime

import requests
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """애플리케이션 설정을 관리하는 클래스"""
    
    # Gemini API 설정
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = "gemini-2.5-flash-preview-09-2025"
    gemini_api_url: str = "https://generativelanguage.googleapis.com/v1beta/models"
    
    # 생성 설정
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 40
    max_output_tokens: int = 1024
    
    # RAG 설정
    max_retrieval_results: int = 5
    similarity_threshold: float = 0.5
    chunk_size: int = 500
    chunk_overlap: int = 100
    
    # 응용 설정
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # API 서버 설정
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    
    # 타임아웃 설정 (초 단위)
    request_timeout: int = 30
    max_retries: int = 3
    
    class Config:
        case_sensitive = False
        env_file = ".env"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """싱글톤 패턴으로 설정 객체 반환"""
    return Settings()


class APIClient:
    """Gemini API 클라이언트"""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.api_key = self.settings.gemini_api_key
        self.model = self.settings.gemini_model
        self.base_url = self.settings.gemini_api_url
        self.logger = logging.getLogger(__name__)
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
    
    @property
    def api_endpoint(self) -> str:
        """API 엔드포인트 URL 생성"""
        return f"{self.base_url}/{self.model}:generateContent"
    
    def call_gemini(
        self, 
        prompt: str, 
        system_instruction: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: str = "application/json"
    ) -> Dict[str, Any]:
        """
        Gemini API를 호출하여 구조화된 JSON 데이터를 반환합니다.
        
        Args:
            prompt: 사용자 메시지
            system_instruction: 시스템 지시사항
            temperature: 창의성 수준 (0.0-1.0)
            max_tokens: 최대 출력 토큰 수
            response_format: 응답 형식
            
        Returns:
            API 응답 JSON 데이터
            
        Raises:
            Exception: API 호출 실패 시
        """
        params = {"key": self.api_key}
        
        # 생성 설정
        generation_config = {
            "responseMimeType": response_format,
            "temperature": temperature or self.settings.temperature,
            "topP": self.settings.top_p,
            "topK": self.settings.top_k,
            "maxOutputTokens": max_tokens or self.settings.max_output_tokens,
        }
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": generation_config
        }
        
        self.logger.debug(f"API 요청: {self.api_endpoint}")
        self.logger.debug(f"요청 페이로드: {json.dumps(payload, ensure_ascii=False)}")
        
        try:
            response = requests.post(
                self.api_endpoint,
                params=params,
                json=payload,
                timeout=self.settings.request_timeout
            )
            response.raise_for_status()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API 요청 실패: {e}")
            raise Exception(f"API 호출 실패: {str(e)}")
        
        try:
            result = response.json()
            
            # 에러 응답 확인
            if "error" in result:
                error_msg = result["error"].get("message", "알 수 없는 에러")
                self.logger.error(f"API 에러: {error_msg}")
                raise Exception(f"API 에러: {error_msg}")
            
            # 응답 구조 검증
            if not result.get("candidates") or len(result["candidates"]) == 0:
                raise Exception("API 응답에 candidates가 없습니다.")
            
            candidate = result["candidates"][0]
            
            # 완료 이유 확인
            finish_reason = candidate.get("finishReason", "STOP")
            if finish_reason == "MAX_TOKENS":
                self.logger.warning("응답이 MAX_TOKENS로 도달했습니다.")
            
            # 응답 텍스트 추출
            if not candidate.get("content") or not candidate["content"].get("parts"):
                raise Exception("API 응답에서 텍스트를 추출할 수 없습니다.")
            
            content_text = candidate["content"]["parts"][0].get("text", "")
            
            if not content_text:
                raise Exception("API 응답 텍스트가 비어있습니다.")
            
            self.logger.debug(f"API 응답: {content_text}")
            
            # JSON 파싱
            try:
                return json.loads(content_text)
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON 파싱 실패: {e}")
                self.logger.error(f"응답 텍스트: {content_text}")
                raise Exception(f"JSON 파싱 실패: {str(e)}")
        
        except json.JSONDecodeError as e:
            self.logger.error(f"응답 JSON 파싱 실패: {e}")
            raise Exception(f"응답 JSON 파싱 실패: {str(e)}")
    
    def call_gemini_text(
        self,
        prompt: str,
        system_instruction: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Gemini API를 호출하여 텍스트 응답을 반환합니다.
        
        Args:
            prompt: 사용자 메시지
            system_instruction: 시스템 지시사항
            temperature: 창의성 수준
            max_tokens: 최대 출력 토큰 수
            
        Returns:
            API 응답 텍스트
        """
        params = {"key": self.api_key}
        
        generation_config = {
            "temperature": temperature or self.settings.temperature,
            "topP": self.settings.top_p,
            "topK": self.settings.top_k,
            "maxOutputTokens": max_tokens or self.settings.max_output_tokens,
        }
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": generation_config
        }
        
        try:
            response = requests.post(
                self.api_endpoint,
                params=params,
                json=payload,
                timeout=self.settings.request_timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "error" in result:
                error_msg = result["error"].get("message", "Unknown error")
                raise Exception(f"API 에러: {error_msg}")
            
            candidate = result["candidates"][0]
            return candidate["content"]["parts"][0]["text"].strip()
        
        except Exception as e:
            self.logger.error(f"텍스트 응답 호출 실패: {e}")
            raise


# 전역 인스턴스 생성
settings = get_settings()
api_client = APIClient(settings)