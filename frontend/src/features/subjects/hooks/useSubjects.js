import { useQuery } from "@tanstack/react-query";
import { subjectsApi } from "@/api/endpoints/subjects";
import { queryKeys } from "@/api/queryKeys";

export function useSubjects() {
  return useQuery({
    queryKey: queryKeys.subjects.all,
    queryFn: subjectsApi.list,
  });
}

export function useSubject(id) {
  return useQuery({
    queryKey: queryKeys.subjects.detail(id),
    queryFn: () => subjectsApi.get(id),
    enabled: !!id,
  });
}

export function useTopics(subjectId) {
  return useQuery({
    queryKey: queryKeys.topics.bySubject(subjectId),
    queryFn: () => subjectsApi.topics.bySubject(subjectId),
    enabled: !!subjectId,
  });
}

export function useTopicDetail(topicId) {
  return useQuery({
    queryKey: queryKeys.topics.detail(topicId),
    queryFn: () => subjectsApi.topics.detail(topicId),
    enabled: !!topicId,
  });
}
