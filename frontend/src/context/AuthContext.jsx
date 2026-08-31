import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, getStoredToken, setStoredToken, registerUnauthorizedHandler } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // "loading" covers the initial /auth/me check on page load, so routes
  // don't flash a login screen before we know a stored token is still valid.
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    setStoredToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    registerUnauthorizedHandler(logout);
  }, [logout]);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .get("/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => setStoredToken(null))
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const res = await api.post("/auth/login", { email, password });
    setStoredToken(res.data.access_token);
    setUser(res.data.user);
    return res.data.user;
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
