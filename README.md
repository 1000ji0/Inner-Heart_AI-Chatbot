# 💭 Inner-Heart-AI-Chat
### Gemini 2.5 Flash 기반 멀티 에이전트 공감 채팅 웹앱

> 사용자의 감정을 분석하고, RAG 지식베이스에서 공감 전략을 인출하여  
> NVC(비폭력대화) 이론 기반의 맞춤 응답을 생성하는 Google Apps Script 웹앱

[![Google Apps Script](https://img.shields.io/badge/Google_Apps_Script-4285F4?style=flat&logo=google&logoColor=white)](https://script.google.com)
[![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-8E75B2?style=flat&logo=google&logoColor=white)](https://ai.google.dev)
[![RAG](https://img.shields.io/badge/RAG-Retrieval_Augmented_Generation-orange?style=flat)](https://en.wikipedia.org/wiki/Prompt_engineering)
[![NVC](https://img.shields.io/badge/NVC-Nonviolent_Communication-green?style=flat)](https://en.wikipedia.org/wiki/Nonviolent_Communication)

🔗 **서비스 URL**: [바로 사용해보기](https://script.google.com/macros/s/AKfycbxxGrG9O_9TtiFKg8NBeEfFoo6UIwMwXM2XS0nk1kAxHWoJzsx3xEEUYCpo6GA0sag/exec)

---

## 📌 프로젝트 소개

속마음 말하기 앱은 감정적 고민이 있는 사용자가 AI와 자연스럽게 대화하며 감정을 해소할 수 있도록 설계된 웹앱입니다.

단순한 챗봇이 아닌 **멀티 에이전트 파이프라인**으로 구성되어 있으며, 사용자의 발화에서 감정을 분석하고, RAG 문서에서 공감 전략을 검색하고, 페르소나 설정에 맞는 최종 응답을 생성하는 3단계 구조를 갖습니다.

---

## 🤖 멀티 에이전트 아키텍처

```
사용자 입력
    │
    ▼
┌─────────────────────────────────────────────┐
│              Orchestrator (code.gs)          │
│         에이전트 실행 순서 및 폴백 관리         │
└──────────┬──────────────────────────────────┘
           │
    ┌──────▼──────┐
    │  Analyst    │  ← Gemini API 호출 #1
    │   Agent     │     감정 / 관계 / 강도 / 키워드 추출
    └──────┬──────┘     JSON 구조화 응답
           │
    ┌──────▼──────┐
    │     RAG     │  ← Google Drive 문서 로딩 (CacheService)
    │  Retriever  │     ### 헤더 기준 섹션 추출
    └──────┬──────┘     공감 전략 / 모범 예시 / 금지 표현 인출
           │
    ┌──────▼──────┐
    │  Listener   │  ← Gemini API 호출 #2
    │   Agent     │     페르소나 + RAG 컨텍스트 + NVC 구조 주입
    └──────┬──────┘     최종 공감 응답 생성
           │
    ┌──────▼──────┐
    │  사용자 응답  │
    └─────────────┘
```

### 에이전트별 역할

| 에이전트 | 파일 | 역할 |
|---------|------|------|
| **Analyst Agent** | `gs/analyst_agent.gs` | 사용자 발화 → 감정/관계/강도/키워드 JSON 추출 |
| **RAG Retriever** | `gs/rag_retriever.gs` | 분석 결과 태그로 Drive 문서에서 관련 섹션 인출 |
| **Listener Agent** | `gs/listener_agent.gs` | 페르소나 + RAG 컨텍스트 조합 → 최종 응답 생성 |
| **Orchestrator** | `gs/code.gs` | 에이전트 파이프라인 연결 및 폴백 처리 |

---

## 🗂️ RAG 지식베이스 구조

Google Drive에 저장된 6개의 Markdown 문서를 지식베이스로 활용합니다.

| 문서 | 내용 |
|------|------|
| `01_emotion_responses.md` | 감정 6개 × 관계 4개 × 강도 3단계 모범 응답 (72개 조합) |
| `02_relationship_scenarios.md` | 연인 / 직장상사 / 부모 관계 심화 시나리오 (18개) |
| `03_tone_style_guide.md` | 5가지 말투(다정/무뚝뚝/차가움/유머러스/보통) 변환 가이드 |
| `04_nvc_theory.md` | NVC 비폭력대화 이론 및 공감적 경청 기법 |
| `05_nvc_violation_pattern.md` | 역효과 응답 패턴 및 금지 표현 목록 |
| `06_nvc_vocabulary_guide.md` | 감정/욕구 어휘 사전 |

RAG 인출 방식은 `###` 헤더 기준 섹션 분리 + 태그 키워드 매칭으로 구현되어 있으며,  
`CacheService`로 6시간 캐싱하여 Drive 접근을 최소화합니다.

---

## 🛠️ 기술 스택

| 구분 | 기술 |
|------|------|
| 백엔드 | Google Apps Script (GAS) |
| AI | Google Gemini 2.5 Flash REST API |
| 프론트엔드 | HTML5 / CSS3 / Vanilla JS (카카오톡 스타일 UI) |
| 저장소 | Google Sheets + PropertiesService |
| RAG 문서 | Google Drive + CacheService |
| 배포 | GAS 웹앱 (`doGet` / `doPost`) |
| 개발 도구 | clasp (로컬 ↔ GAS 동기화) |

---

## 📁 프로젝트 구조

```
Inner-Heart-AI-Chat/
├── appsscript.json          # Apps Script 설정 (oauthScopes 포함)
├── index.html               # 프론트엔드 채팅 UI
├── gs/
│   ├── code.gs              # Orchestrator + 웹앱 진입점
│   ├── analyst_agent.gs     # Analyst Agent (감정 분석)
│   ├── rag_loader.gs        # Drive RAG 문서 로더 + CacheService
│   ├── rag_retriever.gs     # RAG 섹션 추출기 (태그 매칭)
│   └── listener_agent.gs    # Listener Agent (최종 응답 생성)
├── knowledge/               # RAG 원문 문서 소스 (6개 .md)
├── PRD.md                   # 제품 요구사항 문서
├── TRD.md                   # 기술 요구사항 문서
└── README.md
```

---

## ⚙️ 설치 및 설정

### 1. clasp 설치 및 배포

```bash
npm install -g @google/clasp
clasp login
clasp clone {YOUR_SCRIPT_ID}
clasp push
```

### 2. 스크립트 속성 등록

GAS 편집기 → ⚙️ 프로젝트 설정 → 스크립트 속성에 아래 값을 등록합니다.

| 키 | 설명 |
|----|------|
| `GEMINI_API_KEY` | Google AI Studio에서 발급한 API 키 |
| `SHEET_ID` | 채팅 기록 저장용 Google Sheets ID |
| `RAG_EMOTION` | `01_emotion_responses.md` 파일 ID |
| `RAG_SCENARIOS` | `02_relationship_scenarios.md` 파일 ID |
| `RAG_TONE` | `03_tone_style_guide.md` 파일 ID |
| `RAG_NVC` | `04_nvc_theory.md` 파일 ID |
| `RAG_VIOLATION` | `05_nvc_violation_pattern.md` 파일 ID |
| `RAG_VOCABULARY` | `06_nvc_vocabulary_guide.md` 파일 ID |

### 3. RAG 파일 ID 등록

Google Drive에 `knowledge/` 폴더의 `.md` 파일 6개를 업로드한 뒤,  
`gs/code.gs`의 `initRAGSettings()` 함수에 파일 ID를 입력하고 1회 실행합니다.

### 4. 웹앱 배포

GAS 편집기 → 배포 → 새 배포 → 웹앱으로 배포

---

## 💬 사용 방법

1. 웹앱 URL 접속
2. 페르소나 설정: 대상 관계 / 감정 / 원하는 반응 / 반응 강도 / 말투 선택
3. 채팅 시작: 메시지 입력 → Analyst → RAG → Listener 파이프라인으로 응답 생성
4. 모든 대화는 Google Sheets에 자동 저장

---

## 🔒 보안

- API 키 및 파일 ID는 모두 `PropertiesService`에 저장 (코드에 하드코딩 없음)
- `.env`, `.clasp.json`은 `.gitignore`로 Git 제외
- 사용자 데이터는 Google Sheets에 저장되며 외부 서버 전송 없음

---

## 📌 개발 노트

- GAS 환경 특성상 `import` / `require` 없이 `.gs` 파일만으로 동작
- 외부 라이브러리 없이 Google 기본 서비스(DriveApp, CacheService, SpreadsheetApp 등)만 사용
- LangGraph 미사용, 에이전트 파이프라인은 함수 체인으로 직접 구현
- Analyst / Retriever 실패 시 기존 `callGeminiAPIWithHistory()`로 자동 폴백

---

## 📄 라이선스

별도 지정 전까지 비공개 / 내부 사용 기준으로 관리합니다.