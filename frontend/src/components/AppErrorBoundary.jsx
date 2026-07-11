import React from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";

export default class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    if (import.meta.env.DEV) {
      console.error(error);
    }
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className="min-h-screen bg-background text-foreground dark flex items-center justify-center px-6">
        <div className="max-w-md w-full border border-border rounded-lg bg-card/70 p-6 text-center space-y-4">
          <div className="mx-auto h-10 w-10 rounded-full border border-border flex items-center justify-center">
            <AlertTriangle className="h-5 w-5 text-amber-400" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">Something went wrong</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Refresh the page and continue from where you were.
            </p>
          </div>
          <Button onClick={() => window.location.reload()} className="w-full">
            <RotateCcw className="h-4 w-4 mr-2" /> Refresh
          </Button>
        </div>
      </div>
    );
  }
}
