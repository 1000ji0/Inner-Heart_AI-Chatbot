"""
검색 에이전트 (Retriever) - RAG 기반 전략 검색
"""

import logging
import json
from typing import Dict, Any, List, Optional

from config import api_client
from rag_indexer import get_rag_indexer
from utils import PromptBuilder, ErrorHandler

logger = logging.getLogger(__name__)


class RetrieverAgent:
    """
    분석된 감정을 바탕으로 '지식 베이스(knowledge 폴더)'에서 
    최적의 공감 전략을 찾아오는 검색 전문가 (RAG 기반)
    
    주요 기능:
    1. RAG 인덱싱을 통한 감정×관계×말투 문서 검색
    2. 심리학적 공감 전략 추출
    3. 구조화된 답변 뼈대 제공
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_client = api_client
        self.rag_indexer = get_rag_indexer()
        
        # RAG 통계 로깅
        stats = self.rag_indexer.get_statistics()
        self.logger.info(f"RAG 인덱서 초기화: {stats['total_documents']}개 문서 로드")
    
    def retrieve_strategy(
        self,
        analysis_data: Dict[str, Any],
        persona: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        감정 분석 결과를 기반으로 공감 전략 검색
        
        Args:
            analysis_data: Analyst에서 제공한 감정 분석 결과
            persona: 사용자의 페르소나 설정
            
        Returns:
            검색된 공감 전략 및 응답 구조
        """
        self.logger.info(f"전략 검색 시작: {analysis_data.get('category')}")
        
        try:
            # 1. RAG에서 관련 문서 검색
            relevant_docs = self.rag_indexer.search_by_analysis(
                analysis_data,
                persona,
                max_results=3
            )
            
            if not relevant_docs:
                self.logger.warning("관련 문서를 찾을 수 없음, 기본 전략 사용")
                relevant_docs = []
            
            self.logger.info(f"검색된 문서: {len(relevant_docs)}개")
            
            # 2. LLM을 통한 전략 생성 (검색된 문서 + 분석 결과)
            enhanced_strategy = self._generate_strategy_with_rag(
                analysis_data,
                persona,
                relevant_docs
            )
            
            self.logger.info(f"전략 생성 완료: {enhanced_strategy.get('strategy_name')}")
            
            return {
                "success": True,
                "strategy": enhanced_strategy,
                "rag_sources": [
                    {
                        "title": doc.section_title,
                        "source": doc.source_file,
                        "metadata": doc.metadata
                    }
                    for doc in relevant_docs
                ]
            }
        
        except Exception as e:
            self.logger.error(f"전략 검색 중 오류: {e}")
            return ErrorHandler.handle_api_error(e, "RetrieverAgent.retrieve_strategy")
    
    def _generate_strategy_with_rag(
        self,
        analysis_data: Dict[str, Any],
        persona: Dict[str, Any],
        rag_documents: List[Any]
    ) -> Dict[str, Any]:
        """RAG 문서를 활용한 전략 생성"""
        
        # RAG 문서 내용 통합
        rag_context = ""
        if rag_documents:
            rag_context = "\n\n---RAG 지식 베이스 참고---\n\n"
            for doc in rag_documents:
                rag_context += f"## {doc.section_title}\n"
                rag_context += f"출처: {doc.source_file}\n"
                rag_context += doc.content[:1000] + "\n\n"  # 첫 1000자 포함
        
        # 전략 생성 프롬프트
        generation_prompt = f"""다음 정보를 기반으로 구체적인 공감 전략을 생성하세요.

[감정 분석 결과]
- 감정: {analysis_data.get('category', '')}
- 상황: {analysis_data.get('situation_type', '')}
- 강도: {analysis_data.get('sentiment_score', 5)}/10
- 요약: {analysis_data.get('summary', '')}

[페르소나 설정]
- 관계: {persona.get('relationship', '')}
- 말투: {persona.get('tone', '')}
- 반응 강도: {persona.get('intensity', '')}

{rag_context}

위 지식 베이스를 참고하여, 다음을 포함하는 공감 전략을 JSON 형식으로 생성하세요:
1. 전략명
2. 구체적인 공감 접근법 (2-3문장)
3. 답변 구조 (단계별)
4. 실제 사용 가능한 예시 문장들
5. 해야 할 것들
6. 하지 말아야 할 것들
7. 말투 조정 지침

반드시 JSON 형식으로만 응답하세요."""

        system_instruction = """당신은 심리 치료사 겸 공감 전문가입니다.
RAG 지식 베이스의 모범 사례를 활용하여 
사용자의 감정과 관계에 맞는 최적의 공감 전략을 생성하세요.

생성된 전략은 다음 조건을 만족해야 합니다:
1. 감정의 정당성을 먼저 인정
2. 제시된 말투와 강도를 정확히 반영
3. 관계의 특성을 충분히 고려
4. 실제 사용 가능하고 자연스러운 표현"""

        try:
            response = self.api_client.call_gemini(
                prompt=generation_prompt,
                system_instruction=system_instruction,
                temperature=0.7
            )
            
            return response
        
        except Exception as e:
            self.logger.error(f"LLM 기반 전략 생성 실패: {e}")
            return self._get_default_strategy(analysis_data)
    
    def _get_default_strategy(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """기본 전략 제공"""
        category = analysis_data.get("category", "일반적인 문제")
        sentiment_score = analysis_data.get("sentiment_score", 5)
        
        # 강도에 따른 기본 구조
        if sentiment_score >= 8:
            structure = "[감정 즉시 인정] → [상황 정당화] → [함께하기] → [심리 조언]"
            tone_adjustment = "더 따뜻하고 깊은 공감"
        elif sentiment_score >= 5:
            structure = "[감정 인정] → [상황 이해] → [격려] → [전망"
            tone_adjustment = "중간 정도의 따뜻한 공감"
        else:
            structure = "[감정 수용] → [긍정적 해석] → [격려] → [제안]"
            tone_adjustment = "밝고 희망적인 톤"
        
        return {
            "strategy_name": f"{category} 기본 공감 전략 (RAG 기반)",
            "strategy": f"사용자의 {category} 감정을 지식 베이스의 모범 사례를 참고하여 깊이 있게 이해하고 함께하세요.",
            "structure": structure,
            "examples": [
                "그 상황이라면 당연히 그렇게 느껴야 해.",
                "너에게 무슨 일이 있었나? 응, 내가 여기 있으니 천천히 말해.",
                "충분히 잘 버텨냈어. 이제 조금씩 나아질 거야."
            ],
            "do_s": [
                "사용자의 감정 검증하기",
                "구체적인 경청",
                "공감적 반응 보내기"
            ],
            "dont_s": [
                "상대방 변호",
                "감정 축소",
                "즉각적인 해결책 제시"
            ],
            "tone_adjustment": tone_adjustment
        }
    
    def get_rag_statistics(self) -> Dict[str, Any]:
        """RAG 인덱서 통계 조회"""
        return self.rag_indexer.get_statistics()
    
    def search_direct(
        self,
        emotion: str = None,
        relationship: str = None,
        tone: str = None,
        query: str = None
    ) -> List[Dict[str, Any]]:
        """
        직접 검색 (디버깅 용)
        
        Args:
            emotion: 감정
            relationship: 관계
            tone: 말투
            query: 텍스트 검색 쿼리
            
        Returns:
            검색 결과
        """
        docs = self.rag_indexer.search(
            emotion=emotion,
            relationship=relationship,
            tone=tone,
            query=query,
            max_results=5
        )
        
        return [
            {
                "title": doc.section_title,
                "source": doc.source_file,
                "metadata": doc.metadata,
                "preview": doc.content[:200] + "..."
            }
            for doc in docs
        ]


# 전역 인스턴스
retriever_agent = RetrieverAgent()
