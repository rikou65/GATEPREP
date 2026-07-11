import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import { queryClient } from "@/api/client";
import ProtectedRoute from "@/components/ProtectedRoute";
import AppErrorBoundary from "@/components/AppErrorBoundary";

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
import StagingQueue from "@/pages/StagingQueue";
import ImportPDF from "@/pages/ImportPDF";
import NotFound from "@/pages/NotFound";

function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
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
      <Route path="/data/staging" element={<ProtectedRoute><StagingQueue /></ProtectedRoute>} />
      <Route path="/data/import" element={<ProtectedRoute><ImportPDF /></ProtectedRoute>} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default function App() {
  return (
    <div className="App dark">
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <AppErrorBoundary>
              <AppRouter />
            </AppErrorBoundary>
            <Toaster theme="dark" position="top-right" />
          </AuthProvider>
        </QueryClientProvider>
      </BrowserRouter>
    </div>
  );
}
