import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Layout from "../components/Layout";
import StageBadge from "../components/StageBadge";
import { useAuth } from "../context/AuthContext";
import { getDashboard } from "../api/dashboard";

const STAGE_COLOR_VARS = {
  applied: "var(--color-stage-applied)",
  screening: "var(--color-stage-screening)",
  interview: "var(--color-stage-interview)",
  offer: "var(--color-stage-offer)",
  hired: "var(--color-stage-hired)",
  rejected: "var(--color-stage-rejected)",
};

// Recharts sets fill/stroke as raw SVG presentation attributes rather than
// inline style, and CSS custom properties don't reliably resolve there
// (unlike style="fill:var(...)", which always works) — so the chart needs
// the actual computed color values, not the var() reference.
function useCssVar(name, fallback) {
  const [value, setValue] = useState(fallback);
  useEffect(() => {
    const resolved = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    if (resolved) setValue(resolved);
  }, [name]);
  return value;
}

function KpiCard({ label, value }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <p className="text-sm text-ink-muted">{label}</p>
      <p className="mt-1 text-3xl font-bold text-ink">{value}</p>
    </div>
  );
}

// This is the "/" route recruiters land on (README goal 8). It's
// recruiter-only throughout, consistent with goal 1 — interviewers never
// see cross-opening pipeline data, so rather than adding an
// interviewer-scoped variant, an interviewer landing here is bounced to
// their real landing page instead.
export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (user?.role !== "recruiter") return;
    getDashboard()
      .then(setData)
      .catch(() => setError("Could not load the dashboard."))
      .finally(() => setLoading(false));
  }, [user]);

  if (user?.role !== "recruiter") {
    return <Navigate to="/my-assignments" replace />;
  }

  const maxStageCount = data ? Math.max(...data.by_stage.map((row) => row.count), 1) : 1;
  const brandColor = useCssVar("--color-brand", "#2f5d9f");
  const borderColor = useCssVar("--color-border", "#e4e4e0");
  const inkMutedColor = useCssVar("--color-ink-muted", "#5b5f6b");

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-ink">Dashboard</h1>

      {error && (
        <p role="alert" className="mt-4 text-sm font-medium text-danger">
          {error}
        </p>
      )}

      {loading ? (
        <p className="mt-6 text-ink-muted">Loading...</p>
      ) : (
        data && (
          <>
            <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <KpiCard label="Open Positions" value={data.open_positions} />
              <KpiCard label="Active Applications" value={data.active_applications} />
              <KpiCard label="Interviews This Week" value={data.interviews_scheduled_this_week} />
              <KpiCard label="Hires This Month" value={data.hires_this_month} />
            </div>

            <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
              <div className="rounded-lg border border-border bg-surface p-4">
                <h2 className="text-sm font-semibold text-ink">By Job Opening</h2>
                {data.by_opening.length === 0 ? (
                  <p className="mt-3 text-sm text-ink-muted">No applications yet.</p>
                ) : (
                  <table className="mt-3 w-full text-left text-sm">
                    <tbody>
                      {data.by_opening.map((row) => (
                        <tr key={row.job_opening_id} className="border-t border-border first:border-0">
                          <td className="py-2 text-ink">{row.job_opening_title}</td>
                          <td className="py-2 text-right font-medium text-ink">{row.count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              <div className="rounded-lg border border-border bg-surface p-4">
                <h2 className="text-sm font-semibold text-ink">By Stage</h2>
                <div className="mt-3 flex flex-col gap-2">
                  {data.by_stage.map((row) => (
                    <div key={row.stage} className="flex items-center gap-3">
                      <div className="w-24 shrink-0">
                        <StageBadge stage={row.stage} />
                      </div>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-bg">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${(row.count / maxStageCount) * 100}%`,
                            backgroundColor: STAGE_COLOR_VARS[row.stage],
                          }}
                        />
                      </div>
                      <span className="w-8 shrink-0 text-right text-sm font-medium text-ink">
                        {row.count}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-6 rounded-lg border border-border bg-surface p-4">
              <h2 className="text-sm font-semibold text-ink">Applications Received Per Week</h2>
              <div className="mt-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.applications_per_week}>
                    <CartesianGrid strokeDasharray="3 3" stroke={borderColor} />
                    <XAxis
                      dataKey="week_start"
                      tick={{ fontSize: 12, fill: inkMutedColor }}
                      tickFormatter={(value) => value.slice(5)}
                    />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: inkMutedColor }} />
                    <Tooltip />
                    <Bar dataKey="count" fill={brandColor} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        )
      )}
    </Layout>
  );
}
