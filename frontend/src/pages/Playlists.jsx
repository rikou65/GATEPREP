import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { ListVideo, Plus, Play, Trash2 } from "lucide-react";
import { toast } from "sonner";

export default function Playlists() {
  const [playlists, setPlaylists] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ youtube_url: "", subject_id: "" });
  const [loading, setLoading] = useState(false);

  const load = () => api.get("/playlists").then(r => setPlaylists(r.data?.data || []));
  useEffect(() => { load(); api.get("/subjects").then(r => setSubjects(r.data?.data || [])); }, []);

  const submit = async () => {
    if (!form.youtube_url || !form.subject_id) { toast.error("Fill all fields"); return; }
    setLoading(true);
    try {
      await api.post("/playlists/import", form);
      toast.success("Playlist imported");
      setOpen(false); setForm({ youtube_url: "", subject_id: "" }); load();
    } catch (e) {
      toast.error(e?.response?.data?.error?.message || "Import failed");
    }
    setLoading(false);
  };

  const remove = async (id) => {
    await api.delete(`/playlists/${id}`);
    load();
  };

  return (
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
              <select
                value={form.subject_id}
                onChange={(e) => setForm(f => ({ ...f, subject_id: e.target.value }))}
                className="w-full h-10 px-3 text-sm bg-transparent border border-border rounded-md"
                data-testid="playlist-subject-select"
              >
                <option value="">Select subject</option>
                {subjects.map(s => <option key={s.subject_id} value={s.subject_id}>{s.name}</option>)}
              </select>
            </div>
            <DialogFooter>
              <Button onClick={submit} disabled={loading} data-testid="confirm-import-btn">
                {loading ? "Importing…" : "Import"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {playlists.length === 0 ? (
        <div className="text-sm text-muted-foreground border border-dashed border-border rounded-lg p-12 text-center flex flex-col items-center gap-2">
          <ListVideo className="w-5 h-5" />
          No playlists yet. Paste a YouTube playlist URL to import.
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {playlists.map(p => (
            <div key={p.playlist_id} className="border border-border rounded-lg overflow-hidden bg-card/40" data-testid={`playlist-card-${p.playlist_id}`}>
              <div className="aspect-video bg-secondary relative">
                {p.thumbnail && <img src={p.thumbnail} alt="" className="w-full h-full object-cover" />}
                <Link to={`/playlists/${p.playlist_id}`} className="absolute inset-0 flex items-center justify-center bg-black/30 hover:bg-black/50 transition-colors">
                  <Play className="w-8 h-8 text-white" fill="white" />
                </Link>
              </div>
              <div className="p-4">
                <div className="text-sm font-medium line-clamp-2">{p.title}</div>
                <div className="text-xs text-muted-foreground mono mt-2 flex items-center justify-between">
                  <span>{p.completed_videos || 0}/{p.video_count} videos</span>
                  <button onClick={() => remove(p.playlist_id)} data-testid={`delete-pl-${p.playlist_id}`} className="hover:text-red-500">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
