import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import StageBadge from "../components/StageBadge";
import { bulkAction, downloadApplicationsCsv, listApplications } from "../api/applications";
import { listOpenings } from "../api/openings";

const STAGE_OPTIONS = ["applied", "screening", "interview", "offer", "hired", "rejected"];

const SORT_OPTIONS = [
  { value: "-applied_date", label: "Applied date (newest first)" },
  { value: "applied_date", label: "Applied date (oldest first)" },
  { value: "stage", label: "Stage (Applied → Hired)" },
  { value: "-stage", label: "Stage (Hired → Applied)" },
  { value: "-last_update", label: "Last updated (newest first)" },
  { value: "last_update", label: "Last updated (oldest first)" },
];

const PAGE_SIZE = 20;

function capitalize(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : value;
}

export default function Applications() {
  const [openings, setOpenings] = useState([]);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [jobOpeningId, setJobOpeningId] = useState("");
  const [stage, setStage] = useState("");
  const [source, setSource] = useState("");
  const [sort, setSort] = useState("-applied_date");
  const [page, setPage] = useState(1);
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [bulkResults, setBulkResults] = useState({});
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkError, setBulkError] = useState("");
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    listOpenings({ includeArchived: true })
      .then(setOpenings)
      .catch(() => {});
  }, []);

  const resetSelection = () => {
    setSelectedIds(new Set());
    setBulkResults({});
  };

  // Debounce only the free-text box; every other control refetches immediately.
  useEffect(() => {
    const timeout = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
      resetSelection();
    }, 300);
    return () => clearTimeout(timeout);
  }, [searchInput]);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    listApplications({
      search: search || undefined,
      job_opening_id: jobOpeningId || undefined,
      stage: stage || undefined,
      source: source || undefined,
      sort,
      page,
      page_size: PAGE_SIZE,
    })
      .then((data) => {
        setResults(data.results);
        setTotal(data.total);
      })
      .catch(() => setError("Could not load applications."))
      .finally(() => setLoading(false));
  }, [search, jobOpeningId, stage, source, sort, page]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const handleFilterChange = (setter) => (event) => {
    setter(event.target.value);
    setPage(1);
    resetSelection();
  };

  const goToPage = (updater) => {
    setPage(updater);
    resetSelection();
  };

  const toggleSelected = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const allOnPageSelected = results.length > 0 && results.every((r) => selectedIds.has(r.id));

  const toggleSelectAllOnPage = () => {
    setSelectedIds((prev) => {
      if (allOnPageSelected) {
        const next = new Set(prev);
        results.forEach((r) => next.delete(r.id));
        return next;
      }
      const next = new Set(prev);
      results.forEach((r) => next.add(r.id));
      return next;
    });
  };

  const runBulkAction = async (action) => {
    if (selectedIds.size === 0) return;
    setBulkError("");
    setBulkBusy(true);
    try {
      const response = await bulkAction(Array.from(selectedIds), action);
      const resultsMap = {};
      for (const item of response.results) {
        resultsMap[item.application_id] = { success: item.success, message: item.message };
      }
      setBulkResults(resultsMap);
      setSelectedIds(new Set());
      await load();
    } catch (err) {
      setBulkError(err.response?.data?.detail || "Could not complete the bulk action.");
    } finally {
      setBulkBusy(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await downloadApplicationsCsv();
    } catch {
      setError("Could not export applications.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <Layout>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-ink">Applications</h1>
        <button
          type="button"
          onClick={handleExport}
          disabled={exporting}
          className="rounded-md border border-border px-3 py-2 text-sm font-medium text-ink hover:bg-black/5 disabled:opacity-60"
        >
          {exporting ? "Exporting..." : "Export CSV"}
        </button>
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-3">
        <div className="min-w-[220px] flex-1">
          <label htmlFor="search" className="mb-1 block text-sm font-medium text-ink">
            Search
          </label>
          <input
            id="search"
            type="text"
            placeholder="Name or email"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
          />
        </div>

        <div>
          <label htmlFor="job_opening" className="mb-1 block text-sm font-medium text-ink">
            Job Opening
          </label>
          <select
            id="job_opening"
            value={jobOpeningId}
            onChange={handleFilterChange(setJobOpeningId)}
            className="rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
          >
            <option value="">All openings</option>
            {openings.map((opening) => (
              <option key={opening.id} value={opening.id}>
                {opening.title}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="stage" className="mb-1 block text-sm font-medium text-ink">
            Stage
          </label>
          <select
            id="stage"
            value={stage}
            onChange={handleFilterChange(setStage)}
            className="rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
          >
            <option value="">All stages</option>
            {STAGE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {capitalize(option)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="source" className="mb-1 block text-sm font-medium text-ink">
            Source
          </label>
          <input
            id="source"
            type="text"
            placeholder="e.g. referral"
            value={source}
            onChange={handleFilterChange(setSource)}
            className="w-40 rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
          />
        </div>

        <div>
          <label htmlFor="sort" className="mb-1 block text-sm font-medium text-ink">
            Sort by
          </label>
          <select
            id="sort"
            value={sort}
            onChange={(event) => {
              setSort(event.target.value);
              setPage(1);
              resetSelection();
            }}
            className="rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <p role="alert" className="mt-4 text-sm font-medium text-danger">
          {error}
        </p>
      )}

      {selectedIds.size > 0 && (
        <div className="mt-4 flex items-center gap-3 rounded-md border border-border bg-surface px-4 py-2">
          <span className="text-sm text-ink-muted">{selectedIds.size} selected</span>
          <button
            type="button"
            onClick={() => runBulkAction("advance")}
            disabled={bulkBusy}
            className="rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-60"
          >
            Advance Selected
          </button>
          <button
            type="button"
            onClick={() => runBulkAction("reject")}
            disabled={bulkBusy}
            className="rounded-md border border-danger px-3 py-1.5 text-sm font-medium text-danger hover:bg-danger/10 disabled:opacity-60"
          >
            Reject Selected
          </button>
        </div>
      )}

      {bulkError && (
        <p role="alert" className="mt-3 text-sm font-medium text-danger">
          {bulkError}
        </p>
      )}

      {loading ? (
        <p className="mt-6 text-ink-muted">Loading...</p>
      ) : results.length === 0 ? (
        <p className="mt-6 text-ink-muted">No applications match these filters.</p>
      ) : (
        <>
          <div className="mt-6 overflow-x-auto rounded-lg border border-border bg-surface">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border text-xs uppercase tracking-wide text-ink-muted">
                <tr>
                  <th className="w-8 px-4 py-3">
                    <input
                      type="checkbox"
                      checked={allOnPageSelected}
                      onChange={toggleSelectAllOnPage}
                      aria-label="Select all on this page"
                    />
                  </th>
                  <th className="px-4 py-3 font-medium">Candidate</th>
                  <th className="px-4 py-3 font-medium">Email</th>
                  <th className="px-4 py-3 font-medium">Source</th>
                  <th className="px-4 py-3 font-medium">Stage</th>
                  <th className="px-4 py-3 font-medium">Result</th>
                </tr>
              </thead>
              <tbody>
                {results.map((application) => {
                  const result = bulkResults[application.id];
                  return (
                    <tr key={application.id} className="border-b border-border last:border-0">
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(application.id)}
                          onChange={() => toggleSelected(application.id)}
                          aria-label={`Select ${application.candidate_name}`}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          to={`/applications/${application.id}/edit`}
                          className="font-medium text-brand hover:underline"
                        >
                          {application.candidate_name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-ink-muted">{application.candidate_email}</td>
                      <td className="px-4 py-3 text-ink-muted">{application.source || "—"}</td>
                      <td className="px-4 py-3">
                        <StageBadge stage={application.current_stage} />
                      </td>
                      <td className="px-4 py-3">
                        {result && (
                          <span
                            title={result.message}
                            className={`text-xs font-medium ${result.success ? "text-success" : "text-danger"}`}
                          >
                            {result.success ? "✓ " : "✗ "}
                            {result.message}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex items-center justify-between text-sm text-ink-muted">
            <span>
              {total} match{total === 1 ? "" : "es"} — page {page} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => goToPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="rounded-md border border-border px-3 py-1.5 font-medium text-ink hover:bg-black/5 disabled:opacity-50"
              >
                Previous
              </button>
              <button
                type="button"
                onClick={() => goToPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="rounded-md border border-border px-3 py-1.5 font-medium text-ink hover:bg-black/5 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </Layout>
  );
}
