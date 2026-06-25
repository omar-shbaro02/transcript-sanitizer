import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Entity:
    start: int
    end: int
    entity_type: str
    text: str
    source: str
    score: float = 0.8
    canonical_text: str | None = None


PRESIDIO_TYPE_MAP = {
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "PHONE",
    "PERSON": "PERSON",
    "LOCATION": "LOCATION",
    "URL": "URL",
    "DATE_TIME": "DATE",
    "IBAN_CODE": "ID",
    "CREDIT_CARD": "ID",
    "IP_ADDRESS": "ID",
}

SPACY_TYPE_MAP = {
    "PERSON": "PERSON",
    "ORG": "ORG",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "FAC": "LOCATION",
    "DATE": "DATE",
    "TIME": "DATE",
}

SPECIFICITY = {
    "EMAIL": 100,
    "URL": 95,
    "PHONE": 90,
    "ID": 85,
    "CLIENT": 80,
    "ORG": 70,
    "PERSON": 65,
    "LOCATION": 60,
    "DATE": 40,
    "OTHER_SENSITIVE": 20,
}

COMMON_LOCATIONS = {
    "beirut",
    "lebanon",
    "dubai",
    "riyadh",
    "doha",
    "amman",
    "cairo",
    "london",
    "paris",
    "new york",
}

GENERIC_SPEAKER_RE = re.compile(r"^(speaker|participant|attendee|host|moderator)\s*\d*$", re.I)
NAME_TOKEN_RE = re.compile(r"[A-Z][A-Za-z.'-]*")
MAX_PERSON_NAME_TOKENS = 4


def _presidio_entities(text: str, config: dict, warnings: list[str]) -> list[Entity]:
    try:
        from presidio_analyzer import AnalyzerEngine
    except Exception:
        warnings.append("Presidio is not installed; regex and spaCy detectors were used.")
        return []

    requested = ["EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON", "LOCATION", "URL", "IBAN_CODE", "CREDIT_CARD", "IP_ADDRESS"]
    if config.get("anonymize_dates", False):
        requested.append("DATE_TIME")

    try:
        analyzer = AnalyzerEngine()
        results = analyzer.analyze(text=text, language="en", entities=requested)
    except Exception as exc:
        warnings.append(f"Presidio detection was skipped: {exc}")
        return []

    entities: list[Entity] = []
    for result in results:
        entity_type = PRESIDIO_TYPE_MAP.get(result.entity_type)
        if entity_type and _type_enabled(entity_type, config):
            entities.append(
                Entity(
                    result.start,
                    result.end,
                    entity_type,
                    text[result.start : result.end],
                    "presidio",
                    float(result.score),
                )
            )
    return entities


def _spacy_entities(text: str, config: dict, warnings: list[str]) -> list[Entity]:
    try:
        import spacy
    except Exception:
        warnings.append("spaCy is not installed; spaCy NER was skipped.")
        return []

    nlp = None
    for model_name in ("en_core_web_lg", "en_core_web_sm"):
        try:
            nlp = spacy.load(model_name)
            break
        except Exception:
            continue

    if nlp is None:
        warnings.append("No spaCy English model found; install en_core_web_lg or en_core_web_sm for better NER.")
        return []

    doc = nlp(text)
    entities: list[Entity] = []
    for ent in doc.ents:
        entity_type = SPACY_TYPE_MAP.get(ent.label_)
        if entity_type and _type_enabled(entity_type, config):
            entities.append(Entity(ent.start_char, ent.end_char, entity_type, ent.text, "spacy", 0.75))
    return entities


def _regex_entities(text: str, config: dict) -> list[Entity]:
    patterns = [
        ("EMAIL", r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
        ("URL", r"\b(?:https?://|www\.)[^\s<>()]+|\b(?:teams|zoom|meet)\.[A-Z0-9.-]+/[^\s<>()]+"),
        ("PHONE", r"(?<!\w)(?:\+961|00961|961)?[\s.-]?(?:0)?(?:3|7[01689]|8[0139]|9|1)[\s.-]?\d{3}[\s.-]?\d{3}(?!\w)"),
        ("PHONE", r"(?<!\w)(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{3,4}(?!\w)"),
        ("ID", r"\b(?:passport|pass|national id|employee id|emp id|client code|client id)[:#\s-]*[A-Z0-9-]{4,}\b"),
        ("ID", r"\b[A-Z]{1,3}\d{5,10}\b"),
        ("ID", r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),
    ]
    entities: list[Entity] = []
    for entity_type, pattern in patterns:
        if not _type_enabled(entity_type, config):
            continue
        for match in re.finditer(pattern, text, re.I):
            entities.append(Entity(match.start(), match.end(), entity_type, match.group(0), "regex", 0.85))

    entities.extend(_speaker_entities(text))
    entities.extend(_configured_term_entities(text, config))
    entities.extend(_organization_heuristics(text, config))
    entities.extend(_location_heuristics(text, config))
    if config.get("anonymize_dates", False):
        entities.extend(_date_heuristics(text))
    return entities


def _speaker_entities(text: str) -> list[Entity]:
    entities: list[Entity] = []
    for match in re.finditer(r"(?m)^([A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*){0,3})(?:\s+-\s+[^:\n]{2,60})?:", text):
        speaker = match.group(1).strip()
        if not GENERIC_SPEAKER_RE.match(speaker):
            entities.append(Entity(match.start(1), match.end(1), "PERSON", speaker, "speaker-label", 0.95))
    return entities


def _configured_term_entities(text: str, config: dict) -> list[Entity]:
    configured = [
        ("CLIENT", config.get("client_names", [])),
        ("ORG", config.get("company_names", [])),
        ("PERSON", config.get("known_people", [])),
        ("OTHER_SENSITIVE", config.get("custom_sensitive_terms", [])),
    ]
    entities: list[Entity] = []
    for entity_type, terms in configured:
        if not _type_enabled(entity_type, config):
            continue
        for term in terms:
            term = str(term).strip()
            if not term:
                continue
            for match in re.finditer(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.I):
                entities.append(Entity(match.start(), match.end(), entity_type, match.group(0), "config", 0.98, term))
    return entities


def _organization_heuristics(text: str, config: dict) -> list[Entity]:
    if not config.get("anonymize_organizations", True):
        return []
    suffixes = r"Holding|Holdings|Group|Company|Co\.|Ltd\.?|LLC|S\.A\.L\.?|Inc\.?|Corp\.?|Corporation|Bank|University|Agency|Foundation"
    pattern = rf"\b[A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*){{0,4}}\s+(?:{suffixes})\b"
    return [Entity(m.start(), m.end(), "ORG", m.group(0), "org-heuristic", 0.7) for m in re.finditer(pattern, text)]


def _location_heuristics(text: str, config: dict) -> list[Entity]:
    if not config.get("anonymize_locations", True):
        return []
    entities: list[Entity] = []
    for location in COMMON_LOCATIONS:
        for match in re.finditer(rf"(?<!\w){re.escape(location)}(?!\w)", text, re.I):
            entities.append(Entity(match.start(), match.end(), "LOCATION", match.group(0), "location-heuristic", 0.65, location.title()))
    return entities


def _date_heuristics(text: str) -> list[Entity]:
    date_words = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|today|tomorrow|yesterday"
    return [Entity(m.start(), m.end(), "DATE", m.group(0), "date-heuristic", 0.65) for m in re.finditer(rf"\b(?:{date_words})\b", text, re.I)]


def _add_person_alias_occurrences(text: str, entities: list[Entity]) -> list[Entity]:
    full_people = [e.text.strip() for e in entities if e.entity_type == "PERSON" and len(e.text.split()) > 1]
    speaker_people = [e.text.strip() for e in entities if e.entity_type == "PERSON"]
    aliases: dict[str, str] = {}
    ambiguous: set[str] = set()
    for person in full_people + speaker_people:
        first = person.split()[0]
        key = first.casefold()
        if key in aliases and aliases[key] != person:
            ambiguous.add(key)
        aliases[key] = person

    additions: list[Entity] = []
    for first_key, canonical in aliases.items():
        if first_key in ambiguous or len(first_key) < 2:
            continue
        first_name = canonical.split()[0]
        for match in re.finditer(rf"(?<!\w){re.escape(first_name)}(?!\w)", text):
            additions.append(Entity(match.start(), match.end(), "PERSON", match.group(0), "person-alias", 0.7, canonical))
    return entities + additions


def _add_full_person_name_occurrences(text: str, entities: list[Entity]) -> list[Entity]:
    full_names = sorted(
        {e.text.strip() for e in entities if e.entity_type == "PERSON" and len(e.text.split()) > 1},
        key=len,
        reverse=True,
    )
    additions: list[Entity] = []
    for full_name in full_names:
        for match in re.finditer(rf"(?<!\w){re.escape(full_name)}(?!\w)", text, re.I):
            additions.append(Entity(match.start(), match.end(), "PERSON", match.group(0), "person-full-name", 0.85, full_name))
    return entities + additions


def _expand_person_entities(text: str, entities: list[Entity]) -> list[Entity]:
    expanded: list[Entity] = []
    for entity in entities:
        if entity.entity_type != "PERSON":
            expanded.append(entity)
            continue

        start, end = _expand_person_span(text, entity.start, entity.end)
        expanded_text = text[start:end]
        expanded.append(
            Entity(
                start,
                end,
                entity.entity_type,
                expanded_text,
                entity.source,
                entity.score,
                entity.canonical_text if entity.canonical_text and entity.canonical_text != entity.text else expanded_text,
            )
        )
    return expanded


def _expand_person_span(text: str, start: int, end: int) -> tuple[int, int]:
    current_start = start
    current_end = end

    while True:
        before = text[:current_start]
        separator = re.search(r"[ \t]+$", before)
        if not separator:
            break
        candidate_end = separator.start()
        match = _previous_name_token(text, candidate_end)
        if not match or _name_token_count(text[match.start() : current_end]) > MAX_PERSON_NAME_TOKENS:
            break
        current_start = match.start()

    while True:
        separator = re.match(r"[ \t]+", text[current_end:])
        if not separator:
            break
        candidate_start = current_end + separator.end()
        match = NAME_TOKEN_RE.match(text, candidate_start)
        if not match or _name_token_count(text[current_start : match.end()]) > MAX_PERSON_NAME_TOKENS:
            break
        current_end = match.end()

    return current_start, current_end


def _previous_name_token(text: str, end: int) -> re.Match[str] | None:
    line_start = text.rfind("\n", 0, end) + 1
    matches = list(NAME_TOKEN_RE.finditer(text, line_start, end))
    if not matches:
        return None
    match = matches[-1]
    if match.end() != end:
        return None
    return match


def _name_token_count(value: str) -> int:
    return len(NAME_TOKEN_RE.findall(value))


def _type_enabled(entity_type: str, config: dict) -> bool:
    if entity_type == "DATE":
        return bool(config.get("anonymize_dates", False))
    if entity_type == "LOCATION":
        return bool(config.get("anonymize_locations", True))
    if entity_type == "ORG":
        return bool(config.get("anonymize_organizations", True))
    return True


def merge_overlaps(entities: Iterable[Entity]) -> list[Entity]:
    sorted_entities = sorted(
        entities,
        key=lambda e: (e.start, -(e.end - e.start), -SPECIFICITY.get(e.entity_type, 0), -e.score),
    )
    accepted: list[Entity] = []
    for entity in sorted_entities:
        if not entity.text.strip():
            continue
        overlap_index = next((i for i, current in enumerate(accepted) if entity.start < current.end and current.start < entity.end), None)
        if overlap_index is None:
            accepted.append(entity)
            continue

        current = accepted[overlap_index]
        entity_rank = (entity.end - entity.start, SPECIFICITY.get(entity.entity_type, 0), entity.score)
        current_rank = (current.end - current.start, SPECIFICITY.get(current.entity_type, 0), current.score)
        if entity_rank > current_rank:
            accepted[overlap_index] = entity

    return sorted(accepted, key=lambda e: e.start)


def detect_entities(text: str, config: dict) -> tuple[list[Entity], list[str], list[str]]:
    warnings: list[str] = []
    confidence_notes = [
        "Automated anonymization can miss context-specific sensitive terms.",
        "Review the anonymized transcript before sharing it externally.",
    ]
    entities = []
    entities.extend(_presidio_entities(text, config, warnings))
    entities.extend(_spacy_entities(text, config, warnings))
    entities.extend(_regex_entities(text, config))
    entities = _expand_person_entities(text, entities)
    entities = _add_full_person_name_occurrences(text, entities)
    entities = _add_person_alias_occurrences(text, entities)
    return merge_overlaps(entities), warnings, confidence_notes
