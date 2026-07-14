import api from "@/lib/api";
import type { ApiEnvelope } from "@/types/api";

export class ApiError extends Error {
  code: string;
  status?: number;

  constructor(code: string, message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

export async function unwrap<T>(request: Promise<{ data: ApiEnvelope<T> }>) {
  const response = await request;
  const env = response.data;
  if (env && env.success === false) {
    const err = env.error as unknown;
    const code =
      typeof err === "object" && err && "code" in err
        ? String((err as { code: string }).code)
        : "request_failed";
    const message =
      (typeof err === "object" && err && "message" in err
        ? String((err as { message: string }).message)
        : env.message) || "Request failed";
    throw new ApiError(code, message);
  }
  return env?.data;
}

export { api };
