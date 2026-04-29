/**
 * Retriever Agent
 * 분석 결과를 바탕으로 RAG 문서의 관련 섹션을 추출한다.
 */

function retrieveContext(analysisResult) {
  var documents = loadAllRAGDocuments();
  var keywords = [];

  if (analysisResult) {
    if (analysisResult.emotion) {
      keywords.push(String(analysisResult.emotion));
    }
    if (analysisResult.relationship) {
      keywords.push(String(analysisResult.relationship));
    }
    if (analysisResult.intensity) {
      keywords.push(String(analysisResult.intensity));
    }
    if (analysisResult.keywords && analysisResult.keywords.length) {
      keywords = keywords.concat(analysisResult.keywords);
    }
  }

  var strategyParts = [];
  var examplesParts = [];
  var forbiddenParts = [];
  var toneGuideParts = [];

  var emotionText = documents.RAG_EMOTION || '';
  var scenariosText = documents.RAG_SCENARIOS || '';
  var toneText = documents.RAG_TONE || '';
  var nvcText = documents.RAG_NVC || '';
  var violationText = documents.RAG_VIOLATION || '';
  var vocabularyText = documents.RAG_VOCABULARY || '';

  var strategySources = [emotionText, scenariosText, nvcText, vocabularyText];
  for (var i = 0; i < strategySources.length; i++) {
    var strategySection = extractMatchingSections(strategySources[i], keywords);
    if (strategySection) {
      strategyParts.push(strategySection);
    }
  }

  var exampleSources = [emotionText, scenariosText, nvcText];
  for (var j = 0; j < exampleSources.length; j++) {
    var exampleSection = extractMatchingSections(exampleSources[j], keywords);
    if (exampleSection) {
      examplesParts.push(exampleSection);
    }
  }

  var forbiddenSection = extractMatchingSections(violationText, keywords);
  if (forbiddenSection) {
    forbiddenParts.push(forbiddenSection);
  }

  var toneGuideSection = extractMatchingSections(toneText, keywords);
  if (toneGuideSection) {
    toneGuideParts.push(toneGuideSection);
  }

  return {
    strategy: truncateText(strategyParts.join('\n\n'), 2000),
    examples: truncateText(examplesParts.join('\n\n'), 2000),
    forbidden: truncateText(forbiddenParts.join('\n\n'), 2000),
    tone_guide: truncateText(toneGuideParts.join('\n\n'), 2000)
  };
}

function extractSection(documentText, keyword) {
  if (!documentText || !keyword) {
    return '';
  }

  var sections = String(documentText).split(/\n(?=###\s)/);
  var matched = [];
  var normalizedKeyword = String(keyword).toLowerCase();

  for (var i = 0; i < sections.length; i++) {
    var section = sections[i];
    if (section && section.toLowerCase().indexOf(normalizedKeyword) !== -1) {
      matched.push(section.trim());
    }
  }

  return matched.join('\n\n');
}

function truncateText(text, maxLength) {
  var content = String(text || '');
  if (content.length <= maxLength) {
    return content;
  }
  return content.substring(0, maxLength).trim();
}

function extractMatchingSections(documentText, keywords) {
  if (!documentText) {
    return '';
  }

  var sections = String(documentText).split(/\n(?=###\s)/);
  var matched = [];

  for (var i = 0; i < sections.length; i++) {
    var section = sections[i].trim();
    if (!section) {
      continue;
    }

    var normalizedSection = section.toLowerCase();
    var matchedKeyword = false;

    for (var j = 0; j < keywords.length; j++) {
      var keyword = String(keywords[j] || '').trim().toLowerCase();
      if (keyword && normalizedSection.indexOf(keyword) !== -1) {
        matchedKeyword = true;
        break;
      }
    }

    if (matchedKeyword) {
      matched.push(section);
    }
  }

  return matched.join('\n\n');
}