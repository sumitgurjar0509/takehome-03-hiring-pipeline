import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { listAlerts } from "../api/alerts";

const AlertsContext = createContext(null);

// Holds the stalled-alerts count for the sidebar badge (README goal 10).
// Lives above the router so the count survives page navigation. Stalling
// is purely a function of elapsed time, so the count can go stale just by
// sitting on one page — this refetches on every route change (a cheap,
// natural "check for anything new" moment) as well as right after a
// dismiss, rather than only once on mount.
export function AlertsProvider({ children }) {
  const { user } = useAuth();
  const location = useLocation();
  const [count, setCount] = useState(0);

  const refresh = useCallback(() => {
    if (user?.role !== "recruiter") {
      setCount(0);
      return;
    }
    listAlerts()
      .then((alerts) => setCount(alerts.length))
      .catch(() => {});
  }, [user]);

  useEffect(() => {
    refresh();
  }, [refresh, location.pathname]);

  return <AlertsContext.Provider value={{ count, refresh }}>{children}</AlertsContext.Provider>;
}

export function useAlerts() {
  const ctx = useContext(AlertsContext);
  if (!ctx) throw new Error("useAlerts must be used within an AlertsProvider");
  return ctx;
}
