"""Drop all alembic state, re-apply migrations, and re-seed.

Usage (from backend/):
    python -m scripts.reset_db --yes

Refuses to run when settings.environment == "production".
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import get_settings


def _alembic_config() -> Config:
    backend_root = Path(__file__).resolve().parent.parent
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    return cfg


def _guard_production() -> None:
    settings = get_settings()
    if settings.environment == "production":
        raise SystemExit("[reset_db] refusing to run against production environment")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required confirmation flag. Without it, this script refuses to run.",
    )
    return parser.parse_args()


def main() -> None:
    _guard_production()
    args = _parse_args()
    if not args.yes:
        raise SystemExit("[reset_db] aborting: pass --yes to confirm destructive reset")

    cfg = _alembic_config()
    print("[reset_db] alembic downgrade base")
    command.downgrade(cfg, "base")
    print("[reset_db] alembic upgrade head")
    command.upgrade(cfg, "head")

    from scripts.seed_dev import run as seed_run

    print("[reset_db] seeding dev data")
    asyncio.run(seed_run())
    print("[reset_db] done")


if __name__ == "__main__":
    main()
