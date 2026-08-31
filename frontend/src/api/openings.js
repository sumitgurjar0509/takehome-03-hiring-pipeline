import { api } from "./client";

export function listOpenings({ includeArchived = false } = {}) {
  return api
    .get("/openings", { params: { include_archived: includeArchived } })
    .then((res) => res.data);
}

export function getOpening(id) {
  return api.get(`/openings/${id}`).then((res) => res.data);
}

export function createOpening(data) {
  return api.post("/openings", data).then((res) => res.data);
}

export function updateOpening(id, data) {
  return api.patch(`/openings/${id}`, data).then((res) => res.data);
}

export function archiveOpening(id) {
  return api.post(`/openings/${id}/archive`).then((res) => res.data);
}

export function restoreOpening(id) {
  return api.post(`/openings/${id}/restore`).then((res) => res.data);
}
