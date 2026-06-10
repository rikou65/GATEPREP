import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
//
// Module-level guard: React 19 StrictMode in dev simulates a mount→unmount→mount cycle
// which RESETS useState/useRef state. A `useRef` flag inside the component will not survive
// that cycle, causing the same `session_id` to be exchanged twice — and the second exchange
// fails (one-time-use token) which bounces the user back to the login page even though the
// first exchange already established the session. Tracking processed session_ids at module
// scope survives the StrictMode remount.
const processedSessionIds = new Set();

export default function AuthCallback() {
  const navigate = useNavigate();
  const { setUser, checkAuth } = useAuth();

  useEffect(() => {
    const hash = window.location.hash || "";
    const match = hash.match(/session_id=([^&]+)/);
    if (!match) {
      navigate("/");
      return;
    }
    const sessionId = match[1];

    // If we've already exchanged this session_id in this page lifetime,
    // the cookie is set — just confirm via /auth/me and route to dashboard.
    if (processedSessionIds.has(sessionId)) {
      (async () => {
        await checkAuth();
        window.history.replaceState({}, "", "/dashboard");
        navigate("/dashboard", { replace: true });
      })();
      return;
    }
    processedSessionIds.add(sessionId);

    (async () => {
      try {
        const r = await api.post("/auth/session", { session_id: sessionId });
        setUser(r.data?.data?.user || null);
        window.history.replaceState({}, "", "/dashboard");
        navigate("/dashboard", { replace: true, state: { user: r.data?.data?.user } });
      } catch (e) {
        // The exchange failed. Before bouncing to login, check whether a session
        // was already established (e.g. a prior tab, or a successful first call
        // whose response we lost). If yes, route to dashboard instead.
        try {
          const me = await api.get("/auth/me");
          if (me?.data?.data?.user) {
            setUser(me.data.data.user);
            window.history.replaceState({}, "", "/dashboard");
            navigate("/dashboard", { replace: true });
            return;
          }
        } catch {}
        navigate("/", { replace: true });
      }
    })();
  }, [navigate, setUser, checkAuth]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
      <div className="text-center space-y-3">
        <div className="w-10 h-10 border-2 border-foreground/30 border-t-foreground rounded-full animate-spin mx-auto" />
        <p className="text-sm text-muted-foreground">Signing you in…</p>
      </div>
    </div>
  );
}
