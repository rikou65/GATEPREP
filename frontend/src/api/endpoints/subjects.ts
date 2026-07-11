import { api, unwrap } from "@/api/http";
import type { Subject, Topic } from "@/types/api";

export const subjectsApi = {
  list: () => unwrap<Subject[]>(api.get("/subjects")),
  get: (id: string) => unwrap<Subject>(api.get(`/subjects/${id}`)),
  topics: {
    bySubject: (subjectId: string) =>
      unwrap<Topic[]>(api.get(`/subjects/${subjectId}/topics`)),
    detail: (topicId: string) => unwrap<Topic>(api.get(`/topics/${topicId}`)),
  },
};
