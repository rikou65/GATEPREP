import { api, unwrap } from "@/api/http";
import type { Playlist } from "@/types/api";

export const playlistsApi = {
  list: (params?: { subject_id?: string }) =>
    unwrap<Playlist[]>(api.get("/playlists", { params })),
  detail: (playlistId: string) => unwrap<Playlist>(api.get(`/playlists/${playlistId}`)),
  import: (payload: { youtube_url: string; subject_id: string }) =>
    unwrap(api.post("/playlists/import", payload)),
  remove: (playlistId: string) => unwrap(api.delete(`/playlists/${playlistId}`)),
  videoNotes: (videoId: string) => unwrap(api.get(`/videos/${videoId}/notes`)),
  saveVideoNotes: (videoId: string, note_content: string) =>
    unwrap(api.post(`/videos/${videoId}/notes`, { note_content })),
  saveProgress: (videoId: string, payload: unknown) =>
    unwrap(api.post(`/videos/${videoId}/progress`, payload)),
};
