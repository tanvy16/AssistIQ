import Badge from "../ui/Badge";
import type { Citation } from "../../lib/chat.types";

type MessageCitationsProps = {
  citations: Citation[];
};

export default function MessageCitations({ citations }: MessageCitationsProps) {
  if (!citations.length) {
    return <p className="text-xs text-ink-subtle">No knowledge citations for this response.</p>;
  }

  return (
    <div className="space-y-2">
      <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-ai">Sources</p>
      <ul className="space-y-2">
        {citations.map((citation) => (
          <li
            key={citation.id}
            className="rail-ai border border-surface-border bg-ai-soft px-3 py-2 text-sm"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium text-ink">{citation.title}</span>
              {citation.category ? <Badge variant="muted">{citation.category}</Badge> : null}
              <Badge variant="muted">{(citation.similarity_score * 100).toFixed(0)}% match</Badge>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
