import React from "react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { LogOut } from "lucide-react";

export default function Settings() {
  const { user, logout } = useAuth();
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Account</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-1">Settings</h1>
      </div>
      <div className="border border-border rounded-lg p-5 space-y-3">
        <div className="flex items-center gap-4">
          {user?.picture && <img src={user.picture} alt="" className="w-12 h-12 rounded-full border border-border" />}
          <div>
            <div className="text-sm font-medium">{user?.name}</div>
            <div className="text-xs text-muted-foreground mono">{user?.email}</div>
            {user?.is_admin && <div className="text-[10px] mono text-emerald-500 mt-1">ADMIN</div>}
          </div>
        </div>
      </div>
      <div className="border border-border rounded-lg p-5">
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Session</div>
        <Button variant="outline" onClick={logout} data-testid="settings-logout-btn">
          <LogOut className="w-4 h-4 mr-1" /> Sign out
        </Button>
      </div>
    </div>
  );
}
