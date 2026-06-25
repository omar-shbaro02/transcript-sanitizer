import json
import sys
from datetime import datetime
from pathlib import Path

from .cleaner import clean_transcript
from .detectors import detect_entities
from .file_io import ensure_directories, read_transcript, write_docx, write_text
from .replacements import apply_replacements
from .report import build_report, write_report


def bundled_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base.joinpath(*parts)


DEFAULT_CONFIG_PATH = bundled_path("config", "default_config.json")


def load_config(path: str | Path | None = None) -> dict:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    return json.loads(config_path.read_text(encoding="utf-8"))


def process_transcript(
    input_path: str | Path,
    output_dir: str | Path,
    config_path: str | Path | None = None,
    config_overrides: dict | None = None,
) -> dict:
    source = Path(input_path)
    output = Path(output_dir)
    base_dir = output.parent if output.name == "output" else output
    maps_dir = base_dir / "local_maps"
    ensure_directories([output, maps_dir])

    config = load_config(config_path)
    if config_overrides:
        config.update(config_overrides)

    raw_text = read_transcript(source)
    cleaned = clean_transcript(raw_text)
    entities, warnings, confidence_notes = detect_entities(cleaned, config)
    replacement = apply_replacements(cleaned, entities)

    anonymized_txt = output / f"{source.stem}_anonymized.txt"
    report_path = output / f"{source.stem}_processing_report.json"
    write_text(anonymized_txt, replacement.text)

    anonymized_docx = None
    if source.suffix.lower() == ".docx":
        anonymized_docx = output / f"{source.stem}_anonymized.docx"
        write_docx(anonymized_docx, replacement.text)

    mapping_path = None
    mapping_saved = bool(config.get("save_local_mapping", True))
    if mapping_saved:
        mapping_path = maps_dir / f"{source.stem}_mapping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        mapping_payload = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "source_file": str(source),
            "entities": replacement.mapping,
        }
        write_text(mapping_path, json.dumps(mapping_payload, indent=2, ensure_ascii=False))

    if config.get("mapping_file_warning", True) and mapping_saved:
        warnings.append("Local mapping file saved. Do not upload mapping files to external AI tools.")

    report = build_report(
        source,
        sum(replacement.counts_by_type.values()),
        replacement.counts_by_type,
        mapping_saved,
        warnings,
        confidence_notes,
    )
    write_report(report_path, report)

    return {
        "anonymized_txt": str(anonymized_txt),
        "anonymized_docx": str(anonymized_docx) if anonymized_docx else None,
        "mapping_file": str(mapping_path) if mapping_path else None,
        "report": str(report_path),
        "entity_count": report["entities_anonymized"],
        "warnings": warnings,
    }
