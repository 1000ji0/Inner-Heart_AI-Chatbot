# Inner-Heart-AI-Chat TRD

## 1. 기술 개요

이 프로젝트는 Google Apps Script 기반 웹앱으로, Google Gemini 2.5 Flash API를 호출해 공감형 응답을 생성한다.

## 2. 실제 배포 구조

```text
브라우저
  ↓
index.html
  ↓
gs/code.gs
  ├── 페르소나 저장
  ├── 채팅 히스토리 관리
  ├── Analyst Agent 호출
  ├── RAG Retriever 호출
  ├── Listener Agent 호출
  └── Google Sheets 저장
        ↓
Google Drive RAG 문서 + CacheService
Google Sheets + PropertiesService
Gemini 2.5 Flash REST API
```

## 3. 파일 구조

```text
Inner-Heart-AI-Chat/
├── appsscript.json
├── index.html
├── gs/
│   ├── code.gs
│   ├── rag_loader.gs
│   ├── analyst_agent.gs
│   ├── rag_retriever.gs
│   └── listener_agent.gs
├── knowledge/
├── README.md
├── PRD.md
├── TRD.md
├── .env.example
└── .gitignore
```

## 4. 서비스 구성

### 4.1 Apps Script
- 웹앱 진입점: `doGet()`
- 요청 처리: `doPost(e)`
- 메인 채팅 처리: `sendChatMessage()` / `handleChatMessage()`

### 4.2 RAG 로더
- `DriveApp.getFileById(fileId)`로 문서를 읽는다.
- `CacheService.getScriptCache()`를 사용해 6시간 캐싱한다.
- 파일 ID가 없으면 빈 문자열을 반환한다.

### 4.3 Analyst Agent
- Gemini REST API를 호출한다.
- 응답 형식은 JSON으로 강제한다.
- 파싱 실패 시 기본값을 반환한다.

### 4.4 Retriever
- `###` 헤더를 기준으로 문서를 분할한다.
- 분석 결과의 emotion, relationship, intensity, keywords를 기준으로 매칭한다.
- 반환 텍스트는 2000자로 제한한다.

### 4.5 Listener
- 페르소나와 RAG 컨텍스트를 합쳐 시스템 프롬프트를 만든다.
- RAG가 비어 있어도 기본 공감 응답을 생성한다.

## 5. 저장소 설계

### 5.1 PropertiesService
- `persona_{sessionId}`: 페르소나 JSON
- `chat_{sessionId}`: 대화 히스토리 JSON 배열
- `GEMINI_API_KEY`: Gemini API 키
- `SHEET_ID`: Google Sheets ID
- `RAG_*`: Drive 문서 ID

### 5.2 Google Sheets
채팅 기록 시트는 대화 로그와 분석 결과를 저장한다.

권장 컬럼:
- 세션ID
- 요청일시
- 대상관계
- 내감정
- 원하는반응
- 반응강도
- 리스너말투
- 욕설허용
- 사용자메시지
- AI응답
- 분석감정
- 분석키워드
- 처리상태

## 6. API 호출 방식

### 6.1 Analyst Request
- 엔드포인트: `https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent`
- 요청 방식: `UrlFetchApp.fetch()`
- `systemInstruction`으로 JSON-only 응답을 강제한다.

### 6.2 Listener Request
- 동일 모델을 사용한다.
- 시스템 프롬프트에는 페르소나, RAG 전략, 금지 표현, 말투 가이드를 합친다.

## 7. 에러 처리

### 7.1 Analyst 실패
- JSON 파싱 실패 또는 API 실패 시 기본 분석 결과를 사용한다.

### 7.2 Retriever 실패
- 문서가 비어 있거나 매칭이 없으면 빈 컨텍스트로 진행한다.

### 7.3 Listener 실패
- 최종 응답 생성이 실패하면 기존 단일 호출 방식으로 폴백한다.

## 8. 보안

- API 키는 PropertiesService에만 저장한다.
- `.env`와 `.clasp.json`은 Git에 포함하지 않는다.
- RAG 파일 ID는 공개 전 제거하거나 로컬에서만 입력한다.

## 9. 운영 절차

1. RAG 문서 6개를 Google Drive에 업로드한다.
2. 파일 ID를 `initRAGSettings()`에 로컬 입력한다.
3. Apps Script 편집기에서 1회 실행해 PropertiesService에 저장한다.
4. `GEMINI_API_KEY`와 `SHEET_ID`를 설정한다.
5. 웹앱으로 배포한다.

## 10. 테스트 포인트

- `loadRAGDocument()` 캐시 동작 확인
- `runAnalystAgent()` JSON 파싱 확인
- `retrieveContext()` 섹션 추출 확인
- `runListenerAgent()` 응답 생성 확인
- `saveChatToSheet()` 컬럼 저장 확인

## 11. 공개 저장소 체크포인트

- 비밀값 제거
- 로컬 메타파일 제외
- 실험용 중복 파일 정리
- 실제 배포 파일 구조 문서화