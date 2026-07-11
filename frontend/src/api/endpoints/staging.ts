import { api, unwrap } from "@/api/http";

export const stagingApi = {
  importPdf: (formData: FormData) =>
    unwrap(
      api.post("/data/import/pdf", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
    ),
  items: () => unwrap(api.get("/data/staging")),
  jobs: () => unwrap(api.get("/data/import/jobs")),
  approveReady: () => unwrap(api.post("/data/staging/bulk-approve")),
  approveOne: (staging_id: string) =>
    unwrap(api.post("/data/staging/approve-specific", { staging_id })),
  deleteOne: (stagingId: string) => unwrap(api.delete(`/data/staging/${stagingId}`)),
  deleteJob: (jobId: string) => unwrap(api.delete(`/data/import/jobs/${jobId}`)),
  clear: () => unwrap(api.delete("/data/staging")),
};
