import { FormEvent, useState } from "react";

import Button from "../ui/Button";
import EmptyState from "../ui/EmptyState";
import Input from "../ui/Input";
import LoadingState from "../ui/LoadingState";
import Panel from "../ui/Panel";
import { searchKnowledge } from "../../lib/knowledge";
import type { KnowledgeSearchResult } from "../../lib/knowledge.types";
import { knowledgeCategoryLabels } from "../../lib/knowledgeLabels";

type KnowledgeSearchPanelProps = {
  accessToken: string;
  title?: string;
  description?: string;
};

export default function KnowledgeSearchPanel({
  accessToken,
  title = "Search Knowledge Base",
  description = "Find published articles and procedures relevant to your question.",
}: KnowledgeSearchPanelProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<KnowledgeSearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) {
      setError("Enter a search query.");
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await searchKnowledge(accessToken, query.trim());
      setResults(response.results);
      setHasSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <Panel title={title} description={description}>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 sm:flex-row">
          <Input
            id="knowledge-search"
            label="Search query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="How do I reset my corporate password?"
            className="flex-1"
          />
          <div className="flex items-end">
            <Button type="submit" disabled={isLoading}>
              {isLoading ? "Searching…" : "Search"}
            </Button>
          </div>
        </form>
      </Panel>

      {isLoading ? <LoadingState label="Searching knowledge base…" /> : null}
      {error ? <EmptyState title="Search failed" description={error} /> : null}

      {!isLoading && !error && hasSearched && results.length === 0 ? (
        <EmptyState
          title="No results found"
          description="Try different keywords or contact IT support."
        />
      ) : null}

      {!isLoading && results.length > 0 ? (
        <div className="space-y-4">
          {results.map((result) => (
            <Panel
              key={result.chunk_id}
              className="rail-ai"
              title={result.title}
              description={`${knowledgeCategoryLabels[result.category as keyof typeof knowledgeCategoryLabels] ?? result.category} · Score ${(result.similarity_score * 100).toFixed(1)}%`}
            >
              <p className="whitespace-pre-wrap text-sm text-ink-muted">{result.content}</p>
            </Panel>
          ))}
        </div>
      ) : null}
    </div>
  );
}
