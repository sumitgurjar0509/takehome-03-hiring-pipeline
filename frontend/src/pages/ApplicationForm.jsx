import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Layout from "../components/Layout";
import { createApplication, getApplication, updateApplication } from "../api/applications";
import { getOpening } from "../api/openings";

const EMPTY_FORM = { candidate_name: "", candidate_email: "", source: "", notes: "" };

export default function ApplicationForm() {
  const { openingId, id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_FORM);
  const [openingTitle, setOpeningTitle] = useState("");
  const [resolvedOpeningId, setResolvedOpeningId] = useState(openingId ? Number(openingId) : null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isEdit) {
      getApplication(id)
        .then((application) => {
          setForm({
            candidate_name: application.candidate_name,
            candidate_email: application.candidate_email,
            source: application.source,
            notes: application.notes,
          });
          setResolvedOpeningId(application.job_opening_id);
          return getOpening(application.job_opening_id);
        })
        .then((opening) => setOpeningTitle(opening.title))
        .catch(() => setError("Could not load that application."))
        .finally(() => setLoading(false));
    } else {
      getOpening(openingId)
        .then((opening) => setOpeningTitle(opening.title))
        .catch(() => setError("Could not load that job opening."))
        .finally(() => setLoading(false));
    }
  }, [id, isEdit, openingId]);

  const handleChange = (field) => (event) => setForm((f) => ({ ...f, [field]: event.target.value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      if (isEdit) {
        await updateApplication(id, form);
      } else {
        await createApplication(openingId, form);
      }
      navigate(`/openings/${resolvedOpeningId ?? openingId}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not save that application.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-ink">{isEdit ? "Edit Application" : "New Application"}</h1>
      {openingTitle && <p className="mt-1 text-ink-muted">{openingTitle}</p>}

      {loading ? (
        <p className="mt-6 text-ink-muted">Loading...</p>
      ) : (
        <form onSubmit={handleSubmit} className="mt-6 flex max-w-lg flex-col gap-4">
          <div>
            <label htmlFor="candidate_name" className="mb-1 block text-sm font-medium text-ink">
              Candidate name
            </label>
            <input
              id="candidate_name"
              required
              value={form.candidate_name}
              onChange={handleChange("candidate_name")}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
            />
          </div>
          <div>
            <label htmlFor="candidate_email" className="mb-1 block text-sm font-medium text-ink">
              Email
            </label>
            <input
              id="candidate_email"
              type="email"
              required
              value={form.candidate_email}
              onChange={handleChange("candidate_email")}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
            />
          </div>
          <div>
            <label htmlFor="source" className="mb-1 block text-sm font-medium text-ink">
              Source
            </label>
            <input
              id="source"
              value={form.source}
              onChange={handleChange("source")}
              placeholder="e.g. referral, LinkedIn, careers page"
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
            />
          </div>
          <div>
            <label htmlFor="notes" className="mb-1 block text-sm font-medium text-ink">
              Notes
            </label>
            <textarea
              id="notes"
              rows={5}
              value={form.notes}
              onChange={handleChange("notes")}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
            />
          </div>

          {error && (
            <p role="alert" className="text-sm font-medium text-danger">
              {error}
            </p>
          )}

          <div className="mt-2 flex gap-3">
            <button
              type="submit"
              disabled={saving}
              className="rounded-md bg-brand px-3 py-2 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-60"
            >
              {saving ? "Saving..." : isEdit ? "Save Changes" : "Create Application"}
            </button>
            <button
              type="button"
              onClick={() => navigate(resolvedOpeningId ? `/openings/${resolvedOpeningId}` : "/openings")}
              className="rounded-md border border-border px-3 py-2 text-sm font-medium text-ink hover:bg-black/5"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </Layout>
  );
}
