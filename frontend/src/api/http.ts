import api from "@/lib/api";
import type { ApiEnvelope } from "@/types/api";

export async function unwrap<T>(request: Promise<{ data: ApiEnvelope<T> }>) {
  const response = await request;
  return response.data?.data;
}

export { api };
