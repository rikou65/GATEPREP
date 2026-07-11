import { api, unwrap } from "@/api/http";
import type { IntegrationStatus } from "@/types/api";

export const settingsApi = {
  driveStatus: () => unwrap<IntegrationStatus>(api.get("/drive/status")),
  youtubeStatus: () => unwrap<IntegrationStatus>(api.get("/youtube/status")),
  driveConnect: () => unwrap<{ authorization_url: string }>(api.get("/drive/connect")),
  driveDisconnect: () => unwrap(api.post("/drive/disconnect")),
  youtubeConnect: () => unwrap<{ authorization_url: string }>(api.get("/youtube/auth")),
  youtubeDisconnect: () => unwrap(api.post("/youtube/disconnect")),
};
