import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { GraduationCap, ArrowRight, BookOpen, Brain, BarChart3, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function Login() {
  const [loading, setLoading] = useState(false);
  const { setUser } = useAuth();

  const handleSignIn = () => {
    const clientId = "522307348549-g2f69df6qu1uqn28uqf70sq51uvm42bl.apps.googleusercontent.com";
    const redirectUri = encodeURIComponent("http://127.0.0.1:3000/auth/callback");
    const scope = encodeURIComponent("openid email profile");
    window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${redirectUri}&response_type=code&scope=${scope}&access_type=offline&prompt=consent`;
  };

  const handleDevLogin = async () => {
    setLoading(true);
    try {
      const r = await api.post("/auth/dev-login");
      if (r.data?.success) {
        setUser(r.data.data.user);
        localStorage.setItem("driveSyncNeeded", "true");
        window.location.href = "/dashboard";
      }
    } catch {
      alert("Local login failed. Make sure your backend is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground dark relative overflow-hidden">
      <div className="absolute inset-0 bg-dot-grid opacity-30" />
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-foreground/20 to-transparent" />

      <header className="relative z-10 px-8 py-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GraduationCap className="w-6 h-6" />
          <span className="font-bold tracking-tight">GATEPREP</span>
        </div>
        <span className="text-xs mono text-muted-foreground">v1.0</span>
      </header>

      <main className="relative z-10 max-w-5xl mx-auto px-8 pt-16 pb-24">
        <div className="grid md:grid-cols-5 gap-12 items-start">
          <div className="md:col-span-3 space-y-8 page-enter">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 border border-border rounded-full text-xs mono text-muted-foreground mb-6">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                Personal study platform · not a coaching platform
              </div>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.05]">
                Your personal
                <br />
                <span className="text-muted-foreground">GATEPREP dashboard</span>
                <br />
                for GATE.
              </h1>
              <p className="mt-6 text-base text-muted-foreground max-w-xl leading-relaxed">
                Subjects, topics, question banks, PYQs, playlists, notes and mistakes — all wired
                together. Progress derived from what you actually solve, not from manual statuses.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Button
                data-testid="google-signin-btn"
                onClick={handleSignIn}
                className="h-12 px-6 text-sm font-medium group"
              >
                Continue with Google
                <ArrowRight className="ml-2 w-4 h-4 transition-transform group-hover:translate-x-0.5" />
              </Button>
              
              <Button
                variant="outline"
                onClick={handleDevLogin}
                className="h-12 px-6 text-sm font-medium border-dashed"
                disabled={loading}
              >
                {loading && <Loader2 className="mr-2 w-4 h-4 animate-spin" />}
                Quick Access (Dev Mode)
              </Button>
            </div>
          </div>

          <div className="md:col-span-2 space-y-3">
            {[
              { icon: BookOpen, t: "Subject → Topic", d: "Official GATE CSE syllabus. System-owned. No drift." },
              { icon: Brain, t: "MCQ · MSQ · NAT", d: "Inline solutions, personal notes, attempt history." },
              { icon: BarChart3, t: "Separate analytics", d: "Question Bank and PYQs tracked independently." },
            ].map((f, i) => (
              <div key={i} className="border border-border rounded-lg p-5 bg-card/40 backdrop-blur-sm">
                <f.icon className="w-5 h-5 mb-3" strokeWidth={1.5} />
                <div className="font-medium text-sm">{f.t}</div>
                <div className="text-xs text-muted-foreground mt-1">{f.d}</div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
