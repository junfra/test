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
        """Generate dense mock JSON that looks like an LM chapter reconstruction.
        
        Produces many seeds across all collections so that when 
        _render_draft() rotates through them with its modulo indexing,
        the resulting draft has sufficient content density (>5000 chars)
        and exercises real validation paths.
        """

        # Extract topic from prompt
        topic = "Learning"
        for line in prompt.splitlines():
            if line.startswith("Topic:"):
                topic = line.split(":", 1)[1].strip()
                break

        chapter_match = re.search(r"Chapter (\d+) of (\d+)", prompt)
        chapter_num = int(chapter_match.group(1)) if chapter_match else 1
        total_chapters = int(chapter_match.group(2)) if chapter_match else 3
        
        noun = self._topic_noun(topic)

        # Build rich section_structure for learning system compatibility
        section_structure = textwrap.dedent(f"""# Chapter {chapter_num}: {self._chapter_title(chapter_num, topic)}

## Concept Reconstruction
The {noun} is not merely a surface phenomenon; it is a structural pressure that shapes how systems organize themselves under constraint. When we reconstruct this concept, we must start from the observation that any system operating with limited resources must make trade-offs between isolation and cooperation, between certainty and adaptability, between immediate response and long-term planning. The {noun} emerges precisely at the boundary where these tensions become unsolvable by simple rules, requiring a more sophisticated architecture of coordination.

## Mechanism
The mechanism operates through three coupled layers. First, the system identifies the resource or state that is being contested. Second, it establishes a protocol for how agents within the system can signal their needs and negotiate access. Third, it implements a feedback loop that adjusts the protocol based on observed outcomes, ensuring that the system does not settle into a suboptimal equilibrium. This three-layer mechanism is what distinguishes a {noun} from a simple resource allocation scheme: the mechanism itself is adaptive, learning from the pattern of contention to improve future decisions.

## Learning Model
To truly understand the {noun}, you must be able to reconstruct the mechanism from first principles. Start by asking: what would happen if the system had no mechanism for coordination? You would observe chaos, inefficiency, and systemic failure. Now ask: what would happen if the coordination were entirely centralized? You would observe a single point of failure and a bottleneck that limits scalability. The {noun} lives in the space between these two extremes, providing enough structure to prevent chaos while enough flexibility to avoid bottlenecks.

## Verification Point
Can you explain how the three-layer mechanism prevents both chaos and centralization failure? Can you identify a real-world {noun} and map its layers to this model?
        """).strip()

        # Generate dense seed content across all four collections
        # Each collection gets 25+ items so _render_draft() has enough unique seeds
        concept_layers = [
            f"The {noun} represents a structural pressure that shapes system organization under constraint.",
            f"A {noun} requires a three-layer mechanism: identification, protocol design, and adaptive feedback.",
            f"Understanding the {noun} demands reconstruction from first principles, not memorization of surface forms.",
            f"When systems face resource contention, the {noun} provides coordination without central authority.",
            f"The {noun} emerges at boundaries where simple rules fail to resolve competing interests.",
            f"A well-functioning {noun} balances isolation against cooperation in dynamic ways.",
            f"Learning the {noun} involves tracing how agents negotiate access to contested resources.",
            f"The {noun} prevents both chaos and centralization failure through decentralized protocols.",
            f"Every instance of a {noun} reveals an underlying tension between efficiency and robustness.",
            f"A {noun} is best understood as a coordination mechanism rather than a resource distribution scheme.",
            f"The evolution of the {noun} follows predictable patterns across different domains.",
            f"When designing a {noun}, one must consider failure modes at every layer of the system.",
            f"The {noun} operates through recursive refinement: each iteration improves coordination quality.",
            f"Systems that lack a {noun} tend toward either fragmentation or bureaucratic bottlenecks.",
            f"A {noun} requires agents to share incomplete information while maintaining incentives.",
            f"The mathematical structure underlying the {noun} involves fixed-point theorems.",
            f"Real-world {noun}s often emerge organically rather than being deliberately designed.",
            f"The {noun} framework generalizes beyond economics to biology, computer science, and governance.",
            f"A {noun} that scales well must handle increasing numbers of agents without degradation.",
            f"When the {noun} mechanism breaks down, systemic inefficiencies compound rapidly.",
            f"Studying the {noun} reveals universal patterns in how complex systems coordinate.",
            f"The {noun} concept connects to Nash equilibria, mechanism design, and distributed computing.",
            f"A well-designed {noun} can achieve near-optimal outcomes without centralized control.",
            f"The historical development of the {noun} spans centuries across multiple disciplines.",
            f"Modern research on the {noun} combines game theory with empirical field studies.",
        ]

        verification_points = [
            f"The learner can reconstruct the {noun} mechanism from first principles without relying on analogies.",
            f"The learner can distinguish between a genuine {noun}, simple resource allocation, and centralized coordination.",
            f"Given a real-world system, the learner identifies which {noun} mechanisms are present or missing.",
            f"The learner explains why a {noun} prevents both chaos and centralization failure using first principles.",
            f"The learner traces how each layer of the {noun} mechanism contributes to overall coordination quality.",
            f"Given two competing {noun} designs, the learner predicts which handles scale better.",
            f"The learner identifies failure modes in a {noun} when agents have misaligned incentives.",
            f"The learner maps a real-world example (e.g., blockchain, market, ecosystem) to the {noun} framework.",
            f"The learner explains what happens when the feedback layer of the {noun} is disabled.",
            f"The learner derives a simple {noun} protocol for coordinating agents with limited information.",
            f"Given observed system behavior, the learner infers whether a {noun} mechanism is at work.",
            f"The learner distinguishes between emergent and designed instances of the {noun}.",
            f"The learner identifies conditions under which a {noun} transitions from coordination to conflict.",
            f"The learner predicts how increasing agent heterogeneity affects {noun} performance.",
            f"Given a breakdown in a real-world {noun}, the learner diagnoses which layer failed first.",
            f"The learner explains why centralized alternatives fail for large-scale {noun} applications.",
            f"The learner identifies what information requirements make a {noun} mechanism feasible.",
            f"The learner derives necessary conditions for any system to function as a {noun}.",
            f"Given two systems with different {noun} structures, the learner predicts coordination outcomes.",
            f"The learner explains why decentralized {noun}s are more robust than centralized alternatives.",
            f"The learner traces the historical evolution of the {noun} concept through key publications.",
            f"Given a scenario with asymmetric information, the learner designs an appropriate {noun}.",
            f"The learner identifies which real-world systems approximate optimal {noun} behavior.",
            f"The learner explains how the {noun} framework applies to biological and social coordination.",
        ]

        recall_hooks = [
            f"Explain how the three-layer {noun} mechanism prevents both chaos and centralization failure.",
            f"Identify a real-world {noun} and map its coordination layers to the model.",
            f"Describe what happens when the feedback layer of a {noun} is disabled or delayed.",
            f"Trace how agents in a {noun} negotiate access to contested resources step by step.",
            f"Explain why a {noun} that scales must handle increasing agent counts without degradation.",
            f"Compare the {noun} mechanism to centralized coordination: what trade-offs emerge?",
            f"Given observed system behavior, determine whether a {noun} is present and identify its structure.",
            f"Design a simple {noun} protocol for coordinating agents who have incomplete information.",
            f"Explain how fixed-point theorems relate to the mathematical structure of the {noun}.",
            f"Predict what happens when agent heterogeneity increases in a system with a {noun}.",
            f"Trace the historical development of the {noun} concept across key publications and eras.",
            f"Diagnose which layer of a {noun} mechanism failed first given a real-world breakdown scenario.",
            f"Explain why decentralized {noun}s are more robust than centralized coordination alternatives.",
            f"Design an appropriate {noun} for a scenario with asymmetric information among agents.",
            f"Identify conditions under which a {noun} transitions from productive coordination to conflict.",
            f"Compare three real-world examples of the {noun}: market, ecosystem, and open-source software.",
            f"Explain how the {noun} concept generalizes across economics, biology, and computer science.",
            f"Derive necessary conditions for any system to function effectively as a {noun}.",
            f"Predict coordination outcomes in two systems with different {noun} designs.",
            f"Given a real-world {noun} breakdown, explain why centralized alternatives would also fail.",
            f"Map the layers of an observed real-world {noun} back to the three-layer model.",
            f"Explain what information requirements make a particular {noun} mechanism feasible or infeasible.",
            f"Trace how increasing scale affects the performance of different {noun} designs.",
            f"Compare emergent and designed instances of the {noun}: what distinguishes them?",
        ]

        bibliography = [
            f"Aumann, R. (1974). Subjectivity and Correlation in Randomized Strategies. Journal of Mathematical Economics.",
            f"Hart, S., & Mas-Colell, A. (2003). A Unitary Approach to Bets, Games, Decision-Making, and Information. Working Paper.",
            f"Schelling, T. C. (1960). The Strategy of Conflict. Harvard University Press.",
            f"Axelrod, R. (1984). The Evolution of Cooperation. Basic Books.",
            f"Ostrom, E. (1990). Governing the Commons: The Evolution of Institutions for Collective Action. Cambridge University Press.",
            f"Myerson, R. B. (1991). Game Theory: Analysis of Conflict. Harvard University Press.",
            f"Milgrom, P., & Roberts, J. (1992). Economics, Organization, and Management. Prentice Hall.",
            f"Williamson, O. E. (1985). The Economic Institutions of Capitalism. Free Press.",
            f"Nash, J. F. Jr. (1950). Equilibrium Points in N-Person Games. Proceedings of the National Academy of Sciences.",
            f"Fudenberg, D., & Tirole, J. (1991). Game Theory. MIT Press.",
        ]

        result: dict[str, Any] = {
            "topic": topic,
            "concept_layers": concept_layers,
            "section_structure": [section_structure],
            "recall_hooks": recall_hooks,
            "verification_points": verification_points,
            "bibliography": bibliography,
        }

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
