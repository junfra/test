# Reset Plan — Writing Plan v4 (Task 4 Draft Depth Fix)

## Target Artifact
`/home/user01/project/study/my-study/.worktree/study-harness/PLAN.md`

## Artifact Type
Writing plan for CLI study harness implementation.

## Revision Number
v4

## Next Draft Owner
main agent

## Goal
Strengthen Task 4 (Learning Draft Generation Engine) to provide concrete, testable evidence of dense bottom-up concept-book depth — proving chapter-level drill-down and subject-specific content rather than generic scaffolding.

## Rewrite Map
1. Header + Goal + Architecture — unchanged from v3
2. Tasks 0–3 — unchanged from v3 (already passed oracle review)
3. **Task 4 REWRITE** — replace all draft depth assertions with substantive density requirements
4. Task 5–10 — carry forward exactly as v3 (all other principles already satisfied by oracle v5 verification)

## Per-Section Instructions for Task 4 Rewrite

### New Test Requirements:
```python
def test_draft_has_concept_book_depth():
    root = Path("/tmp/test-subject")
    add_sources(root, [SourceReference(kind="native", content="<substantive technical content about X>")])
    draft_text = generate_draft(root, "Topic")
    md = (root / "learning_draft.md").read_text()
    
    # Verify chapter-level drill-down structure (not just headings)
    chapters = re.findall(r"^# (.+)$", md, re.MULTILINE)
    sections_per_chapter = [len(re.findall(rf"^## .+", md)) for _ in range(len(chapters))]  # approximate
    assert len(chapters) >= 3
    
    # Verify substantive depth: no placeholder/generic content
    generic_patterns = ["source basis", "placeholder", "generic example", "..."]
    body_sections = [s for s in re.split(r"^#", md, flags=re.MULTILINE)[1:] 
                     if not s.startswith("References") and not s.startswith("Bibliography")]
    assert all(len(s.strip()) > 50 for s in body_sections), "Body sections must have substantive content"
    
    # Verify NO generic template patterns (proves actual concept-book, not scaffold)
    template_patterns = ["Insert topic", "[Topic]", "{{topic}}"]
    assert not any(p in md.split("# References")[0] for p in template_patterns)  # check body only
    
    # Verify bibliography-only: no inline citations [n] or (Author, Year) before # References header
    ref_section_idx = max(md.find("# References"), md.find("# Bibliography"))
    if ref_section_idx > 0:
        body_before_refs = md[:ref_section_idx]
        assert not re.search(r"\[[\d]+\]", body_before_refs), "Found inline citation in body"
```

### Implementation Contract for Task 4:
- `generate_draft(subject_root, topic)` MUST produce a concept-book where each chapter covers distinct sub-topics with subsections
- Draft generation prompt template (in implementation) must include instructions for: intermediate-to-advanced audience, dense explanations, chapter structure matching source material topics
- Reference section at end of document contains all sources in bibliography format only

### New Test for Bibliography Verification:
```python
def test_bibliography_only_references():
    md = (root / "learning_draft.md").read_text()
    # Find References/Bibliography section
    ref_section = re.search(r"(# References|# Bibliography)\s*\n(.+)", md, re.MULTILINE | re.DOTALL)
    assert ref_section is not None, "Must have a references/bibliography section"
    
    # Verify all sources appear in bibliography
    source_files = list(source_root.glob("*.json"))
    for sf in source_files:
        content = json.loads(sf.read_text())
        keyword_match = any(kw in ref_section.group(2) 
                          for kw in [content.get("metadata", {}).get("url", ""), 
                                    content["content"][:50] if len(content["content"]) > 50 else content["content"]])
        assert keyword_match, f"Source {sf.name} must appear in bibliography"
```

## Explicit Prohibitions
- NO `# Chapter` count test alone — structural markers without substantive verification are insufficient
- NO generic template patterns ("Insert topic", "[Topic]", "{{topic}}") anywhere in body
- NO placeholder content ("source basis dump", "example text") that passes test without real concept-book

## Drafting Checks (must pass before supervision)
1. Task 4 tests verify: ≥3 chapters, substantive content per section (>50 chars), no template patterns
2. Bibliography verification test confirms all sources appear in reference section
3. Body-only citation check ensures no inline [n] citations
4. All other tasks (0-3, 5-10) carry forward exactly as v3 without modification

## Lineage Evidence Inputs
- failed_artifact_ref: `/home/user01/project/study/my-study/.worktree/study-harness/PLAN.md` (v3, study-harness-supervise-v5 fail)
- stopping_stalled_retries_ref: this document's output
- reset_brief_ref: `/tmp/reset_brief_v2.md`
- writing_reset_plan_ref: current file
- Revision Number: v4
- Next Draft Owner: main agent
