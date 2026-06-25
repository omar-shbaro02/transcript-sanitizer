import json
from datetime import datetime
from pathlib import Path


def build_report(
    source_file: str | Path,
    entity_count: int,
    counts_by_type: dict[str, int],
    mapping_saved: bool,
    warnings: list[str],
    confidence_notes: list[str],
) -> dict:
    return {
        "source_file": str(source_file),
        "processed_at": datetime.now().isoformat(timespec="seconds"),
        "entities_anonymized": entity_count,
        "counts_by_entity_type": counts_by_type,
        "mapping_file_saved": mapping_saved,
        "warnings": warnings,
        "confidence_notes": confidence_notes,
    }


def write_report(path: str | Path, report: dict) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

