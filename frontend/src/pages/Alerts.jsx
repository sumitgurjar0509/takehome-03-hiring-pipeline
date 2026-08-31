import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import StageBadge from "../components/StageBadge";
import { useAlerts } from "../context/AlertsContext";
import { dismissAlert, listAlerts } from "../api/alerts";

function daysStalled(stageChangedAt) {
  const ms = Date.now() - new Date(stageChangedAt).getTime();
  return Math.floor(ms / (1000 * 60 * 60 * 24));
}

export default function Alerts() {
  const { refresh: refreshBadge } = useAlerts();
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [dismissingId, setDismissingId] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    listAlerts()
      .then(setAlerts)
      .catch(() => setError("Could not load alerts."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDismiss = async (applicationId) => {
    setDismissingId(applicationId);
    setError("");
    try {
      await dismissAlert(applicationId);
      setAlerts((prev) => prev.filter((alert) => alert.id !== applicationId));
      refreshBadge();
    } catch {
      setError("Could not dismiss that alert.");
    } finally {
      setDismissingId(null);
    }
  };

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-ink">Alerts</h1>
      <p className="mt-1 text-ink-muted">
        Applications that have sat in the same stage for more than ten days.
      </p>

      {error && (
        <p role="alert" className="mt-4 text-sm font-medium text-danger">
          {error}
        </p>
      )}

      {loading ? (
        <p className="mt-6 text-ink-muted">Loading...</p>
      ) : alerts.length === 0 ? (
        <p className="mt-6 text-ink-muted">No stalled applications right now.</p>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border text-xs uppercase tracking-wide text-ink-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Candidate</th>
                <th className="px-4 py-3 font-medium">Job Opening</th>
                <th className="px-4 py-3 font-medium">Stage</th>
                <th className="px-4 py-3 font-medium">Stalled For</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert) => (
                <tr key={alert.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-3">
                    <Link
                      to={`/applications/${alert.id}/edit`}
                      className="font-medium text-brand hover:underline"
                    >
                      {alert.candidate_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-ink-muted">{alert.job_opening_title}</td>
                  <td className="px-4 py-3">
                    <StageBadge stage={alert.current_stage} />
                  </td>
                  <td className="px-4 py-3 text-ink-muted">{daysStalled(alert.stage_changed_at)} days</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleDismiss(alert.id)}
                      disabled={dismissingId === alert.id}
                      className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-ink hover:bg-black/5 disabled:opacity-60"
                    >
                      Dismiss
                    </button>
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
