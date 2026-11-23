const capabilities = [
  {
    title: "Intelligent knowledge search",
    detail: "Retrieve published IT procedures with source citations.",
  },
  {
    title: "Transparent ticket and SLA tracking",
    detail: "Follow status, priority, and due times across the queue.",
  },
  {
    title: "Policy-controlled automation",
    detail: "Software, access, and identity workflows stay simulated and gated.",
  },
];

export default function LoginBrandPanel() {
  return (
    <section className="relative isolate overflow-hidden bg-canvas px-6 py-8 sm:px-10 lg:min-h-screen lg:px-14 lg:py-12">
      <BrandArtwork />
      <div className="relative z-10 mx-auto flex h-full max-w-xl flex-col lg:max-w-none">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-accent">AssistIQ</p>
        <p className="mt-8 text-[11px] font-medium uppercase tracking-[0.18em] text-ink-subtle">
          Enterprise IT operations
        </p>
        <h1 className="mt-4 max-w-xl text-4xl font-semibold leading-[1.08] tracking-tight text-ink sm:text-5xl lg:text-6xl">
          Your IT operations,{" "}
          <span className="text-accent">under control.</span>
        </h1>
        <p className="mt-5 max-w-lg text-sm leading-6 text-ink-muted sm:text-base">
          Resolve IT issues, find trusted answers, and keep your team&apos;s workflows moving — all in
          one intelligent support platform.
        </p>

        <ul className="mt-8 hidden max-w-lg space-y-4 sm:block">
          {capabilities.map((item) => (
            <li key={item.title} className="flex gap-3">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden="true" />
              <div>
                <p className="text-sm font-medium text-ink">{item.title}</p>
                <p className="mt-0.5 text-sm text-ink-muted">{item.detail}</p>
              </div>
            </li>
          ))}
        </ul>

        <p className="mt-10 hidden text-xs text-ink-subtle lg:mt-auto lg:block">
          AssistIQ · Local-first IT helpdesk
        </p>
      </div>
    </section>
  );
}

function BrandArtwork() {
  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full opacity-40"
      viewBox="0 0 960 1080"
      fill="none"
      aria-hidden="true"
    >
      <defs>
        <radialGradient id="loginGlow" cx="28%" cy="18%" r="55%">
          <stop offset="0%" stopColor="var(--color-accent)" stopOpacity="0.08" />
          <stop offset="55%" stopColor="var(--color-network)" stopOpacity="0.04" />
          <stop offset="100%" stopColor="var(--color-canvas)" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="960" height="1080" fill="url(#loginGlow)" />
      {Array.from({ length: 18 }, (_, index) => (
        <line
          key={`h-${index}`}
          x1="40"
          y1={80 + index * 52}
          x2="920"
          y2={80 + index * 52}
          stroke="var(--color-border)"
          strokeOpacity="0.35"
        />
      ))}
      {Array.from({ length: 12 }, (_, index) => (
        <line
          key={`v-${index}`}
          x1={80 + index * 72}
          y1="40"
          x2={80 + index * 72}
          y2="1040"
          stroke="var(--color-border)"
          strokeOpacity="0.28"
        />
      ))}
      <path
        d="M80 760C220 620 340 880 520 700C700 520 780 820 900 640"
        stroke="var(--color-accent)"
        strokeOpacity="0.35"
        strokeWidth="1.4"
      />
      <path
        d="M60 430C200 360 310 520 470 410C630 300 740 470 900 360"
        stroke="var(--color-network)"
        strokeOpacity="0.32"
        strokeWidth="1.2"
      />
      <circle cx="220" cy="640" r="3.5" fill="var(--color-accent)" fillOpacity="0.7" />
      <circle cx="470" cy="410" r="3" fill="var(--color-network)" fillOpacity="0.8" />
      <circle cx="740" cy="690" r="3" fill="var(--color-accent)" fillOpacity="0.55" />
      <circle cx="860" cy="360" r="2.5" fill="var(--color-network)" fillOpacity="0.7" />
    </svg>
  );
}
