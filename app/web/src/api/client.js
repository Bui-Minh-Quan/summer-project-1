import axios from 'axios';

// Target FastAPI Gateway (Defaults to relative '/api/v1' for Vite proxy & Docker Nginx)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 2 minutes timeout for vLLM extraction & reasoning calls
});

// Dual Prediction (Regressions + vLLM Reasoning)
export const getDualPrediction = async (symbol, date = null) => {
  const params = {};
  if (date) params.date = date;
  const response = await apiClient.get(`/predictions/${symbol.toUpperCase()}`, { params });
  return response.data;
};

// Backtest Classification History
export const getClassificationBacktest = async (symbol, page = 1, limit = 20) => {
  const response = await apiClient.get(`/predictions/backtest/classification/${symbol.toUpperCase()}`, {
    params: { page, limit },
  });
  return response.data;
};

// Backtest Regression History
export const getRegressionBacktest = async (symbol, page = 1, limit = 20) => {
  const response = await apiClient.get(`/predictions/backtest/regression/${symbol.toUpperCase()}`, {
    params: { page, limit },
  });
  return response.data;
};

// Market Sentiment Score
export const getSentimentScore = async (symbol) => {
  const response = await apiClient.get(`/sentiment/score/${symbol.toUpperCase()}`);
  return response.data;
};

// Related News Feed
export const getRelatedNews = async (symbol, page = 1, limit = 20) => {
  const response = await apiClient.get(`/sentiment/news/${symbol.toUpperCase()}`, {
    params: { page, limit },
  });
  return response.data;
};

// Historical Market Quotes
export const getMarketHistory = async (symbol, limit = 30) => {
  const response = await apiClient.get(`/stream/history/${symbol.toUpperCase()}`, {
    params: { limit },
  });
  return response.data;
};

// Knowledge Graph Document Extraction
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