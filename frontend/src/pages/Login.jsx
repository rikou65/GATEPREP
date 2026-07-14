import React, { useState } from "react";
import {
  GraduationCap,
  Check,
  ArrowRight,
  Loader2,
  UserPlus,
  KeyRound,
  Eye,
  EyeOff,
  Code2,
  Lock,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useAuthApiActions } from "@/features/auth/hooks/useAuth";
import { isSupabaseEnabled, supabase } from "@/lib/supabase";
import { setSupabaseToken } from "@/lib/api";
import { toast } from "sonner";
import { consumeAuthReturnTo, setAuthReturnTo } from "@/lib/routeMemory";

const driveSyncKey = (userId) =>
  userId ? `driveSyncNeeded:${userId}` : null;

const featureItems = [
  {
    title: "Question bank",
    text: "Curated and topic-wise questions",
  },
  {
    title: "PYQs",
    text: "Past-year papers with solutions",
  },
  {
    title: "Playlists",
    text: "Structured learning paths",
  },
  {
    title: "Progress tracker",
    text: "Stay consistent, improve daily",
  },
];

export default function Login() {
  const [loading, setLoading] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState("login");
  const [rememberMe, setRememberMe] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const { setUser } = useAuth();
  const authActions = useAuthApiActions();
  const isDevelopment = import.meta.env.DEV;

  const establishSupabaseSession = async (session) => {
    if (!session?.access_token) {
      toast.error("No Supabase session returned. Check your email verification settings.");
      return;
    }
    setSupabaseToken(session.access_token);
    const result = await authActions.supabaseSession({
      access_token: session.access_token,
    });
    if (result?.user) {
      setUser(result.user);
      window.location.href = consumeAuthReturnTo();
      return;
    }
    toast.error("Could not start app session.");
  };

  const handleGoogleSignIn = async () => {
    if (isSupabaseEnabled()) {
      setAuthReturnTo("/dashboard");
      const redirectTo = `${window.location.origin}/auth/callback`;
      await supabase.auth.signOut({ scope: "local" }).catch(() => {});
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo,
          queryParams: {
            prompt: "select_account",
          },
        },
      });
      if (error) {
        toast.error(error.message || "Google sign-in failed.");
      }
      return;
    }

    try {
      const result = await authActions.legacyGoogleUrl();
      const url = result?.authorization_url;
      if (url) {
        setAuthReturnTo("/dashboard");
        window.location.href = url;
      } else {
        toast.error("Failed to get sign-in URL.");
      }
    } catch {
      toast.error("Sign-in service unavailable.");
    }
  };

  const handleEmailLogin = async () => {
    if (!isSupabaseEnabled()) return toast.error("Supabase is not configured.");
    if (!email || !password) return toast.error("Enter email and password.");
    setAuthLoading(true);
    try {
      setAuthReturnTo("/dashboard");
      const { data, error } = await supabase.auth.signInWithPassword({
        email: email.trim(),
        password,
      });
      if (error) throw error;
      await establishSupabaseSession(data.session);
    } catch (e) {
      toast.error(e?.message || "Email login failed.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleEmailSignup = async () => {
    if (!isSupabaseEnabled()) return toast.error("Supabase is not configured.");
    if (!email || !password) return toast.error("Enter email and password.");
    setAuthLoading(true);
    try {
      setAuthReturnTo("/dashboard");
      const redirectTo = `${window.location.origin}/auth/callback`;
      const { data, error } = await supabase.auth.signUp({
        email: email.trim(),
        password,
        options: { emailRedirectTo: redirectTo },
      });
      if (error) throw error;
      if (data.session) {
        await establishSupabaseSession(data.session);
      } else {
        toast.success("Account created. Check your email to confirm your account.");
      }
    } catch (e) {
      toast.error(e?.message || "Signup failed.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handlePasswordReset = async () => {
    if (!isSupabaseEnabled()) return toast.error("Supabase is not configured.");
    if (!email) return toast.error("Enter your email first.");
    setAuthLoading(true);
    try {
      const redirectTo = `${window.location.origin}/auth/callback`;
      const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), {
        redirectTo,
      });
      if (error) throw error;
      toast.success("Password reset email sent.");
    } catch (e) {
      toast.error(e?.message || "Could not send reset email.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleDevLogin = async () => {
    setLoading(true);
    try {
      const result = await authActions.devLogin();
      if (result?.user) {
        const user = result.user;
        setUser(user);
        const syncKey = driveSyncKey(user?.user_id);
        if (syncKey) localStorage.removeItem(syncKey);
        window.location.href = "/dashboard";
      }
    } catch {
      toast.error("Local login failed. Make sure your backend is running on port 8001.");
    } finally {
      setLoading(false);
    }
  };

  const submitLabel = mode === "signup" ? "Create account" : "Log in";
  const submitIcon = mode === "signup" ? UserPlus : ArrowRight;
  const SubmitIcon = submitIcon;

  return (
    <div className="h-screen overflow-hidden bg-[#f6f1e1] text-[#1b2233]">
      <main className="grid h-full w-full grid-cols-1 overflow-hidden bg-[#f6f1e1] lg:grid-cols-[1.02fr_34px_1fr]">
        <section className="relative hidden min-h-0 overflow-hidden bg-[linear-gradient(155deg,#121727_0%,#1f2433_100%)] px-14 py-8 text-[#f6f1e1] lg:flex lg:flex-col">
          <div className="absolute inset-0 opacity-[0.045] [background-image:linear-gradient(#f6f1e1_1px,transparent_1px),linear-gradient(90deg,#f6f1e1_1px,transparent_1px)] [background-size:42px_42px]" />
          <div className="absolute bottom-0 right-0 h-80 w-80 bg-[radial-gradient(circle,rgba(201,154,62,.1),transparent_60%)]" />

          <div className="relative z-10 mb-7 flex items-center justify-between">
            <div className="flex items-center gap-4 font-mono text-3xl font-semibold tracking-[0.04em]">
              <GraduationCap className="h-12 w-12" strokeWidth={1.7} />
              GATEPREP
            </div>
            <div className="flex h-12 items-center rounded-md bg-[#e1c77e] px-5 font-mono text-base font-semibold tracking-[0.08em] text-[#1b2233]">
              GATE · CSE
            </div>
          </div>

          <div className="relative z-10 my-auto">
            <div className="mb-4 flex items-center gap-3 font-mono text-xs uppercase tracking-[0.16em] text-[#e1c77e]">
              <span className="h-[7px] w-[7px] rounded-full bg-[#e1c77e] shadow-[0_0_0_4px_rgba(201,154,62,.18)]" />
              Admit card
            </div>
            <h1 className="max-w-[460px] font-serif text-[36px] font-semibold leading-[1.08] tracking-[-0.01em] xl:text-[42px]">
              Your ticket to <br />
              <span className="italic text-[#e1c77e]">GATE CSE</span> mastery.
            </h1>
            <p className="mt-3 max-w-[42ch] text-[15px] leading-[1.55] text-[#f6f1e1]/65">
              One syllabus-aligned workspace for question banks, PYQs, playlists and notes — built to get you through exam day, not just through the syllabus.
            </p>

            <ul className="mt-6 border-y border-[#f6f1e1]/15">
              {featureItems.map(({ title, text }, index) => (
                <li
                  key={title}
                  className={`flex gap-4 py-3 ${index !== featureItems.length - 1 ? "border-b border-[#f6f1e1]/15" : ""}`}
                >
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border border-[#e1c77e] text-[#e1c77e]">
                    <Check className="h-3 w-3" strokeWidth={2.4} />
                  </span>
                  <span>
                    <span className="block text-sm font-semibold">{title}</span>
                    <span className="mt-0.5 block text-[12.5px] text-[#f6f1e1]/62">{text}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="relative z-10 mt-5 flex items-center justify-between">
            <div className="flex h-20 w-20 rotate-[-9deg] items-center justify-center rounded-full border border-dashed border-[#c99a3e]/60 p-2 text-center font-mono text-[7.5px] uppercase leading-[1.45] tracking-[0.06em] text-[#e1c77e]">
              Valid for<br />all attempts<br />· 2027 ·
            </div>
            <div className="text-right font-mono text-[11px] leading-[1.7] text-[#f6f1e1]/60">
              SEAT NO. <b className="text-[#f6f1e1]">GP-CSE-2027</b><br />
              WORKSPACE <b className="text-[#f6f1e1]">PERSONAL</b>
            </div>
          </div>
        </section>

        <div className="relative hidden bg-[#f6f1e1] lg:flex lg:items-center lg:justify-center" aria-hidden="true">
          <div className="absolute inset-y-0 left-1/2 border-l-2 border-dashed border-[#1b2233]/20" />
        </div>

        <section className="flex h-full min-h-0 items-center justify-center overflow-hidden bg-[#f6f1e1] px-7 py-8 lg:px-14">
          <div className="w-full max-w-[430px]">
            <div className="mb-8 flex items-center justify-between lg:hidden">
              <div className="flex items-center gap-3 font-mono text-2xl font-semibold tracking-[0.04em]">
                <GraduationCap className="h-10 w-10" strokeWidth={1.7} />
                GATEPREP
              </div>
              <div className="flex h-10 items-center rounded-md bg-[#e1c77e] px-4 font-mono text-sm font-semibold tracking-[0.08em] text-[#1b2233]">
                GATE · CSE
              </div>
            </div>

            <div className="mb-8">
              <h2 className="font-serif text-[32px] font-semibold tracking-[-0.01em] text-[#1b2233]">
                {mode === "signup" ? "Create account" : mode === "reset" ? "Reset password" : "Welcome back"}
              </h2>
              {mode === "reset" && (
                <button
                  type="button"
                  onClick={() => setMode("login")}
                  className="mt-2 font-mono text-[11px] font-semibold uppercase tracking-[0.08em] text-[#9c3b2e] hover:underline"
                >
                  Back to sign in
                </button>
              )}
              <p className="mt-2 text-sm text-[#1b2233]/55">
                {mode !== "signup" && mode !== "reset" ? (
                  <>
                    New to GATEPREP?{" "}
                    <button
                      type="button"
                      onClick={() => setMode("signup")}
                      className="border-b border-[#9c3b2e]/35 font-semibold text-[#9c3b2e] hover:border-[#9c3b2e]"
                    >
                      Create an account
                    </button>
                  </>
                ) : mode === "signup" ? (
                  <>
                    Already have an account?{" "}
                    <button
                      type="button"
                      onClick={() => setMode("login")}
                      className="border-b border-[#9c3b2e]/35 font-semibold text-[#9c3b2e] hover:border-[#9c3b2e]"
                    >
                      Log in
                    </button>
                  </>
                ) : null}
              </p>
            </div>

            <div className="space-y-[18px]">
              <label className="block">
                <span className="mb-2 block font-mono text-[11px] uppercase tracking-[0.08em] text-[#1b2233]/55">
                  Email or roll number
                </span>
                <span className="block rounded-[9px] border-[1.5px] border-[#1b2233]/15 bg-white transition focus-within:border-[#9c3b2e] focus-within:ring-4 focus-within:ring-[#9c3b2e]/10">
                  <input
                    type="text"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="username"
                    className="h-[48px] w-full rounded-[9px] bg-transparent px-3.5 text-[14.5px] text-[#1b2233] outline-none placeholder:text-[#1b2233]/35"
                  />
                </span>
              </label>

              {mode !== "reset" && (
                <label className="block">
                  <span className="mb-2 block font-mono text-[11px] uppercase tracking-[0.08em] text-[#1b2233]/55">
                    Password
                  </span>
                  <span className="relative block rounded-[9px] border-[1.5px] border-[#1b2233]/15 bg-white transition focus-within:border-[#9c3b2e] focus-within:ring-4 focus-within:ring-[#9c3b2e]/10">
                    <input
                      type={showPassword ? "text" : "password"}
                      placeholder={mode === "signup" ? "Create your password" : "Enter your password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      autoComplete={mode === "signup" ? "new-password" : "current-password"}
                      className="h-[48px] w-full rounded-[9px] bg-transparent px-3.5 pr-12 text-[14.5px] text-[#1b2233] outline-none placeholder:text-[#1b2233]/35"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((value) => !value)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-1 text-[#1b2233]/55 transition hover:bg-[#ece4cc]"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                    </button>
                  </span>
                </label>
              )}

              {mode === "login" && (
                <div className="flex items-center justify-between gap-4 py-1 text-[13.5px]">
                  <label className="flex cursor-pointer items-center gap-2 text-[#1b2233]/55">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="h-4 w-4 cursor-pointer accent-[#9c3b2e]"
                    />
                    Keep me signed in
                  </label>
                  <button
                    type="button"
                    onClick={() => setMode("reset")}
                    className="font-semibold text-[#9c3b2e] hover:underline"
                  >
                    Forgot password?
                  </button>
                </div>
              )}

              <button
                type="button"
                onClick={mode === "reset" ? handlePasswordReset : mode === "signup" ? handleEmailSignup : handleEmailLogin}
                disabled={authLoading}
                className="flex h-[50px] w-full items-center justify-center gap-2.5 rounded-[9px] bg-[#9c3b2e] px-5 font-mono text-[13.5px] font-semibold uppercase tracking-[0.09em] text-[#f6f1e1] shadow-[0_8px_20px_-8px_rgba(156,59,46,.55)] transition hover:-translate-y-px hover:bg-[#7e2e23] disabled:cursor-not-allowed disabled:opacity-70"
              >
                {authLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : mode === "reset" ? (
                  <KeyRound className="h-4 w-4" />
                ) : (
                  <SubmitIcon className="h-4 w-4" />
                )}
                {mode === "reset" ? "Send reset email" : mode === "signup" ? submitLabel : "Sign in"}
              </button>

              <div className="flex items-center gap-3 py-1 font-mono text-[11px] uppercase tracking-[0.08em] text-[#1b2233]/55">
                <div className="h-px flex-1 bg-[#1b2233]/15" />
                Or continue with
                <div className="h-px flex-1 bg-[#1b2233]/15" />
              </div>

              <button
                type="button"
                data-testid="google-signin-btn"
                onClick={handleGoogleSignIn}
                className="flex h-[48px] w-full items-center justify-center gap-2.5 rounded-[9px] border-[1.5px] border-[#1b2233]/15 bg-white text-sm font-semibold text-[#1b2233] transition hover:bg-[#ece4cc]"
              >
                <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" aria-hidden="true">
                  <path fill="#4285F4" d="M23.52 12.27c0-.85-.08-1.67-.22-2.45H12v4.64h6.47a5.54 5.54 0 0 1-2.4 3.63v3h3.87c2.27-2.09 3.58-5.17 3.58-8.82Z" />
                  <path fill="#34A853" d="M12 24c3.24 0 5.96-1.07 7.95-2.91l-3.87-3c-1.08.72-2.45 1.15-4.08 1.15-3.13 0-5.79-2.11-6.74-4.96H1.27v3.1A12 12 0 0 0 12 24Z" />
                  <path fill="#FBBC05" d="M5.26 14.28A7.2 7.2 0 0 1 4.88 12c0-.79.14-1.56.38-2.28v-3.1H1.27A12 12 0 0 0 0 12c0 1.94.46 3.77 1.27 5.38l3.99-3.1Z" />
                  <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.23 0 12 0 7.31 0 3.26 2.7 1.27 6.62l3.99 3.1C6.21 6.86 8.87 4.75 12 4.75Z" />
                </svg>
                Continue with Google
              </button>

              {isDevelopment && (
                <button
                  type="button"
                  onClick={handleDevLogin}
                  className="flex h-[48px] w-full items-center justify-center rounded-[9px] border-[1.5px] border-dashed border-[#1b2233]/15 bg-transparent px-4 text-sm font-semibold text-[#1b2233] transition hover:bg-[#ece4cc] disabled:cursor-not-allowed disabled:opacity-70"
                  disabled={loading}
                >
                  {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Code2 className="mr-2 h-4 w-4 text-[#9c3b2e]" />}
                  Quick Access (Dev Mode)
                </button>
              )}

              <p className="flex items-center justify-center gap-2 pt-2 text-xs text-[#1b2233]/55">
                <Lock className="h-3.5 w-3.5" />
                Secure and private — your data stays yours.
              </p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
