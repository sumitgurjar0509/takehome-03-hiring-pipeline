import Layout from "../components/Layout";
import { useAuth } from "../context/AuthContext";

// Placeholder landing page — just enough for the post-login redirect to have
// somewhere to go. Becomes the real dashboard in goal 8.
export default function Home() {
  const { user } = useAuth();

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-ink">Welcome, {user?.name}</h1>
      <p className="mt-2 text-ink-muted">
        Signed in as <span className="capitalize">{user?.role}</span>. The dashboard lands here in goal 8.
      </p>
    </Layout>
  );
}
