import React, { useEffect, useRef, useState, useMemo } from "react";
import { api } from "@/lib/api";
import { Link, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { CheckCircle2, Circle, ArrowLeft, ChevronRight, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import Layout from "@/components/Layout";

export default function PlaylistDetail() {
  const { id } = useParams();
  const [playlist, setPlaylist] = useState(null);
  const [activeIdx, setActiveIdx] = useState(0);
  const playerRef = useRef(null);
  const trackRef = useRef(null);

  const [notes, setNotes] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [subjects, setSubjects] = useState([]);

  const load = () => api.get(`/playlists/${id}`).then(r => setPlaylist(r.data?.data));
  useEffect(() => { load(); }, [id]);

  useEffect(() => {
    api.get("/subjects").then(r => setSubjects(r.data?.data || []));
  }, []);

  const active = playlist?.videos?.[activeIdx];

  useEffect(() => {
    if (!active) {
      setNotes("");
      return;
    }
    api.get(`/videos/${active.video_id}/notes`)
      .then(r => setNotes(r.data?.data?.note_content || ""))
      .catch(() => setNotes(""));
  }, [active?.video_id]);

  const saveNotes = async () => {
    if (!active) return;
    setSavingNote(true);
    try {
      await api.post(`/videos/${active.video_id}/notes`, { note_content: notes });
      toast.success("Notes saved");
    } catch {
      toast.error("Failed to save notes");
    }
    setSavingNote(false);
  };

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

  const subjectName = useMemo(() => {
    if (!playlist || !subjects.length) return "General Subject";
    const found = subjects.find(s => s.subject_id === playlist.subject_id);
    return found ? found.name : "General Subject";
  }, [playlist, subjects]);

  // Key moments and active recall memos removed per requirements

  if (!playlist) return (
    <Layout title="Playlist Detail">
      <div className="text-sm text-muted-foreground">Loading…</div>
    </Layout>
  );

  const total = playlist.videos.length;
  const completed = playlist.videos.filter(v => v.progress?.completed).length;
  const pct = total ? Math.round((completed / total) * 100) : 0;
  const activePct = active?.progress?.watch_percentage || 0;
  const activeDone = !!active?.progress?.completed;

  const next = () => activeIdx < total - 1 && setActiveIdx(activeIdx + 1);

  const seekToTime = (seconds) => {
    if (playerRef.current && typeof playerRef.current.seekTo === "function") {
      playerRef.current.seekTo(seconds, true);
      playerRef.current.playVideo();
    } else {
      toast.error("Player not ready yet");
    }
  };

  return (
    <Layout title="Playlist Detail">
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

        <div className="grid grid-cols-12 gap-6 items-start">
          {/* Left Column (60%) */}
          <div className="col-span-12 xl:col-span-7 space-y-6">
            <div className="aspect-video w-full rounded-3xl overflow-hidden border border-border bg-black">
              <div id="yt-player" className="w-full h-full" />
            </div>
            {active && (
              <div className="space-y-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
                      Active Video
                    </span>
                    <span className="px-2 py-0.5 bg-primary/10 border border-primary/20 rounded-full text-[10px] text-primary">
                      {subjectName}
                    </span>
                  </div>
                  <h2 className="text-xl font-bold text-foreground mt-1" data-testid="active-video-title">
                    {active.title}
                  </h2>
                  <p className="text-xs text-muted-foreground mt-1">
                    {playlist.channel_title}
                  </p>
                </div>

                <div className="flex items-center gap-3">
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
                      Next Video <ChevronRight className="w-3.5 h-3.5 ml-1" />
                    </Button>
                  )}
                </div>

                <div className="space-y-1">
                  <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${activeDone ? "bg-emerald-500" : "bg-primary"}`}
                      style={{ width: `${activePct}%` }}
                    />
                  </div>
                  <div className="text-[10px] font-mono text-muted-foreground">
                    {activePct}% watched · {activeDone ? "completed" : "in progress"}
                  </div>
                </div>
              </div>
            )}

            {/* Horizontal Playlist Queue */}
            <div className="space-y-3 pt-2">
              <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Playlist Queue</h3>
              <div className="flex gap-4 overflow-x-auto pb-4 pt-1 snap-x scrollbar-thin scrollbar-thumb-muted">
                {playlist.videos.map((v, i) => {
                  const isActive = i === activeIdx;
                  const isDone = !!v.progress?.completed;
                  return (
                    <div
                      key={v.video_id}
                      onClick={() => setActiveIdx(i)}
                      className={`min-w-[220px] max-w-[220px] snap-start border rounded-2xl p-4 cursor-pointer transition-all duration-200 ${
                        isActive
                          ? "bg-secondary/50 border-primary"
                          : "bg-card/20 border-border hover:bg-card/40 hover:border-muted-foreground"
                      }`}
                      data-testid={`video-row-${v.video_id}`}
                    >
                      <div className="flex justify-between items-start gap-1">
                        <span className="text-[10px] font-mono text-muted-foreground">#{String(i + 1).padStart(2, "0")}</span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            isDone ? unmark(i) : markWatched(i);
                          }}
                          data-testid={`toggle-watched-${v.video_id}`}
                        >
                          {isDone ? (
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <Circle className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground" />
                          )}
                        </button>
                      </div>
                      <p className="text-xs font-medium mt-1 line-clamp-2 text-foreground/90">{v.title}</p>
                      {v.progress?.watch_percentage > 0 && (
                        <div className="mt-2 h-1 bg-secondary rounded-full overflow-hidden">
                          <div
                            className={`h-full ${isDone ? "bg-emerald-400" : "bg-primary"}`}
                            style={{ width: `${v.progress.watch_percentage}%` }}
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Column (40%) */}
          <div className="col-span-12 xl:col-span-5 space-y-6">
            <div className="border border-border rounded-3xl p-6 bg-card/25 backdrop-blur-xl sticky top-24">
              {/* Personal Notes */}
              <div className="space-y-2 h-full flex flex-col">
                <div className="flex justify-between items-center">
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                    Video Notes
                  </h3>
                  <span className="text-[10px] font-mono text-muted-foreground">
                    {savingNote ? "Saving..." : "Auto-saved"}
                  </span>
                </div>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  onBlur={saveNotes}
                  placeholder="Capture key equations, proofs, or notes for this video..."
                  className="w-full h-[32rem] bg-white/5 border border-border rounded-2xl p-4 text-sm text-foreground placeholder:text-muted-foreground/30 focus:ring-1 focus:ring-primary/50 resize-none outline-none"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
