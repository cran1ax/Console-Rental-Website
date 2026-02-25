/**
 * Axios instance with JWT interceptors.
 *
 * • Reads the access token from localStorage.
 * • On 401, attempts a silent token refresh once before rejecting.
 */
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

/* ── Request: attach access token ──────────────────────────────── */
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

/* ── Response: silent refresh on 401 ───────────────────────────── */
let isRefreshing = false;
let pendingQueue = [];

const processQueue = (error, token = null) => {
  pendingQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token);
  });
  pendingQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pendingQueue.push({ resolve, reject });
      }).then((token) => {
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      });
    }

    original._retry = true;
    isRefreshing = true;

    const refresh = localStorage.getItem("refresh");
    if (!refresh) {
      isRefreshing = false;
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      window.location.href = "/login";
      return Promise.reject(error);
    }

    try {
      const { data } = await axios.post(`${API_BASE}/auth/token/refresh/`, {
        refresh,
      });
      localStorage.setItem("access", data.access);
      if (data.refresh) localStorage.setItem("refresh", data.refresh);
      processQueue(null, data.access);
      original.headers.Authorization = `Bearer ${data.access}`;
      return api(original);
    } catch (refreshError) {
      processQueue(refreshError, null);
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      window.location.href = "/login";
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

export default api;
