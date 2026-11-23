"""Manually reseed default AI model registry entries.

This CLI force-upserts the four default keys (provider, model name, capabilities,
metadata, and enabled=True). It does not delete other registry rows.

Normal application startup uses insert-if-missing initialization instead
(`app.ai.default_models.ensure_default_ai_models`) and will not overwrite
administrator settings. Use this script only when you intentionally want to
restore the packaged defaults.
"""

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.ai.default_models import DEFAULT_MODELS, reseed_default_ai_models


async def seed() -> None:
    result = await reseed_default_ai_models()
    print("AI model registry seeded.")
    print(f"Inserted: {', '.join(result['inserted']) or '(none)'}")
    print(f"Updated: {', '.join(result['updated']) or '(none)'}")


if __name__ == "__main__":
    asyncio.run(seed())
