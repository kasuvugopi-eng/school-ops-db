'use client';

import { useEffect, useRef, useCallback } from 'react';

type EventHandler = (event: any) => void;

export function useSchoolWebSocket(schoolId: string | null, onEvent: EventHandler) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);

  const connect = useCallback(() => {
    if (!schoolId) return;
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/ws/school/${schoolId}?token=${token}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
      reconnectAttempts.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onEvent(data);
      } catch (e) {
        console.error('Failed to parse WebSocket message', e);
      }
    };

    ws.onclose = (e) => {
      console.log(`WebSocket disconnected (code: ${e.code})`);
      const delay = Math.min(3000 * Math.pow(2, reconnectAttempts.current), 30000);
      // eslint-disable-next-line react-hooks/exhaustive-deps
      reconnectTimeoutRef.current = setTimeout(() => {
        reconnectAttempts.current++;
        // eslint-disable-next-line
        connect();
      }, delay);
    };

    ws.onerror = (error) => {
      console.warn('WebSocket error', error);
    };

    wsRef.current = ws;
  }, [schoolId, onEvent]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };
  }, [connect]);

  return wsRef;
}
