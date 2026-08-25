import axios from "axios";

const RAW_BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "").trim();
const BACKEND_URL = RAW_BACKEND_URL.replace(/\/+$/, "");
export const API_BASE = BACKEND_URL ? (BACKEND_URL.endsWith("/api") ? BACKEND_URL : `${BACKEND_URL}/api`) : "/api";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
});

// Attach JWT token when present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("sf_token");
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function getErrorMessage(error, fallback = "An unexpected error occurred") {
  if (!error) return fallback;
  if (typeof error === "string") return error;
  const detail = error?.response?.data?.detail || error?.response?.data?.message || error?.message;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => (typeof d === "string" ? d : d?.msg || JSON.stringify(d))).join(", ");
  }
  if (detail && typeof detail === "object") {
    return detail.msg || detail.message || JSON.stringify(detail);
  }
  return fallback;
}

// Global 401 handler and error message normalizer
api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem("sf_token");
    }
    if (error) {
      error.normalizedMessage = getErrorMessage(error);
    }
    return Promise.reject(error);
  }
);
