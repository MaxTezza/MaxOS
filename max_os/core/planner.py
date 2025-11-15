"""Hybrid intent planner that can fall back to rule-based parsing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from max_os.core.intent import Intent, Slot


@dataclass
class KeywordRule:
    keyword: str
    intent: str
    summary: str
    slot_name: str | None = None


class IntentPlanner:
    """Maps natural language to Intent objects."""

    def __init__(self, rules: Iterable[KeywordRule] | None = None, default_intent: str = "system.general"):
        self.rules: List[KeywordRule] = list(rules) if rules else self._default_rules()
        self.default_intent = default_intent

    def plan(self, text: str, context: Dict[str, str] | None = None) -> Intent:
        lowered = text.lower()
        for rule in self.rules:
            if rule.keyword in lowered:
                slots = []
                if rule.slot_name:
                    slots.append(Slot(name=rule.slot_name, value=rule.keyword))
                return Intent(
                    name=rule.intent,
                    confidence=0.65,
                    slots=slots,
                    summary=rule.summary,
                )
        return Intent(name=self.default_intent, confidence=0.2, slots=[], summary="General system request")

    @staticmethod
    def _default_rules() -> List[KeywordRule]:
        return [
            KeywordRule("file", "file.manage", "Handle filesystem operations", "keyword"),
            KeywordRule("folder", "file.organize", "Organize directories", "keyword"),
            KeywordRule("archive", "file.archive", "Archive or compress files", "keyword"),
            KeywordRule("project", "dev.scaffold", "Scaffold a software project", "keyword"),
            KeywordRule("deploy", "dev.deploy", "Coordinate deployment", "keyword"),
            KeywordRule("test", "dev.test", "Run developer tests", "keyword"),
            KeywordRule("service", "system.service", "Inspect or modify services", "keyword"),
            KeywordRule("cpu", "system.metrics", "Collect resource metrics", "keyword"),
            KeywordRule("wifi", "network.manage", "Manage Wi-Fi connections", "keyword"),
            KeywordRule("vpn", "network.vpn", "Manage VPN connections", "keyword"),
            KeywordRule("firewall", "network.firewall", "Adjust firewall", "keyword"),
        ]
