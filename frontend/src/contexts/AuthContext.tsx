/**
 * Authentication context for optional HTTP Basic Auth
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { setAuthHeader, clearAuthHeader, hasAuth } from "../api/client";

interface AuthContextType {
  isAuthenticated: boolean;
  authRequired: boolean | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  checkAuth: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(hasAuth());
  const [authRequired, setAuthRequired] = useState<boolean | null>(null);

  const login = useCallback(async (username: string, password: string) => {
    try {
      setAuthHeader(username, password);

      // Test the credentials with a health check
      const response = await fetch("http://localhost:8000/api/v1/health", {
        headers: {
          Authorization: `Basic ${btoa(`${username}:${password}`)}`,
        },
      });

      if (response.ok) {
        setIsAuthenticated(true);
        return true;
      } else {
        clearAuthHeader();
        setIsAuthenticated(false);
        return false;
      }
    } catch (error) {
      console.error("Login failed:", error);
      clearAuthHeader();
      setIsAuthenticated(false);
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    clearAuthHeader();
    setIsAuthenticated(false);
  }, []);

  const checkAuth = useCallback(async () => {
    if (!hasAuth()) {
      setIsAuthenticated(false);
      return false;
    }

    try {
      const response = await fetch("http://localhost:8000/api/v1/health");
      const authenticated = response.ok;
      setIsAuthenticated(authenticated);
      return authenticated;
    } catch (error) {
      console.error("Auth check failed:", error);
      setIsAuthenticated(false);
      return false;
    }
  }, []);

  // Check if backend requires authentication on mount
  useEffect(() => {
    const checkAuthRequired = async () => {
      try {
        const response = await fetch("/api/v1/health");
        const data = await response.json();
        const authEnabled = data.data?.auth_enabled ?? false;

        setAuthRequired(authEnabled);

        // If auth is not required, auto-authenticate
        if (!authEnabled) {
          setIsAuthenticated(true);
        }
      } catch (error) {
        console.error("Failed to check auth status:", error);
        // On error, assume auth is not required (fail open for better UX)
        setAuthRequired(false);
        setIsAuthenticated(true);
      }
    };

    checkAuthRequired();
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, authRequired, login, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
