import React, { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { queryClient } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import {
  useConnectDrive,
  useConnectYouTube,
  useDisconnectDrive,
  useDisconnectYouTube,
  useDriveIntegrationStatus,
  useYouTubeIntegrationStatus,
} from "@/features/settings/hooks/useIntegrations";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { LogOut, HardDrive, Youtube, CheckCircle2, Plug, Loader2 } from "lucide-react";
import { toast } from "sonner";
import Layout from "@/components/Layout";
import { Skeleton } from "@/components/common/skeletons";

const processedDriveParams = new Set();
const processedYoutubeParams = new Set();

export default function Settings() {
  const { user, logout } = useAuth();
  const [search, setSearch] = useSearchParams();

  const { data: drive, isLoading: driveLoading, isError: driveError } = useDriveIntegrationStatus();
  const { data: youtube, isLoading: youtubeLoading, isError: youtubeError } = useYouTubeIntegrationStatus();
  const connectDriveMutation = useConnectDrive();
  const connectYouTubeMutation = useConnectYouTube();
  const disconnectDriveMutation = useDisconnectDrive();
  const disconnectYouTubeMutation = useDisconnectYouTube();

  useEffect(() => {
    const status = search.get("drive");
    if (!status) return;
    const key = `drive-${status}`;
    if (processedDriveParams.has(key)) return;
    processedDriveParams.add(key);
    Promise.resolve().then(() => {
      if (status === "connected") {
        toast.success("Google Drive connected — your existing GATEPREP files will reappear on the Resources page");
        queryClient.invalidateQueries({ queryKey: queryKeys.drive.status });
      } else if (status === "error") {
        toast.error("Google Drive connection failed");
      }
      search.delete("drive");
      setSearch(search, { replace: true });
    });
  }, [search, setSearch]);

  useEffect(() => {
    const status = search.get("youtube");
    if (!status) return;
    const key = `youtube-${status}`;
    if (processedYoutubeParams.has(key)) return;
    processedYoutubeParams.add(key);
    Promise.resolve().then(() => {
      if (status === "connected") {
        toast.success("YouTube connected — you can now import your playlists");
        queryClient.invalidateQueries({ queryKey: queryKeys.youtube.status });
      } else if (status === "error") {
        toast.error("YouTube connection failed");
      }
      search.delete("youtube");
      setSearch(search, { replace: true });
    });
  }, [search, setSearch]);

  const connectDrive = async () => {
    try {
      const result = await connectDriveMutation.mutateAsync();
      window.location.href = result.authorization_url;
    } catch {
      toast.error("Failed to start Drive connection");
    }
  };

  const disconnectDrive = async () => {
    if (!window.confirm("Disconnect Google Drive? Files stay in your Drive; new uploads will be disabled.")) return;
    try {
      await disconnectDriveMutation.mutateAsync();
      toast.success("Disconnected");
    } catch { toast.error("Disconnect failed"); }
  };

  const connectYoutube = async () => {
    try {
      const result = await connectYouTubeMutation.mutateAsync();
      window.location.href = result.authorization_url;
    } catch {
      toast.error("Failed to start YouTube connection");
    }
  };

  const disconnectYoutube = async () => {
    if (!window.confirm("Disconnect YouTube? Playlist imports will stop working.")) return;
    try {
      await disconnectYouTubeMutation.mutateAsync();
      toast.success("YouTube disconnected");
    } catch { toast.error("Disconnect failed"); }
  };

  return (
    <Layout title="Settings">
      <div className="space-y-6 max-w-3xl">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Account</div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-1">Settings</h1>
        </div>

        <div className="border border-border rounded-lg p-5 space-y-3">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Profile</div>
          <div className="flex items-center gap-4">
            {user?.picture ? (
              <img src={user.picture} alt="" className="w-12 h-12 rounded-full border border-border" />
            ) : (
              <Skeleton className="w-12 h-12 rounded-full" />
            )}
            {user ? (
              <div>
                <div className="text-sm font-medium">{user?.name}</div>
                <div className="text-xs text-muted-foreground mono">{user?.email}</div>
              </div>
            ) : (
              <div className="space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-44" />
              </div>
            )}
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
              <p className="text-xs text-muted-foreground mt-1">Connect Drive to manage resources</p>
              {driveError && <div data-testid="query-error" className="text-xs text-muted-foreground">Could not load Drive status.</div>}
            </div>
            {driveLoading ? (
              <Button variant="outline" size="sm" disabled data-testid="drive-loading-btn">
                <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> Loading…
              </Button>
            ) : drive?.connected ? (
              <Button variant="outline" size="sm" onClick={disconnectDrive} data-testid="drive-disconnect-btn">
                Disconnect
              </Button>
            ) : (
              <Button size="sm" onClick={connectDrive} data-testid="drive-connect-btn">
                <Plug className="w-3.5 h-3.5 mr-1" /> Connect Drive
              </Button>
            )}
          </div>
        </div>

        <div className="border border-border rounded-lg p-5 space-y-4" data-testid="youtube-section">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Media</div>
              <div className="flex items-center gap-2 mt-1">
                <Youtube className="w-4 h-4" />
                <h2 className="text-base font-semibold">YouTube</h2>
                {youtube?.connected && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Connect YT to import playlists</p>
              {youtubeError && <div data-testid="query-error" className="text-xs text-muted-foreground">Could not load YouTube status.</div>}
            </div>
            {youtubeLoading ? (
              <Button variant="outline" size="sm" disabled data-testid="youtube-loading-btn">
                <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> Loading…
              </Button>
            ) : youtube?.connected ? (
              <Button variant="outline" size="sm" onClick={disconnectYoutube} data-testid="youtube-disconnect-btn">
                Disconnect
              </Button>
            ) : (
              <Button size="sm" onClick={connectYoutube} data-testid="youtube-connect-btn">
                <Plug className="w-3.5 h-3.5 mr-1" /> Connect YouTube
              </Button>
            )}
          </div>
        </div>

        <div className="border border-border rounded-lg p-5">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Session</div>
          <Button variant="outline" onClick={logout} data-testid="settings-logout-btn">
            <LogOut className="w-4 h-4 mr-1" /> Sign out
          </Button>
        </div>
      </div>
    </Layout>
  );
}
