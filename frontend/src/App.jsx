import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { AlertsProvider } from "./context/AlertsContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Openings from "./pages/Openings";
import Applications from "./pages/Applications";
import Alerts from "./pages/Alerts";
import OpeningForm from "./pages/OpeningForm";
import OpeningDetail from "./pages/OpeningDetail";
import ApplicationForm from "./pages/ApplicationForm";
import ApplicationDetail from "./pages/ApplicationDetail";
import MyAssignments from "./pages/MyAssignments";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AlertsProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Dashboard />
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
              path="/applications"
              element={
                <ProtectedRoute roles={["recruiter"]}>
                  <Applications />
                </ProtectedRoute>
              }
            />
            <Route
              path="/alerts"
              element={
                <ProtectedRoute roles={["recruiter"]}>
                  <Alerts />
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
            <Route
              path="/openings/:openingId/applications/new"
              element={
                <ProtectedRoute roles={["recruiter"]}>
                  <ApplicationForm />
                </ProtectedRoute>
              }
            />
            <Route
              path="/applications/:id/edit"
              element={
                <ProtectedRoute roles={["recruiter"]}>
                  <ApplicationForm />
                </ProtectedRoute>
              }
            />
            <Route
              path="/openings/:id"
              element={
                <ProtectedRoute roles={["recruiter"]}>
                  <OpeningDetail />
                </ProtectedRoute>
              }
            />
            <Route
              path="/my-assignments"
              element={
                <ProtectedRoute roles={["interviewer"]}>
                  <MyAssignments />
                </ProtectedRoute>
              }
            />
            <Route
              path="/applications/:id"
              element={
                <ProtectedRoute roles={["interviewer"]}>
                  <ApplicationDetail />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AlertsProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
