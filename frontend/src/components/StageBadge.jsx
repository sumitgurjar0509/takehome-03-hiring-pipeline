const STAGE_STYLES = {
  applied: "bg-stage-applied/10 text-stage-applied",
  screening: "bg-stage-screening/10 text-stage-screening",
  interview: "bg-stage-interview/10 text-stage-interview",
  offer: "bg-stage-offer/10 text-stage-offer",
  hired: "bg-stage-hired/10 text-stage-hired",
  rejected: "bg-stage-rejected/10 text-stage-rejected",
};

export default function StageBadge({ stage }) {
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STAGE_STYLES[stage] ?? ""}`}
    >
      {stage}
    </span>
  );
}
