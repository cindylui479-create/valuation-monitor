"""从 data/index_universe.yaml 导入 markets / indices / funds。

用法：
    python -m scripts.seed_universe
    python -m scripts.seed_universe --yaml /path/to/index_universe.yaml
"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.db import SessionLocal
from app.services.universe_service import import_universe, load_universe_yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--yaml",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "index_universe.yaml",
    )
    args = parser.parse_args()

    data = load_universe_yaml(args.yaml)
    with SessionLocal() as session:
        counts = import_universe(session, data)
    print(f"Imported: {counts}")


if __name__ == "__main__":
    main()
