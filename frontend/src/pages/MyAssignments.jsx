import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import StageBadge from "../components/StageBadge";
import { listMyAssignments } from "../api/panel";

export default function MyAssignments() {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listMyAssignments()
      .then(setAssignments)
      .catch(() => setError("Could not load your assignments."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-ink">My Assignments</h1>

      {error && (
        <p role="alert" className="mt-4 text-sm font-medium text-danger">
          {error}
        </p>
      )}

      {loading ? (
        <p className="mt-6 text-ink-muted">Loading...</p>
      ) : assignments.length === 0 ? (
        <p className="mt-6 text-ink-muted">You're not on any interview panels yet.</p>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border text-xs uppercase tracking-wide text-ink-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Candidate</th>
                <th className="px-4 py-3 font-medium">Job Opening</th>
                <th className="px-4 py-3 font-medium">Stage</th>
              </tr>
            </thead>
            <tbody>
              {assignments.map((application) => (
                <tr key={application.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-3">
                    <Link
                      to={`/applications/${application.id}`}
                      className="font-medium text-brand hover:underline"
                    >
                      {application.candidate_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-ink-muted">{application.job_opening_title}</td>
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
