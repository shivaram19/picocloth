---
title: Rich Search Protocol
trigger: research_task, knowledge_discovery, fact_checking, competitive_intelligence
author: PicoCloth
version: 3.0
---

# Rich Search Protocol v3.0

## Philosophy

> Don't fight SEO. Out-search it.

Search **cleverly**. Search **curiously**. Search **targetedly**.

Three modes, one goal: find the knowledge that algorithms bury.

---

## Three Modes of Discovery

### 1. CLEVERLY — Pattern-Optimized Search

Use optimized query patterns that experts use. Don't just type keywords.

**Command:**
```bash
picocloth search clever "AI agent market 2026" --type business --execute --store
```

**What it does:**
- Expands your topic into expert terminology (TAM, CAGR, SOM)
- Targets high-yield platforms (SEC for business, arXiv for research, HN for tech)
- Uses site-specific and filetype-specific filters
- Runs 3-5 parallel query variants

**Query patterns:**
```
# Academic
site:arxiv.org "topic" after:2024
"topic" filetype:pdf site:arxiv.org OR site:openreview.net

# Technical  
site:github.com "topic" stars:>100
site:news.ycombinator.com "topic"
"topic" site:stackoverflow.com is:question score:>10

# Business
site:sec.gov "company" 10-K OR 10-Q
"topic" market size revenue CAGR filetype:pdf
```

**When to use:** You know WHAT you're looking for. You want the BEST sources efficiently.

---

### 2. CURIOUSLY — Exploratory Discovery

Follow scent trails. Find what lives NEXT to your topic. Discover the unexpected.

**Command:**
```bash
picocloth search curious "AI agent architectures" --execute --store
```

**What it does:**
- Searches for adjacent concepts and alternatives
- Finds the people, stories, and controversies behind the topic
- Looks for cross-domain applications (healthcare? finance? education?)
- Hunts emerging signals on Hacker News and GitHub trending

**Query patterns:**
```
# Adjacent concepts
"topic" related to OR compared with OR alternative
"topic" history evolution timeline
"topic" unexpected use case OR hack OR workaround

# People and stories
who created "topic" OR who invented "topic"
"topic" founder story OR origin story
"topic" controversy OR debate OR disagreement

# Cross-domain
"topic" applied to healthcare OR finance OR education
"topic" interdisciplinary OR cross-functional

# Emerging signals
"topic" 2026 OR "upcoming" OR "next generation"
"topic" github trending OR new repository
```

**When to use:** You want to DISCOVER. You're building intuition, mapping the landscape.

---

### 3. TARGETEDLY — Precision Strikes

Surgical precision. Exact phrase. Specific domain. Known author. Date range. File type.

**Command:**
```bash
picocloth search targeted "transformer architectures" \
  --exact "attention is all you need" \
  --domain arxiv.org \
  --author "Ashish Vaswani" \
  --filetype pdf \
  --execute --store
```

**What it does:**
- Exact phrase matching with noise exclusion
- Site-specific deep dives
- Author following (find everything by an expert)
- Date-bounded historical or recent search
- Filetype filtering (PDFs for papers, PPTX for slides, CSV for data)

**Query patterns:**
```
# Exact phrase
"exact phrase" -site:pinterest.com -site:medium.com

# Site-specific
site:arxiv.org "topic"
site:github.com "topic"

# Author following
"author name" "topic"
author:"author name" "topic"

# Date bounded
"topic" after:2025-01-01 before:2026-01-01
"topic" 2025

# Filetype
"topic" filetype:pdf
"topic" filetype:csv OR filetype:xlsx
```

**When to use:** You know WHERE or WHO or WHEN. You want precision, not breadth.

---

## The Hybrid Stack

For maximum knowledge yield, run all three in sequence:

```bash
picocloth search hybrid "your topic" --type technical --execute --store
```

**Phase 1: TARGETED** — Precision strikes on what you already suspect
**Phase 2: CLEVER** — Pattern-optimized discovery of what you know to look for  
**Phase 3: CURIOUS** — Exploratory sweep of what you don't know exists

This mirrors expert researcher behavior:
1. Check what you already know (targeted)
2. Systematically expand (clever)
3. Serendipitously discover (curious)

---

## Retrospective Optimization

Track what works. Double down. Build institutional search memory.

```bash
# See which search modes yield the most knowledge per query
picocloth search yield-report --topic "AI agents"
```

**Knowledge Yield Formula:**
```
Knowledge Yield = facts_extracted × avg_confidence / queries_count
```

**Weekly review questions:**
1. Which query patterns produced highest yield?
2. Which domains consistently produce high-confidence facts?
3. Which platforms underperform for our use cases?

Results feed back into query template optimization automatically.

---

## Academic Foundations

1. **Pirolli & Card (1999)** — Information Foraging Theory: experts follow scent trails to high-yield patches
2. **Schweiger & Cress (2019)** — PLOS ONE: source credibility moderates search behavior
3. **JMIR (2025)** — e64901: experts engage with fewer cues but higher frequency; focus on external references and dates
4. **Bioptic Agent (2025)** — 79.7% F1 via completeness-oriented search control vs Perplexity 44.2%
5. **LiveResearchBench (2025)** — multi-agent deep research outperforms single-agent on citation association
