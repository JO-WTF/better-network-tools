from dataclasses import dataclass


@dataclass
class AutocompleteResult:
    items: list[dict]
