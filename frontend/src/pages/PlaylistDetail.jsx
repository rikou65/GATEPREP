import React, { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Link, useParams } from "react-router-dom";
import { CheckCircle2, Circle, ArrowLeft } from "lucide-react";

export default function PlaylistDetail() {
  const { id } = useParams();
  const [playlist, setPlaylist] = useState(null);
  const [activeIdx, setActiveIdx] = useState(0);
  const iframeRef = useRef(null);
  const playerRef = useRef(null);
  const trackRef = useRef(null);

  const load = () => api.get(`/playlists/${id}`).then(r => setPlaylist(r.data?.data));
  useEffect(() => { load(); }, [id]);

  // YouTube IFrame API
  useEffect(() => {
    if (!playlist) return;
    if (!window.YT) {
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(tag);
    }
    const initPlayer = () => {
      const vid = playlist.videos[activeIdx]?.youtube_video_id;
      if (!vid || !window.YT?.Player) return;
      if (playerRef.current) {
        try { playerRef.current.loadVideoById(vid); } catch {}
        return;
      }
      playerRef.current = new window.YT.Player("yt-player", {
        videoId: vid,
        playerVars: { rel: 0, modestbranding: 1 },
        events: {
          onStateChange: (e) => {
            // 1 = playing
            if (e.data === 1) startTracking();
            else stopTracking();
          },
        },
      });
    };
    if (window.YT?.Player) initPlayer();
    else {
      window.onYouTubeIframeAPIReady = initPlayer;
    }
    return () => stopTracking();
    // eslint-disable-next-line
  }, [playlist, activeIdx]);

  const startTracking = () => {
    stopTracking();
    trackRef.current = setInterval(async () => {
      try {
        const p = playerRef.current;
        if (!p?.getCurrentTime) return;
        const cur = p.getCurrentTime();
        const dur = p.getDuration();
        if (!dur) return;
        const pct = Math.min(100, Math.round((cur / dur) * 100));
        const video = playlist.videos[activeIdx];
        await api.post(`/videos/${video.video_id}/progress`, {
          watch_percentage: pct,
          watch_time: Math.round(cur),
        });
        if (pct >= 90 && !video.progress?.completed) {
          // refresh on completion
          load();
        }
      } catch {}
    }, 10000);
  };
  const stopTracking = () => { if (trackRef.current) clearInterval(trackRef.current); trackRef.current = null; };

  if (!playlist) return <div className="text-sm text-muted-foreground">Loading…</div>;
  const active = playlist.videos[activeIdx];

  return (
    <div className="space-y-6">
      <Link to="/playlists" className="text-xs mono text-muted-foreground hover:text-foreground inline-flex items-center gap-1"><ArrowLeft className="w-3 h-3" /> Playlists</Link>
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">{playlist.title}</h1>
        <p className="text-xs text-muted-foreground mono mt-1">{playlist.video_count} videos · {playlist.channel_title}</p>
      </div>
      <div className="grid lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 space-y-2">
          <div className="aspect-video w-full rounded-lg overflow-hidden border border-border bg-black">
            <div id="yt-player" ref={iframeRef} className="w-full h-full" />
          </div>
          {active && (
            <div className="text-sm font-medium" data-testid="active-video-title">{active.title}</div>
          )}
        </div>
        <div className="border border-border rounded-lg max-h-[600px] overflow-y-auto">
          <div className="px-4 py-3 border-b border-border text-xs uppercase tracking-[0.2em] text-muted-foreground">
            Videos · {playlist.videos.filter(v => v.progress?.completed).length}/{playlist.videos.length}
          </div>
          {playlist.videos.map((v, i) => (
            <button
              key={v.video_id}
              data-testid={`video-row-${v.video_id}`}
              onClick={() => setActiveIdx(i)}
              className={`w-full text-left p-3 border-b border-border hover:bg-secondary/40 flex items-start gap-3 ${i === activeIdx ? "bg-secondary/40" : ""}`}
            >
              <div className="mt-0.5">
                {v.progress?.completed ? <CheckCircle2 className="w-4 h-4 text-emerald-500" /> : <Circle className="w-4 h-4 text-muted-foreground" />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs mono text-muted-foreground">#{String(i + 1).padStart(2, "0")}</div>
                <div className="text-sm line-clamp-2">{v.title}</div>
                {v.progress?.watch_percentage > 0 && (
                  <div className="mt-1 h-1 bg-secondary rounded">
                    <div className="h-1 bg-emerald-500 rounded" style={{ width: `${v.progress.watch_percentage}%` }} />
                  </div>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
