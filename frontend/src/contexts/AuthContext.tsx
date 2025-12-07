/**
 * Authentication context for optional HTTP Basic Auth
 */

import React, { createContext, useContext, useState, useCallback } from "react";
import { setAuthHeader, clearAuthHeader, hasAuth } from "../api/client";

interface AuthContextType {
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  checkAuth: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(hasAuth());

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

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout, checkAuth }}>
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
