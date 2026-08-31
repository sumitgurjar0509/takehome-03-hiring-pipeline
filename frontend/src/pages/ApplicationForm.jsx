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
import {
  assignInterviewer,
  getApplicationPanel,
  listInterviewers,
  unassignInterviewer,
} from "../api/panel";

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
  const [panel, setPanel] = useState(null);
  const [interviewerOptions, setInterviewerOptions] = useState([]);
  const [selectedInterviewerId, setSelectedInterviewerId] = useState("");
  const [panelError, setPanelError] = useState("");
  const [panelBusy, setPanelBusy] = useState(false);

  useEffect(() => {
    if (isEdit) {
      Promise.all([getApplication(id), getApplicationPanel(id), listInterviewers()])
        .then(([data, panelData, interviewersData]) => {
          setApplication(data);
          setForm({
            candidate_name: data.candidate_name,
            candidate_email: data.candidate_email,
            source: data.source,
            notes: data.notes,
          });
          setResolvedOpeningId(data.job_opening_id);
          setPanel(panelData);
          setInterviewerOptions(interviewersData);
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

  const handleAssign = async () => {
    if (!selectedInterviewerId) return;
    setPanelError("");
    setPanelBusy(true);
    try {
      const updated = await assignInterviewer(id, Number(selectedInterviewerId));
      setPanel(updated);
      setSelectedInterviewerId("");
    } catch (err) {
      setPanelError(err.response?.data?.detail || "Could not assign that interviewer.");
    } finally {
      setPanelBusy(false);
    }
  };

  const handleUnassign = async (interviewerId) => {
    setPanelError("");
    setPanelBusy(true);
    try {
      const updated = await unassignInterviewer(id, interviewerId);
      setPanel(updated);
    } catch (err) {
      setPanelError(err.response?.data?.detail || "Could not remove that interviewer.");
    } finally {
      setPanelBusy(false);
    }
  };

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

      {isEdit && panel !== null && (
        <div className="mt-6 max-w-lg rounded-lg border border-border bg-surface p-4">
          <h2 className="text-sm font-semibold text-ink">Interview panel</h2>

          {panelError && (
            <p role="alert" className="mt-3 text-sm font-medium text-danger">
              {panelError}
            </p>
          )}

          <div className="mt-3 flex flex-wrap gap-2">
            {panel.length === 0 ? (
              <p className="text-sm text-ink-muted">No interviewers assigned yet.</p>
            ) : (
              panel.map((assignedInterviewer) => (
                <span
                  key={assignedInterviewer.id}
                  className="inline-flex items-center gap-1.5 rounded-full border border-border bg-bg px-2.5 py-1 text-xs font-medium text-ink"
                >
                  {assignedInterviewer.name}
                  <button
                    type="button"
                    onClick={() => handleUnassign(assignedInterviewer.id)}
                    disabled={panelBusy}
                    aria-label={`Remove ${assignedInterviewer.name} from the panel`}
                    className="text-ink-muted hover:text-danger disabled:opacity-60"
                  >
                    ×
                  </button>
                </span>
              ))
            )}
          </div>

          <div className="mt-4 flex gap-2">
            <select
              value={selectedInterviewerId}
              onChange={(event) => setSelectedInterviewerId(event.target.value)}
              className="flex-1 rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
            >
              <option value="">Select an interviewer…</option>
              {interviewerOptions
                .filter((option) => !panel.some((assigned) => assigned.id === option.id))
                .map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name} ({option.email})
                  </option>
                ))}
            </select>
            <button
              type="button"
              onClick={handleAssign}
              disabled={panelBusy || !selectedInterviewerId}
              className="rounded-md bg-brand px-3 py-2 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-60"
            >
              Assign
            </button>
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
