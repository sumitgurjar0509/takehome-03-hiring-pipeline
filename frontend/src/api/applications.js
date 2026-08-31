import { api } from "./client";

export function listApplicationsForOpening(openingId) {
  return api.get(`/openings/${openingId}/applications`).then((res) => res.data);
}

export function getApplication(id) {
  return api.get(`/applications/${id}`).then((res) => res.data);
}

export function createApplication(openingId, data) {
  return api.post(`/openings/${openingId}/applications`, data).then((res) => res.data);
}

export function updateApplication(id, data) {
  return api.patch(`/applications/${id}`, data).then((res) => res.data);
}

export function advanceApplication(id, toStage) {
  return api.post(`/applications/${id}/advance`, { to_stage: toStage }).then((res) => res.data);
}

export function rejectApplication(id) {
  return api.post(`/applications/${id}/reject`).then((res) => res.data);
}

export function reinstateApplication(id) {
  return api.post(`/applications/${id}/reinstate`).then((res) => res.data);
}
