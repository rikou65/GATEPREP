import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { stagingApi } from "@/api/endpoints/staging";
import { queryKeys } from "@/api/queryKeys";

export function useStagingItems() {
  return useQuery({
    queryKey: queryKeys.staging.items,
    queryFn: stagingApi.items,
  });
}

export function useImportJobs() {
  return useQuery({
    queryKey: queryKeys.staging.jobs,
    queryFn: stagingApi.jobs,
    refetchInterval: 5000,
  });
}

export function useImportPdf() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: stagingApi.importPdf,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.staging.jobs });
      queryClient.invalidateQueries({ queryKey: queryKeys.staging.items });
    },
  });
}

export function useApproveReadyStaging() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: stagingApi.approveReady,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.staging.items }),
  });
}

export function useApproveStagingItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: stagingApi.approveOne,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.staging.items }),
  });
}

export function useDeleteStagingItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: stagingApi.deleteOne,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.staging.items }),
  });
}

export function useDeleteImportJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: stagingApi.deleteJob,
    onSettled: () => queryClient.invalidateQueries({ queryKey: queryKeys.staging.jobs }),
  });
}

export function useClearStaging() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: stagingApi.clear,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.staging.items }),
  });
}
