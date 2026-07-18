export const queryKeys = {
  subjects: { all: ["subjects"] as const, detail: (id: string) => ["subjects", id] as const },
  topics: {
    bySubject: (subjectId: string) => ["topics", subjectId] as const,
    detail: (id: string) => ["topics", "detail", id] as const,
  },
  questions: {
    all: (filters?: unknown) => ["questions", filters] as const,
    detail: (id: string) => ["questions", id] as const,
    notes: (id: string) => ["questions", "notes", id] as const,
    attempts: (id: string) => ["questions", "attempts", id] as const,
  },
  pyqs: {
    all: (filters?: unknown) => ["pyqs", filters] as const,
    attempts: (id: string) => ["pyqs", "attempts", id] as const,
  },
  mistakes: {
    all: (filters?: unknown) => ["mistakes", filters] as const,
  },
  playlists: {
    all: (filters?: unknown) => ["playlists", filters] as const,
    detail: (id: string) => ["playlists", id] as const,
  },
  resources: {
    all: (filters?: unknown) => ["resources", filters] as const,
    notes: (id: string) => ["resources", "notes", id] as const,
  },
  drive: {
    status: ["drive", "status"] as const,
  },
  youtube: {
    status: ["youtube", "status"] as const,
  },
  analytics: {
    dashboard: ["dashboard"] as const,
    subject: (id: string) => ["analytics", "subject", id] as const,
    topic: (id: string) => ["analytics", "topic", id] as const,
  },
  staging: {
    items: ["staging", "items"] as const,
    jobs: ["staging", "jobs"] as const,
  },
  dashboard: ["dashboard"] as const,
  search: (query: string, limit?: number) => ["search", query, limit] as const,
};
