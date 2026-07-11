import React, { lazy, Suspense } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import { queryClient } from "@/api/client";
import ProtectedRoute from "@/components/ProtectedRoute";
import AppErrorBoundary from "@/components/AppErrorBoundary";

const Login = lazy(() => import("@/pages/Login"));
const AuthCallback = lazy(() => import("@/pages/AuthCallback"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Subjects = lazy(() => import("@/pages/Subjects"));
const SubjectDetail = lazy(() => import("@/pages/SubjectDetail"));
const TopicDetail = lazy(() => import("@/pages/TopicDetail"));
const QuestionBank = lazy(() => import("@/pages/QuestionBank"));
const PYQs = lazy(() => import("@/pages/PYQs"));
const MistakeLab = lazy(() => import("@/pages/MistakeLab"));
const Playlists = lazy(() => import("@/pages/Playlists"));
const PlaylistDetail = lazy(() => import("@/pages/PlaylistDetail"));
const Resources = lazy(() => import("@/pages/Resources"));
const Analytics = lazy(() => import("@/pages/Analytics"));
const Settings = lazy(() => import("@/pages/Settings"));
const StagingQueue = lazy(() => import("@/pages/StagingQueue"));
const ImportPDF = lazy(() => import("@/pages/ImportPDF"));
const NotFound = lazy(() => import("@/pages/NotFound"));

function PageLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground dark">
      <div className="w-10 h-10 border-2 border-foreground/30 border-t-foreground rounded-full animate-spin" />
    </div>
  );
}

function AppRouter() {
  return (
    <Suspense fallback={<PageLoader />}>
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
    </Suspense>
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
