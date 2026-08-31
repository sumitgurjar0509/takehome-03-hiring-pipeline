import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Layout from "../components/Layout";
import { getOpening } from "../api/openings";
import { listApplicationsForOpening } from "../api/applications";

const STAGE_STYLES = {
  applied: "bg-stage-applied/10 text-stage-applied",
  screening: "bg-stage-screening/10 text-stage-screening",
  interview: "bg-stage-interview/10 text-stage-interview",
  offer: "bg-stage-offer/10 text-stage-offer",
  hired: "bg-stage-hired/10 text-stage-hired",
  rejected: "bg-stage-rejected/10 text-stage-rejected",
};

function StageBadge({ stage }) {
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STAGE_STYLES[stage] ?? ""}`}
    >
      {stage}
    </span>
  );
}

export default function OpeningDetail() {
  const { id } = useParams();
  const [opening, setOpening] = useState(null);
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    Promise.all([getOpening(id), listApplicationsForOpening(id)])
      .then(([openingData, applicationsData]) => {
        setOpening(openingData);
        setApplications(applicationsData);
      })
      .catch(() => setError("Could not load this job opening."))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <Layout>
        <p className="text-ink-muted">Loading...</p>
      </Layout>
    );
  }

  if (error || !opening) {
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
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-ink">{opening.title}</h1>
            {opening.archived && (
              <span className="inline-block rounded-full border border-border px-2 py-0.5 text-xs font-medium text-ink-muted">
                Archived
              </span>
            )}
          </div>
          <p className="mt-1 text-ink-muted">{opening.department}</p>
        </div>
        <Link
          to={`/openings/${opening.id}/edit`}
          className="rounded-md border border-border px-3 py-2 text-sm font-medium text-ink hover:bg-black/5"
        >
          Edit Opening
        </Link>
      </div>

      {opening.description && (
        <p className="mt-4 max-w-2xl text-sm text-ink-muted">{opening.description}</p>
      )}

      <div className="mt-8 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-ink">Applications</h2>
        <Link
          to={`/openings/${opening.id}/applications/new`}
          className="rounded-md bg-brand px-3 py-2 text-sm font-medium text-white hover:bg-brand-hover"
        >
          New Application
        </Link>
      </div>

      {applications.length === 0 ? (
        <p className="mt-4 text-ink-muted">No applications yet.</p>
      ) : (
        <div className="mt-4 overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border text-xs uppercase tracking-wide text-ink-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Candidate</th>
                <th className="px-4 py-3 font-medium">Email</th>
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3 font-medium">Stage</th>
              </tr>
            </thead>
            <tbody>
              {applications.map((application) => (
                <tr key={application.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-3">
                    <Link
                      to={`/applications/${application.id}/edit`}
                      className="font-medium text-brand hover:underline"
                    >
                      {application.candidate_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-ink-muted">{application.candidate_email}</td>
                  <td className="px-4 py-3 text-ink-muted">{application.source || "—"}</td>
                  <td className="px-4 py-3">
                    <StageBadge stage={application.current_stage} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}
