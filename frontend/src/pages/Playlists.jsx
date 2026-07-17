import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useSubjects } from "@/features/subjects/hooks/useSubjects";
import {
  useDeletePlaylist,
  useImportPlaylist,
  usePlaylists,
} from "@/features/playlists/hooks/usePlaylists";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import AppSelect from "@/components/common/AppSelect";
import { ListVideo, Plus, Play, Trash2 } from "lucide-react";
import { toast } from "sonner";
import Layout from "@/components/Layout";
import QueryError from "@/components/common/QueryError";
import { CardGridSkeleton } from "@/components/common/skeletons";

function formatDuration(seconds) {
  if (!seconds) return "0m";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

export default function Playlists() {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ youtube_url: "", subject_id: "" });
  const [loading, setLoading] = useState(false);

  const { data: playlists = [], isLoading, isError, refetch } = usePlaylists();
  const { data: subjects = [], isLoading: subjectsLoading } = useSubjects();
  const importPlaylist = useImportPlaylist();
  const deletePlaylist = useDeletePlaylist();

  const submit = async () => {
    if (!form.youtube_url || !form.subject_id) { toast.error("Fill all fields"); return; }
    setLoading(true);
    try {
      const result = await importPlaylist.mutateAsync(form);
      if (result?.already_exists) {
        toast.info("Playlist already imported");
      } else {
        toast.success("Playlist imported");
      }
      setOpen(false); setForm({ youtube_url: "", subject_id: "" });
    } catch (e) {
      const backendError = e?.response?.data?.error;
      const message = backendError?.message || "Import failed";
      toast.error(backendError?.code ? `${message} (${backendError.code})` : message);
    }
    setLoading(false);
  };

  const remove = async (id) => {
    await deletePlaylist.mutateAsync(id);
  };

  // Group playlists by subject in the canonical subject order
  const groups = useMemo(() => {
    const bySubject = new Map();
    for (const p of playlists) {
      if (!bySubject.has(p.subject_id)) bySubject.set(p.subject_id, []);
      bySubject.get(p.subject_id).push(p);
    }
    return subjects
      .filter(s => bySubject.has(s.subject_id))
      .map(s => ({ subject: s, items: bySubject.get(s.subject_id) }));
  }, [playlists, subjects]);

  if (isError) return (
    <Layout title="Playlists">
      <QueryError onRetry={refetch} />
    </Layout>
  );

  return (
    <Layout title="Playlists">
      <div className="space-y-6">
        <div className="flex items-end justify-between">
          <div>
            <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Video</div>
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-1">Playlists</h1>
            <p className="text-sm text-muted-foreground mt-1">Imported from YouTube · play inside the platform.</p>
          </div>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button data-testid="import-playlist-btn"><Plus className="w-4 h-4 mr-1" /> Import playlist</Button>
            </DialogTrigger>
            <DialogContent className="bg-card border-border">
              <DialogHeader><DialogTitle>Import YouTube Playlist</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <Input
                  placeholder="https://www.youtube.com/playlist?list=…"
                  value={form.youtube_url}
                  onChange={(e) => setForm(f => ({ ...f, youtube_url: e.target.value }))}
                  data-testid="playlist-url-input"
                />
                <AppSelect
                  value={form.subject_id}
                  onChange={(value) => setForm(f => ({ ...f, subject_id: value }))}
                  className="w-full"
                  testId="playlist-subject-select"
                  options={[
                    { value: "", label: "Select subject" },
                    ...subjects.map((s) => ({ value: s.subject_id, label: s.name })),
                  ]}
                />
              </div>
              <DialogFooter>
                <Button onClick={submit} disabled={loading} data-testid="confirm-import-btn">
                  {loading ? "Importing…" : "Import"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        {isLoading || subjectsLoading ? (
          <div className="space-y-10">
            <div className="space-y-4">
              <div className="flex items-baseline justify-between border-b border-border pb-2">
                <div className="space-y-2">
                  <div className="h-3 w-24 rounded bg-white/[0.07] animate-pulse" />
                  <div className="h-6 w-44 rounded bg-white/[0.07] animate-pulse" />
                </div>
                <div className="h-3 w-20 rounded bg-white/[0.07] animate-pulse" />
              </div>
              <CardGridSkeleton count={3} columns="grid-cols-1 sm:grid-cols-2 lg:grid-cols-3" />
            </div>
          </div>
        ) : playlists.length === 0 ? (
          <div className="text-sm text-muted-foreground border border-dashed border-border rounded-lg p-12 text-center flex flex-col items-center gap-2">
            <ListVideo className="w-5 h-5" />
            No playlists yet. Paste a YouTube playlist URL to import.
          </div>
        ) : (
          <div className="space-y-10">
            {groups.map(({ subject, items }) => (
              <section key={subject.subject_id} data-testid={`playlist-group-${subject.subject_id}`}>
                <div className="flex items-baseline justify-between border-b border-border pb-2 mb-4">
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mono">
                      Subject · {String(subject.order + 1).padStart(2, "0")}
                    </div>
                    <h2 className="text-lg font-semibold tracking-tight mt-0.5">{subject.name}</h2>
                  </div>
                  <div className="text-xs mono text-muted-foreground">{items.length} playlist{items.length > 1 ? "s" : ""}</div>
                </div>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {items.map(p => {
                    const pct = p.video_count ? Math.round(((p.completed_videos || 0) / p.video_count) * 100) : 0;
                    return (
                      <div key={p.playlist_id} className="border border-border rounded-lg overflow-hidden bg-card/40" data-testid={`playlist-card-${p.playlist_id}`}>
                        <div className="aspect-video bg-secondary relative">
                          {p.thumbnail && <img src={p.thumbnail} alt="" className="w-full h-full object-cover" />}
                          <Link to={`/playlists/${p.playlist_id}`} className="absolute inset-0 flex items-center justify-center bg-black/30 hover:bg-black/50 transition-colors">
                            <Play className="w-8 h-8 text-white" fill="white" />
                          </Link>
                        </div>
                        <div className="p-4 space-y-2">
                          <div className="text-sm font-medium line-clamp-2">{p.title}</div>
                          <div className="h-1 bg-secondary rounded overflow-hidden">
                            <div className="h-full bg-emerald-500 transition-all" style={{ width: `${pct}%` }} />
                          </div>
                          <div className="text-xs text-muted-foreground mono flex items-center justify-between">
                            <span>{p.completed_videos || 0}/{p.video_count} videos · {formatDuration(p.watched_duration || 0)}/{formatDuration(p.total_duration || 0)} · {pct}%</span>
                            <button onClick={() => remove(p.playlist_id)} data-testid={`delete-pl-${p.playlist_id}`} className="hover:text-red-500">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
