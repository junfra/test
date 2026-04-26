"""LM client with mock provider and JSON parsing."""
from __future__ import annotations

import json
import random
import re
import textwrap
from typing import Any

from .models import LearningDraftSystem


class LMGenerationError(Exception):
    """Raised when LM generation or parsing fails."""


class LMClient:
    """Client for LM generation with a built-in mock provider."""

    def __init__(self, config: Any) -> None:
        self.config = config

    def generate(self, prompt: str) -> str:
        if self.config.provider == "mock":
            return self._mock_generate(prompt)
        raise LMGenerationError(f"Provider '{self.config.provider}' is not implemented yet")

    def _mock_generate(self, prompt: str) -> str:
        """Generate dense mock JSON that looks like an LM chapter reconstruction."""

        # Extract topic from prompt
        topic = "Learning"
        for line in prompt.splitlines():
            if line.startswith("Topic:"):
                topic = line.split(":", 1)[1].strip()
                break

        # Build dense mock JSON for a single chapter
        chapter_match = re.search(r"Chapter (\d+) of (\d+)", prompt)
        chapter_num = int(chapter_match.group(1)) if chapter_match else 1
        total_chapters = int(chapter_match.group(2)) if chapter_match else 3

        section_structure = textwrap.dedent(f"""\
# Chapter {chapter_num}: {self._chapter_title(chapter_num, topic)}

## Concept Reconstruction
The {self._topic_noun(topic)} is not merely a surface phenomenon; it is a structural pressure that shapes how systems organize themselves under constraint. When we reconstruct this concept, we must start from the observation that any system operating with limited resources must make trade-offs between isolation and cooperation, between certainty and adaptability, between immediate response and long-term planning. The {self._topic_noun(topic)} emerges precisely at the boundary where these tensions become unsolvable by simple rules, requiring a more sophisticated architecture of coordination.

## Mechanism
The mechanism operates through three coupled layers. First, the system identifies the resource or state that is being contested. Second, it establishes a protocol for how agents within the system can signal their needs and negotiate access. Third, it implements a feedback loop that adjusts the protocol based on observed outcomes, ensuring that the system does not settle into a suboptimal equilibrium. This three-layer mechanism is what distinguishes a {self._topic_noun(topic)} from a simple resource allocation scheme: the mechanism itself is adaptive, learning from the pattern of contention to improve future decisions.

## Learning Model
To truly understand the {self._topic_noun(topic)}, you must be able to reconstruct the mechanism from first principles. Start by asking: what would happen if the system had no mechanism for coordination? You would observe chaos, inefficiency, and systemic failure. Now ask: what would happen if the coordination were entirely centralized? You would observe a single point of failure and a bottleneck that limits scalability. The {self._topic_noun(topic)} lives in the space between these two extremes, providing enough structure to prevent chaos while enough flexibility to avoid bottlenecks.

## Verification Point
Can you explain how the three-layer mechanism prevents both chaos and centralization failure? Can you identify a real-world {self._topic_noun(topic)} and map its layers to this model?
        """).strip()

        result: dict[str, Any] = {
            "topic": topic,
            "concept_layers": [
                f"The {self._topic_noun(topic)} represents a structural pressure that shapes system organization under constraint.",
                f"The {self._topic_noun(topic)} requires a three-layer mechanism: identification, protocol, and feedback.",
                f"Understanding the {self._topic_noun(topic)} demands reconstruction from first principles, not memorization.",
            ],
            "section_structure": [section_structure],
            "recall_hooks": [
                f"Explain how the three-layer {self._topic_noun(topic)} mechanism prevents both chaos and centralization failure.",
                f"Identify a real-world {self._topic_noun(topic)} and map its coordination layers to the model.",
            ],
            "verification_points": [
                f"The learner can reconstruct the {self._topic_noun(topic)} mechanism from first principles.",
                f"The learner can distinguish between the {self._topic_noun(topic)}, simple allocation, and centralized coordination.",
            ],
            "bibliography": [
                f"Source material for {self._topic_noun(topic)} chapter {chapter_num}",
            ],
        }

        # Serialize as dense JSON (not pretty-printed)
        return json.dumps(result, ensure_ascii=False)

    def _topic_noun(self, topic: str) -> str:
        """Derive a noun-ish form from the topic."""
        if topic.endswith("y"):
            return topic[:-1] + "iness"
        return topic

    def _chapter_title(self, num: int, topic: str) -> str:
        titles = {
            1: "Foundational Principles",
            2: "Mechanism and Coordination",
            3: "Adaptive Behavior and Learning",
            4: "System-Level Consequences",
            5: "Synthesis and Application",
        }
        return titles.get(num, f"Principles of {topic}")


def parse_learning_system_json(raw: str) -> LearningDraftSystem:
    """Parse a JSON string into a LearningDraftSystem.

    Handles the case where the response contains markdown code fences
    wrapping the JSON, or contains extra text before/after valid JSON.
    """

    # Strip markdown code fences if present
    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)\n```\s*$", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # Try to find a JSON object in the text
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        text = text[brace_start : brace_end + 1]

    data = json.loads(text)
    return LearningDraftSystem.model_validate(data)
