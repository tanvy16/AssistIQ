/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        canvas: "var(--color-canvas)",
        nav: "var(--color-nav)",
        overlay: "var(--color-overlay)",
        surface: {
          DEFAULT: "var(--color-surface)",
          muted: "var(--color-surface-muted)",
          hover: "var(--color-surface-hover)",
          elevated: "var(--color-surface-muted)",
          border: "var(--color-border)",
          divider: "var(--color-divider)",
        },
        ink: {
          DEFAULT: "var(--color-ink)",
          muted: "var(--color-ink-muted)",
          subtle: "var(--color-ink-subtle)",
        },
        accent: {
          DEFAULT: "var(--color-accent)",
          hover: "var(--color-accent-hover)",
          soft: "var(--color-accent-soft)",
          fg: "var(--color-accent-fg)",
        },
        ai: {
          DEFAULT: "var(--color-ai)",
          soft: "var(--color-ai-soft)",
        },
        storage: {
          DEFAULT: "var(--color-storage)",
          soft: "var(--color-storage-soft)",
        },
        activity: {
          DEFAULT: "var(--color-activity)",
          soft: "var(--color-activity-soft)",
        },
        network: {
          DEFAULT: "var(--color-network)",
          soft: "var(--color-network-soft)",
        },
        danger: {
          DEFAULT: "var(--color-danger)",
          soft: "var(--color-danger-soft)",
        },
      },
      boxShadow: {
        card: "var(--shadow-card)",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      borderRadius: {
        DEFAULT: "0.375rem",
      },
    },
  },
  plugins: [],
};
