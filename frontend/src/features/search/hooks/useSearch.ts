import { useQuery } from "@tanstack/react-query";

import { searchApi } from "@/api/endpoints/search";
import { queryKeys } from "@/api/queryKeys";

export function useGlobalSearch(query: string, enabled: boolean) {
  const trimmed = query.trim();
  return useQuery({
    queryKey: queryKeys.search(trimmed, 12),
    queryFn: () => searchApi.global(trimmed, 12),
    enabled: enabled && trimmed.length >= 2,
    staleTime: 30_000,
  });
}
