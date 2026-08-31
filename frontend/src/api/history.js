import { api } from "./client";

export function getHistory(applicationId) {
  return api.get(`/applications/${applicationId}/history`).then((res) => res.data);
}

export function addFeedback(applicationId, feedbackText) {
  return api
    .post(`/applications/${applicationId}/feedback`, { feedback_text: feedbackText })
    .then((res) => res.data);
}
