import React, { useEffect } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { rememberProtectedPath } from "@/lib/routeMemory";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  useEffect(() => {
    if (!loading && user) {
      rememberProtectedPath(`${location.pathname}${location.search}`);
    }
  }, [loading, user, location.pathname, location.search]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background text-foreground dark">
        <div className="w-10 h-10 border-2 border-foreground/30 border-t-foreground rounded-full animate-spin" />
      </div>
    );
  }
  if (!user) return <Navigate to="/" replace state={{ from: location }} />;
  return children;
}
