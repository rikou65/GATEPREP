import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { LogOut, HardDrive, CheckCircle2, Plug, RefreshCw } from "lucide-react";
import { toast } from "sonner";

export default function Settings() {
  const { user, logout } = useAuth();
  const [drive, setDrive] = useState(null);
  const [search, setSearch] = useSearchParams();
  const [syncing, setSyncing] = useState(false);
  const [lastSync, setLastSync] = useState(null);

  const loadDrive = () => api.get("/drive/status").then(r => setDrive(r.data?.data));
  useEffect(() => { loadDrive(); }, []);

  const runSync = async (silent = false) => {
    setSyncing(true);
    try {
      const r = await api.post("/drive/sync");
      const d = r.data?.data || {};
      setLastSync(d);
      if (!silent) {
        if (d.error === "no_gateprep_folder") {
          toast.info("No existing GATEPREP folder found in your Drive.");
        } else if (d.synced > 0) {
          toast.success(`Restored ${d.synced} file${d.synced === 1 ? "" : "s"} from your Drive`);
        } else {
          toast.info("Drive is in sync — nothing new to import.");
        }
      }
    } catch (e) {
      if (!silent) toast.error("Drive sync failed: " + (e?.response?.data?.error?.message || e.message));
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    const status = search.get("drive");
    if (!status) return;
    // Defer state mutations out of the effect tick so React 19's strict
    // "set-state-in-effect" rule is satisfied while we clear the query param.
    Promise.resolve().then(() => {
      if (status === "connected") {
        toast.success("Google Drive connected");
        loadDrive();
        runSync(true);
      } else if (status === "error") {
        toast.error("Google Drive connection failed");
      }
      search.delete("drive");
      setSearch(search, { replace: true });
    });
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
          <div className="flex flex-col gap-2 items-end">
            {drive?.connected ? (
              <>
                <Button variant="outline" size="sm" onClick={disconnectDrive} data-testid="drive-disconnect-btn">
                  Disconnect
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => runSync(false)}
                  disabled={syncing}
                  data-testid="drive-sync-btn"
                >
                  <RefreshCw className={`w-3.5 h-3.5 mr-1 ${syncing ? "animate-spin" : ""}`} />
                  {syncing ? "Syncing…" : "Sync from Drive"}
                </Button>
              </>
            ) : (
              <Button size="sm" onClick={connectDrive} data-testid="drive-connect-btn">
                <Plug className="w-3.5 h-3.5 mr-1" /> Connect Drive
              </Button>
            )}
          </div>
        </div>
        {drive?.connected && (
          <div className="text-xs mono border-l-2 border-emerald-500 pl-3 py-1 bg-emerald-500/5">
            Connected as <span className="text-foreground">{drive.drive_email || "your Google account"}</span>
            {drive.connected_at && <span className="text-muted-foreground"> · since {new Date(drive.connected_at).toLocaleDateString()}</span>}
          </div>
        )}
        {lastSync && (
          <div className="text-xs mono text-muted-foreground border border-border rounded px-3 py-2">
            Last sync: <span className="text-foreground">{lastSync.synced}</span> restored,{" "}
            <span className="text-foreground">{lastSync.skipped}</span> already tracked
            {Array.isArray(lastSync.unknown_subjects) && lastSync.unknown_subjects.length > 0 && (
              <div className="mt-1 text-amber-500">
                Skipped folders (no matching subject): {lastSync.unknown_subjects.join(", ")}
              </div>
            )}
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

