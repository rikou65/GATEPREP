import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { setSupabaseToken } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useAuthApiActions } from "@/features/auth/hooks/useAuth";
import { isSupabaseEnabled, supabase } from "@/lib/supabase";
import { consumeAuthReturnTo } from "@/lib/routeMemory";
import { toast } from "sonner";

const processedSessionIds = new Set();
const driveSyncKey = (userId) =>
  userId ? `driveSyncNeeded:${userId}` : null;

export default function AuthCallback() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const authActions = useAuthApiActions();

  useEffect(() => {
    if (isSupabaseEnabled()) {
      let active = true;
      let completed = false;
      const urlParams = new URLSearchParams(window.location.search);

      const finishSupabaseSession = async (session) => {
        if (!active || completed || !session?.access_token) return;
        completed = true;
        setSupabaseToken(session.access_token);
        try {
          const result = await authActions.supabaseSession({
            access_token: session.access_token,
          });
          if (!active) return;
          if (result?.user) {
            setUser(result.user);
          }
          navigate(consumeAuthReturnTo(), { replace: true });
        } catch {
          if (active) navigate("/", { replace: true });
        }
      };

      const waitForStoredSession = async () => {
        for (let i = 0; i < 12; i += 1) {
          if (!active || completed) return;
          const { data } = await supabase.auth.getSession();
          if (data?.session) {
            await finishSupabaseSession(data.session);
            return;
          }
          await new Promise((resolve) => setTimeout(resolve, 250));
        }

        if (!active || completed) return;
        try {
          const result = await authActions.me();
          if (result?.user) {
            setUser(result.user);
            navigate(consumeAuthReturnTo(), { replace: true });
            return;
          }
        } catch {}
        toast.error("Google sign-in did not return a session. Please try again.");
        navigate("/", { replace: true });
      };

      const {
        data: { subscription },
      } = supabase.auth.onAuthStateChange(async (event, session) => {
        if (event === "SIGNED_IN" && session) {
          await finishSupabaseSession(session);
        }
      });

      const code = urlParams.get("code");
      if (code) {
        supabase.auth
          .exchangeCodeForSession(code)
          .then(({ data, error }) => {
            if (error) throw error;
            if (data?.session) return finishSupabaseSession(data.session);
            return waitForStoredSession();
          })
          .catch(() => {
            if (!active || completed) return;
            toast.error("Google sign-in failed. Please try again.");
            navigate("/", { replace: true });
          });
      } else {
        waitForStoredSession();
      }

      return () => {
        active = false;
        subscription.unsubscribe();
      };
    }

    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get("code");

    if (!code) {
      (async () => {
        try {
          const result = await authActions.me();
          if (result?.user) {
            setUser(result.user);
            navigate("/dashboard", { replace: true });
            return;
          }
        } catch {}
        navigate("/", { replace: true });
      })();
      return;
    }

    const state = urlParams.get("state") || "";
    handleLegacyCallback(code, state);
  }, [navigate, setUser]);

  function handleLegacyCallback(code, state) {
    if (processedSessionIds.has(code)) return;
    processedSessionIds.add(code);

    (async () => {
      try {
        const result = await authActions.legacyGoogleSession({ code, state });
        const user = result?.user || null;
        setUser(user);
        const syncKey = driveSyncKey(user?.user_id);
        if (syncKey) localStorage.setItem(syncKey, "true");
        window.location.href = "/dashboard";
      } catch {
        navigate("/", { replace: true });
      }
    })();
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
      <div className="text-center space-y-3">
        <div className="w-10 h-10 border-2 border-foreground/30 border-t-foreground rounded-full animate-spin mx-auto" />
        <p className="text-sm text-muted-foreground">Signing you in...</p>
      </div>
    </div>
  );
}
