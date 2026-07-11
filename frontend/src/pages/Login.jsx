import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  GraduationCap,
  ArrowRight,
  Loader2,
  Mail,
  UserPlus,
  KeyRound,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useAuthApiActions } from "@/features/auth/hooks/useAuth";
import { isSupabaseEnabled, supabase } from "@/lib/supabase";
import { setSupabaseToken } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { consumeAuthReturnTo, setAuthReturnTo } from "@/lib/routeMemory";

const driveSyncKey = (userId) =>
  userId ? `driveSyncNeeded:${userId}` : null;

export default function Login() {
  const [loading, setLoading] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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

  return (
    <div className="min-h-screen bg-background text-foreground dark relative overflow-hidden">
      <div className="absolute inset-0 bg-dot-grid opacity-30" />
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-foreground/20 to-transparent" />

      <header className="relative z-10 px-6 py-5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GraduationCap className="w-6 h-6" />
          <span className="font-bold tracking-tight">GATEPREP</span>
        </div>
        <span className="text-xs mono text-muted-foreground">GATE · CSE</span>
      </header>

      <main className="relative z-10 max-w-6xl mx-auto px-6 py-8 lg:py-12">
        <div className="grid lg:grid-cols-[1.05fr_0.95fr] gap-10 items-center min-h-[calc(100vh-120px)]">
          <section className="space-y-6 page-enter">
            <div className="inline-flex items-center gap-2 px-3 py-1 border border-border rounded-full text-xs mono text-muted-foreground">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Personal GATE CSE workspace
            </div>
            <div className="space-y-4">
              <h1 className="text-4xl lg:text-5xl xl:text-6xl font-bold tracking-tight leading-[1.05]">
                Study from one clean command center.
              </h1>
              <p className="text-base lg:text-lg text-muted-foreground max-w-2xl leading-relaxed">
                Organize subjects, PYQs, playlists, PDFs, notes, mistakes, and progress in one syllabus-aligned place.
              </p>
            </div>
            <div className="grid sm:grid-cols-3 gap-3 max-w-2xl">
              {["Question Bank", "PYQs", "Drive PDFs"].map((item) => (
                <div key={item} className="border border-border rounded-md px-4 py-3 bg-card/40 text-sm font-medium">
                  {item}
                </div>
              ))}
            </div>
          </section>

          <section className="border border-border rounded-lg bg-card/70 backdrop-blur-xl p-5 sm:p-6 shadow-2xl">
            <div className="space-y-1 mb-5">
              <h2 className="text-xl font-semibold tracking-tight">Sign in</h2>
              <p className="text-sm text-muted-foreground">Use Google or email to continue.</p>
            </div>
            <div className="space-y-4">
              <Button
                data-testid="google-signin-btn"
                onClick={handleGoogleSignIn}
                className="h-12 w-full px-6 text-sm font-medium group"
              >
                Continue with Google
                <ArrowRight className="ml-2 w-4 h-4 transition-transform group-hover:translate-x-0.5" />
              </Button>

              <Tabs defaultValue="login" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="login">Login</TabsTrigger>
                  <TabsTrigger value="signup">Sign up</TabsTrigger>
                  <TabsTrigger value="reset">Reset</TabsTrigger>
                </TabsList>
                <div className="mt-4 space-y-3">
                  <Input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                  />
                  <TabsContent value="login" className="space-y-3">
                    <Input
                      type="password"
                      placeholder="Password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      autoComplete="current-password"
                    />
                    <Button
                      onClick={handleEmailLogin}
                      disabled={authLoading}
                      variant="outline"
                      className="h-11 w-full"
                    >
                      {authLoading ? <Loader2 className="mr-2 w-4 h-4 animate-spin" /> : <Mail className="mr-2 w-4 h-4" />}
                      Login with email
                    </Button>
                  </TabsContent>
                  <TabsContent value="signup" className="space-y-3">
                    <Input
                      type="password"
                      placeholder="Create password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      autoComplete="new-password"
                    />
                    <Button
                      onClick={handleEmailSignup}
                      disabled={authLoading}
                      variant="outline"
                      className="h-11 w-full"
                    >
                      {authLoading ? <Loader2 className="mr-2 w-4 h-4 animate-spin" /> : <UserPlus className="mr-2 w-4 h-4" />}
                      Create account
                    </Button>
                  </TabsContent>
                  <TabsContent value="reset" className="space-y-3">
                    <Button
                      onClick={handlePasswordReset}
                      disabled={authLoading}
                      variant="outline"
                      className="h-11 w-full"
                    >
                      {authLoading ? <Loader2 className="mr-2 w-4 h-4 animate-spin" /> : <KeyRound className="mr-2 w-4 h-4" />}
                      Send reset email
                    </Button>
                  </TabsContent>
                </div>
              </Tabs>

              {isDevelopment && (
                <Button
                  variant="outline"
                  onClick={handleDevLogin}
                  className="h-11 w-full text-sm font-medium border-dashed"
                  disabled={loading}
                >
                  {loading && <Loader2 className="mr-2 w-4 h-4 animate-spin" />}
                  Quick Access (Dev Mode)
                </Button>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
