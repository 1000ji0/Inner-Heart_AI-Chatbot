/**
 * 속마음 말하기 앱 - 구글 Apps Script 백엔드
 * Gemini API를 활용한 실시간 채팅 웹앱
 * 페르소나 설정 후 지속적인 대화 가능
 */

// 스크립트 속성에서 API 키 가져오기
function getApiKey() {
  return PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
}

// 웹 앱 진입점
function doGet() {
  return HtmlService.createTemplateFromFile('index')
    .evaluate()
    .setTitle('속마음 말하기')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// HTML 파일 포함을 위한 헬퍼 함수
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

// POST 요청 처리 - 채팅 메시지 처리
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    
    // 요청 타입에 따른 분기 처리
    if (data.action === 'setup_persona') {
      return handlePersonaSetup(data);
    } else if (data.action === 'send_message') {
      return handleChatMessage(data);
    } else {
      return ContentService
        .createTextOutput(JSON.stringify({success: false, error: '잘못된 요청입니다.'}))
        .setMimeType(ContentService.MimeType.JSON);
    }
      
  } catch (error) {
    console.error('doPost 에러:', error);
    return ContentService
      .createTextOutput(JSON.stringify({
        success: false, 
        error: '서버 오류가 발생했습니다: ' + error.toString()
      }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// 페르소나 설정 처리 (직접 호출용)
function setupPersona(data) {
  try {
    console.log('페르소나 설정 시작:', data);
    
    // 입력 데이터 검증
    if (!data.relationship || !data.emotion || !data.desiredResponse || 
        !data.intensity || !data.tone) {
      throw new Error('필수 입력값이 누락되었습니다.');
    }
    
    // 세션 ID 생성 (사용자별 고유 식별자)
    const sessionId = generateSessionId();
    console.log('생성된 세션 ID:', sessionId);
    
    // 페르소나 정보를 PropertiesService에 임시 저장
    const personaData = {
      relationship: data.relationship,
      emotion: data.emotion,
      desiredResponse: data.desiredResponse,
      intensity: data.intensity,
      tone: data.tone,
      profanityAllowed: data.profanityAllowed || false,
      createdAt: new Date().toISOString()
    };
    
    PropertiesService.getScriptProperties().setProperty(`persona_${sessionId}`, JSON.stringify(personaData));
    console.log('페르소나 데이터 저장 완료');
    
    return {
      success: true, 
      sessionId: sessionId,
      message: '페르소나가 설정되었습니다. 이제 대화를 시작할 수 있습니다.'
    };
      
  } catch (error) {
    console.error('페르소나 설정 에러:', error);
    throw new Error('페르소나 설정에 실패했습니다: ' + error.toString());
  }
}

// 페르소나 설정 처리 (POST 요청용)
function handlePersonaSetup(data) {
  try {
    // 입력 데이터 검증
    if (!data.relationship || !data.emotion || !data.desiredResponse || 
        !data.intensity || !data.tone) {
      return ContentService
        .createTextOutput(JSON.stringify({success: false, error: '필수 입력값이 누락되었습니다.'}))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    // 세션 ID 생성 (사용자별 고유 식별자)
    const sessionId = generateSessionId();
    
    // 페르소나 정보를 PropertiesService에 임시 저장
    const personaData = {
      relationship: data.relationship,
      emotion: data.emotion,
      desiredResponse: data.desiredResponse,
      intensity: data.intensity,
      tone: data.tone,
      profanityAllowed: data.profanityAllowed || false,
      createdAt: new Date().toISOString()
    };
    
    PropertiesService.getScriptProperties().setProperty(`persona_${sessionId}`, JSON.stringify(personaData));
    
    return ContentService
      .createTextOutput(JSON.stringify({
        success: true, 
        sessionId: sessionId,
        message: '페르소나가 설정되었습니다. 이제 대화를 시작할 수 있습니다.'
      }))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    console.error('페르소나 설정 에러:', error);
    return ContentService
      .createTextOutput(JSON.stringify({
        success: false, 
        error: '페르소나 설정에 실패했습니다: ' + error.toString()
      }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// 채팅 메시지 처리 (직접 호출용)
function sendChatMessage(data) {
  return processChatMessage(data);
}

// 채팅 메시지 처리 (POST 요청용)
function handleChatMessage(data) {
  try {
    const result = processChatMessage(data);
    return ContentService
      .createTextOutput(JSON.stringify(result))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    console.error('채팅 메시지 처리 에러:', error);
    return ContentService
      .createTextOutput(JSON.stringify({
        success: false, 
        error: '메시지 처리에 실패했습니다: ' + error.toString()
      }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function processChatMessage(data) {
  try {
    console.log('채팅 메시지 처리 시작:', data);

    if (!data.sessionId || !data.message) {
      throw new Error('세션 ID와 메시지가 필요합니다.');
    }

    const personaData = JSON.parse(PropertiesService.getScriptProperties().getProperty(`persona_${data.sessionId}`) || '{}');
    if (!personaData.relationship) {
      throw new Error('페르소나가 설정되지 않았습니다.');
    }

    const chatHistory = getChatHistory(data.sessionId);

    let analysisResult = null;
    let ragContext = {
      strategy: '',
      examples: '',
      forbidden: '',
      tone_guide: ''
    };

    try {
      analysisResult = runAnalystAgent(data.message, personaData);
    } catch (error) {
      console.error('Analyst Agent 실패:', error);
      analysisResult = null;
    }

    try {
      if (analysisResult) {
        ragContext = retrieveContext(analysisResult);
      }
    } catch (error) {
      console.error('Retriever 실패:', error);
      ragContext = {
        strategy: '',
        examples: '',
        forbidden: '',
        tone_guide: ''
      };
    }

    const useFallback = !analysisResult || isEmptyRagContext(ragContext);

    const aiResponse = useFallback
      ? callGeminiAPIWithHistory({
          ...personaData,
          message: data.message,
          chatHistory: chatHistory
        })
      : runListenerAgent(personaData, ragContext, data.message, chatHistory);

    const newChatEntry = {
      userMessage: data.message,
      aiResponse: aiResponse,
      timestamp: new Date().toISOString(),
      analysis: analysisResult || null
    };

    updateChatHistory(data.sessionId, newChatEntry);

    saveChatToSheet({
      sessionId: data.sessionId,
      persona: personaData,
      userMessage: data.message,
      aiResponse: aiResponse,
      analysisResult: analysisResult,
      timestamp: new Date()
    });

    return {
      success: true,
      response: aiResponse,
      sessionId: data.sessionId
    };
  } catch (error) {
    console.error('채팅 메시지 처리 에러:', error);
    throw new Error('메시지 처리에 실패했습니다: ' + error.toString());
  }
}

function isEmptyRagContext(ragContext) {
  if (!ragContext) {
    return true;
  }

  return ['strategy', 'examples', 'forbidden', 'tone_guide'].every(function(key) {
    return !ragContext[key] || String(ragContext[key]).trim() === '';
  });
}

// 세션 ID 생성
function generateSessionId() {
  return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// 채팅 히스토리 가져오기
function getChatHistory(sessionId) {
  const historyData = PropertiesService.getScriptProperties().getProperty(`chat_${sessionId}`);
  return historyData ? JSON.parse(historyData) : [];
}

// 채팅 히스토리 업데이트
function updateChatHistory(sessionId, newEntry) {
  const currentHistory = getChatHistory(sessionId);
  currentHistory.push(newEntry);
  
  // 최근 20개 대화만 유지 (메모리 절약)
  if (currentHistory.length > 20) {
    currentHistory.splice(0, currentHistory.length - 20);
  }
  
  PropertiesService.getScriptProperties().setProperty(`chat_${sessionId}`, JSON.stringify(currentHistory));
}

// Gemini API 호출 함수 (채팅 히스토리 포함)
function callGeminiAPIWithHistory(data) {
  const apiKey = getApiKey();
  if (!apiKey) {
    throw new Error('Gemini API 키가 설정되지 않았습니다.');
  }
  
  // 프롬프트 구성 (채팅 히스토리 포함)
  const prompt = buildChatPrompt(data);
  
  const url = `https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key=${apiKey}`;
  
  const payload = {
    contents: [{
      parts: [{
        text: prompt
      }]
    }],
    generationConfig: {
      temperature: 0.7,
      topK: 40,
      topP: 0.95,
      maxOutputTokens: 1024  // 증가: 토큰 초과 방지
    }
  };
  
  const options = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    payload: JSON.stringify(payload)
  };
  
  const response = UrlFetchApp.fetch(url, options);
  const responseText = response.getContentText();
  
  console.log('Gemini API 응답:', responseText);
  
  if (response.getResponseCode() !== 200) {
    throw new Error(`API 요청 실패: ${response.getResponseCode()} - ${responseText}`);
  }
  
  const responseData = JSON.parse(responseText);
  
  if (responseData.error) {
    throw new Error(`API 오류: ${responseData.error.message || '알 수 없는 오류'}`);
  }
  
  if (responseData.candidates && responseData.candidates.length > 0) {
    const candidate = responseData.candidates[0];
    if (candidate.content && candidate.content.parts && candidate.content.parts.length > 0) {
      return candidate.content.parts[0].text.trim();
    } else {
      // MAX_TOKENS 처리
      if (candidate.finishReason === 'MAX_TOKENS') {
        console.warn('MAX_TOKENS 발생: 응답이 잘림');
        return '응답이 너무 길어 잘렸습니다. 더 짧은 메시지를 시도해주세요.';
      } else {
        console.log('응답 구조:', JSON.stringify(responseData, null, 2));
        throw new Error('Gemini API 응답을 처리할 수 없습니다. 응답: ' + responseText);
      }
    }
  } else {
    console.log('응답 구조:', JSON.stringify(responseData, null, 2));
    throw new Error('Gemini API 응답을 처리할 수 없습니다. 응답: ' + responseText);
  }
}

// 채팅용 프롬프트 구성
function buildChatPrompt(data) {
  const relationshipMap = {
    '연인': '연인',
    '친구': '친한 친구',
    '부모': '부모님',
    '직장상사': '직장 상사',
    '교수': '교수님',
    '기타': '특별한 사람'
  };
  
  const emotionMap = {
    '분노': '화가 나고 분노스러운',
    '슬픔': '슬프고 아픈',
    '후회': '후회스러운',
    '감사': '고마운',
    '미련': '미련이 남는',
    '복잡함': '복잡한 감정의'
  };
  
  const responseMap = {
    '사과': '사과하는',
    '위로': '위로하는',
    '공감': '공감하는',
    '무시': '무시하는',
    '솔직한 피드백': '솔직하게 피드백하는',
    '책임 인정': '책임을 인정하는'
  };
  
  const intensityMap = {
    '부드럽게': '부드럽고 따뜻하게',
    '중간': '적당한 강도로',
    '강하게': '강하게'
  };
  
  const toneMap = {
    '다정': '다정하고 따뜻한',
    '무뚝뚝함': '무뚝뚝하지만 진심이 담긴',
    '차가움': '차갑지만 정확한',
    '유머러스함': '유머러스하고 재미있는',
    '보통': '자연스러운'
  };
  
  const relationship = relationshipMap[data.relationship] || data.relationship;
  const emotion = emotionMap[data.emotion] || data.emotion;
  const desiredResponse = responseMap[data.desiredResponse] || data.desiredResponse;
  const intensity = intensityMap[data.intensity] || data.intensity;
  const tone = toneMap[data.tone] || data.tone;
  
  let prompt = `당신은 ${relationship}의 페르소나입니다.\n\n`;
  prompt += `페르소나 설정:\n`;
  prompt += `- 관계: ${relationship}\n`;
  prompt += `- 감정 상태: ${emotion}\n`;
  prompt += `- 원하는 반응: ${desiredResponse}\n`;
  prompt += `- 반응 강도: ${intensity}\n`;
  prompt += `- 말투: ${tone}\n\n`;
  
  if (data.profanityAllowed) {
    prompt += `상대방의 메시지에 욕설이 포함될 수 있지만, 당신의 응답은 항상 건전하고 건설적이어야 합니다.\n\n`;
  }
  
  // 채팅 히스토리 추가
  if (data.chatHistory && data.chatHistory.length > 0) {
    prompt += `이전 대화 내용:\n`;
    data.chatHistory.slice(-10).forEach((entry, index) => {
      prompt += `사용자: ${entry.userMessage}\n`;
      prompt += `${relationship}: ${entry.aiResponse}\n\n`;
    });
  }
  
  prompt += `현재 메시지: ${data.message}\n\n`;
  prompt += `위 메시지에 대해 ${relationship}의 입장에서 ${intensity} ${tone} 말투로 응답해주세요. `;
  prompt += `자연스럽고 진심 어린 대화를 이어가세요.`;
  
  return prompt;
}

// Gemini API 호출 함수 (기존 단일 응답용)
function callGeminiAPI(data) {
  const apiKey = getApiKey();
  if (!apiKey) {
    throw new Error('Gemini API 키가 설정되지 않았습니다.');
  }
  
  // 프롬프트 구성
  const prompt = buildPrompt(data);
  
  const url = `https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key=${apiKey}`;
  
  const payload = {
    contents: [{
      parts: [{
        text: prompt
      }]
    }],
    generationConfig: {
      temperature: 0.7,
      topK: 40,
      topP: 0.95,
      maxOutputTokens: 1024  // 증가: 토큰 초과 방지
    }
  };
  
  const options = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    payload: JSON.stringify(payload)
  };
  
  const response = UrlFetchApp.fetch(url, options);
  const responseText = response.getContentText();
  
  console.log('Gemini API 응답:', responseText);
  
  if (response.getResponseCode() !== 200) {
    throw new Error(`API 요청 실패: ${response.getResponseCode()} - ${responseText}`);
  }
  
  const responseData = JSON.parse(responseText);
  
  if (responseData.error) {
    throw new Error(`API 오류: ${responseData.error.message || '알 수 없는 오류'}`);
  }
  
  if (responseData.candidates && responseData.candidates.length > 0) {
    const candidate = responseData.candidates[0];
    if (candidate.content && candidate.content.parts && candidate.content.parts.length > 0) {
      return candidate.content.parts[0].text.trim();
    } else {
      // MAX_TOKENS 처리
      if (candidate.finishReason === 'MAX_TOKENS') {
        console.warn('MAX_TOKENS 발생: 응답이 잘림');
        return '응답이 너무 길어 잘렸습니다. 더 짧은 메시지를 시도해주세요.';
      } else {
        console.log('응답 구조:', JSON.stringify(responseData, null, 2));
        throw new Error('Gemini API 응답을 처리할 수 없습니다. 응답: ' + responseText);
      }
    }
  } else {
    console.log('응답 구조:', JSON.stringify(responseData, null, 2));
    throw new Error('Gemini API 응답을 처리할 수 없습니다. 응답: ' + responseText);
  }
}

// 프롬프트 구성 함수
function buildPrompt(data) {
  const relationshipMap = {
    '연인': '연인',
    '친구': '친한 친구',
    '부모': '부모님',
    '직장상사': '직장 상사',
    '교수': '교수님',
    '기타': '특별한 사람'
  };
  
  const emotionMap = {
    '분노': '화가 나고 분노스러운',
    '슬픔': '슬프고 아픈',
    '후회': '후회스러운',
    '감사': '고마운',
    '미련': '미련이 남는',
    '복잡함': '복잡한 감정의'
  };
  
  const responseMap = {
    '사과': '사과하는',
    '위로': '위로하는',
    '공감': '공감하는',
    '무시': '무시하는',
    '솔직한 피드백': '솔직하게 피드백하는',
    '책임 인정': '책임을 인정하는'
  };
  
  const intensityMap = {
    '부드럽게': '부드럽고 따뜻하게',
    '중간': '적당한 강도로',
    '강하게': '강하게'
  };
  
  const toneMap = {
    '다정': '다정하고 따뜻한',
    '무뚝뚝함': '무뚝뚝하지만 진심이 담긴',
    '차가움': '차갑지만 정확한',
    '유머러스함': '유머러스하고 재미있는',
    '보통': '자연스러운'
  };
  
  const relationship = relationshipMap[data.relationship] || data.relationship;
  const emotion = emotionMap[data.emotion] || data.emotion;
  const desiredResponse = responseMap[data.desiredResponse] || data.desiredResponse;
  const intensity = intensityMap[data.intensity] || data.intensity;
  const tone = toneMap[data.tone] || data.tone;
  
  let prompt = `당신은 ${relationship}의 입장에서 ${data.content}라는 ${emotion} 마음을 전달받았습니다.\n\n`;
  prompt += `상대방이 원하는 반응: ${desiredResponse}\n`;
  prompt += `반응 강도: ${intensity}\n`;
  prompt += `말투: ${tone}\n\n`;
  
  if (data.profanityAllowed) {
    prompt += `상대방의 원문에 욕설이 포함될 수 있지만, 당신의 응답은 항상 건전하고 건설적이어야 합니다.\n\n`;
  }
  
  prompt += `위 상황에서 당신이 ${relationship}의 입장에서 할 수 있는 2-3문장의 진심 어린 응답을 해주세요. `;
  prompt += `상대방의 감정을 이해하고, 원하는 반응을 ${intensity} ${tone} 말투로 표현해주세요.`;
  
  return prompt;
}

// 감정 분석 함수 (간단한 키워드 기반)
function analyzeSentiment(text) {
  const positiveWords = ['좋', '사랑', '고마', '행복', '기쁘', '감사', '즐거', '웃', '미소'];
  const negativeWords = ['싫', '화', '분노', '슬프', '아프', '힘들', '우울', '짜증', '후회', '미련'];
  
  const positiveCount = positiveWords.filter(word => text.includes(word)).length;
  const negativeCount = negativeWords.filter(word => text.includes(word)).length;
  
  if (positiveCount > negativeCount) return 'positive';
  if (negativeCount > positiveCount) return 'negative';
  return 'neutral';
}

// 감정 키워드 추출
function extractEmotionKeywords(text) {
  const emotions = {
    'anger': ['화', '분노', '짜증', '열받', '빡쳐'],
    'sadness': ['슬프', '아프', '우울', '눈물', '힘들'],
    'joy': ['기쁘', '행복', '즐거', '웃', '미소'],
    'fear': ['무서', '걱정', '불안', '두려'],
    'hope': ['희망', '기대', '바라', '원하']
  };
  
  const foundEmotions = [];
  for (const [emotion, keywords] of Object.entries(emotions)) {
    if (keywords.some(keyword => text.includes(keyword))) {
      foundEmotions.push(emotion);
    }
  }
  
  return foundEmotions.join(',') || 'neutral';
}

// 채팅 데이터를 구글 시트에 저장
function saveChatToSheet(data) {
  try {
    // 스크립트 속성에서 시트 ID 가져오기
    const sheetId = PropertiesService.getScriptProperties().getProperty('SHEET_ID');
    if (!sheetId) {
      throw new Error('구글 시트 ID가 설정되지 않았습니다.');
    }
    
    const spreadsheet = SpreadsheetApp.openById(sheetId);
    let sheet = spreadsheet.getSheetByName('채팅기록');
    
    // 시트가 없으면 생성
    if (!sheet) {
      sheet = spreadsheet.insertSheet('채팅기록');
      
      // 헤더 설정
      const headers = [
        '세션ID', '요청일시', '대상관계', '내감정', '원하는반응', '반응강도', 
        '리스너말투', '욕설허용', '사용자메시지', 'AI응답', '분석감정', 
        '분석키워드', '처리상태'
      ];
      sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    }
    
    // 감정 분석
    const sentiment = analyzeSentiment(data.userMessage);
    const emotionKeywords = data.analysisResult && data.analysisResult.keywords && data.analysisResult.keywords.length
      ? data.analysisResult.keywords.join(', ')
      : extractEmotionKeywords(data.userMessage);
    const analysisEmotion = data.analysisResult && data.analysisResult.emotion ? data.analysisResult.emotion : sentiment;
    
    // 데이터 행 추가
    const rowData = [
      data.sessionId,
      data.timestamp,
      data.persona.relationship,
      data.persona.emotion,
      data.persona.desiredResponse,
      data.persona.intensity,
      data.persona.tone,
      data.persona.profanityAllowed,
      data.userMessage,
      data.aiResponse,
      analysisEmotion,
      emotionKeywords,
      '성공'
    ];
    
    sheet.appendRow(rowData);
    
    return sheetId;
    
  } catch (error) {
    console.error('채팅 시트 저장 에러:', error);
    throw new Error('채팅 데이터 저장에 실패했습니다: ' + error.toString());
  }
}

// 기존 단일 응답용 시트 저장 (호환성 유지)
function saveToSheet(data) {
  try {
    // 스크립트 속성에서 시트 ID 가져오기
    const sheetId = PropertiesService.getScriptProperties().getProperty('SHEET_ID');
    if (!sheetId) {
      throw new Error('구글 시트 ID가 설정되지 않았습니다.');
    }
    
    const spreadsheet = SpreadsheetApp.openById(sheetId);
    let sheet = spreadsheet.getSheetByName('기록');
    
    // 시트가 없으면 생성
    if (!sheet) {
      sheet = spreadsheet.insertSheet('기록');
      
      // 헤더 설정
      const headers = [
        '요청일시', '대상관계', '내감정', '원하는반응', '반응강도', 
        '리스너말투', '욕설허용', '입력내용', 'AI응답', '감정라벨', 
        '감정키워드', '처리상태'
      ];
      sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    }
    
    // 데이터 행 추가
    const rowData = [
      data.timestamp,
      data.relationship,
      data.emotion,
      data.desiredResponse,
      data.intensity,
      data.tone,
      data.profanityAllowed,
      data.content,
      data.aiResponse,
      data.sentiment,
      data.emotionKeywords,
      '성공'
    ];
    
    sheet.appendRow(rowData);
    
    return sheetId;
    
  } catch (error) {
    console.error('시트 저장 에러:', error);
    throw new Error('데이터 저장에 실패했습니다: ' + error.toString());
  }
}

// 설정 확인 함수 (개발용)
function checkSettings() {
  const apiKey = getApiKey();
  const sheetId = PropertiesService.getScriptProperties().getProperty('SHEET_ID');
  
  console.log('API 키 설정:', apiKey ? '설정됨' : '설정 안됨');
  console.log('시트 ID 설정:', sheetId ? '설정됨' : '설정 안됨');
  
  return {
    apiKeySet: !!apiKey,
    sheetIdSet: !!sheetId
  };
}

// 테스트용 페르소나 설정 함수
function testPersonaSetup() {
  const testData = {
    relationship: '친구',
    emotion: '슬픔',
    desiredResponse: '위로',
    intensity: '부드럽게',
    tone: '다정',
    profanityAllowed: false
  };
  
  try {
    const result = setupPersona(testData);
    console.log('테스트 결과:', result);
    return result;
  } catch (error) {
    console.error('테스트 실패:', error);
    return { success: false, error: error.toString() };
  }
}

// API 키 유효성 테스트
function testApiKey() {
  const apiKey = getApiKey();
  if (!apiKey) {
    return { success: false, error: 'API 키가 설정되지 않았습니다.' };
  }
  
  try {
    const url = `https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key=${apiKey}`;
    const payload = {
      contents: [{
        parts: [{
          text: "안녕하세요. 간단한 테스트입니다."
        }]
      }],
      generationConfig: {
        temperature: 0.7,
        maxOutputTokens: 50
      }
    };
    
    const options = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      payload: JSON.stringify(payload)
    };
    
    const response = UrlFetchApp.fetch(url, options);
    const responseText = response.getContentText();
    
    console.log('API 테스트 응답:', responseText);
    
    if (response.getResponseCode() === 200) {
      return { success: true, message: 'API 키가 유효합니다.' };
    } else {
      return { success: false, error: `API 테스트 실패: ${response.getResponseCode()} - ${responseText}` };
    }
  } catch (error) {
    console.error('API 테스트 에러:', error);
    return { success: false, error: 'API 테스트 중 오류: ' + error.toString() };
  }
}

// 세션 데이터 확인 함수
function checkSessionData(sessionId) {
  const personaData = PropertiesService.getScriptProperties().getProperty(`persona_${sessionId}`);
  const chatData = PropertiesService.getScriptProperties().getProperty(`chat_${sessionId}`);
  
  return {
    persona: personaData ? JSON.parse(personaData) : null,
    chatHistory: chatData ? JSON.parse(chatData) : []
  };
}

// RAG 파일 ID 최초 등록용 설정 함수
function initRAGSettings() {
  const idMap = {
    RAG_EMOTION: '', // 01_emotion_responses.md 파일 ID를 여기에 입력
    RAG_SCENARIOS: '', // 02_relationship_scenarios.md 파일 ID를 여기에 입력
    RAG_TONE: '', // 03_tone_style_guide.md 파일 ID를 여기에 입력
    RAG_NVC: '', // 04_nvc_theory.md 파일 ID를 여기에 입력
    RAG_VIOLATION: '', // 05_nvc_violation_pattern.md 파일 ID를 여기에 입력
    RAG_VOCABULARY: '' // 06_nvc_vocabulary_guide.md 파일 ID를 여기에 입력
  };

  if (!idMap.RAG_EMOTION || !idMap.RAG_SCENARIOS || !idMap.RAG_TONE || !idMap.RAG_NVC || !idMap.RAG_VIOLATION || !idMap.RAG_VOCABULARY) {
    throw new Error('RAG 파일 ID를 모두 입력한 뒤 다시 실행하세요.');
  }

  return setRAGFileIds(idMap);
}