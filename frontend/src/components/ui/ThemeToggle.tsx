import { useTheme } from "../../context/ThemeContext";

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="inline-flex h-8 w-8 items-center justify-center rounded border border-surface-border bg-surface text-ink-muted hover:bg-surface-hover hover:text-ink focus-visible:outline-none"
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Light mode" : "Dark mode"}
    >
      {isDark ? (
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
          <path d="M10 3.5a.75.75 0 01.75.75v1.25a.75.75 0 01-1.5 0V4.25A.75.75 0 0110 3.5zm0 10.5a.75.75 0 01.75.75v1.25a.75.75 0 01-1.5 0V14.75A.75.75 0 0110 14zm6.5-4a.75.75 0 01-.75.75h-1.25a.75.75 0 010-1.5H15.75A.75.75 0 0116.5 10zM6.5 10a.75.75 0 01-.75.75H4.5a.75.75 0 010-1.5h1.25A.75.75 0 016.5 10zm8.01-4.51a.75.75 0 010 1.06l-.88.88a.75.75 0 11-1.06-1.06l.88-.88a.75.75 0 011.06 0zM7.43 12.57a.75.75 0 010 1.06l-.88.88a.75.75 0 11-1.06-1.06l.88-.88a.75.75 0 011.06 0zm7.14 1.94a.75.75 0 01-1.06 0l-.88-.88a.75.75 0 011.06-1.06l.88.88a.75.75 0 010 1.06zM7.43 6.37a.75.75 0 01-1.06 0l-.88-.88A.75.75 0 016.55 4.43l.88.88a.75.75 0 010 1.06zM10 6.5a3.5 3.5 0 100 7 3.5 3.5 0 000-7z" />
        </svg>
      ) : (
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
          <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
        </svg>
      )}
    </button>
  );
}
