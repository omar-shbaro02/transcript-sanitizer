import re
from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class ReplacementResult:
    text: str
    mapping: dict[str, str]
    counts_by_type: dict[str, int]


class PlaceholderMapper:
    def __init__(self) -> None:
        self._mapping: dict[str, str] = {}
        self._aliases: dict[tuple[str, str], str] = {}
        self._counters: defaultdict[str, int] = defaultdict(int)

    @staticmethod
    def normalize(value: str) -> str:
        return re.sub(r"\s+", " ", value.strip()).casefold()

    def add_alias(self, entity_type: str, alias: str, canonical: str) -> None:
        canonical_key = (entity_type, self.normalize(canonical))
        alias_key = (entity_type, self.normalize(alias))
        if canonical_key in self._aliases:
            self._aliases[alias_key] = self._aliases[canonical_key]

    def placeholder_for(self, entity_type: str, value: str) -> str:
        key = (entity_type, self.normalize(value))
        if key in self._aliases:
            placeholder = self._aliases[key]
            self._mapping.setdefault(value, placeholder)
            return placeholder

        self._counters[entity_type] += 1
        placeholder = f"[{entity_type}_{self._counters[entity_type]:03d}]"
        self._aliases[key] = placeholder
        self._mapping[value] = placeholder
        return placeholder

    @property
    def mapping(self) -> dict[str, str]:
        return dict(sorted(self._mapping.items(), key=lambda item: item[0].casefold()))


def seed_person_aliases(mapper: PlaceholderMapper, entities: list) -> None:
    full_names: dict[str, str] = {}
    ambiguous: set[str] = set()
    person_values = sorted(
        {e.text.strip() for e in entities if e.entity_type == "PERSON" and len(e.text.split()) > 1},
        key=len,
        reverse=True,
    )
    for full_name in person_values:
        placeholder = mapper.placeholder_for("PERSON", full_name)
        first_name = full_name.split()[0]
        normalized = mapper.normalize(first_name)
        if normalized in full_names and full_names[normalized] != placeholder:
            ambiguous.add(normalized)
        full_names[normalized] = placeholder

    for full_name in person_values:
        first_name = full_name.split()[0]
        if mapper.normalize(first_name) not in ambiguous:
            mapper.add_alias("PERSON", first_name, full_name)


def apply_replacements(text: str, entities: list) -> ReplacementResult:
    mapper = PlaceholderMapper()
    seed_person_aliases(mapper, entities)
    counts: defaultdict[str, int] = defaultdict(int)
    output = text

    for entity in sorted(entities, key=lambda item: item.start, reverse=True):
        original = output[entity.start : entity.end]
        placeholder = mapper.placeholder_for(entity.entity_type, entity.canonical_text or original)
        if original != placeholder:
            output = output[: entity.start] + placeholder + output[entity.end :]
            counts[entity.entity_type] += 1

    return ReplacementResult(text=output, mapping=mapper.mapping, counts_by_type=dict(counts))

