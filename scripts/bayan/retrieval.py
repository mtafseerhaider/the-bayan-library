"""Reference context builder: the retrieval ladder under a token budget.

    Metadata card -> Summary -> Executive summary -> Full content

Every target starts at its card. The builder then upgrades targets one
layer at a time, highest priority first, and stops as soon as the next
upgrade would exceed the budget. Full content is added section by section
(Markdown H2 chunks), never as a whole file unless it fits. The result is
the smallest context that still covers every target.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .common import estimate_tokens, read_optional

LAYERS = ("card", "summary", "executive", "full")
STATUS_WEIGHT = {"canonical": 1.0, "reviewed": 0.9, "draft": 0.5,
                 "deprecated": 0.1}


@dataclass
class Item:
    id: str
    priority: float
    card: dict
    layer: str = "card"
    text: dict = field(default_factory=dict)
    chunks_loaded: int = 0

    def tokens(self) -> int:
        return sum(estimate_tokens(t) for t in self.text.values())


def load_cards(root: Path) -> dict[str, dict]:
    cards = {}
    for shard in sorted((root / "metadata" / "index").glob("*.jsonl")):
        for line in shard.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entry = json.loads(line)
                cards[entry["id"]] = entry
    return cards


def priority(card: dict, relevance: float = 1.0) -> float:
    """relevance x authority. Callers pass relevance from their query."""
    return round(relevance * STATUS_WEIGHT.get(card.get("status", "draft"),
                                               0.5), 4)


def chunks(markdown: str) -> list[str]:
    """Split Markdown at H2 headings, keeping the heading with its text."""
    parts = re.split(r"(?m)^(?=## )", markdown)
    return [p for p in parts if p.strip()]


def _card_text(card: dict) -> str:
    keep = {k: v for k, v in card.items()
            if k not in ("summary", "tokens", "executive_summary",
                         "content", "record")}
    return json.dumps(keep, ensure_ascii=False, sort_keys=True)


def build(root: Path, targets: dict[str, float], budget: int,
          max_layer: str = "full", cards: dict | None = None) -> dict:
    """Assemble a context pack.

    targets: {record_id: relevance between 0 and 1}
    budget:  maximum input tokens for the context (excluding the prompt)
    """
    cards = cards if cards is not None else load_cards(root)
    stop = LAYERS.index(max_layer)
    items, missing = [], []
    for record_id, relevance in targets.items():
        card = cards.get(record_id)
        if card is None:
            missing.append(record_id)
            continue
        item = Item(record_id, priority(card, relevance), card)
        item.text["card"] = _card_text(card)
        items.append(item)
    items.sort(key=lambda i: (-i.priority, i.id))

    used = sum(i.tokens() for i in items)
    dropped = []
    while used > budget and items:          # even cards do not fit
        victim = items.pop()                # lowest priority first
        used -= victim.tokens()
        dropped.append(victim.id)

    for layer_index in range(1, stop + 1):
        layer = LAYERS[layer_index]
        for item in items:
            if item.layer != LAYERS[layer_index - 1]:
                continue                    # previous layer did not fit
            if layer == "summary":
                pieces = [item.card.get("summary", "")]
            elif layer == "executive":
                pieces = [read_optional(
                    root, item.card.get("executive_summary"))]
            else:
                pieces = chunks(read_optional(
                    root, item.card.get("content")))
            pieces = [p for p in pieces if p]
            if not pieces:
                item.layer = layer          # nothing to load at this layer
                continue
            for piece in pieces:
                cost = estimate_tokens(piece)
                if used + cost > budget:
                    break
                key = layer if layer != "full" else \
                    f"full:{item.chunks_loaded}"
                item.text[key] = piece
                used += cost
                item.layer = layer
                if layer == "full":
                    item.chunks_loaded += 1

    return {
        "budget": budget,
        "used_tokens": used,
        "items": [{"id": i.id, "priority": i.priority, "layer": i.layer,
                   "chunks": i.chunks_loaded, "tokens": i.tokens(),
                   "text": i.text} for i in items],
        "missing": missing,
        "dropped": dropped,
    }
