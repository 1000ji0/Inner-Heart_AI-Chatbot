/**
 * Listener Agent
 * 페르소나와 RAG 컨텍스트를 합쳐 최종 응답을 생성한다.
 */

function buildListenerPrompt(personaData, ragContext) {
  var promptParts = [];
  var persona = personaData || {};
  var rag = ragContext || {};

  promptParts.push('너는 ' + (persona.relationship || '기타') + ' 역할을 하는 공감 리스너야. 사용자의 감정: ' + (persona.emotion || '') + '. 원하는 반응: ' + (persona.desiredResponse || '') + '. 반응 강도: ' + (persona.intensity || '') + '. 말투: ' + (persona.tone || '') + '.');

  if (rag.strategy) {
    promptParts.push('【응답 전략】\n' + rag.strategy);
  }

  if (rag.examples) {
    promptParts.push('【참고 예시】\n' + rag.examples);
  }

  if (rag.forbidden) {
    promptParts.push('【절대 금지 표현】\n' + rag.forbidden);
  }

  if (rag.tone_guide) {
    promptParts.push('【말투 가이드】\n' + rag.tone_guide);
  }

  promptParts.push('응답은 자연스럽게. 너무 짧지 않게, 하지만 장황하지 않게. 상담사처럼 딱딱하게 말하지 말고 친구처럼 대화해. 절대 금지 표현은 사용하지 마. 응답이 끊기지 않고 완전한 문장으로 마무리해.');

  return promptParts.join('\n\n');
}

function runListenerAgent(personaData, ragContext, userMessage, chatHistory) {
  var apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  if (!apiKey) {
    throw new Error('Gemini API 키가 설정되지 않았습니다.');
  }

  var systemPrompt = buildListenerPrompt(personaData, ragContext);
  var conversationPrompt = buildListenerConversation(userMessage, chatHistory);

  var url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=' + encodeURIComponent(apiKey);
  var payload = {
    systemInstruction: {
      parts: [{ text: systemPrompt }]
    },
    contents: [{
      role: 'user',
      parts: [{ text: conversationPrompt }]
    }],
   generationConfig: {
  temperature: 0.7,
  topK: 40,
  topP: 0.95,
  maxOutputTokens: 8192  // 최대치로
}
  };

  var options = {
    method: 'POST',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  var response = UrlFetchApp.fetch(url, options);
  var responseText = response.getContentText();

  if (response.getResponseCode() !== 200) {
    throw new Error('API 요청 실패: ' + response.getResponseCode() + ' - ' + responseText);
  }

  var responseData = JSON.parse(responseText);
  console.log('finishReason:', responseData.candidates[0].finishReason);
  console.log('전체 응답:', responseText);

  var text = extractGeminiText(responseData);

  if (!text) {
    throw new Error('Gemini 응답이 비어 있습니다.');
  }

  return text.trim();
}

function buildListenerConversation(userMessage, chatHistory) {
  var lines = [];
  var history = Array.isArray(chatHistory) ? chatHistory.slice(-10) : [];

  for (var i = 0; i < history.length; i++) {
    var entry = history[i] || {};
    if (entry.userMessage) {
      lines.push('사용자: ' + entry.userMessage);
    }
    if (entry.aiResponse) {
      lines.push('리스너: ' + entry.aiResponse);
    }
  }

  lines.push('사용자: ' + String(userMessage || ''));
  lines.push('리스너:');

  return lines.join('\n');
}