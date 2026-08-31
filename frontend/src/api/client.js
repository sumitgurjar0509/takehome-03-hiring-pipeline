import axios from "axios";

// In dev this falls back to the Vite proxy target; in production it's set
// via VITE_API_URL at build time (see .env.example).
const baseURL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({ baseURL });

const TOKEN_KEY = "hiring_pipeline_token";

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Centralized 401 handling: any expired/invalid token drops the user back
// to login rather than every page having to handle it individually.
let onUnauthorized = null;
export function registerUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && onUnauthorized) {
      onUnauthorized();
    }
    return Promise.reject(error);
  }
);
