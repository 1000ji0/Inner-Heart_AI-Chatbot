"""
RAG 인덱싱 시스템 - 지식 베이스 문서 저장소 및 검색 엔진
"""

import os
import json
import logging
import re
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class RAGDocument:
    """RAG 문서 청크"""
    doc_id: str
    chunk_id: str
    content: str
    source_file: str
    metadata: Dict[str, Any]
    section_title: str


class KnowledgeBaseParser:
    """지식 베이스 파일 파싱"""
    
    @staticmethod
    def parse_emotion_responses(content: str) -> List[RAGDocument]:
        """emotion_responses.md 파싱"""
        documents = []
        
        # 감정 카테고리별로 섹션 나누기
        emotion_pattern = r'^# (\d+)\. (.*?) \((.*?)\)'
        relationship_pattern = r'^### (\d+\-\d+)\. (.*?) 관계'
        
        current_emotion = None
        current_emotion_eng = None
        current_relationship = None
        current_section = []
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            emotion_match = re.match(emotion_pattern, line)
            relationship_match = re.match(relationship_pattern, line)
            
            if emotion_match:
                # 이전 섹션 저장
                if current_section:
                    doc = RAGDocument(
                        doc_id=f"emotion_{current_emotion}_{current_relationship}".replace(' ', '_'),
                        chunk_id=f"emotion_{current_emotion}_{current_relationship}_{len(documents)}",
                        content='\n'.join(current_section),
                        source_file="emotion_responses.md",
                        metadata={
                            "type": "emotion_response",
                            "emotion": current_emotion,
                            "emotion_eng": current_emotion_eng,
                            "relationship": current_relationship
                        },
                        section_title=f"{current_emotion} × {current_relationship}"
                    )
                    documents.append(doc)
                    current_section = []
                
                current_emotion = emotion_match.group(2)
                current_emotion_eng = emotion_match.group(3)
            
            elif relationship_match:
                # 이전 섹션 저장
                if current_section:
                    doc = RAGDocument(
                        doc_id=f"emotion_{current_emotion}_{current_relationship}".replace(' ', '_'),
                        chunk_id=f"emotion_{current_emotion}_{current_relationship}_{len(documents)}",
                        content='\n'.join(current_section),
                        source_file="emotion_responses.md",
                        metadata={
                            "type": "emotion_response",
                            "emotion": current_emotion,
                            "emotion_eng": current_emotion_eng,
                            "relationship": current_relationship
                        },
                        section_title=f"{current_emotion} × {current_relationship}"
                    )
                    documents.append(doc)
                    current_section = []
                
                current_relationship = relationship_match.group(2).strip()
            
            current_section.append(line)
        
        # 마지막 섹션 저장
        if current_section and current_emotion and current_relationship:
            doc = RAGDocument(
                doc_id=f"emotion_{current_emotion}_{current_relationship}".replace(' ', '_'),
                chunk_id=f"emotion_{current_emotion}_{current_relationship}_{len(documents)}",
                content='\n'.join(current_section),
                source_file="emotion_responses.md",
                metadata={
                    "type": "emotion_response",
                    "emotion": current_emotion,
                    "emotion_eng": current_emotion_eng,
                    "relationship": current_relationship
                },
                section_title=f"{current_emotion} × {current_relationship}"
            )
            documents.append(doc)
        
        return documents
    
    @staticmethod
    def parse_relationship_scenarios(content: str) -> List[RAGDocument]:
        """relationship_scenarios.md 파싱"""
        documents = []
        
        # PART 분류 패턴
        part_pattern = r'^# PART \d+\. (.*?) 시나리오'
        scenario_pattern = r'^### 시나리오 ([A-Z]+-\d+)\. (.*?)$'
        
        current_part = None
        current_scenario = None
        current_section = []
        
        lines = content.split('\n')
        
        for line in lines:
            part_match = re.match(part_pattern, line)
            scenario_match = re.match(scenario_pattern, line)
            
            if part_match:
                if current_section and current_scenario:
                    doc = RAGDocument(
                        doc_id=f"scenario_{current_scenario}",
                        chunk_id=f"scenario_{current_scenario}_{len(documents)}",
                        content='\n'.join(current_section),
                        source_file="relationship_scenarios.md",
                        metadata={
                            "type": "relationship_scenario",
                            "part": current_part,
                            "scenario_id": current_scenario
                        },
                        section_title=f"{current_part} - {current_scenario}"
                    )
                    documents.append(doc)
                    current_section = []
                
                current_part = part_match.group(1)
            
            elif scenario_match:
                if current_section and current_scenario:
                    doc = RAGDocument(
                        doc_id=f"scenario_{current_scenario}",
                        chunk_id=f"scenario_{current_scenario}_{len(documents)}",
                        content='\n'.join(current_section),
                        source_file="relationship_scenarios.md",
                        metadata={
                            "type": "relationship_scenario",
                            "part": current_part,
                            "scenario_id": current_scenario
                        },
                        section_title=f"{current_part} - {current_scenario}"
                    )
                    documents.append(doc)
                    current_section = []
                
                current_scenario = scenario_match.group(1)
            
            current_section.append(line)
        
        # 마지막 섹션 저장
        if current_section and current_scenario:
            doc = RAGDocument(
                doc_id=f"scenario_{current_scenario}",
                chunk_id=f"scenario_{current_scenario}_{len(documents)}",
                content='\n'.join(current_section),
                source_file="relationship_scenarios.md",
                metadata={
                    "type": "relationship_scenario",
                    "part": current_part,
                    "scenario_id": current_scenario
                },
                section_title=f"{current_part} - {current_scenario}"
            )
            documents.append(doc)
        
        return documents
    
    @staticmethod
    def parse_tone_style_guide(content: str) -> List[RAGDocument]:
        """tone_style_guide.md 파싱"""
        documents = []
        
        # 말투 섹션 패턴
        tone_pattern = r'^## (\d+\-\d+)\. (.*?) \((.*?)\)'
        
        current_tone = None
        current_tone_eng = None
        current_section = []
        
        lines = content.split('\n')
        
        for line in lines:
            tone_match = re.match(tone_pattern, line)
            
            if tone_match:
                if current_section and current_tone:
                    doc = RAGDocument(
                        doc_id=f"tone_{current_tone}",
                        chunk_id=f"tone_{current_tone}_{len(documents)}",
                        content='\n'.join(current_section),
                        source_file="tone_style_guide.md",
                        metadata={
                            "type": "tone_style",
                            "tone": current_tone,
                            "tone_eng": current_tone_eng
                        },
                        section_title=f"말투: {current_tone}"
                    )
                    documents.append(doc)
                    current_section = []
                
                current_tone = tone_match.group(2)
                current_tone_eng = tone_match.group(3)
            
            current_section.append(line)
        
        # 마지막 섹션 저장
        if current_section and current_tone:
            doc = RAGDocument(
                doc_id=f"tone_{current_tone}",
                chunk_id=f"tone_{current_tone}_{len(documents)}",
                content='\n'.join(current_section),
                source_file="tone_style_guide.md",
                metadata={
                    "type": "tone_style",
                    "tone": current_tone,
                    "tone_eng": current_tone_eng
                },
                section_title=f"말투: {current_tone}"
            )
            documents.append(doc)
        
        return documents


class RAGIndexer:
    """RAG 인덱싱 엔진"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.documents: List[RAGDocument] = []
        self.index: Dict[str, List[int]] = defaultdict(list)  # 메타데이터 인덱스
        self.parser = KnowledgeBaseParser()
    
    def load_knowledge_base(self, knowledge_dir: str = None) -> int:
        """지식 베이스 폴더 로드"""
        if not knowledge_dir:
            # 상대 경로에서 지식 베이스 찾기
            current_dir = Path(__file__).parent
            knowledge_dir = current_dir / ".." / ".." / "knowledge"
        
        knowledge_path = Path(knowledge_dir)
        
        if not knowledge_path.exists():
            self.logger.warning(f"지식 베이스 폴더를 찾을 수 없습니다: {knowledge_path}")
            return 0
        
        total_loaded = 0
        
        # 각 파일 로드
        try:
            # emotion_responses.md
            emotion_file = knowledge_path / "emotion_responses.md"
            if emotion_file.exists():
                with open(emotion_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    docs = self.parser.parse_emotion_responses(content)
                    self.documents.extend(docs)
                    total_loaded += len(docs)
                    self.logger.info(f"emotion_responses.md: {len(docs)}개 청크 로드")
            
            # relationship_scenarios.md
            scenario_file = knowledge_path / "relationship_scenarios.md"
            if scenario_file.exists():
                with open(scenario_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    docs = self.parser.parse_relationship_scenarios(content)
                    self.documents.extend(docs)
                    total_loaded += len(docs)
                    self.logger.info(f"relationship_scenarios.md: {len(docs)}개 청크 로드")
            
            # tone_style_guide.md
            tone_file = knowledge_path / "tone_style_guide.md"
            if tone_file.exists():
                with open(tone_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    docs = self.parser.parse_tone_style_guide(content)
                    self.documents.extend(docs)
                    total_loaded += len(docs)
                    self.logger.info(f"tone_style_guide.md: {len(docs)}개 청크 로드")
        
        except Exception as e:
            self.logger.error(f"지식 베이스 로드 중 오류: {e}")
            return total_loaded
        
        # 메타데이터 인덱싱
        self._build_index()
        
        self.logger.info(f"총 {total_loaded}개 문서 청크 로드 완료")
        return total_loaded
    
    def _build_index(self):
        """메타데이터 인덱싱"""
        for idx, doc in enumerate(self.documents):
            # 감정별 인덱싱
            if "emotion" in doc.metadata:
                emotion = doc.metadata["emotion"]
                self.index[f"emotion:{emotion}"].append(idx)
            
            # 관계별 인덱싱
            if "relationship" in doc.metadata:
                relationship = doc.metadata["relationship"]
                self.index[f"relationship:{relationship}"].append(idx)
            
            # 말투별 인덱싱
            if "tone" in doc.metadata:
                tone = doc.metadata["tone"]
                self.index[f"tone:{tone}"].append(idx)
            
            # 문서 타입별 인덱싱
            doc_type = doc.metadata.get("type", "unknown")
            self.index[f"type:{doc_type}"].append(idx)
    
    def search(
        self,
        emotion: str = None,
        relationship: str = None,
        tone: str = None,
        query: str = None,
        max_results: int = 5
    ) -> List[RAGDocument]:
        """
        메타데이터 기반 검색
        
        Args:
            emotion: 감정 카테고리
            relationship: 관계 유형
            tone: 말투
            query: 텍스트 검색 쿼리
            max_results: 최대 결과 수
            
        Returns:
            검색된 RAGDocument 리스트
        """
        results = []
        candidate_indices = set(range(len(self.documents)))
        
        # 메타데이터 필터링
        if emotion:
            filtered = set(self.index.get(f"emotion:{emotion}", []))
            candidate_indices &= filtered
        
        if relationship:
            filtered = set(self.index.get(f"relationship:{relationship}", []))
            candidate_indices &= filtered
        
        if tone:
            filtered = set(self.index.get(f"tone:{tone}", []))
            candidate_indices &= filtered
        
        candidates = [self.documents[i] for i in candidate_indices]
        
        # 텍스트 검색 (간단한 키워드 매칭)
        if query:
            query_lower = query.lower()
            scored_candidates = []
            
            for doc in candidates:
                content_lower = doc.content.lower()
                title_lower = doc.section_title.lower()
                
                # 섹션 제목에 일치하면 높은 점수
                if query_lower in title_lower:
                    score = 3
                # 콘텐츠에 일치하면 점수
                elif query_lower in content_lower:
                    score = 1
                else:
                    score = 0
                
                if score > 0:
                    scored_candidates.append((score, doc))
            
            # 점수로 정렬
            scored_candidates.sort(key=lambda x: x[0], reverse=True)
            results = [doc for _, doc in scored_candidates[:max_results]]
        else:
            results = candidates[:max_results]
        
        self.logger.debug(f"검색 결과: {len(results)}개 문서 반환")
        return results
    
    def search_by_analysis(
        self,
        analysis_data: Dict[str, Any],
        persona: Dict[str, Any],
        max_results: int = 5
    ) -> List[RAGDocument]:
        """
        감정 분석 결과로 검색
        
        Args:
            analysis_data: Analyst의 분석 결과
            persona: 사용자의 페르소나 설정
            max_results: 최대 결과 수
            
        Returns:
            관련 문서 리스트
        """
        return self.search(
            emotion=analysis_data.get("category"),
            relationship=persona.get("relationship"),
            tone=persona.get("tone"),
            max_results=max_results
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """인덱싱 통계"""
        stats = {
            "total_documents": len(self.documents),
            "by_type": {},
            "by_emotion": {},
            "by_relationship": {},
            "by_tone": {},
            "by_source": {}
        }
        
        for doc in self.documents:
            # 타입별
            doc_type = doc.metadata.get("type", "unknown")
            stats["by_type"][doc_type] = stats["by_type"].get(doc_type, 0) + 1
            
            # 감정별
            if "emotion" in doc.metadata:
                emotion = doc.metadata["emotion"]
                stats["by_emotion"][emotion] = stats["by_emotion"].get(emotion, 0) + 1
            
            # 관계별
            if "relationship" in doc.metadata:
                relationship = doc.metadata["relationship"]
                stats["by_relationship"][relationship] = stats["by_relationship"].get(relationship, 0) + 1
            
            # 말투별
            if "tone" in doc.metadata:
                tone = doc.metadata["tone"]
                stats["by_tone"][tone] = stats["by_tone"].get(tone, 0) + 1
            
            # 파일별
            source = doc.source_file
            stats["by_source"][source] = stats["by_source"].get(source, 0) + 1
        
        return stats


# 전역 인덱서 인스턴스
rag_indexer = None


def get_rag_indexer(knowledge_dir: str = None) -> RAGIndexer:
    """싱글톤 인덱서 반환"""
    global rag_indexer
    
    if rag_indexer is None:
        rag_indexer = RAGIndexer()
        rag_indexer.load_knowledge_base(knowledge_dir)
    
    return rag_indexer
