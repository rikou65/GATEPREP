import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { playlistsApi } from "@/api/endpoints/playlists";
import { queryKeys } from "@/api/queryKeys";

export function usePlaylists(filters?: { subject_id?: string }) {
  return useQuery({
    queryKey: queryKeys.playlists.all(filters),
    queryFn: () => playlistsApi.list(filters),
  });
}

export function usePlaylist(playlistId: string | undefined) {
  return useQuery({
    queryKey: playlistId ? queryKeys.playlists.detail(playlistId) : ["playlists", "missing"],
    queryFn: () => playlistsApi.detail(playlistId as string),
    enabled: Boolean(playlistId),
  });
}

export function useImportPlaylist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: playlistsApi.import,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.playlists.all() }),
  });
}

export function useDeletePlaylist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: playlistsApi.remove,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.playlists.all() }),
  });
}

export function useVideoNotes(videoId: string | undefined) {
  return useQuery({
    queryKey: videoId ? ["videos", "notes", videoId] : ["videos", "notes", "missing"],
    queryFn: () => playlistsApi.videoNotes(videoId as string),
    enabled: Boolean(videoId),
  });
}

export function useSaveVideoNotes(videoId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (note_content: string) => playlistsApi.saveVideoNotes(videoId as string, note_content),
    onSuccess: () => {
      if (videoId) queryClient.invalidateQueries({ queryKey: ["videos", "notes", videoId] });
    },
  });
}

export function useSaveVideoProgress(playlistId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ videoId, payload }: { videoId: string; payload: {
      watch_percentage?: number;
      watch_time?: number;
      completed?: boolean;
    }; invalidate?: boolean }) =>
      playlistsApi.saveProgress(videoId, payload),
    onMutate: async ({ videoId, payload }) => {
      if (!playlistId) return {};
      const queryKey = queryKeys.playlists.detail(playlistId);
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData(queryKey);
      queryClient.setQueryData(queryKey, (old: any) => {
        if (!old?.videos) return old;
        return {
          ...old,
          videos: old.videos.map((video: any) =>
            video.video_id === videoId
              ? {
                  ...video,
                  progress: {
                    ...(video.progress || {}),
                    ...payload,
                  },
                }
              : video
          ),
        };
      });
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (playlistId && context?.previous) {
        queryClient.setQueryData(queryKeys.playlists.detail(playlistId), context.previous);
      }
    },
    onSuccess: (_data, variables) => {
      if (!variables.invalidate) return;
      if (playlistId) queryClient.invalidateQueries({ queryKey: queryKeys.playlists.detail(playlistId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.playlists.all() });
    },
  });
}
