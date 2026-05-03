# 🪶 PicoCloth Outreach Engine

## A Fleet-Powered LinkedIn Outreach Product

Built on the PicoCloth multi-agent fleet architecture. Uses existing Node-A (Curiosity Brain) and Node-B (Executor) without modifying their digital twins.

---

## 🏛️ Architecture

```
shared/project/outreach/
├── ARCHITECTURE.md          # This file
├── targets.csv              # CSV input (prospects to reach)
├── picocloth_outreach_engine.py  # Main entrypoint
├── node_a.py                # Curiosity Brain — research & enrichment
├── node_b.py                # Executor — browser automation
├── orchestrator.py          # Fleet coordination
├── capture_session.html     # One-time session capture (run locally)
├── enriched/                # Node-A output (enriched profiles)
├── state/
│   ├── sessions/            # LinkedIn cookie jars
│   ├── sent.jsonl           # Log of sent requests
│   ├── queue.json           # Pending task queue
│   └── stats.json           # Aggregate metrics
├── logs/                    # Per-run execution logs
└── screenshots/             # Evidence captures
```

---

## 🤖 Fleet Roles

### Node-A: Curiosity Brain (Research & Enrichment)

```yaml
role: outreach_researcher
archetype: Explorer-Builder (Openness 0.90, Conscientiousness 0.83)
behaviors:
  - Reads targets.csv and identifies knowledge gaps
  - Web-researches each prospect (company, role, recent activity)
  - Generates personalized connection messages using voice profile
  - Writes enriched profiles to shared/project/outreach/enriched/
  - Extracts durable facts to shared/project/facts/outreach-facts.jsonl
  - Tags prospects as entities in shared/project/entities/prospects.json
```

### Node-B: Executor (Browser Automation)

```yaml
role: outreach_executor
archetype: Builder (Conscientiousness 0.83, Extraversion 0.84)
behaviors:
  - Reads enriched targets from shared memory
  - Loads LinkedIn session from state/sessions/
  - Validates session health (feed check)
  - Sends connection requests with personalized notes
  - Respects daily limits (20/day), adds human-like delays
  - Logs every action to state/sent.jsonl
  - Captures screenshots for evidence
  - Reports completion to orchestrator
```

---

## 🧠 Shared Memory Integration

### Input: `targets.csv`
```csv
name,company,role,profile_url,industry,trigger_event
Kostya Rapina,Powerkh,CEO,https://www.linkedin.com/in/kostya-rapina/,VDC Construction,UK expansion
```

### Output Layer 1: `enriched/{id}.json`
Node-A writes enriched prospect data including:
- Research summary (3-5 bullet points)
- Personalized message (300 chars max)
- Confidence score (0.0-1.0)
- Source citations

### Output Layer 2: `state/sent.jsonl`
Node-B appends every action:
```json
{"timestamp":"2026-04-23T18:00:00Z","target_id":"kostya-rapina","action":"connect_sent","status":"success","screenshot":"screenshots/001_kostya.png"}
```

### Output Layer 3: Shared Project Facts
```jsonl
// shared/project/facts/outreach-facts.jsonl
{"type":"prospect_fact","entity":"Powerkh","content":"Boutique VDC firm, 20+ staff, expanding to UK","confidence":0.92,"source":"web_research","extracted_at":"2026-04-23T18:00:00Z"}
```

### Output Layer 4: Entity Registry
```json
// shared/project/entities/prospects.json
{"prospects":[{"id":"kostya-rapina","name":"Kostya Rapina","company":"Powerkh","status":"connected","enriched":true,"last_contact":"2026-04-23"}]}
```

---

## 🔐 Session Model (Zero-Credential Storage)

**Design principle:** We NEVER store user credentials. We ONLY store session cookies.

```
User opens Brave → Logs into LinkedIn → Runs capture_session.html
                        │
                        ▼
              Copies cookie JSON
                        │
                        ▼
              Pastes into server: state/sessions/linkedin.json
                        │
                        ▼
              Bot validates session → Proceeds autonomously
```

Session validation: Navigate to `/feed/`. If URL contains "feed", session is valid.

---

## 📊 Observability

Every action is logged in PicoCloth format:
- `logs/engine-{timestamp}.jsonl` — full execution trace
- `state/stats.json` — aggregate counters
- Screenshots saved with descriptive names

Compatible with Langfuse tracing via the existing `langfuse_bridge.py` hook.

---

## 🚀 Usage

### One-Time Setup
```bash
# User runs this ONCE on their local machine
cd shared/project/outreach
# Open capture_session.html in Brave, follow instructions
# Paste resulting JSON to state/sessions/linkedin.json
```

### Run Outreach
```bash
# Full pipeline: research → enrich → send
python3 picocloth_outreach_engine.py --targets targets.csv --limit 5

# Research only (Node-A)
python3 node_a.py --targets targets.csv --output-dir enriched/

# Send only (Node-B, assumes enriched/ exists)
python3 node_b.py --input-dir enriched/ --session state/sessions/linkedin.json
```

---

## 🛡️ Safety Guardrails

- Daily connect limit: 20 (configurable)
- Minimum delay between requests: 20s (randomized 20-60s)
- Session expiry check before every action
- Screenshot capture on every send for evidence
- Dry-run mode available
- No credential storage — sessions only

---

*Built with PicoCloth. Respecting all existing digital twins.*
