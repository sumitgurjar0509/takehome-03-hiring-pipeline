import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

/**
 * Gates a route behind login, and optionally behind a specific role.
 * This is a UX convenience only — the server enforces every permission
 * independently, so hiding a link here is never the actual security boundary.
 */
export default function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="p-8 text-ink-muted">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return children;
}
