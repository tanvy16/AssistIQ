"""Append missing Phase 1 env vars to backend/.env without printing secrets."""

import secrets
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def main() -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    keys = {
        line.split("=", 1)[0]
        for line in lines
        if "=" in line and not line.strip().startswith("#")
    }
    changed = False

    if "JWT_SECRET_KEY" not in keys:
        lines.append(f"JWT_SECRET_KEY={secrets.token_urlsafe(48)}")
        changed = True

    if "CORS_ORIGINS" not in keys:
        lines.append('CORS_ORIGINS=["http://127.0.0.1:5173"]')
        changed = True

    if changed:
        ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("Updated backend/.env with missing Phase 1 variables.")
    else:
        print("backend/.env already contains Phase 1 variables.")


if __name__ == "__main__":
    main()
