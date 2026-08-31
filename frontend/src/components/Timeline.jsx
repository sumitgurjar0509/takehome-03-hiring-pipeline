import StageBadge from "./StageBadge";

const EVENT_LABELS = {
  created: "Application created",
  stage_change: "Advanced",
  rejected: "Rejected",
  reinstated: "Reinstated",
  feedback: "Left feedback",
};

function formatDateTime(value) {
  return new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

// Every application's append-only timeline (README goal 9) — nothing in
// it is ever edited or deleted, so this is purely a read view. Shown
// newest-first regardless of the API's chronological order, since that's
// what's most useful when checking "what just happened."
export default function Timeline({ entries }) {
  if (entries.length === 0) {
    return <p className="text-sm text-ink-muted">No history yet.</p>;
  }

  const newestFirst = [...entries].reverse();

  return (
    <ol className="flex flex-col gap-4">
      {newestFirst.map((entry) => (
        <li key={entry.id} className="border-l-2 border-border pl-4">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium text-ink">{EVENT_LABELS[entry.event_type] ?? entry.event_type}</span>
            {entry.old_stage && entry.new_stage && (
              <span className="flex items-center gap-1">
                <StageBadge stage={entry.old_stage} />
                <span className="text-ink-muted">→</span>
                <StageBadge stage={entry.new_stage} />
              </span>
            )}
            {!entry.old_stage && entry.new_stage && <StageBadge stage={entry.new_stage} />}
          </div>
          {entry.feedback_text && (
            <p className="mt-1 whitespace-pre-wrap text-sm text-ink">{entry.feedback_text}</p>
          )}
          <p className="mt-1 text-xs text-ink-muted">
            {entry.actor_name} · {formatDateTime(entry.created_at)}
          </p>
        </li>
      ))}
    </ol>
  );
}
