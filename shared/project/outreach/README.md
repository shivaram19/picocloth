# 🪶 PicoCloth Outreach Engine

> A fleet-powered LinkedIn outreach product built on the PicoCloth multi-agent architecture.

**No credentials stored. No manual scripting. Just a CSV and a command.**

---

## 🚀 What It Does

1. **Reads your targets** from a CSV file
2. **Researches each prospect** across the web (company, role, recent news, pain points)
3. **Generates personalized connection messages** — not templates, real hooks
4. **Sends connection requests** via stealth browser automation
5. **Records everything** to a durable shared memory layer

All orchestrated by the **PicoCloth Fleet** — four archetypes working together:

| Archetype | Role | File |
|-----------|------|------|
| 🔍 **Scout** | Deep web research, 5-source triangulation | `node_a.py` |
| 💌 **Messenger** | Personalized message crafting | `node_a.py` |
| 🚴 **Courier** | Stealth browser delivery with safety guards | `node_b.py` |
| 📚 **Archivist** | Shared memory, facts, entities, decisions | `archivist.py` |

---

## 📦 Installation

```bash
# 1. Clone or navigate to the outreach directory
cd shared/project/outreach

# 2. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 3. Create your .env file
cat > .env << EOF
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password
EOF
```

---

## 📝 Prepare Your Targets

Create a `targets.csv` file:

```csv
id,name,company,role,profile_url,industry,trigger_event,notes
kostya-rapina,Kostya Rapina,Powerkh,CEO,https://linkedin.com/in/kostya-rapina,VDC Construction,UK expansion,Boutique VDC firm
han-hoang,Han Hoang,THE BIM FACTORY,CEO,https://linkedin.com/in/han-hoang,VDC Consulting,C-DRIVE methodology,MIT alum
```

| Column | Description |
|--------|-------------|
| `id` | Unique identifier (lowercase, no spaces) |
| `name` | Full name |
| `company` | Company name |
| `role` | Job title |
| `profile_url` | LinkedIn profile URL |
| `industry` | Industry segment |
| `trigger_event` | Specific angle (expansion, funding, methodology, etc.) |
| `notes` | Additional context for the Scout |

---

## 🎯 Usage

### Full Pipeline (Research → Craft → Send)

```bash
python3 picocloth_outreach_engine.py --targets targets.csv --limit 5
```

The Orchestrator will:
1. Run the Scout to research each target
2. Run the Messenger to craft personalized messages
3. Check for a valid LinkedIn session
4. If no session → enter **Session Acquisition Mode** (see below)
5. If session exists → the Courier sends connection requests
6. The Archivist records everything

### Dry Run (Research + Craft, No Sending)

```bash
python3 picocloth_outreach_engine.py --targets targets.csv --dry-run --limit 5
```

Perfect for reviewing messages before sending.

### Research Only

```bash
python3 node_a.py --targets targets.csv --limit 5
```

### With Existing Session

```bash
python3 picocloth_outreach_engine.py --targets targets.csv --session linkedin_state.json --limit 5
```

---

## 🔐 Session Acquisition (One-Time Setup)

LinkedIn requires a valid browser session. The Orchestrator handles this automatically.

### Remote Server (No Display)

The Orchestrator will detect no display and provide instructions:

```bash
# On your LOCAL machine:
python3 session_exporter.py --output linkedin_state.json

# Upload to server:
scp linkedin_state.json user@server:/path/to/outreach/state/sessions/

# The Orchestrator auto-detects the file and continues
```

### Local Machine (With Display)

The Orchestrator auto-spawns the Session Exporter, which opens Chrome for you to log in.

### Session Persistence

Once created, the session is saved to `state/sessions/linkedin_state.json` and reused across runs. It typically lasts 1-2 weeks before needing refresh.

---

## 🧠 Shared Memory Architecture

The Archivist writes to four locations:

```
shared/project/
├── outreach/
│   ├── logs/outreach-facts.jsonl    # Durable facts from research
│   ├── state/sent.jsonl             # Every sent request (audit trail)
│   ├── state/queue.json             # Pending tasks
│   ├── state/stats.json             # Aggregate metrics
│   └── state/last_run_summary.json  # Last execution summary
├── entities/prospects.json          # Prospect registry
└── decisions/outreach-decisions.json # Fleet decision log
```

---

## 🛡️ Safety Guardrails

- **Daily limit**: 20 connection requests/day (configurable in `node_b.py`)
- **Human-like delays**: 20-60 seconds between requests
- **Stealth browser**: Playwright + anti-detection patches
- **Session-only**: No credentials stored, only session cookies
- **Screenshot evidence**: Every send is captured
- **Rate limiting**: Automatic pause if LinkedIn throttles

---

## 📊 Monitoring

Check the Archivist summary after each run:

```
📊 [Archivist] Fleet Memory Summary
============================================================
  Total targets:     5
  Researched:        5
  Messages drafted:  5
  Requests sent:     3
  Connected:         3
  Failed:            0
  Sent today:        3
============================================================
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│     PICOLOTH OUTREACH ENGINE            │
│                                         │
│  ┌─────────┐    ┌─────────┐            │
│  │ Node-A  │───►│ Node-B  │            │
│  │ (Scout) │    │(Courier)│            │
│  └────┬────┘    └────┬────┘            │
│       │              │                  │
│       └──────┬───────┘                  │
│              ▼                          │
│      ┌─────────────┐                    │
│      │ Orchestrator│                    │
│      └──────┬──────┘                   │
│             ▼                           │
│      ┌─────────────┐                    │
│      │  Archivist  │                    │
│      │ (Librarian) │                    │
│      └─────────────┘                    │
│                                         │
│  Shared Memory:                         │
│    ├── doctrine/  (read-only archetypes)│
│    ├── project/   (facts, entities)     │
│    ├── state/     (queue, sent log)     │
│    └── run/       (ephemeral sessions)  │
└─────────────────────────────────────────┘
```

---

## ⚠️ Known Limitations

1. **LinkedIn Checkpoint**: New IPs/datacenter IPs may trigger CAPTCHA on first login. The Session Exporter handles this gracefully.
2. **Rate Limits**: LinkedIn actively limits automation. The 20/day guardrail is conservative.
3. **Dynamic Selectors**: LinkedIn changes their HTML. Selectors in `node_b.py` may need updates.

---

## 📜 License

MIT — Built with PicoCloth. Respecting all existing digital twins.

---

*"The gap between good and best is bridged by curiosity."*
