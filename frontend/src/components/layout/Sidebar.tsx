import { NavLink } from "react-router-dom";

import { useAuth } from "../../context/AuthContext";
import { getNavigationForRole } from "../../lib/navigation";

type SidebarProps = {
  open: boolean;
  onClose: () => void;
};

export default function Sidebar({ open, onClose }: SidebarProps) {
  const { user } = useAuth();

  if (!user) {
    return null;
  }

  const items = getNavigationForRole(user.role);

  return (
    <>
      {open ? (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-overlay md:hidden"
          aria-label="Close navigation overlay"
          onClick={onClose}
        />
      ) : null}

      <aside
        id="app-sidebar"
        className={`shell-nav fixed inset-y-0 left-0 z-50 flex w-52 flex-col border-r border-surface-border pt-12 transition-transform md:static md:z-0 md:translate-x-0 md:pt-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-label="Primary navigation"
      >
        <nav className="flex-1 overflow-y-auto px-2 py-3">
          <ul className="space-y-0.5">
            {items.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  end={item.end}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `block rounded-sm px-2.5 py-1.5 text-[13px] transition focus-visible:outline-none ${
                      isActive
                        ? "border-l-2 border-accent bg-surface-hover pl-[8px] font-medium text-ink"
                        : "border-l-2 border-transparent text-ink-muted hover:bg-surface-hover hover:text-ink"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="border-t border-surface-border px-3 py-2.5 text-[11px] text-ink-subtle">
          AssistIQ · Local operations console
        </div>
      </aside>
    </>
  );
}
