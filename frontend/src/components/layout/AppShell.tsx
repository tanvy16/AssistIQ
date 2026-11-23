import { Suspense, useState } from "react";
import { Link, Outlet } from "react-router-dom";

import { useAuth } from "../../context/AuthContext";

import { PageFallback } from "../ui/LoadingState";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";

export default function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-canvas">
      <TopBar
        menuOpen={menuOpen}
        onMenuToggle={() => setMenuOpen((current) => !current)}
      />
      <div className="flex min-h-[calc(100vh-3rem)]">
        <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
        <main className="min-w-0 flex-1 px-4 py-5 sm:px-6 sm:py-6 lg:px-8">
          {user?.mfa_enrollment_required ? (
            <div
              role="status"
              className="mb-5 flex flex-wrap items-center justify-between gap-2 rounded border border-storage bg-storage-soft px-3 py-2 text-sm text-ink"
            >
              <span>
                Multi-factor authentication is required for your role and is not set up yet.
              </span>
              <Link to={`/app/${user.role}/security`} className="font-medium text-accent hover:underline">
                Set up now
              </Link>
            </div>
          ) : null}
          <Suspense fallback={<PageFallback />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  );
}
