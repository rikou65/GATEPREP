import { api, unwrap } from "@/api/http";
import type { Resource } from "@/types/api";

export const resourcesApi = {
  list: (params?: { subject_id?: string; resource_type?: string }) =>
    unwrap<Resource[]>(api.get("/resources", { params })),
  createLink: (payload: unknown) => unwrap<Resource>(api.post("/resources", payload)),
  upload: (formData: FormData) =>
    unwrap<Resource>(
      api.post("/resources/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
    ),
  remove: (resourceId: string) => unwrap(api.delete(`/resources/${resourceId}`)),
  view: (resourceId: string) => unwrap(api.get(`/resources/${resourceId}/view`)),
  stream: (resourceId: string) =>
    api.get(`/resources/${resourceId}/stream`, { responseType: "blob" }),
  notes: (resourceId: string) => unwrap(api.get(`/resources/${resourceId}/notes`)),
  saveNotes: (resourceId: string, payload: unknown) =>
    unwrap(api.post(`/resources/${resourceId}/notes`, payload)),
  togglePage: (resourceId: string, payload: unknown) =>
    unwrap(api.post(`/resources/${resourceId}/pages/toggle`, payload)),
  labelPage: (resourceId: string, payload: unknown) =>
    unwrap(api.post(`/resources/${resourceId}/pages/label`, payload)),
  driveRefresh: () => unwrap(api.post("/drive/refresh")),
  driveSync: () => unwrap(api.post("/drive/sync")),
};
