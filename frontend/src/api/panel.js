import { api } from "./client";

export function listInterviewers() {
  return api.get("/interviewers").then((res) => res.data);
}

export function getApplicationPanel(applicationId) {
  return api.get(`/applications/${applicationId}/interviewers`).then((res) => res.data);
}

export function assignInterviewer(applicationId, interviewerId) {
  return api
    .post(`/applications/${applicationId}/interviewers`, { interviewer_id: interviewerId })
    .then((res) => res.data);
}

export function unassignInterviewer(applicationId, interviewerId) {
  return api.delete(`/applications/${applicationId}/interviewers/${interviewerId}`).then((res) => res.data);
}

export function listMyAssignments() {
  return api.get("/my-assignments").then((res) => res.data);
}
