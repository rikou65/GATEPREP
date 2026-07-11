import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, SearchX } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-background text-foreground dark flex items-center justify-center px-6">
      <div className="max-w-md w-full border border-border rounded-lg bg-card/70 p-6 text-center space-y-4">
        <div className="mx-auto h-10 w-10 rounded-full border border-border flex items-center justify-center">
          <SearchX className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">404</div>
          <h1 className="text-xl font-semibold mt-1">Page not found</h1>
          <p className="text-sm text-muted-foreground mt-1">
            This route does not exist in GATEPREP.
          </p>
        </div>
        <Button asChild className="w-full">
          <Link to="/dashboard">
            <ArrowLeft className="h-4 w-4 mr-2" /> Back to Dashboard
          </Link>
        </Button>
      </div>
    </div>
  );
}
