import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  LayoutDashboard, BookOpen, FileQuestion, History, ListVideo,
  FolderArchive, AlertOctagon, BarChart3, Settings, LogOut,
  GraduationCap,
} from "lucide-react";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, id: "nav-dashboard" },
  { to: "/subjects", label: "Subjects", icon: BookOpen, id: "nav-subjects" },
  { to: "/questions", label: "Question Bank", icon: FileQuestion, id: "nav-questions" },
  { to: "/pyqs", label: "PYQs", icon: History, id: "nav-pyqs" },
  { to: "/playlists", label: "Playlists", icon: ListVideo, id: "nav-playlists" },
  { to: "/resources", label: "Resources", icon: FolderArchive, id: "nav-resources" },
  { to: "/mistakes", label: "Mistake Lab", icon: AlertOctagon, id: "nav-mistakes" },
  { to: "/analytics", label: "Analytics", icon: BarChart3, id: "nav-analytics" },
  { to: "/settings", label: "Settings", icon: Settings, id: "nav-settings" },
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-background text-foreground dark">
      <aside className="fixed left-0 top-0 w-64 h-screen border-r border-border bg-card/40 backdrop-blur-xl z-30 flex flex-col">
        <div
          className="px-5 py-5 flex items-center gap-2 border-b border-border cursor-pointer"
          onClick={() => navigate("/dashboard")}
          data-testid="brand-link"
        >
          <GraduationCap className="w-5 h-5" />
          <div>
            <div className="text-sm font-bold tracking-tight leading-none">GATEPREP</div>
            <div className="text-[10px] text-muted-foreground mono mt-0.5">GATE · CSE</div>
          </div>
        </div>
        <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              data-testid={n.id}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                  isActive
                    ? "bg-secondary text-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                }`
              }
            >
              <n.icon className="w-4 h-4" strokeWidth={1.6} />
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-border">
          <div className="flex items-center gap-3 px-2 py-2">
            {user?.picture ? (
              <img src={user.picture} alt="" className="w-8 h-8 rounded-full border border-border" />
            ) : (
              <div className="w-8 h-8 rounded-full bg-secondary" />
            )}
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium truncate" data-testid="user-name">{user?.name}</div>
              <div className="text-[10px] text-muted-foreground truncate">{user?.email}</div>
            </div>
            <button
              onClick={logout}
              data-testid="logout-btn"
              className="p-1.5 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground"
              title="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>
      <main className="ml-64 min-h-screen p-6 md:p-8 page-enter">{children}</main>
    </div>
  );
}
