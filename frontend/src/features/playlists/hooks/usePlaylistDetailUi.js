import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

export function formatDuration(seconds) {
  if (!seconds) return "0m";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

function findResumeIndex(videos) {
  let bestIdx = 0;
  let bestIsInProgress = false;
  let bestTime = null;

  videos.forEach((video, index) => {
    const progress = video.progress || {};
    const pct = progress.watch_percentage || 0;
    const watchedAt = progress.last_watched_at;
    const isInProgress = pct > 0 && pct < 100 && !progress.completed;

    if (isInProgress && (!bestIsInProgress || (watchedAt && bestTime && watchedAt > bestTime))) {
      bestIdx = index;
      bestIsInProgress = true;
      bestTime = watchedAt;
      return;
    }

    if (!bestIsInProgress && watchedAt && (!bestTime || watchedAt > bestTime)) {
      bestIdx = index;
      bestTime = watchedAt;
    }
  });

  return bestIdx;
}

export function usePlaylistDraft(playlistData) {
  const [playlist, setPlaylist] = useState(null);
  const [activeIdx, setActiveIdx] = useState(0);
  const [resumed, setResumed] = useState(false);
  const playlistIdRef = useRef(null);

  useEffect(() => {
    if (!playlistData) return;
    setPlaylist(playlistData);
    if (playlistData.playlist_id !== playlistIdRef.current) {
      playlistIdRef.current = playlistData.playlist_id;
      setActiveIdx(0);
      setResumed(false);
    }
  }, [playlistData]);

  useEffect(() => {
    if (!playlist?.videos?.length || resumed) return;
    setActiveIdx(findResumeIndex(playlist.videos));
    setResumed(true);
  }, [playlist, resumed]);

  const updateVideoProgress = (index, pct, watchTime, completed) => {
    setPlaylist((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        videos: prev.videos.map((video, i) => i === index
          ? {
              ...video,
              progress: {
                ...(video.progress || {}),
                watch_percentage: pct,
                watch_time: typeof watchTime === "number" ? watchTime : 0,
                ...(typeof completed === "boolean" ? { completed } : {}),
              },
            }
          : video),
      };
    });
  };

  return {
    playlist,
    activeIdx,
    setActiveIdx,
    active: playlist?.videos?.[activeIdx],
    setPlaylist,
    updateVideoProgress,
  };
}

export function useActiveQueueScroll(queueRef, activeIdx, videos) {
  useEffect(() => {
    if (!queueRef.current || !videos?.length) return;
    const rows = queueRef.current.querySelectorAll('[data-testid^="video-row-"]');
    if (rows[activeIdx]) {
      rows[activeIdx].scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [queueRef, activeIdx, videos]);
}

export function useVideoNotesDraft(activeVideoId, videoNotes, saveVideoNotes) {
  const [notes, setNotes] = useState("");
  const [lastSavedNotes, setLastSavedNotes] = useState("");

  useEffect(() => {
    if (!activeVideoId) {
      setNotes("");
      setLastSavedNotes("");
      return;
    }
    const content = videoNotes?.note_content || "";
    setNotes(content);
    setLastSavedNotes(content);
  }, [activeVideoId, videoNotes?.note_content]);

  const saveNotes = async () => {
    if (!activeVideoId || notes === lastSavedNotes) return;
    try {
      await saveVideoNotes.mutateAsync(notes);
      setLastSavedNotes(notes);
    } catch {
      toast.error("Failed to save notes");
    }
  };

  return { notes, setNotes, saveNotes };
}
