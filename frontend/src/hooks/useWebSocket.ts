/**
 * React hooks for WebSocket integration
 */

import { useEffect, useState, useCallback } from "react";
import type {
  WebSocketMessage,
  MessageHandler,
  ConnectionState,
} from "../types/websocket";
import { WebSocketClient } from "../lib/websocket";

/**
 * Hook to connect to a WebSocket and handle messages
 */
export function useWebSocket(
  client: WebSocketClient,
  handler?: MessageHandler
): ConnectionState {
  const [state, setState] = useState<ConnectionState>(client.getState());

  useEffect(() => {
    // Connect on mount
    client.connect();

    // Subscribe to state changes
    const unsubscribeState = client.onStateChange(setState);

    // Subscribe to messages if handler provided
    const unsubscribeMessage = handler ? client.onMessage(handler) : undefined;

    // Cleanup on unmount
    return () => {
      unsubscribeState();
      unsubscribeMessage?.();
      // Don't disconnect - let other components use the connection
    };
  }, [client, handler]);

  return state;
}

/**
 * Hook to send messages via WebSocket
 */
export function useWebSocketSend(client: WebSocketClient) {
  return useCallback(
    (message: unknown) => {
      client.send(message);
    },
    [client]
  );
}

/**
 * Hook to subscribe to specific message types
 */
export function useWebSocketMessage<T extends WebSocketMessage>(
  client: WebSocketClient,
  messageType: T["type"],
  handler: (message: T) => void
): void {
  useEffect(() => {
    const typedHandler: MessageHandler = (message) => {
      if (message.type === messageType) {
        handler(message as T);
      }
    };

    const unsubscribe = client.onMessage(typedHandler);
    return unsubscribe;
  }, [client, messageType, handler]);
}
