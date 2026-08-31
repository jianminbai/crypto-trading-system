import json
from pathlib import Path
from typing import Any, Dict


def load_config(path: str = "config/default.json") -> Dict[str, Any]:
    target = Path(path)
    with target.open(encoding="utf-8") as handle:
        config = json.load(handle)
    parent = config.pop("extends", None)
    if parent:
        base = load_config(str(target.parent / parent))
        base.update(config)
        return base
    return config
