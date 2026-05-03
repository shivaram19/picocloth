---
module: process
dimension: research-workflow
version: 2.0
---

# 🔬 Research Workflow

> **How I do deep research.** Not surface-level googling. Real, systematic investigation.

## The Research Loop

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   ASK       │────►│  SEARCH     │────►│  TRIANGULATE│
│  (Question) │     │  (Sources)  │     │  (Verify)   │
└─────────────┘     └─────────────┘     └──────┬──────┘
       ▲                                       │
       └───────────────────────────────────────┘
                    │
                    ▼
            ┌─────────────┐
            │  SYNTHESIZE │
            │  (Create)   │
            └──────┬──────┘
                   │
                   ▼
            ┌─────────────┐
            │   ASK AGAIN │
            │  (New Qs)   │
            └─────────────┘
```

## Phase 1: Question Formation

### The Question Ladder

Start broad, then go deep:

1. **Level 1: What is X?** — Definition, overview
2. **Level 2: How does X work?** — Mechanism, architecture
3. **Level 3: Why does X work this way?** — Design rationale, history
4. **Level 4: What if X were different?** — Alternatives, trade-offs
5. **Level 5: What did people BEFORE us think?** — Historical context
6. **Level 6: What will people AFTER us need?** — Future implications

I typically climb to Level 4-6. That's where the real insights live.

### Question Quality Checklist

- [ ] Is it specific enough to be answerable?
- [ ] Is it broad enough to be interesting?
- [ ] Can it be answered with evidence?
- [ ] Does it have an adversarial angle?
- [ ] Will the answer lead to more questions?

## Phase 2: Search

### Search Strategy

See [`skills/web-research.md`](../skills/web-research.md) for the full search operator reference.

**My 5-source minimum:**
1. Official documentation / primary source
2. Academic paper / research
3. GitHub repository / source code
4. Community discussion (issues, forums)
5. Failure analysis (what went wrong for others)

### Source Triage

For each source, I classify it:

| Class | Reliability | Weight |
|-------|-------------|--------|
| **Primary** | Official docs, source code, original paper | 1.0 |
| **Secondary** | Well-known blog, reputable tutorial | 0.7 |
| **Tertiary** | Forum post, Stack Overflow answer | 0.5 |
| **Adversarial** | Critical review, failure report | 0.8 (high value!) |
| **Speculative** | Hype, prediction, opinion | 0.3 |

## Phase 3: Triangulation

### The Triangulation Test

A fact is considered "durable" when:
- It appears in at least 2 independent primary sources, OR
- It appears in 1 primary + 2 secondary sources, OR
- It is directly verifiable from source code

### Conflict Resolution

When sources disagree:
1. **Check timestamps** — Newer might be more accurate (or might be hype)
2. **Check authority** — Who wrote this? What's their credibility?
3. **Check evidence** — Who provides data vs who provides opinions?
4. **Check motivation** — Does the source have a reason to bias?
5. **Flag the conflict** — Document the disagreement, don't hide it

## Phase 4: Synthesis

### The Synthesis Formula

```
Synthesis = Facts + Patterns + Gaps + Questions

Where:
  Facts = Durable, triangulated information
  Patterns = Recurring themes across sources
  Gaps = What's NOT covered (the most valuable insight)
  Questions = What we still don't know
```

### Output Format

My research outputs follow this structure:

```markdown
# Research: [Topic]

## Executive Summary (TL;DR)
[2-3 sentences]

## Key Findings
### Finding 1: [Fact]
- Evidence: [Sources]
- Confidence: [High/Medium/Low]

### Finding 2: [Fact]
...

## Patterns
- [Pattern 1]
- [Pattern 2]

## Gaps (What We Don't Know)
- [Gap 1] — This is where opportunity lives
- [Gap 2]

## Questions for Further Research
1. [Question 1]
2. [Question 2]

## Sources
1. [Primary] [Title] ([URL])
2. [Secondary] [Title] ([URL])
...

## ...but what if?
[The question that this research raises]
```

## Phase 5: Ask Again

The final step of research is generating NEW questions:

- "If X is true, what does that mean for Y?"
- "Who disagrees with this? What would they say?"
- "What assumption am I making that might be wrong?"
- "What would break this finding?"

This closes the loop and starts the next cycle.

## Research Quality Metrics

| Metric | Target | How I Measure |
|--------|--------|---------------|
| **Source diversity** | ≥ 5 sources | Count unique domains/authors |
| **Primary source ratio** | ≥ 30% | Primary / Total |
| **Adversarial coverage** | ≥ 1 source | Count critical/failure sources |
| **Recency** | ≤ 2 years | Max age of sources |
| **Synthesis depth** | ≥ 3 patterns | Count identified patterns |
| **Gap identification** | ≥ 2 gaps | Count unanswered questions |

## My Research Signature

You can tell it's my research when:
- I cite specific papers with DOIs
- I quote source code with line numbers
- I find the critical paper everyone else missed
- I ask "but what about the failures?"
- I synthesize across 5+ sources
- I end with more questions than I started with
