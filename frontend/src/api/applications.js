import { api } from "./client";

export function listApplicationsForOpening(openingId) {
  return api.get(`/openings/${openingId}/applications`).then((res) => res.data);
}

// Recruiter-scoped, cross-opening search/filter/sort/pagination (goal 6).
// Every param is forwarded straight to the server — no client-side
// filtering here.
export function listApplications(params = {}) {
  return api.get("/applications", { params }).then((res) => res.data);
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

// action is "advance" or "reject". Returns { results: [{ application_id, success, message }] } —
// one ineligible application never fails the whole batch.
export function bulkAction(applicationIds, action) {
  return api
    .post("/applications/bulk", { application_ids: applicationIds, action })
    .then((res) => res.data);
}

// The endpoint requires a JWT bearer header, so a plain <a href> download
// link won't work — fetch it via axios (which attaches the token) and
// save the blob via a synthetic click instead.
export async function downloadApplicationsCsv() {
  const response = await api.get("/applications/export", { responseType: "blob" });
  const blob = new Blob([response.data], { type: "text/csv" });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "applications.csv";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}
