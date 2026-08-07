import { useEffect, useState, useRef, useCallback } from 'react';

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/api/v1/stream';

/**
 * Custom React Hook for streaming real-time market ticks via WebSocket.
 * Connects to ws://localhost:8000/api/v1/stream/{symbol}
 */
export const useMarketStream = (symbol) => {
  const [latestTick, setLatestTick] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);

  const connect = useCallback(() => {
    if (!symbol) return;

    const wsUrl = `${WS_BASE_URL}/${symbol.toUpperCase()}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
      console.log(`[WebSocket] Connected to market stream for ${symbol.toUpperCase()}`);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLatestTick(data);
      } catch (err) {
        console.error('[WebSocket] Failed to parse tick payload:', err);
      }
    };

    ws.onerror = (err) => {
      console.error(`[WebSocket] Stream error for ${symbol}:`, err);
      setError('Connection error');
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log(`[WebSocket] Disconnected from stream for ${symbol.toUpperCase()}`);
    };

    wsRef.current = ws;
  }, [symbol]);

  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { latestTick, isConnected, error };
};