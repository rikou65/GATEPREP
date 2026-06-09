import React, { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Link, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { CheckCircle2, Circle, ArrowLeft, ChevronRight, RotateCcw } from "lucide-react";
import { toast } from "sonner";

export default function PlaylistDetail() {
  const { id } = useParams();
  const [playlist, setPlaylist] = useState(null);
  const [activeIdx, setActiveIdx] = useState(0);
  const playerRef = useRef(null);
  const trackRef = useRef(null);

  const load = () => api.get(`/playlists/${id}`).then(r => setPlaylist(r.data?.data));
  useEffect(() => { load(); }, [id]);

  // Load YouTube IFrame API and (re)initialise player when active video changes
  useEffect(() => {
    if (!playlist?.videos?.length) return;
    if (!window.YT) {
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(tag);
    }
    const initPlayer = () => {
      const vid = playlist.videos[activeIdx]?.youtube_video_id;
      if (!vid || !window.YT?.Player) return;
      if (playerRef.current) {
        try { playerRef.current.loadVideoById(vid); return; } catch (_err) { /* fall through to recreate */ }
      }
      playerRef.current = new window.YT.Player("yt-player", {
        videoId: vid,
        playerVars: { rel: 0, modestbranding: 1 },
        events: {
          onStateChange: (e) => {
            // 1 = playing, 0 = ended
            if (e.data === 1) startTracking();
            else stopTracking();
            if (e.data === 0) {
              // auto-mark complete on natural end
              syncProgress(100, true);
            }
          },
        },
      });
    };
    if (window.YT?.Player) initPlayer();
    else window.onYouTubeIframeAPIReady = initPlayer;
    return () => stopTracking();
    // eslint-disable-next-line
  }, [playlist?.playlist_id, activeIdx]);

  const startTracking = () => {
    stopTracking();
    trackRef.current = setInterval(async () => {
      const p = playerRef.current;
      if (!p?.getCurrentTime) return;
      const cur = p.getCurrentTime();
      const dur = p.getDuration();
      if (!dur) return;
      const pct = Math.min(100, Math.round((cur / dur) * 100));
      syncProgress(pct, Math.round(cur));
    }, 5000);
  };
  const stopTracking = () => { if (trackRef.current) clearInterval(trackRef.current); trackRef.current = null; };

  const syncProgress = async (pct, watchTime) => {
    const video = playlist?.videos?.[activeIdx];
    if (!video) return;
    try {
      await api.post(`/videos/${video.video_id}/progress`, {
        watch_percentage: pct,
        watch_time: typeof watchTime === "number" ? watchTime : 0,
      });
      // optimistic local update
      setPlaylist((prev) => {
        if (!prev) return prev;
        const next = { ...prev, videos: prev.videos.map((v, i) => i === activeIdx
          ? { ...v, progress: { ...(v.progress || {}), watch_percentage: pct, completed: pct >= 90 } }
          : v) };
        return next;
      });
    } catch (_err) { /* silent */ }
  };

  const markWatched = async (idx) => {
    const video = playlist.videos[idx];
    try {
      await api.post(`/videos/${video.video_id}/progress`, { watch_percentage: 100, watch_time: video.duration || 0 });
      setPlaylist((prev) => ({
        ...prev,
        videos: prev.videos.map((v, i) => i === idx
          ? { ...v, progress: { ...(v.progress || {}), watch_percentage: 100, completed: true } }
          : v),
      }));
      toast.success("Marked as watched");
    } catch { toast.error("Failed"); }
  };

  const unmark = async (idx) => {
    const video = playlist.videos[idx];
    try {
      await api.post(`/videos/${video.video_id}/progress`, { watch_percentage: 0, watch_time: 0 });
      setPlaylist((prev) => ({
        ...prev,
        videos: prev.videos.map((v, i) => i === idx
          ? { ...v, progress: { ...(v.progress || {}), watch_percentage: 0, completed: false } }
          : v),
      }));
    } catch { toast.error("Failed"); }
  };

  if (!playlist) return <div className="text-sm text-muted-foreground">Loading…</div>;

  const total = playlist.videos.length;
  const completed = playlist.videos.filter(v => v.progress?.completed).length;
  const pct = total ? Math.round((completed / total) * 100) : 0;
  const active = playlist.videos[activeIdx];
  const activePct = active?.progress?.watch_percentage || 0;
  const activeDone = !!active?.progress?.completed;

  const next = () => activeIdx < total - 1 && setActiveIdx(activeIdx + 1);

  return (
    <div className="space-y-6">
      <Link to="/playlists" className="text-xs mono text-muted-foreground hover:text-foreground inline-flex items-center gap-1">
        <ArrowLeft className="w-3 h-3" /> Playlists
      </Link>

      <div className="space-y-3">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">{playlist.title}</h1>
        <div className="text-xs text-muted-foreground mono">{playlist.channel_title}</div>
        <div className="flex items-center gap-3" data-testid="playlist-progress-bar">
          <div className="flex-1 h-2 bg-secondary rounded overflow-hidden">
            <div className="h-full bg-emerald-500 transition-all" style={{ width: `${pct}%` }} />
          </div>
          <div className="text-xs mono whitespace-nowrap">
            <span className="text-foreground font-semibold">{completed}</span>
            <span className="text-muted-foreground">/{total}</span>
            <span className="text-muted-foreground ml-2">{pct}%</span>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 space-y-3">
          <div className="aspect-video w-full rounded-lg overflow-hidden border border-border bg-black">
            <div id="yt-player" className="w-full h-full" />
          </div>
          {active && (
            <div className="space-y-2">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="text-xs mono text-muted-foreground">#{String(activeIdx + 1).padStart(2, "0")} of {total}</div>
                  <div className="text-sm font-medium mt-0.5" data-testid="active-video-title">{active.title}</div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {activeDone ? (
                    <Button size="sm" variant="outline" onClick={() => unmark(activeIdx)} data-testid="unmark-btn">
                      <RotateCcw className="w-3.5 h-3.5 mr-1" /> Unmark
                    </Button>
                  ) : (
                    <Button size="sm" onClick={() => markWatched(activeIdx)} data-testid="mark-watched-btn">
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Mark watched
                    </Button>
                  )}
                  {activeIdx < total - 1 && (
                    <Button size="sm" variant="outline" onClick={next} data-testid="next-video-btn">
                      Next <ChevronRight className="w-3.5 h-3.5 ml-1" />
                    </Button>
                  )}
                </div>
              </div>
              <div className="h-1 bg-secondary rounded overflow-hidden">
                <div className={`h-full transition-all ${activeDone ? "bg-emerald-500" : "bg-blue-500"}`}
                     style={{ width: `${activePct}%` }} />
              </div>
              <div className="text-[10px] mono text-muted-foreground">
                {activePct}% watched · {activeDone ? "completed" : "in progress"}
              </div>
            </div>
          )}
        </div>

        <div className="border border-border rounded-lg max-h-[600px] overflow-y-auto">
          <div className="px-4 py-3 border-b border-border text-xs uppercase tracking-[0.2em] text-muted-foreground sticky top-0 bg-card/80 backdrop-blur z-10">
            Videos · {completed}/{total}
          </div>
          {playlist.videos.map((v, i) => {
            const done = !!v.progress?.completed;
            const vpct = v.progress?.watch_percentage || 0;
            return (
              <div
                key={v.video_id}
                className={`p-3 border-b border-border ${i === activeIdx ? "bg-secondary/50" : "hover:bg-secondary/30"} transition-colors`}
              >
                <div className="flex items-start gap-3">
                  <button
                    onClick={(e) => { e.stopPropagation(); done ? unmark(i) : markWatched(i); }}
                    className="mt-0.5 shrink-0"
                    data-testid={`toggle-watched-${v.video_id}`}
                    title={done ? "Mark unwatched" : "Mark watched"}
                  >
                    {done
                      ? <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                      : <Circle className="w-4 h-4 text-muted-foreground hover:text-foreground" />}
                  </button>
                  <button
                    onClick={() => setActiveIdx(i)}
                    className="flex-1 min-w-0 text-left"
                    data-testid={`video-row-${v.video_id}`}
                  >
                    <div className="text-[10px] mono text-muted-foreground">#{String(i + 1).padStart(2, "0")}</div>
                    <div className="text-sm line-clamp-2">{v.title}</div>
                    {vpct > 0 && (
                      <div className="mt-1 h-0.5 bg-secondary rounded">
                        <div className={`h-0.5 rounded ${done ? "bg-emerald-500" : "bg-blue-500"}`} style={{ width: `${vpct}%` }} />
                      </div>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
