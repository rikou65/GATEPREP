import axios from "axios";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

api.interceptors.response.use(
  (r) => r,
  (e) => {
    if (e?.response?.status === 401) {
      // let caller handle
    }
    return Promise.reject(e);
  }
);

export default api;
