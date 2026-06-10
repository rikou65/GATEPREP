import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import ProtectedRoute from "@/components/ProtectedRoute";

import Login from "@/pages/Login";
import AuthCallback from "@/pages/AuthCallback";
import Dashboard from "@/pages/Dashboard";
import Subjects from "@/pages/Subjects";
import SubjectDetail from "@/pages/SubjectDetail";
import TopicDetail from "@/pages/TopicDetail";
import QuestionBank from "@/pages/QuestionBank";
import PYQs from "@/pages/PYQs";
import MistakeLab from "@/pages/MistakeLab";
import Playlists from "@/pages/Playlists";
import PlaylistDetail from "@/pages/PlaylistDetail";
import Resources from "@/pages/Resources";
import Analytics from "@/pages/Analytics";
import Settings from "@/pages/Settings";

function AppRouter() {
  const location = useLocation();
  // Synchronously detect OAuth return - prevents race conditions
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/subjects" element={<ProtectedRoute><Subjects /></ProtectedRoute>} />
      <Route path="/subjects/:id" element={<ProtectedRoute><SubjectDetail /></ProtectedRoute>} />
      <Route path="/topics/:id" element={<ProtectedRoute><TopicDetail /></ProtectedRoute>} />
      <Route path="/questions" element={<ProtectedRoute><QuestionBank /></ProtectedRoute>} />
      <Route path="/pyqs" element={<ProtectedRoute><PYQs /></ProtectedRoute>} />
      <Route path="/mistakes" element={<ProtectedRoute><MistakeLab /></ProtectedRoute>} />
      <Route path="/playlists" element={<ProtectedRoute><Playlists /></ProtectedRoute>} />
      <Route path="/playlists/:id" element={<ProtectedRoute><PlaylistDetail /></ProtectedRoute>} />
      <Route path="/resources" element={<ProtectedRoute><Resources /></ProtectedRoute>} />
      <Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
    </Routes>
  );
}

export default function App() {
  return (
    <div className="App dark">
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
          <Toaster theme="dark" position="top-right" />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}
