import { api, unwrap } from "@/api/http";
import type { SearchResult } from "@/types/api";

export const searchApi = {
  global: (q: string, limit = 12) =>
    unwrap<SearchResult[]>(api.get("/search", { params: { q, limit } })),
};
