/**
 * RAG 문서 로더
 * Google Drive에 저장된 문서를 읽고 CacheService로 캐싱한다.
 */

function loadRAGDocument(propKey) {
  if (!propKey) {
    return '';
  }

  const cache = CacheService.getScriptCache();
  const cacheKey = 'RAG_DOC_' + propKey;
  const cachedText = cache.get(cacheKey);
  if (cachedText !== null) {
    return cachedText;
  }

  const fileId = PropertiesService.getScriptProperties().getProperty(propKey);
  if (!fileId) {
    return '';
  }

  try {
    const file = DriveApp.getFileById(fileId);
    const text = file.getBlob().getDataAsString();
    cache.put(cacheKey, text, 21600);
    return text;
  } catch (error) {
    console.error('RAG 문서 로딩 실패:', propKey, error);
    return '';
  }
}

function loadAllRAGDocuments() {
  return {
    RAG_EMOTION: loadRAGDocument('RAG_EMOTION'),
    RAG_SCENARIOS: loadRAGDocument('RAG_SCENARIOS'),
    RAG_TONE: loadRAGDocument('RAG_TONE'),
    RAG_NVC: loadRAGDocument('RAG_NVC'),
    RAG_VIOLATION: loadRAGDocument('RAG_VIOLATION'),
    RAG_VOCABULARY: loadRAGDocument('RAG_VOCABULARY')
  };
}

function setRAGFileIds(idMap) {
  const props = PropertiesService.getScriptProperties();
  const keys = [
    'RAG_EMOTION',
    'RAG_SCENARIOS',
    'RAG_TONE',
    'RAG_NVC',
    'RAG_VIOLATION',
    'RAG_VOCABULARY'
  ];

  keys.forEach(function(key) {
    if (idMap && idMap[key]) {
      props.setProperty(key, idMap[key]);
    }
  });

  return {
    success: true,
    message: 'RAG 파일 ID가 저장되었습니다.'
  };
}