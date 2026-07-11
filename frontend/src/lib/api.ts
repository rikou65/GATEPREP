import axios, { type AxiosError } from "axios";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8001";
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

let supabaseToken: string | null = null;

export function setSupabaseToken(token: string | null) {
  supabaseToken = token;
}

api.interceptors.request.use((config) => {
  if (supabaseToken) {
    config.headers.Authorization = `Bearer ${supabaseToken}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => Promise.reject(error)
);

export default api;
