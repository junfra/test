# Recall System — Learn Sub-Skill

## Purpose
Generate deep, high-density learning materials (30,000+ characters of pure text) for a given topic. Learning material storage path: `subject/<topic_slug>/index.md`.

---

# Fixed 7-Chapter Structure

All generated materials MUST follow this exact chapter order using Korean labels as specified in the Seed:

1. **탄생배경** — Etymology and historical origins of the concept
2. **정의** — Clear definition with formal specification where applicable
3. **하위개념** — Sub-concepts broken down hierarchically
4. **관계도** — Relationships between concepts (diagram-style text)
5. **사례** — Concrete examples from real-world applications
6. **오해** — Common misconceptions and clarifications
7. **회상키포인트** — Key recall points for each chapter

---

# Output Requirements

## Character Count
- **Minimum: 30,000 characters of pure text** (excluding markdown formatting such as `#`, `-`, `[RETRIEVE:]` tags)
- If underrun → save as `subject/<topic_slug>/draft_failed.md` with reason in a comment header (per BC-7)

## Recall Questions Per Chapter
Each chapter must end with recall questions mixing three types:
- **Fact-based:** "What is X?"
- **Comparison:** "How does X differ from Y?"
- **Understanding:** "Why was Z developed? What problem does it solve?"

These chapter-end recall questions are automatically extracted by the router (per BC-10) and queued for the first recall session.

## Inline Retrieval Points
Embed retrieval points within chapters at natural intervals (approximately every 500–700 characters of content). Format: `[RETRIEVE: <question>]` where `<question>` targets a specific concept or relationship in that paragraph. Example:

```markdown
Deep learning models learn hierarchical representations through layered transformations [RETRIEVE: What do deep learning layers progressively capture?], moving from simple edge detection to complex pattern recognition over many stages.
```

## References At End Only
List all references in a single `## 참고자료` section at the end of document — **do NOT cite inline**. Format:

```markdown
## 참고자료
1. [Author, Title, Year] URL if available
2. ...
```

---

# Source Generation Contract (Agent Execution Contract — from Seed)

Learning materials are generated using:
1. LLM knowledge + web search as primary sources
2. **Oracle Browser** as DEFAULT for web search capability
3. Built-in web search option available as alternative to Oracle Browser
4. User-provided materials (PDF, documents, links) accepted as OPTIONAL input alongside LLM knowledge and web search

When user provides their own materials: merge them into the learning material generation process, giving priority to official/primary sources per source conflict resolution rules below.

---

# Source Conflict Resolution (Agent Execution Contract)
1. Prefer official/primary sources first
2. Check recency of sources
3. Mark uncertainty explicitly — **NEVER** state uncertain information as fact (**단정 금지** in Korean output)
4. Record all resolved conflicts in the references section at end of document

---

# Safety Contracts (Agent Execution Contract)

## Safe File-Write Behavior
Before writing to any file:
1. Create complete replacement content FIRST
2. Preserve recoverable prior content when possible
3. Never frame this as a required Python helper/API implementation — it is agent behavior guidance

## JSON/State Recovery
When reading state files (`metadata.json`, `recall_queue.json`):
- If unreadable or corrupted → attempt recovery from `.bak` evidence
- If no backup available → reinitialize with explicit user-facing notice: "상태 파일을 복구할 수 없습니다. 새로 초기화합니다." (per BC-11)

## Single-Operation Coordination
For the same topic/session:
- Avoid overlapping write operations
- If work appears already in progress, expose clear recovery behavior
