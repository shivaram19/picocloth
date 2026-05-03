---
title: VDC Document Intelligence Doctrine
version: 1.0
author: Trelo Labs / PicoCloth Fleet
project: DOWNTOWN OFFICE TOWER
date: 2026-04-24
---

# VDC Document Intelligence Fleet Doctrine

## Mission
Deploy and operate the Trelo Labs VDC Document Intelligence system across a 2-node PicoCloth fleet. Node-A researches and queries construction documents. Node-B executes backend operations and drafts RFI responses.

## Characters (Document Entities)

| Character ID | Name | Role | Type |
|-------------|------|------|------|
| arch-drawing-notes | A-101 | Design Visionary | ARCH |
| fire-protection-spec | FPS-211313 | Safety Guardian | SPEC |
| mech-spec-hvac | MECH-HVAC | Climate Controller | SPEC |
| rfi-log | RFI-LOG | Question Keeper | LOG |
| struct-spec | STRUCT-CIP | Structure Engineer | SPEC |

## Node Responsibilities

### Node-A: Document Curiosity Brain
- Research document content and cross-references
- Identify contradictions between drawings and specs
- Query the document knowledge base
- Spawn subagents for deep-dive analysis
- **Digital Twin**: Before every compaction, extract document insights and save to shared/project/facts/

### Node-B: Document Executor Builder
- Run the Flask backend (localhost:5001)
- Seed sample documents into the vector database
- Draft RFI responses with cited sources
- Perform contradiction scans
- Deploy frontend (localhost:8080)
- **Digital Twin**: Before every compaction, extract execution patterns and save to shared/project/facts/

## Skills

### 1. Multi-Document RAG Query
Upload an entire project's document set and ask natural language questions. Every answer must be grounded in uploaded documents with citations.

### 2. RFI Response Drafting
Paste an RFI question. The AI scans all project documents and drafts a professional response with cited sources (spec section, drawing sheet, code reference).

### 3. Contradiction Detection
AI automatically scans drawings and specifications to flag:
- Dimension mismatches
- Conflicting requirements
- Code discrepancies
- Finish schedule inconsistencies

## Digital Twin Protocol

Before every context compaction (at 75% context usage):
1. Extract up to 8 durable facts about the documents
2. Save a full conversation snapshot to shared/digital-twins/
3. Update shared/project/facts/ with document insights
4. Emit an event to the fleet EventBus
5. Preserve character relationship knowledge

## Safety Rules
1. No rm -rf on project directories
2. All shell commands that modify files require approval
3. Backend must be started before frontend
4. Sample docs must be seeded before querying
5. Digital twins are immutable after creation
