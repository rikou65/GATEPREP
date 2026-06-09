import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { LogOut, HardDrive, CheckCircle2, Plug } from "lucide-react";
import { toast } from "sonner";

export default function Settings() {
  const { user, logout } = useAuth();
  const [drive, setDrive] = useState(null);
  const [search, setSearch] = useSearchParams();

  const loadDrive = () => api.get("/drive/status").then(r => setDrive(r.data?.data));
  useEffect(() => { loadDrive(); }, []);

  useEffect(() => {
    if (search.get("drive") === "connected") {
      toast.success("Google Drive connected");
      loadDrive();
      search.delete("drive");
      setSearch(search, { replace: true });
    } else if (search.get("drive") === "error") {
      toast.error("Google Drive connection failed");
      search.delete("drive");
      setSearch(search, { replace: true });
    }
  }, [search, setSearch]);

  const connectDrive = async () => {
    try {
      const r = await api.get("/drive/connect");
      window.location.href = r.data?.data?.authorization_url;
    } catch {
      toast.error("Failed to start Drive connection");
    }
  };

  const disconnectDrive = async () => {
    if (!window.confirm("Disconnect Google Drive? Files stay in your Drive; new uploads will be disabled.")) return;
    try {
      await api.post("/drive/disconnect");
      toast.success("Disconnected");
      loadDrive();
    } catch { toast.error("Disconnect failed"); }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Account</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-1">Settings</h1>
      </div>

      <div className="border border-border rounded-lg p-5 space-y-3">
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Profile</div>
        <div className="flex items-center gap-4">
          {user?.picture && <img src={user.picture} alt="" className="w-12 h-12 rounded-full border border-border" />}
          <div>
            <div className="text-sm font-medium">{user?.name}</div>
            <div className="text-xs text-muted-foreground mono">{user?.email}</div>
            {user?.is_admin && <div className="text-[10px] mono text-emerald-500 mt-1">ADMIN</div>}
          </div>
        </div>
      </div>

      <div className="border border-border rounded-lg p-5 space-y-4" data-testid="drive-section">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Storage</div>
            <div className="flex items-center gap-2 mt-1">
              <HardDrive className="w-4 h-4" />
              <h2 className="text-base font-semibold">Google Drive</h2>
              {drive?.connected && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
            </div>
            <p className="text-xs text-muted-foreground mt-2 max-w-md">
              Resource files (PDFs, notes, formula sheets) get uploaded to a <code className="mono">GATEPREP/</code> folder
              inside <em>your</em> Drive. Scope <code className="mono">drive.file</code> — we cannot see any of your other files.
            </p>
          </div>
          {drive?.connected ? (
            <Button variant="outline" size="sm" onClick={disconnectDrive} data-testid="drive-disconnect-btn">
              Disconnect
            </Button>
          ) : (
            <Button size="sm" onClick={connectDrive} data-testid="drive-connect-btn">
              <Plug className="w-3.5 h-3.5 mr-1" /> Connect Drive
            </Button>
          )}
        </div>
        {drive?.connected && (
          <div className="text-xs mono border-l-2 border-emerald-500 pl-3 py-1 bg-emerald-500/5">
            Connected as <span className="text-foreground">{drive.drive_email || "your Google account"}</span>
            {drive.connected_at && <span className="text-muted-foreground"> · since {new Date(drive.connected_at).toLocaleDateString()}</span>}
          </div>
        )}
      </div>

      <div className="border border-border rounded-lg p-5">
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Session</div>
        <Button variant="outline" onClick={logout} data-testid="settings-logout-btn">
          <LogOut className="w-4 h-4 mr-1" /> Sign out
        </Button>
      </div>
    </div>
  );
}
