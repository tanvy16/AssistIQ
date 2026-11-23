import { useEffect, useMemo, useState } from "react";

import type { AIModel, AIModelType } from "../../lib/ai.types";
import {
  aiModelTypeDescriptions,
  aiModelTypeLabels,
  aiModelTypes,
} from "../../lib/aiLabels";
import { fetchAIModels, getStoredModelId, storeModelId } from "../../lib/ai";
import LoadingState from "../ui/LoadingState";
import Panel from "../ui/Panel";

type ModelSelectorProps = {
  accessToken: string;
  title?: string;
  description?: string;
  filterType?: AIModelType | null;
  selectedModelId?: string | null;
  onModelChange?: (model: AIModel | null) => void;
  persistSelection?: boolean;
};

export default function ModelSelector({
  accessToken,
  title = "AI Model Selection",
  description = "Choose which enabled model handles this AI task.",
  filterType = null,
  selectedModelId,
  onModelChange,
  persistSelection = true,
}: ModelSelectorProps) {
  const [models, setModels] = useState<AIModel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<AIModelType>(
    filterType ?? "lightweight_ml",
  );
  const [internalModelId, setInternalModelId] = useState<string | null>(
    selectedModelId ?? getStoredModelId(),
  );

  useEffect(() => {
    if (!accessToken) return;
    const controller = new AbortController();
    void (async () => {
      setIsLoading(true);
      try {
        const response = await fetchAIModels(accessToken, controller.signal);
        if (controller.signal.aborted) return;
        setModels(response.items.filter((model) => model.enabled));
        setError(null);
      } catch (err) {
        if (controller.signal.aborted || (err instanceof Error && err.name === "AbortError")) return;
        setError(err instanceof Error ? err.message : "Failed to load models");
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    })();
    return () => controller.abort();
  }, [accessToken]);

  const filteredModels = useMemo(
    () => models.filter((model) => model.model_type === selectedType),
    [models, selectedType],
  );

  useEffect(() => {
    if (filterType) {
      setSelectedType(filterType);
    }
  }, [filterType]);

  useEffect(() => {
    if (selectedModelId !== undefined) {
      setInternalModelId(selectedModelId);
    }
  }, [selectedModelId]);

  useEffect(() => {
    if (!filteredModels.length) {
      onModelChange?.(null);
      return;
    }
    const current = filteredModels.find((model) => model.id === internalModelId);
    const next = current ?? filteredModels[0];
    if (next.id !== internalModelId) {
      setInternalModelId(next.id);
      if (persistSelection) storeModelId(next.id);
      onModelChange?.(next);
    } else {
      onModelChange?.(next);
    }
  }, [filteredModels, internalModelId, onModelChange, persistSelection]);

  function handleTypeChange(type: AIModelType) {
    setSelectedType(type);
    setInternalModelId(null);
  }

  function handleModelChange(modelId: string) {
    setInternalModelId(modelId);
    if (persistSelection) storeModelId(modelId);
    const model = filteredModels.find((item) => item.id === modelId) ?? null;
    onModelChange?.(model);
  }

  return (
    <Panel title={title} description={description}>
      {isLoading ? <LoadingState label="Loading AI models…" /> : null}
      {error ? <p className="text-sm text-danger">{error}</p> : null}

      {!isLoading && !error ? (
        <div className="space-y-4">
          {!filterType ? (
            <fieldset>
              <legend className="mb-2 text-sm font-medium text-ink">Model class</legend>
              <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                {aiModelTypes.map((type) => (
                  <label
                    key={type}
                    className={`flex cursor-pointer items-start gap-2 rounded border px-3 py-2 ${
                      selectedType === type
                        ? "border-ai bg-ai-soft"
                        : "border-surface-border hover:bg-surface-hover"
                    }`}
                  >
                    <input
                      type="radio"
                      name="ai-model-type"
                      value={type}
                      checked={selectedType === type}
                      onChange={() => handleTypeChange(type)}
                    />
                    <span>
                      <span className="block text-sm font-medium text-ink">
                        {aiModelTypeLabels[type]}
                      </span>
                      <span className="block text-xs text-ink-muted">
                        {aiModelTypeDescriptions[type]}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          ) : null}

          <div className="space-y-1">
            <label htmlFor="ai-model-select" className="text-sm font-medium text-ink">
              Model
            </label>
            <select
              id="ai-model-select"
              value={internalModelId ?? ""}
              onChange={(event) => handleModelChange(event.target.value)}
              className="field-control"
              disabled={filteredModels.length === 0}
            >
              {filteredModels.length === 0 ? (
                <option value="">No enabled models for this class</option>
              ) : (
                filteredModels.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.model_name} ({model.provider}) v{model.version}
                  </option>
                ))
              )}
            </select>
          </div>
        </div>
      ) : null}
    </Panel>
  );
}
