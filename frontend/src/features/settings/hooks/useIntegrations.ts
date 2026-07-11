import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { settingsApi } from "@/api/endpoints/settings";
import { queryKeys } from "@/api/queryKeys";

export function useDriveIntegrationStatus() {
  return useQuery({
    queryKey: queryKeys.drive.status,
    queryFn: settingsApi.driveStatus,
  });
}

export function useYouTubeIntegrationStatus() {
  return useQuery({
    queryKey: queryKeys.youtube.status,
    queryFn: settingsApi.youtubeStatus,
  });
}

export function useDisconnectDrive() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: settingsApi.driveDisconnect,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.drive.status }),
  });
}

export function useConnectDrive() {
  return useMutation({
    mutationFn: settingsApi.driveConnect,
  });
}

export function useDisconnectYouTube() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: settingsApi.youtubeDisconnect,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.youtube.status }),
  });
}

export function useConnectYouTube() {
  return useMutation({
    mutationFn: settingsApi.youtubeConnect,
  });
}
