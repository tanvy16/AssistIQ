import { useEffect, useState } from "react";

import ModelSelector from "../../components/ai/ModelSelector";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import EmptyState from "../../components/ui/EmptyState";
import LoadingState from "../../components/ui/LoadingState";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import { useToast } from "../../components/ui/Toast";
import { useAuth } from "../../context/AuthContext";
import { fetchAIModels, updateAIModelEnabled } from "../../lib/ai";
import type { AIModel } from "../../lib/ai.types";
import { aiModelTypeLabels } from "../../lib/aiLabels";

export default function AdminAIModelsPage() {
  const { accessToken } = useAuth();
  const { showToast } = useToast();
  const [models, setModels] = useState<AIModel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<AIModel | null>(null);

  async function reload() {
    if (!accessToken) return;
    setIsLoading(true);
    try {
      const response = await fetchAIModels(accessToken);
      setModels(response.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load models");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void reload();
  }, [accessToken]);

  if (!accessToken) return null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Models"
        description="Configure model registry entries and default model selection for future AI features."
      />

      <ModelSelector
        accessToken={accessToken}
        onModelChange={setSelectedModel}
      />

      {selectedModel ? (
        <Panel title="Selected model">
          <p className="text-sm text-ink-muted">
            {selectedModel.model_name} · {aiModelTypeLabels[selectedModel.model_type]} ·{" "}
            {selectedModel.provider}
          </p>
        </Panel>
      ) : null}

      {isLoading ? <LoadingState label="Loading registry…" /> : null}
      {!isLoading && error ? (
        <EmptyState title="Unable to load AI models" description={error} />
      ) : null}

      {!isLoading && !error ? (
        <Panel title="Model registry" description={`${models.length} registered models`}>
          <div className="space-y-3">
            {models.map((model) => (
              <div
                key={model.id}
                className="flex flex-col gap-3 rounded border border-surface-border p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-ink">{model.model_key}</span>
                    <Badge variant={model.enabled ? "ai" : "muted"}>
                      {model.enabled ? "Enabled" : "Disabled"}
                    </Badge>
                  </div>
                  <p className="mt-1 text-sm text-ink-muted">
                    {aiModelTypeLabels[model.model_type]} · {model.provider} ·{" "}
                    {model.model_name} · v{model.version}
                  </p>
                </div>
                <Button
                  variant="secondary"
                  onClick={async () => {
                    try {
                      await updateAIModelEnabled(accessToken, model.id, !model.enabled);
                      showToast(
                        model.enabled ? "Model disabled." : "Model enabled.",
                        "success",
                      );
                      await reload();
                    } catch (err) {
                      showToast(
                        err instanceof Error ? err.message : "Update failed",
                        "error",
                      );
                    }
                  }}
                >
                  {model.enabled ? "Disable" : "Enable"}
                </Button>
              </div>
            ))}
          </div>
        </Panel>
      ) : null}
    </div>
  );
}
