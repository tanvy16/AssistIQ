import { useAuth } from "../../context/AuthContext";
import { roleLabels } from "../../lib/labels";
import Badge from "../ui/Badge";
import Button from "../ui/Button";
import ThemeToggle from "../ui/ThemeToggle";

type TopBarProps = {
  onMenuToggle: () => void;
  menuOpen: boolean;
};

export default function TopBar({ onMenuToggle, menuOpen }: TopBarProps) {
  const { user, logout } = useAuth();

  if (!user) {
    return null;
  }

  const displayName = user.display_name ?? user.email;

  return (
    <header className="shell-nav sticky top-0 z-30 border-b border-surface-border">
      <div className="flex h-12 items-center justify-between gap-3 px-3 sm:px-5">
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            className="inline-flex rounded border border-surface-border p-1.5 text-ink hover:bg-surface-hover focus-visible:outline-none md:hidden"
            onClick={onMenuToggle}
            aria-expanded={menuOpen}
            aria-controls="app-sidebar"
            aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
          >
            <span className="sr-only">Menu</span>
            <svg
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-4 w-4"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M2.5 5.75A.75.75 0 013.25 5h13.5a.75.75 0 010 1.5H3.25A.75.75 0 012.5 5.75zm0 4.5a.75.75 0 01.75-.75h13.5a.75.75 0 010 1.5H3.25a.75.75 0 01-.75-.75zm0 4.5a.75.75 0 01.75-.75h13.5a.75.75 0 010 1.5H3.25a.75.75 0 01-.75-.75z"
                clipRule="evenodd"
              />
            </svg>
          </button>
          <div className="min-w-0">
            <p className="text-[10px] font-medium uppercase tracking-[0.18em] text-ink-subtle">
              Enterprise IT operations
            </p>
            <p className="truncate text-sm font-semibold text-ink">AssistIQ</p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <ThemeToggle />
          <div className="hidden text-right sm:block">
            <p className="text-sm font-medium leading-tight text-ink">{displayName}</p>
            <p className="text-[11px] text-ink-subtle">{user.email}</p>
          </div>
          <Badge variant="muted">{roleLabels[user.role]}</Badge>
          <Button variant="secondary" size="sm" onClick={() => void logout()}>
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}
