import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Layout from "../components/Layout";
import StageBadge from "../components/StageBadge";
import Timeline from "../components/Timeline";
import { getApplication } from "../api/applications";
import { getOpening } from "../api/openings";
import { addFeedback, getHistory } from "../api/history";

// Read-only application view for interviewers, scoped server-side to
// applications they're on the panel for. This is the feedback/timeline
// view from goal 9 — candidate info, the full history, and a form to
// leave feedback (interviewer-only, per README goal 1).
export default function ApplicationDetail() {
  const { id } = useParams();
  const [application, setApplication] = useState(null);
  const [openingTitle, setOpeningTitle] = useState("");
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [feedbackText, setFeedbackText] = useState("");
  const [feedbackError, setFeedbackError] = useState("");
  const [feedbackBusy, setFeedbackBusy] = useState(false);

  useEffect(() => {
    Promise.all([getApplication(id), getHistory(id)])
      .then(([data, historyData]) => {
        setApplication(data);
        setHistory(historyData);
        return getOpening(data.job_opening_id);
      })
      .then((opening) => setOpeningTitle(opening.title))
      .catch(() => setError("Could not load that application."))
      .finally(() => setLoading(false));
  }, [id]);

  const handleSubmitFeedback = async (event) => {
    event.preventDefault();
    if (!feedbackText.trim()) return;
    setFeedbackError("");
    setFeedbackBusy(true);
    try {
      await addFeedback(id, feedbackText);
      setFeedbackText("");
      setHistory(await getHistory(id));
    } catch (err) {
      setFeedbackError(err.response?.data?.detail || "Could not submit that feedback.");
    } finally {
      setFeedbackBusy(false);
    }
  };

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

      <div className="mt-6 max-w-lg rounded-lg border border-border bg-surface p-4">
        <h2 className="text-sm font-semibold text-ink">Leave Feedback</h2>
        <form onSubmit={handleSubmitFeedback} className="mt-3 flex flex-col gap-3">
          <textarea
            rows={4}
            value={feedbackText}
            onChange={(event) => setFeedbackText(event.target.value)}
            placeholder="Notes for the recruiting team..."
            className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
          />
          {feedbackError && (
            <p role="alert" className="text-sm font-medium text-danger">
              {feedbackError}
            </p>
          )}
          <button
            type="submit"
            disabled={feedbackBusy || !feedbackText.trim()}
            className="self-start rounded-md bg-brand px-3 py-2 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-60"
          >
            {feedbackBusy ? "Submitting..." : "Submit Feedback"}
          </button>
        </form>
      </div>

      <div className="mt-6 max-w-lg rounded-lg border border-border bg-surface p-4">
        <h2 className="text-sm font-semibold text-ink">History</h2>
        <div className="mt-3">
          <Timeline entries={history} />
        </div>
      </div>
    </Layout>
  );
}
