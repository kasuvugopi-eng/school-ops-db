'use client';

import { useEffect, useRef, useCallback } from 'react';

type EventHandler = (event: any) => void;

export function useSchoolWebSocket(schoolId: string | null, onEvent: EventHandler) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

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

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      if (reconnectAttempts.current < maxReconnectAttempts) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttempts.current++;
          connect();
        }, delay);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error', error);
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
