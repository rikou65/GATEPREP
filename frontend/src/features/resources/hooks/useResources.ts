import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { resourcesApi } from "@/api/endpoints/resources";
import { settingsApi } from "@/api/endpoints/settings";
import { queryKeys } from "@/api/queryKeys";

export function useResources(filters?: { subject_id?: string; resource_type?: string }) {
  return useQuery({
    queryKey: queryKeys.resources.all(filters),
    queryFn: () => resourcesApi.list(filters),
  });
}

export function useDriveStatus() {
  return useQuery({
    queryKey: queryKeys.drive.status,
    queryFn: settingsApi.driveStatus,
  });
}

export function useSyncDrive() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: resourcesApi.driveSync,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["resources"] }),
  });
}

export function useRefreshDrive() {
  return useMutation({
    mutationFn: resourcesApi.driveRefresh,
  });
}

export function useCreateResourceLink() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: resourcesApi.createLink,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["resources"] }),
  });
}

export function useUploadResource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: resourcesApi.upload,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["resources"] }),
  });
}

export function useDeleteResource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: resourcesApi.remove,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["resources"] }),
  });
}

export function useResourceViewerActions() {
  return {
    view: resourcesApi.view,
    stream: resourcesApi.stream,
    notes: resourcesApi.notes,
    saveNotes: resourcesApi.saveNotes,
    togglePage: resourcesApi.togglePage,
    labelPage: resourcesApi.labelPage,
  };
}
