"""Deterministic entity extraction for IT requests. Values are never executable."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, field_validator

from app.models.it_request import ITRequestType

ALLOWED_ENTITY_TYPES = {
    "software_name",
    "software_version",
    "access_resource",
    "system_name",
    "requested_permission",
    "business_justification",
    "department",
    "environment",
    "urgency",
}

VERSION_RE = re.compile(r"\b(?:v(?:ersion)?\s*)?(\d+(?:\.\d+){0,3})\b", re.I)


class ExtractedEntity(BaseModel):
    entity_type: str
    entity_name: str
    entity_value: str = Field(max_length=255)
    confidence: float = Field(ge=0.0, le=1.0)
    source: str = "deterministic"

    @field_validator("entity_type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in ALLOWED_ENTITY_TYPES:
            raise ValueError(f"Unsupported entity type: {value}")
        return value

    @field_validator("entity_value")
    @classmethod
    def reject_commands(cls, value: str) -> str:
        lowered = value.lower()
        forbidden = ("rm -rf", "powershell", "cmd.exe", "curl ", "wget ", "drop table", "invoke-")
        if any(token in lowered for token in forbidden):
            raise ValueError("Entity value looks like an executable command")
        return value.strip()


class ExtractionResult(BaseModel):
    request_type: ITRequestType
    resource: str
    justification: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    entities: list[ExtractedEntity]
    catalog_kind: str | None = None
    catalog_item_id: str | None = None
    catalog_runbook_id: str | None = None
    catalog_enabled: bool = False
    catalog_risk: str | None = None
    catalog_approval_required: bool = False
    needs_clarification: bool = False


@dataclass
class CatalogMatch:
    kind: str
    item_id: str
    name: str
    runbook_id: str
    enabled: bool
    risk: str
    approval_required: bool
    aliases: list[str] = field(default_factory=list)


def infer_request_type(text: str) -> ITRequestType:
    lowered = text.lower()
    if any(token in lowered for token in ("admin", "elevated", "privileg", "sudo")):
        return ITRequestType.PERMISSION
    if any(token in lowered for token in ("access", "shared drive", "jira", "confluence", "dashboard")):
        return ITRequestType.ACCESS
    return ITRequestType.SOFTWARE


def _justification(text: str) -> str | None:
    match = re.search(r"\b(?:for|because)\s+(.+)$", text, re.I)
    if match:
        return match.group(1).strip()[:255]
    return None


def extract_entities(text: str, catalog: list[CatalogMatch]) -> ExtractionResult:
    cleaned = text.strip()
    request_type = infer_request_type(cleaned)
    lowered = cleaned.lower()
    matched: CatalogMatch | None = None
    best_len = 0
    for item in catalog:
        names = [item.name, *item.aliases]
        for alias in names:
            alias_l = alias.lower()
            if alias_l and alias_l in lowered and len(alias_l) > best_len:
                matched = item
                best_len = len(alias_l)

    entities: list[ExtractedEntity] = []
    resource = matched.name if matched else cleaned[:120]
    confidence = 0.9 if matched else 0.35

    if matched:
        entity_type = "software_name" if matched.kind == "software" else "access_resource"
        entities.append(
            ExtractedEntity(
                entity_type=entity_type,
                entity_name=entity_type,
                entity_value=matched.name,
                confidence=0.95,
            )
        )
        if matched.kind == "software":
            version_match = VERSION_RE.search(cleaned)
            if version_match:
                entities.append(
                    ExtractedEntity(
                        entity_type="software_version",
                        entity_name="software_version",
                        entity_value=version_match.group(1),
                        confidence=0.8,
                    )
                )

    justification = _justification(cleaned)
    if justification:
        entities.append(
            ExtractedEntity(
                entity_type="business_justification",
                entity_name="business_justification",
                entity_value=justification,
                confidence=0.7,
            )
        )

    if request_type == ITRequestType.PERMISSION:
        entities.append(
            ExtractedEntity(
                entity_type="requested_permission",
                entity_name="requested_permission",
                entity_value="elevated",
                confidence=0.8,
            )
        )
        confidence = min(confidence, 0.6)

    return ExtractionResult(
        request_type=request_type,
        resource=resource,
        justification=justification,
        confidence=confidence,
        entities=entities,
        catalog_kind=matched.kind if matched else None,
        catalog_item_id=matched.item_id if matched else None,
        catalog_runbook_id=matched.runbook_id if matched else None,
        catalog_enabled=matched.enabled if matched else False,
        catalog_risk=matched.risk if matched else None,
        catalog_approval_required=matched.approval_required if matched else False,
        needs_clarification=matched is None and request_type != ITRequestType.PERMISSION,
    )
