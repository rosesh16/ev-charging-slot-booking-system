import { useState, useCallback } from "react";
import { loginApi, registerApi } from "../api/auth";
import { AuthContext } from "./useAuth";

/**
 * Authentication Provider for VoltSlot.
 * NOTE ON TOKEN STORAGE:
 * In accordance with security requirements, the token is held strictly in-memory
 * (React state) by default, protecting against XSS-based persistent token extraction.
 * Refreshing the browser page resets the in-memory session.
 *
 * NOTE ON LOGOUT:
 * The Django REST Framework backend uses default authtoken authentication without a
 * token-revocation or blacklist endpoint. Logout is handled client-side by discarding
 * the token and user state from memory.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const login = useCallback(async ({ email, password }) => {
    setLoading(true);
    setError(null);
    try {
      const response = await loginApi({ email, password });
      setToken(response.token);
      setUser(response.user);
      return { success: true, user: response.user };
    } catch (err) {
      const msg = err.message || "Failed to log in. Please check your credentials.";
      setError(msg);
      return { success: false, error: msg };
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async ({ email, username, password, phone_number }) => {
    setLoading(true);
    setError(null);
    try {
      const response = await registerApi({ email, username, password, phone_number });
      setToken(response.token);
      setUser(response.user);
      return { success: true, user: response.user };
    } catch (err) {
      const msg = err.message || "Registration failed. Please review your input.";
      setError(msg);
      return { success: false, error: msg };
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    // Client-side token discard (no DRF backend logout endpoint)
    setToken(null);
    setUser(null);
    setError(null);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value = {
    user,
    token,
    isAuthenticated: Boolean(token && user),
    loading,
    error,
    login,
    register,
    logout,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthProvider;
