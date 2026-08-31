import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Layout from "../components/Layout";
import { createOpening, getOpening, updateOpening } from "../api/openings";

const EMPTY_FORM = { title: "", department: "", description: "", status: "open" };

export default function OpeningForm() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isEdit) return;
    getOpening(id)
      .then((opening) =>
        setForm({
          title: opening.title,
          department: opening.department,
          description: opening.description,
          status: opening.status,
        })
      )
      .catch(() => setError("Could not load that job opening."))
      .finally(() => setLoading(false));
  }, [id, isEdit]);

  const handleChange = (field) => (event) => setForm((f) => ({ ...f, [field]: event.target.value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      if (isEdit) {
        await updateOpening(id, form);
      } else {
        await createOpening(form);
      }
      navigate("/openings");
    } catch (err) {
      setError(err.response?.data?.detail || "Could not save that job opening.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-ink">{isEdit ? "Edit Job Opening" : "New Job Opening"}</h1>

      {loading ? (
        <p className="mt-6 text-ink-muted">Loading...</p>
      ) : (
        <form onSubmit={handleSubmit} className="mt-6 flex max-w-lg flex-col gap-4">
          <div>
            <label htmlFor="title" className="mb-1 block text-sm font-medium text-ink">
              Title
            </label>
            <input
              id="title"
              required
              value={form.title}
              onChange={handleChange("title")}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
            />
          </div>
          <div>
            <label htmlFor="department" className="mb-1 block text-sm font-medium text-ink">
              Department
            </label>
            <input
              id="department"
              required
              value={form.department}
              onChange={handleChange("department")}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
            />
          </div>
          <div>
            <label htmlFor="description" className="mb-1 block text-sm font-medium text-ink">
              Description
            </label>
            <textarea
              id="description"
              rows={5}
              value={form.description}
              onChange={handleChange("description")}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
            />
          </div>
          <div>
            <label htmlFor="status" className="mb-1 block text-sm font-medium text-ink">
              Status
            </label>
            <select
              id="status"
              value={form.status}
              onChange={handleChange("status")}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
            >
              <option value="open">Open</option>
              <option value="closed">Closed</option>
            </select>
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
              {saving ? "Saving..." : isEdit ? "Save Changes" : "Create Opening"}
            </button>
            <button
              type="button"
              onClick={() => navigate("/openings")}
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
