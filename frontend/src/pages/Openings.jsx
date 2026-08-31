import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import { useAuth } from "../context/AuthContext";
import { archiveOpening, listOpenings, restoreOpening } from "../api/openings";

const STATUS_STYLES = {
  open: "bg-success/10 text-success",
  closed: "bg-ink-muted/10 text-ink-muted",
};

function StatusBadge({ status }) {
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_STYLES[status] ?? ""}`}
    >
      {status}
    </span>
  );
}

export default function Openings() {
  const { user } = useAuth();
  const isRecruiter = user?.role === "recruiter";
  const [openings, setOpenings] = useState([]);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actioningId, setActioningId] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    listOpenings({ includeArchived })
      .then(setOpenings)
      .catch(() => setError("Could not load job openings."))
      .finally(() => setLoading(false));
  }, [includeArchived]);

  useEffect(() => {
    load();
  }, [load]);

  const handleArchive = async (opening) => {
    setActioningId(opening.id);
    try {
      await archiveOpening(opening.id);
      await load();
    } catch {
      setError("Could not archive that opening.");
    } finally {
      setActioningId(null);
    }
  };

  const handleRestore = async (opening) => {
    setActioningId(opening.id);
    try {
      await restoreOpening(opening.id);
      await load();
    } catch {
      setError("Could not restore that opening.");
    } finally {
      setActioningId(null);
    }
  };

  return (
    <Layout>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-ink">Job Openings</h1>
        {isRecruiter && (
          <Link
            to="/openings/new"
            className="rounded-md bg-brand px-3 py-2 text-sm font-medium text-white hover:bg-brand-hover"
          >
            New Opening
          </Link>
        )}
      </div>

      <label className="mt-4 flex w-fit items-center gap-2 text-sm text-ink-muted">
        <input
          type="checkbox"
          checked={includeArchived}
          onChange={(event) => setIncludeArchived(event.target.checked)}
        />
        Show archived
      </label>

      {error && (
        <p role="alert" className="mt-4 text-sm font-medium text-danger">
          {error}
        </p>
      )}

      {loading ? (
        <p className="mt-6 text-ink-muted">Loading...</p>
      ) : openings.length === 0 ? (
        <p className="mt-6 text-ink-muted">No job openings yet.</p>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border text-xs uppercase tracking-wide text-ink-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Title</th>
                <th className="px-4 py-3 font-medium">Department</th>
                <th className="px-4 py-3 font-medium">Status</th>
                {isRecruiter && <th className="px-4 py-3 font-medium">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {openings.map((opening) => (
                <tr
                  key={opening.id}
                  className={`border-b border-border last:border-0 ${opening.archived ? "opacity-60" : ""}`}
                >
                  <td className="px-4 py-3">
                    {isRecruiter ? (
                      <Link
                        to={`/openings/${opening.id}/edit`}
                        className="font-medium text-brand hover:underline"
                      >
                        {opening.title}
                      </Link>
                    ) : (
                      <span className="font-medium text-ink">{opening.title}</span>
                    )}
                    {opening.archived && (
                      <span className="ml-2 inline-block rounded-full border border-border px-2 py-0.5 text-xs font-medium text-ink-muted">
                        Archived
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-ink-muted">{opening.department}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={opening.status} />
                  </td>
                  {isRecruiter && (
                    <td className="px-4 py-3">
                      {opening.archived ? (
                        <button
                          onClick={() => handleRestore(opening)}
                          disabled={actioningId === opening.id}
                          className="text-sm font-medium text-brand hover:text-brand-hover disabled:opacity-60"
                        >
                          Restore
                        </button>
                      ) : (
                        <button
                          onClick={() => handleArchive(opening)}
                          disabled={actioningId === opening.id}
                          className="text-sm font-medium text-danger hover:text-danger-hover disabled:opacity-60"
                        >
                          Archive
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}
