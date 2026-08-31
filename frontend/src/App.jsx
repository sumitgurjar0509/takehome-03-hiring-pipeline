import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Home from "./pages/Home";
import Openings from "./pages/Openings";
import OpeningForm from "./pages/OpeningForm";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Home />
              </ProtectedRoute>
            }
          />
          <Route
            path="/openings"
            element={
              <ProtectedRoute>
                <Openings />
              </ProtectedRoute>
            }
          />
          <Route
            path="/openings/new"
            element={
              <ProtectedRoute roles={["recruiter"]}>
                <OpeningForm />
              </ProtectedRoute>
            }
          />
          <Route
            path="/openings/:id/edit"
            element={
              <ProtectedRoute roles={["recruiter"]}>
                <OpeningForm />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
