import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Layout from "../components/Layout";
import StageBadge from "../components/StageBadge";
import {
  advanceApplication,
  createApplication,
  getApplication,
  reinstateApplication,
  rejectApplication,
  updateApplication,
} from "../api/applications";
import { getOpening } from "../api/openings";

const EMPTY_FORM = { candidate_name: "", candidate_email: "", source: "", notes: "" };

// Mirrors the backend's STAGE_ORDER (app/models.py) — the one-step-forward
// sequence stage-change controls advance along.
const STAGE_ORDER = ["applied", "screening", "interview", "offer", "hired"];

function nextStage(stage) {
  const index = STAGE_ORDER.indexOf(stage);
  if (index === -1 || index + 1 >= STAGE_ORDER.length) return null;
  return STAGE_ORDER[index + 1];
}

function capitalize(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : value;
}

export default function ApplicationForm() {
  const { openingId, id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_FORM);
  const [application, setApplication] = useState(null);
  const [openingTitle, setOpeningTitle] = useState("");
  const [resolvedOpeningId, setResolvedOpeningId] = useState(openingId ? Number(openingId) : null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [pipelineError, setPipelineError] = useState("");
  const [pipelineBusy, setPipelineBusy] = useState(false);

  useEffect(() => {
    if (isEdit) {
      getApplication(id)
        .then((data) => {
          setApplication(data);
          setForm({
            candidate_name: data.candidate_name,
            candidate_email: data.candidate_email,
            source: data.source,
            notes: data.notes,
          });
          setResolvedOpeningId(data.job_opening_id);
          return getOpening(data.job_opening_id);
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

  const runPipelineAction = async (action) => {
    setPipelineError("");
    setPipelineBusy(true);
    try {
      const updated = await action();
      setApplication(updated);
    } catch (err) {
      setPipelineError(err.response?.data?.detail || "Could not update this application's stage.");
    } finally {
      setPipelineBusy(false);
    }
  };

  const handleAdvance = () => {
    const target = nextStage(application.current_stage);
    if (!target) return;
    runPipelineAction(() => advanceApplication(id, target));
  };

  const handleReject = () => runPipelineAction(() => rejectApplication(id));

  const handleReinstate = () => runPipelineAction(() => reinstateApplication(id));

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

      {isEdit && application && (
        <div className="mt-6 max-w-lg rounded-lg border border-border bg-surface p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-ink">Pipeline stage</h2>
            <StageBadge stage={application.current_stage} />
          </div>

          {pipelineError && (
            <p role="alert" className="mt-3 text-sm font-medium text-danger">
              {pipelineError}
            </p>
          )}

          <div className="mt-4 flex flex-wrap gap-3">
            {application.current_stage === "rejected" ? (
              <button
                onClick={handleReinstate}
                disabled={pipelineBusy}
                className="rounded-md bg-brand px-3 py-2 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-60"
              >
                Reinstate to {capitalize(application.rejected_from_stage)}
              </button>
            ) : (
              <>
                {nextStage(application.current_stage) && (
                  <button
                    onClick={handleAdvance}
                    disabled={pipelineBusy}
                    className="rounded-md bg-brand px-3 py-2 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-60"
                  >
                    Advance to {capitalize(nextStage(application.current_stage))}
                  </button>
                )}
                {application.current_stage !== "hired" && (
                  <button
                    onClick={handleReject}
                    disabled={pipelineBusy}
                    className="rounded-md border border-danger px-3 py-2 text-sm font-medium text-danger hover:bg-danger/10 disabled:opacity-60"
                  >
                    Reject
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      )}

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
