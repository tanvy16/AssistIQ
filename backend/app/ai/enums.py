import enum


class AIModelType(str, enum.Enum):
    LIGHTWEIGHT_ML = "lightweight_ml"
    DEEP_LEARNING = "deep_learning"
    LLM = "llm"


class AITaskType(str, enum.Enum):
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    GENERATION = "generation"
    SUMMARIZATION = "summarization"
    INTENT_DETECTION = "intent_detection"
    ENTITY_EXTRACTION = "entity_extraction"


class AIEvaluationType(str, enum.Enum):
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    LLM_GENERATION = "llm_generation"
