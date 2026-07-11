import { api, unwrap } from "@/api/http";

export const analyticsApi = {
  dashboard: () => unwrap(api.get("/dashboard")),
  subject: (subjectId: string) => unwrap(api.get(`/analytics/subject/${subjectId}`)),
  topic: (topicId: string) => unwrap(api.get(`/analytics/topic/${topicId}`)),
};
