# C-Group Resume Evolution Rules

## Current Target

C-group resume generation aims to keep quality while using a cheaper/faster extraction path.

The final path is:

1. Extract source text with the existing script path.
2. Label source lines with source IDs.
3. Build the C-type source map.
4. Build structured extracted content.
5. Build render JSON through the agreed wrapper path.
6. Generate DOCX only.

Do not generate PDF for this loop unless the user asks.

## Role Split

LLM responsibilities:

- section meaning
- section boundary
- item mapping
- missing-content judgment
- editor-style interpretation

Script responsibilities:

- source ID labeling
- source text delivery
- JSON extraction and mechanical normalization
- JSON shape validation
- source ID coordinate validation
- deterministic assembly
- original renderer/DOCX wrapper calls

Scripts must not decide whether a fact belongs to a semantic section.

## Baseline And Judgment

A-group is a quality baseline, not an absolute answer.

Strict sections:

- personal identity
- contact
- education existence
- work experience existence
- company
- period
- title/role

Editor-judgment sections:

- skills
- core competencies
- self introduction
- training
- overseas experience
- misc

Failure:

- source-backed work experience is missing
- education is invented or omitted
- source facts are contradicted
- factual rows are invented
- a render/DOCX output drops content present in the prior stage

Acceptable difference:

- A-group over-includes soft traits as skills, while C-group keeps explicit skills only
- C-group maps ambiguous narrative content differently with source support
- duration differs because current-date calculation follows original code

## Source Map Strategy

Use source IDs as coordinates, not as semantic truth.

The LLM decides whether a section uses:

- `direct`: one contiguous block
- `split`: one large block split into hierarchy-preserving subgroups
- `collect`: scattered factual rows collected for one section

Do not use script thresholds such as line count or character count to decide "large enough to split".

For work experience:

- Preserve company/period/title hierarchy.
- Keep child groups under the same parent record when they are details of one employer/role.
- Use narrow role/team periods for detailed records when both broad employment and narrow role periods exist.
- Use summary-table source IDs as period evidence when detail rows omit period but order/company/title match.

## Section Boundary Rules

Personal information:

- identity, contact, birth, address, and application metadata.
- availability and desired start date belong to compensation/conditions.

Target position:

- desired role, target work, role fit, contribution plan, post-hire plan.
- general personality or growth story stays in self introduction.

Core competencies:

- professional strengths, performance summary, transferable strengths.
- simple certificates, language scores, OA rows, and tool inventory stay in their factual sections.

Work experience:

- employers, roles, teams, duties, products, projects, achievements, reason for leaving.
- tool names inside duties stay in work experience unless the source has a separate skill inventory.

Education:

- school, degree, major, study period, graduation state.
- non-degree training stays in training.

Training:

- external/internal courses, completion, counts, named programs.
- degree education stays in education.
- training facts inside narrative may be shared as training evidence.

Skills:

- explicit languages, test scores, OA, tools, systems, platforms, technologies.
- soft traits such as sincerity, preparation, ownership, and work attitude are not skills.
- do not create skills only from scattered work-duty keywords.

Compensation:

- current/final/previous/desired salary, bonus, incentives, benefits, allowance, parking, vehicle, conditions, availability.
- ordinary salary/location rows inside employer history stay in work experience unless they are current/final/desired conditions.

Self introduction:

- profile narrative, motivation, growth story, values, personality, career story.
- factual rows inside narrative may be shared with factual sections.

Misc:

- candidate facts that fit no more specific section.
- repeated headers, footers, page numbers, and visual-only markers are not resume facts.

## Prompt Rules

- Keep prompts short and imperative.
- Explain the section purpose when it affects judgment.
- Keep necessary prohibitions for real boundary control.
- Remove case-specific prohibitions after deriving the general principle.
- Do not paste old giant prompts into the final path.
- Store distilled final prompt rules in the current prompt book, not only in GBrain or old test outputs.

## Render/DOCX Rules

When testing full generation:

- If source information is missing from extracted content, fix the first-stage extraction.
- If extracted content has it but render JSON drops it, fix render prompt/wrapper.
- If render JSON has it but DOCX omits it, inspect renderer/template/photo path.
- Reuse original production render/date/language/format rules before inventing C-group-specific replacements.
- DOCX is the comparison artifact.

## Artifact Hygiene

- Keep one final execution path.
- Do not create new runner files for every test.
- Remove obsolete test outputs before a full new loop when the user asks cleanup.
- Keep A-group reference, source text, and current C-group outputs separate.
