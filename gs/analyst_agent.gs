/**
 * Analyst Agent
 * 사용자의 메시지를 분석해 감정, 관계, 강도, 키워드를 JSON으로 반환한다.
 */

function runAnalystAgent(userMessage, personaData) {
  const apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  if (!apiKey) {
    throw new Error('Gemini API 키가 설정되지 않았습니다.');
  }

  const systemPrompt = '너는 감정 분석기야. 반드시 아래 JSON 형식만 출력해. 설명, 마크다운, 줄바꿈 없이 한 줄 JSON만 반환해.\n{"emotion":"분노","relationship":"연인","intensity":"높음","keywords":["키워드1","키워드2"]}';
  const prompt = 'personaData: ' + JSON.stringify(personaData || {}) + '\nuserMessage: ' + String(userMessage || '');

  const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=' + encodeURIComponent(apiKey);
  const payload = {
    systemInstruction: {
      parts: [{ text: systemPrompt }]
    },
    contents: [{
      role: 'user',
      parts: [{ text: prompt }]
    }],
    generationConfig: {
      temperature: 0.1,
      topK: 1,
      topP: 1,
      maxOutputTokens: 1024
    }
  };

  const options = {
    method: 'POST',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  try {
    const response = UrlFetchApp.fetch(url, options);
    const responseText = response.getContentText();

    if (response.getResponseCode() !== 200) {
      throw new Error('API 요청 실패: ' + response.getResponseCode() + ' - ' + responseText);
    }

    const responseData = JSON.parse(responseText);
    const text = extractGeminiText(responseData);
    const parsed = parseAnalystJson(text);

    if (parsed) {
      return parsed;
    }
  } catch (error) {
    console.error('Analyst Agent 오류:', error);
  }

  return {
    emotion: personaData && personaData.emotion ? personaData.emotion : '복잡함',
    relationship: personaData && personaData.relationship ? personaData.relationship : '기타',
    intensity: personaData && personaData.intensity ? personaData.intensity : '중간',
    keywords: []
  };
}

function parseAnalystJson(text) {
  if (!text) {
    return null;
  }

  var normalized = String(text).trim();
  normalized = normalized.replace(/^```json\s*/i, '').replace(/^```\s*/i, '').replace(/\s*```$/, '');

  var start = normalized.indexOf('{');
  var end = normalized.lastIndexOf('}');
  if (start >= 0 && end > start) {
    normalized = normalized.substring(start, end + 1);
  }

  try {
    var data = JSON.parse(normalized);
    return normalizeAnalysisResult(data);
  } catch (error) {
    console.error('Analyst JSON 파싱 실패:', error, normalized);
    return null;
  }
}

function normalizeAnalysisResult(data) {
  var result = data || {};
  var keywords = Array.isArray(result.keywords) ? result.keywords.slice(0, 3) : [];

  return {
    emotion: isAllowedEmotion(result.emotion) ? result.emotion : '복잡함',
    relationship: isAllowedRelationship(result.relationship) ? result.relationship : '기타',
    intensity: isAllowedIntensity(result.intensity) ? result.intensity : '중간',
    keywords: keywords.filter(function(item) {
      return item !== null && item !== undefined && String(item).trim() !== '';
    }).map(function(item) {
      return String(item).trim();
    })
  };
}

function isAllowedEmotion(value) {
  return ['분노', '슬픔', '후회', '감사', '미련', '복잡함'].indexOf(value) !== -1;
}

function isAllowedRelationship(value) {
  return ['연인', '친구', '부모', '직장상사', '기타'].indexOf(value) !== -1;
}

function isAllowedIntensity(value) {
  return ['낮음', '중간', '높음'].indexOf(value) !== -1;
}

function extractGeminiText(responseData) {
  if (!responseData || !responseData.candidates || !responseData.candidates.length) {
    return '';
  }

  var candidate = responseData.candidates[0];
  if (!candidate.content || !candidate.content.parts || !candidate.content.parts.length) {
    return '';
  }

  return String(candidate.content.parts[0].text || '').trim();
}