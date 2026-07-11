import { useQuery, useQueryClient } from "@tanstack/react-query";

import { analyticsApi } from "@/api/endpoints/analytics";
import { queryKeys } from "@/api/queryKeys";

export function useDashboard() {
  return useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: analyticsApi.dashboard,
  });
}

export function useSubjectAnalytics(subjectId: string | undefined) {
  return useQuery({
    queryKey: subjectId ? queryKeys.analytics.subject(subjectId) : ["analytics", "subject", "missing"],
    queryFn: () => analyticsApi.subject(subjectId as string),
    enabled: Boolean(subjectId),
  });
}

export function useTopicAnalytics(topicId: string | undefined) {
  return useQuery({
    queryKey: topicId ? queryKeys.analytics.topic(topicId) : ["analytics", "topic", "missing"],
    queryFn: () => analyticsApi.topic(topicId as string),
    enabled: Boolean(topicId),
  });
}

export function useSubjectAnalyticsLoader() {
  const queryClient = useQueryClient();
  return (subjectId: string) =>
    queryClient.fetchQuery({
      queryKey: queryKeys.analytics.subject(subjectId),
      queryFn: () => analyticsApi.subject(subjectId),
    });
}
