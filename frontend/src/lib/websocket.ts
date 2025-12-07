/**
 * WebSocket client with automatic reconnection and typed message handling
 */

import type { ConnectionState, MessageHandler, WSMessage } from "../types/websocket";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectTimeout: number | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000; // Start with 1 second
  private maxReconnectDelay = 30000; // Max 30 seconds

  private messageHandlers: Set<MessageHandler> = new Set();
  private stateChangeHandlers: Set<(state: ConnectionState) => void> =
    new Set();
  private currentState: ConnectionState = "disconnected";
  private endpoint: string;

  constructor(endpoint: string) {
    this.endpoint = endpoint;
  }

  /**
   * Connect to WebSocket server
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    this.setState("connecting");

    try {
      this.ws = new WebSocket(`${WS_URL}${this.endpoint}`);

      this.ws.onopen = () => {
        console.log(`WebSocket connected: ${this.endpoint}`);
        this.reconnectAttempts = 0;
        this.setState("connected");
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error("Failed to parse WebSocket message:", error);
        }
      };

      this.ws.onerror = (error) => {
        console.error(`WebSocket error on ${this.endpoint}:`, error);
        this.setState("error");
      };

      this.ws.onclose = () => {
        console.log(`WebSocket closed: ${this.endpoint}`);
        this.ws = null;
        this.scheduleReconnect();
      };
    } catch (error) {
      console.error(`Failed to create WebSocket: ${this.endpoint}`, error);
      this.setState("error");
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    if (this.reconnectTimeout !== null) {
      window.clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.setState("disconnected");
  }

  /**
   * Send a message to the server
   */
  send(message: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn("WebSocket not connected, message not sent");
    }
  }

  /**
   * Add a message handler
   */
  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  /**
   * Add a state change handler
   */
  onStateChange(handler: (state: ConnectionState) => void): () => void {
    this.stateChangeHandlers.add(handler);
    handler(this.currentState); // Immediately notify of current state
    return () => this.stateChangeHandlers.delete(handler);
  }

  /**
   * Get current connection state
   */
  getState(): ConnectionState {
    return this.currentState;
  }

  private handleMessage(message: WSMessage): void {
    this.messageHandlers.forEach((handler) => {
      try {
        handler(message);
      } catch (error) {
        console.error("Message handler error:", error);
      }
    });
  }

  private setState(state: ConnectionState): void {
    this.currentState = state;
    this.stateChangeHandlers.forEach((handler) => {
      try {
        handler(state);
      } catch (error) {
        console.error("State change handler error:", error);
      }
    });
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error(
        `Max reconnect attempts (${this.maxReconnectAttempts}) reached for ${this.endpoint}`
      );
      this.setState("error");
      return;
    }

    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectDelay
    );

    console.log(
      `Scheduling reconnect in ${delay}ms (attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`
    );

    this.reconnectAttempts++;
    this.setState("reconnecting");

    this.reconnectTimeout = window.setTimeout(() => {
      this.reconnectTimeout = null;
      this.connect();
    }, delay);
  }
}

/**
 * Global WebSocket client for unified endpoint
 */
export const wsClient = new WebSocketClient("/api/v1/ws");
