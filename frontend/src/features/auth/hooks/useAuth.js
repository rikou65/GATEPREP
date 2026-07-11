import { useCallback, useEffect, useMemo, useState } from "react";
import { authApi } from "@/api/endpoints/auth";
import { isSupabaseEnabled, supabase } from "@/lib/supabase";

export function useAuthProvider() {
  const [user, setUserState] = useState(null);
  const [loading, setLoading] = useState(true);

  const setUser = useCallback((u) => {
    setUserState(u);
    if (u) {
      localStorage.setItem("user", JSON.stringify(u));
    } else {
      localStorage.removeItem("user");
    }
  }, []);

  const checkAuth = useCallback(async () => {
    try {
      const result = await authApi.me();
      setUser(result?.user || null);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [setUser]);

  useEffect(() => {
    const cached = localStorage.getItem("user");
    if (cached) {
      try {
        setUserState(JSON.parse(cached));
      } catch {}
    }

    if (isSupabaseEnabled()) {
      supabase.auth.getSession().then(({ data: { session } }) => {
        if (session) {
          authApi
            .supabaseSession({
              access_token: session.access_token,
            })
            .then((result) => {
              if (result?.user) {
                setUser(result.user);
              }
            })
            .catch(() => {})
            .finally(() => setLoading(false));
        } else {
          checkAuth();
        }
      });
    } else {
      if (window.location.hash?.includes("session_id=")) {
        setLoading(false);
        return;
      }
      checkAuth();
    }
  }, [checkAuth]);

  const logout = useCallback(async () => {
    try {
      if (isSupabaseEnabled()) {
        await supabase.auth.signOut();
      }
      await authApi.logout();
    } catch {}
    setUser(null);
    localStorage.removeItem("user");
    window.location.href = "/";
  }, [setUser]);

  return { user, setUser, loading, checkAuth, logout };
}

export function useAuthApiActions() {
  return useMemo(() => ({
    me: authApi.me,
    devLogin: authApi.devLogin,
    logout: authApi.logout,
    legacyGoogleUrl: authApi.legacyGoogleUrl,
    legacyGoogleSession: authApi.legacyGoogleSession,
    supabaseSession: authApi.supabaseSession,
  }), []);
}
