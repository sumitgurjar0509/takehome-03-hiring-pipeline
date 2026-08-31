import { api } from "./client";

export function listAlerts() {
  return api.get("/alerts").then((res) => res.data);
}

export function dismissAlert(applicationId) {
  return api.post(`/applications/${applicationId}/dismiss-alert`).then((res) => res.data);
}
