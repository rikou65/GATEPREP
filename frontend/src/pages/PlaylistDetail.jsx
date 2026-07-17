import React, { useEffect, useRef } from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { CheckCircle2, Circle, ArrowLeft, ChevronRight, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import Layout from "@/components/Layout";
import QueryError from "@/components/common/QueryError";
import { PlaylistDetailSkeleton } from "@/components/common/skeletons";
import {
  usePlaylist,
  useSaveVideoNotes,
  useSaveVideoProgress,
  useVideoNotes,
} from "@/features/playlists/hooks/usePlaylists";
import {
  formatDuration,
  useActiveQueueScroll,
  usePlaylistDraft,
  useVideoNotesDraft,
} from "@/features/playlists/hooks/usePlaylistDetailUi";

export default function PlaylistDetail() {
  const { id } = useParams();
  const playerRef = useRef(null);
  const trackRef = useRef(null);
  const lastPersistRef = useRef(0);
  const queueRef = useRef(null);
  const playerContainerRef = useRef(null);

  const { data: playlistData, isError, refetch } = usePlaylist(id);
  const {
    playlist,
    activeIdx,
    setActiveIdx,
    active,
    setPlaylist,
    updateVideoProgress,
  } = usePlaylistDraft(playlistData);
  const { data: videoNotes } = useVideoNotes(active?.video_id);
  const saveVideoNotes = useSaveVideoNotes(active?.video_id);
  const saveVideoProgress = useSaveVideoProgress(id);
  const { notes, setNotes, saveNotes } = useVideoNotesDraft(
    active?.video_id,
    videoNotes,
    saveVideoNotes,
  );
  useActiveQueueScroll(queueRef, activeIdx, playlist?.videos);

  // Destroy and recreate YouTube player on active video change to prevent stale callbacks
  useEffect(() => {
    if (!playlist?.videos?.length) return;
    if (!window.YT) {
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(tag);
    }
    const initPlayer = () => {
      const video = playlist.videos[activeIdx];
      if (!video?.youtube_video_id || !window.YT?.Player) return;

      if (playerRef.current) {
        try { playerRef.current.destroy(); } catch (_err) { /* ignore */ }
        playerRef.current = null;
      }

      const seekTime = video.progress?.watch_time && !video.progress?.completed
        ? video.progress.watch_time
        : 0;

      playerRef.current = new window.YT.Player("yt-player", {
        videoId: video.youtube_video_id,
        playerVars: { rel: 0, modestbranding: 1, start: seekTime },
        events: {
          onReady: () => {
            if (seekTime > 0) {
              playerRef.current.seekTo(seekTime, true);
            }
          },
          onStateChange: (e) => {
            if (e.data === 0) {
              stopTracking();
              syncProgress(100, video.duration || 0, { completed: true, invalidate: true });
            } else if (e.data === 1) {
              startTracking();
            } else {
              captureProgress(true);
              stopTracking();
            }
          },
        },
      });
    };
    if (window.YT?.Player) initPlayer();
    else window.onYouTubeIframeAPIReady = initPlayer;
    return () => { stopTracking(); };
    // eslint-disable-next-line
  }, [playlist?.playlist_id, activeIdx]);

  const startTracking = () => {
    stopTracking();
    captureProgress(false);
    trackRef.current = setInterval(() => {
      const shouldPersist = Date.now() - lastPersistRef.current >= 5000;
      captureProgress(shouldPersist);
    }, 1000);
  };
  const stopTracking = () => { if (trackRef.current) clearInterval(trackRef.current); trackRef.current = null; };

  const captureProgress = (persist) => {
    const p = playerRef.current;
    if (!p?.getCurrentTime) return;
    const cur = p.getCurrentTime();
    const dur = p.getDuration();
    if (!dur) return;
    const pct = Math.min(100, Math.round((cur / dur) * 100));
    syncProgress(pct, Math.round(cur), { persist });
  };

  const syncProgress = async (pct, watchTime, options = {}) => {
    const video = playlist?.videos?.[activeIdx];
    if (!video) return;
    updateVideoProgress(activeIdx, pct, watchTime, options.completed);
    if (options.persist === false) return;
    lastPersistRef.current = Date.now();
    try {
      await saveVideoProgress.mutateAsync({
        videoId: video.video_id,
        payload: {
          watch_percentage: pct,
          watch_time: typeof watchTime === "number" ? watchTime : 0,
          ...(typeof options.completed === "boolean" ? { completed: options.completed } : {}),
        },
        invalidate: !!options.invalidate,
      });
    } catch (_err) { /* silent */ }
  };

  const markWatched = async (idx) => {
    const video = playlist.videos[idx];
    try {
      await saveVideoProgress.mutateAsync({
        videoId: video.video_id,
        payload: { watch_percentage: 100, watch_time: video.duration || 0, completed: true },
        invalidate: true,
      });
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
      await saveVideoProgress.mutateAsync({
        videoId: video.video_id,
        payload: { watch_percentage: 0, watch_time: 0, completed: false },
        invalidate: true,
      });
      setPlaylist((prev) => ({
        ...prev,
        videos: prev.videos.map((v, i) => i === idx
          ? { ...v, progress: { ...(v.progress || {}), watch_percentage: 0, completed: false } }
          : v),
      }));
    } catch { toast.error("Failed"); }
  };

  // Key moments and active recall memos removed per requirements

  if (isError) return (
    <Layout title="Playlist Detail">
      <QueryError onRetry={refetch} />
    </Layout>
  );

  if (!playlist) return (
    <Layout title="Playlist Detail">
      <PlaylistDetailSkeleton />
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
      <div className="flex flex-col" style={{ height: 'calc(100vh - 5rem)' }}>
        <div className="shrink-0 space-y-3 mb-4">
          <Link to="/playlists" className="text-xs mono text-muted-foreground hover:text-foreground inline-flex items-center gap-1">
            <ArrowLeft className="w-3 h-3" /> Playlists
          </Link>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">{playlist.title}</h1>
        </div>

        <div className="flex-1 min-h-0 grid grid-cols-12 gap-6 items-stretch">
          {/* Left Column */}
          <div className="col-span-12 xl:col-span-7 flex flex-col min-h-0">
            <div ref={playerContainerRef} className="aspect-video w-full rounded-3xl overflow-hidden border border-border bg-black shrink-0">
              <div id="yt-player" className="w-full h-full" />
            </div>
            {active && (
              <div className="flex flex-col min-h-0 mt-4 space-y-3">
                <h2 className="text-xl font-bold text-foreground" data-testid="active-video-title">
                  {active.title}
                </h2>

                <div className="flex items-center gap-2 flex-wrap">
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
          </div>

          {/* Right Column */}
          <div className="col-span-12 xl:col-span-5 flex flex-col min-h-0 gap-3">
            {/* Queue section — shows 3 rows at a time */}
            <div className="flex flex-col min-h-0 border border-border rounded-2xl p-4 flex-[1]">
              <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground shrink-0">Playlist Queue</h3>
              <div
                ref={queueRef}
                className="flex-1 min-h-0 overflow-y-auto mt-3 space-y-1 scrollbar-thin scrollbar-thumb-muted"
              >
                {playlist.videos.map((v, i) => {
                  const isActive = i === activeIdx;
                  const isDone = !!v.progress?.completed;
                  const thumbnail = `https://img.youtube.com/vi/${v.youtube_video_id}/default.jpg`;
                  return (
                    <div
                      key={v.video_id}
                      onClick={() => setActiveIdx(i)}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-colors ${
                        isActive
                          ? "bg-secondary/40 border border-primary/30"
                          : "hover:bg-card/40 border border-transparent"
                      }`}
                      data-testid={`video-row-${v.video_id}`}
                    >
                      <span className="text-[10px] font-mono text-muted-foreground shrink-0 w-7 text-right">
                        #{String(i + 1).padStart(2, "0")}
                      </span>
                      <img
                        src={thumbnail}
                        alt=""
                        className="w-16 h-12 rounded object-cover shrink-0 bg-secondary"
                        loading="lazy"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium leading-tight line-clamp-2 text-foreground/90">{v.title}</p>
                        {v.progress?.watch_percentage > 0 && (
                          <div className="h-1 bg-secondary rounded-full overflow-hidden mt-1.5">
                            <div
                              className={`h-full ${isDone ? "bg-emerald-400" : "bg-primary"}`}
                              style={{ width: `${v.progress.watch_percentage}%` }}
                            />
                          </div>
                        )}
                      </div>
                      <span className="text-[10px] font-mono text-muted-foreground shrink-0">
                        {formatDuration(v.duration)}
                      </span>
                      <button
                        onClick={(e) => { e.stopPropagation(); isDone ? unmark(i) : markWatched(i); }}
                        className="shrink-0"
                        data-testid={`toggle-watched-${v.video_id}`}
                      >
                        {isDone ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <Circle className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground" />
                        )}
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Notes Panel (always visible) */}
            <div className="flex flex-col min-h-0 border border-border rounded-2xl p-4 flex-[1]">
              <div className="flex justify-between items-center shrink-0">
                <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Video Notes</h3>
                <span className="text-[10px] font-mono text-muted-foreground">
                  {saveVideoNotes.isPending ? "Saving..." : "Auto-saved"}
                </span>
              </div>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                onBlur={saveNotes}
                placeholder="Capture key equations, proofs, or notes for this video..."
                className="w-full flex-1 min-h-0 mt-3 bg-white/5 border border-border rounded-2xl p-4 text-sm text-foreground placeholder:text-muted-foreground/30 focus:ring-1 focus:ring-primary/50 resize-none outline-none"
              />
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
