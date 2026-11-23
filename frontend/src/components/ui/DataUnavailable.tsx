import Button from "./Button";
import EmptyState from "./EmptyState";

type DataUnavailableProps = {
  error: string | null;
  onRetry?: () => void;
  subject?: string;
};

/**
 * Shown when a request failed and no previously loaded data exists.
 * Never substitute zeros for metrics we could not load.
 */
export default function DataUnavailable({ error, onRetry, subject = "this data" }: DataUnavailableProps) {
  return (
    <EmptyState
      title={`Could not load ${subject}`}
      description={`${error ?? "The request did not complete."} No figures are shown because none were received from the server.`}
      action={
        onRetry ? (
          <Button variant="secondary" size="sm" onClick={onRetry}>
            Retry
          </Button>
        ) : undefined
      }
    />
  );
}
