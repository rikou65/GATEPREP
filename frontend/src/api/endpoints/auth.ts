import { api, unwrap } from "@/api/http";
import type { AuthSession } from "@/types/api";

export const authApi = {
  me: () => unwrap<{ user: AuthSession["user"] }>(api.get("/auth/me")),
  logout: () => unwrap(api.post("/auth/logout")),
  devLogin: () => unwrap<AuthSession>(api.post("/auth/dev-login")),
  legacyGoogleUrl: () => unwrap<{ authorization_url: string }>(api.get("/auth/google-url")),
  legacyGoogleSession: (payload: { code: string; state: string }) =>
    unwrap<AuthSession>(api.post("/auth/session", payload)),
  supabaseSession: (payload: { access_token: string }) =>
    unwrap<AuthSession>(api.post("/auth/supabase-session", payload)),
};
