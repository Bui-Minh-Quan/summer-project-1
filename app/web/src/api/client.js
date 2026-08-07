import axios from 'axios';

// Target FastAPI Gateway (default local development URL)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 2 minutes timeout for LLM extraction/reasoning calls
});

// ============================================================================
// 1. PREDICTIONS & REASONING API
// ============================================================================

/**
 * Fetch Dual Prediction (XGBoost 5-day regression + vLLM TRR Reasoning)
 * Endpoint: GET /api/v1/predictions/{symbol}
 */
export const getDualPrediction = async (symbol, date = null) => {
  const params = {};
  if (date) params.date = date;
  
  const response = await apiClient.get(`/predictions/${symbol.toUpperCase()}`, { params });
  return response.data;
};

/**
 * Fetch Backtest Classification History
 * Endpoint: GET /api/v1/predictions/backtest/classification/{symbol}
 */
export const getClassificationBacktest = async (symbol, page = 1, limit = 20) => {
  const response = await apiClient.get(`/predictions/backtest/classification/${symbol.toUpperCase()}`, {
    params: { page, limit },
  });
  return response.data;
};

/**
 * Fetch Backtest Regression History
 * Endpoint: GET /api/v1/predictions/backtest/regression/{symbol}
 */
export const getRegressionBacktest = async (symbol, page = 1, limit = 20) => {
  const response = await apiClient.get(`/predictions/backtest/regression/${symbol.toUpperCase()}`, {
    params: { page, limit },
  });
  return response.data;
};

// ============================================================================
// 2. SENTIMENT & NEWS API
// ============================================================================

/**
 * Fetch Social Sentiment Score & Hype Metrics
 * Endpoint: GET /api/v1/sentiment/score/{symbol}
 */
export const getSentimentScore = async (symbol) => {
  const response = await apiClient.get(`/sentiment/score/${symbol.toUpperCase()}`);
  return response.data;
};

/**
 * Fetch Related News Feed
 * Endpoint: GET /api/v1/sentiment/news/{symbol}
 */
export const getRelatedNews = async (symbol, page = 1, limit = 20) => {
  const response = await apiClient.get(`/sentiment/news/${symbol.toUpperCase()}`, {
    params: { page, limit },
  });
  return response.data;
};

// ============================================================================
// 3. KNOWLEDGE GRAPH EXTRACTION API
// ============================================================================

/**
 * Extract Knowledge Graph from uploaded PDF/TXT document
 * Endpoint: POST /api/v1/graph/extract
 */
export const extractKnowledgeGraph = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post('/graph/extract', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export default apiClient;


/**
 * Fetch Historical Market Bars for Chart Hydration
 * Endpoint: GET /api/v1/stream/history/{symbol}
 */
export const getMarketHistory = async (symbol, limit = 30) => {
  const response = await apiClient.get(`/stream/history/${symbol.toUpperCase()}`, {
    params: { limit },
  });
  return response.data;
};