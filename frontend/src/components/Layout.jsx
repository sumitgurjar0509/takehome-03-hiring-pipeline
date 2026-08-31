import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const recruiterNav = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/openings", label: "Job Openings" },
  { to: "/applications", label: "Applications" },
  { to: "/alerts", label: "Alerts" },
];

const interviewerNav = [{ to: "/my-assignments", label: "My Assignments" }];

function NavItem({ to, label, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
          isActive
            ? "bg-brand text-white"
            : "text-ink-muted hover:bg-black/5 hover:text-ink"
        }`
      }
    >
      {label}
    </NavLink>
  );
}

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navItems = user?.role === "recruiter" ? recruiterNav : interviewerNav;

  return (
    <div className="flex min-h-screen bg-bg">
      <aside className="flex w-60 flex-col border-r border-border bg-surface">
        <div className="px-4 py-5">
          <span className="text-lg font-bold tracking-tight text-ink">Hiring Pipeline</span>
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-3">
          {navItems.map((item) => (
            <NavItem key={item.to} {...item} />
          ))}
        </nav>
        <div className="border-t border-border px-4 py-4">
          <p className="truncate text-sm font-medium text-ink">{user?.name}</p>
          <p className="text-xs capitalize text-ink-muted">{user?.role}</p>
          <button
            onClick={logout}
            className="mt-3 text-sm font-medium text-brand hover:text-brand-hover"
          >
            Log out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-8 py-8">{children}</div>
      </main>
    </div>
  );
}
