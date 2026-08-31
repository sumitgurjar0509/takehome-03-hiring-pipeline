import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Layout from "../components/Layout";
import StageBadge from "../components/StageBadge";
import { getApplication } from "../api/applications";
import { getOpening } from "../api/openings";

// Read-only application view for interviewers, scoped server-side to
// applications they're on the panel for. Becomes the feedback/timeline
// view in goal 9 — for now it's just the candidate info an interviewer
// needs before an interview.
export default function ApplicationDetail() {
  const { id } = useParams();
  const [application, setApplication] = useState(null);
  const [openingTitle, setOpeningTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getApplication(id)
      .then((data) => {
        setApplication(data);
        return getOpening(data.job_opening_id);
      })
      .then((opening) => setOpeningTitle(opening.title))
      .catch(() => setError("Could not load that application."))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <Layout>
        <p className="text-ink-muted">Loading...</p>
      </Layout>
    );
  }

  if (error || !application) {
    return (
      <Layout>
        <p role="alert" className="text-sm font-medium text-danger">
          {error || "Not found."}
        </p>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-ink">{application.candidate_name}</h1>
        <StageBadge stage={application.current_stage} />
      </div>
      <p className="mt-1 text-ink-muted">{openingTitle}</p>

      <dl className="mt-6 max-w-lg divide-y divide-border rounded-lg border border-border bg-surface text-sm">
        <div className="flex justify-between px-4 py-3">
          <dt className="text-ink-muted">Email</dt>
          <dd className="text-ink">{application.candidate_email}</dd>
        </div>
        <div className="flex justify-between px-4 py-3">
          <dt className="text-ink-muted">Source</dt>
          <dd className="text-ink">{application.source || "—"}</dd>
        </div>
        <div className="px-4 py-3">
          <dt className="text-ink-muted">Notes</dt>
          <dd className="mt-1 whitespace-pre-wrap text-ink">{application.notes || "—"}</dd>
        </div>
      </dl>
    </Layout>
  );
}
