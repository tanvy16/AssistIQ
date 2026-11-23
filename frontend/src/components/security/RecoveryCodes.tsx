import { useState } from "react";

import { recoveryCodesFileContent } from "../../lib/security";
import Button from "../ui/Button";

type RecoveryCodesProps = {
  email: string;
  codes: string[];
  onDone: () => void;
  doneLabel?: string;
};

/** Displays one-time recovery codes. They are never retrievable again. */
export default function RecoveryCodes({ email, codes, onDone, doneLabel = "I have saved these codes" }: RecoveryCodesProps) {
  const [copied, setCopied] = useState<"idle" | "copied" | "failed">("idle");
  const [acknowledged, setAcknowledged] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(codes.join("\n"));
      setCopied("copied");
    } catch {
      setCopied("failed");
    }
  }

  function download() {
    const blob = new Blob([recoveryCodesFileContent(email, codes)], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "assistiq-recovery-codes.txt";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      <div className="rounded border border-storage bg-storage-soft px-3 py-2 text-sm text-ink" role="note">
        These {codes.length} recovery codes are shown <strong>only once</strong>. Each works a single
        time if you lose your authenticator. AssistIQ stores only hashes and cannot show them again.
      </div>
      <ol className="grid grid-cols-2 gap-2 rounded border border-surface-border bg-surface-muted p-3 font-mono text-sm text-ink">
        {codes.map((code) => (
          <li key={code} className="tracking-wider">
            {code}
          </li>
        ))}
      </ol>
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="secondary" size="sm" onClick={() => void copy()}>
          Copy
        </Button>
        <Button variant="secondary" size="sm" onClick={download}>
          Download .txt
        </Button>
        {copied === "copied" ? <span className="text-xs text-ink-muted">Copied to clipboard</span> : null}
        {copied === "failed" ? <span className="text-xs text-danger">Clipboard unavailable — use Download</span> : null}
      </div>
      <label className="flex items-center gap-2 text-sm text-ink">
        <input
          type="checkbox"
          checked={acknowledged}
          onChange={(event) => setAcknowledged(event.target.checked)}
          className="h-4 w-4 accent-[var(--color-accent)]"
        />
        I stored these codes somewhere safe
      </label>
      <Button disabled={!acknowledged} onClick={onDone}>
        {doneLabel}
      </Button>
    </div>
  );
}
