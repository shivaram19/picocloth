# LinkedIn Outreach Automation — VDC Document Intelligence

End-to-end LinkedIn automation for the VDC Document Intelligence go-to-market campaign.

---

## ⚠️ Disclaimer

LinkedIn automation violates their [Terms of Service](https://www.linkedin.com/legal/user-agreement). This tool is for educational and research purposes only. Use at your own risk.

---

## 🆕 BREAKTHROUGH: Carbonyl + Playwright Integration

**You can now SEE the browser in your terminal while the bot controls it programmatically.**

### How It Works

1. **Carbonyl** renders Chromium as Unicode characters in your terminal
2. **Playwright** connects to Carbonyl via Chrome DevTools Protocol (CDP)
3. You WATCH LinkedIn render in real-time while the bot automates clicks, typing, scrolling
4. If LinkedIn shows a CAPTCHA or 2FA, you see it in the terminal and complete it

### Architecture

```
Terminal Window
├── Carbonyl renders LinkedIn as colored blocks
│   ├── You see: login form, feed, profile pages
│   └── You can: watch, verify, intervene if needed
│
└── Playwright (via CDP on port 9222)
    ├── Navigates to profiles
    ├── Fills login forms
    ├── Clicks "Connect" buttons
    └── Types personalized messages
```

---

## Quick Start — Carbonyl Mode (Recommended)

### Step 1: Start Carbonyl in Terminal 1

```bash
carbonyl --remote-debugging-port=9222 about:blank
```

You'll see a blank browser in your terminal. Leave this running.

### Step 2: Find the CDP URL

```bash
curl -s http://localhost:9222/json/version | jq -r '.webSocketDebuggerUrl'
# Output: ws://localhost:9222/devtools/browser/xxxxx-xxxxx
```

### Step 3: Run the bot in Terminal 2

```bash
cd ~/tinkering/tinkering-with-claws/picocloth/shared/project/tools/linkedin-scraper
source venv/bin/activate

# Dry run first (preview only)
python3 carbonyl_bot.py --cdp-url ws://localhost:9222/devtools/browser/xxxxx --dry-run --limit 2

# Live run with credentials
python3 carbonyl_bot.py --cdp-url ws://localhost:9222/devtools/browser/xxxxx --limit 2 \
  --email your@email.com --password yourpassword
```

### What You'll See

- **Terminal 1**: Carbonyl shows LinkedIn loading, login form appearing, profile pages scrolling
- **Terminal 2**: Bot logs actions: "Navigating to Kostya Rapina's profile", "Clicking Connect", "Message sent"

If LinkedIn asks for verification, you **see it in Terminal 1** and can complete it manually.

---

## Alternative: Auto-Launch Mode

Let the bot start Carbonyl for you:

```bash
python3 carbonyl_bot.py --auto-launch --dry-run --limit 2
```

**Note:** Carbonyl takes over the terminal with escape sequences. You may want to run it inside `tmux` or `screen` so you can detach and reattach.

---

## Alternative: Headless Mode (No Terminal Browser)

If you prefer the bot to run silently with screenshots:

```bash
python3 outreach_bot_v2.py --dry-run --limit 2 --headless
```

Screenshots are auto-saved to `screenshots/` for review.

---

## Alternative: Session Export (Fastest Long-Term)

Log in once on your local machine, export session, reuse forever:

```bash
# On your LOCAL machine (laptop):
python3 export_session.py
# → Log into LinkedIn manually
# → Press ENTER

# Upload to server:
scp linkedin_state.json server:~/.../linkedin-scraper/

# On server:
python3 outreach_bot_v2.py --limit 2 --headless
```

---

## File Reference

| File | Purpose | Status |
|------|---------|--------|
| `carbonyl_bot.py` | **Carbonyl + Playwright bot** — see browser in terminal | ✅ Ready |
| `outreach_bot_v2.py` | Playwright bot with screenshots + session persistence | ✅ Ready |
| `outreach_bot.py` | Original Selenium bot | ✅ Ready |
| `export_session.py` | Export LinkedIn session from local machine | ✅ Ready |
| `scraper_fast.py` | Fast profile scraper with `--attach` mode | ✅ Ready |
| `targets.json` | 5 VDC contacts with personalized messages | ✅ Ready |
| `test_outreach_bot.py` | Test suite (8 tests, all pass) | ✅ Ready |

---

## Target List

| # | Name | Company | Priority | Message Ready |
|---|------|---------|----------|--------------|
| 1 | Kostya Rapina | Powerkh | 🔴 High | ✅ |
| 2 | Han Hoang | THE BIM FACTORY | 🔴 High | ✅ |
| 3 | Ajith Menon | BIMAGE Consulting | 🟡 Medium | ✅ |
| 4 | Tristen Magallanes | DPR Construction | 🟡 Medium | ✅ |
| 5 | David Antony | Flatworld Solutions | 🟢 Low | ✅ |

---

## Approaches Compared

See `APPROACHES_COMPARISON.md` for detailed analysis of all 6 approaches explored:

| Approach | See Browser? | Complexity | Best For |
|----------|-------------|-----------|----------|
| **Carbonyl + Playwright** | ✅ Terminal | Medium | **This use case** |
| Session Export | ❌ No | Low | Long-term reuse |
| Chrome Attach | ✅ Local Chrome | Medium | Chrome power users |
| VNC | ✅ Full desktop | High | Persistent remote desktop |
| Headless + Screenshots | ❌ No | Low | Background automation |

---

## Safety Features

- Daily limit: 20 connections
- Random delays between actions
- Dry-run mode for previewing
- Screenshot logging for audit trail

---

## Troubleshooting

### "Failed to setup terminal" (Carbonyl)
Some terminal emulators don't support the escape sequences Carbonyl uses. Try a different terminal or use `tmux`.

### CDP connection refused
Make sure Carbonyl is running with `--remote-debugging-port=9222` and you copied the full WebSocket URL.

### Terminal looks garbled after Carbonyl
Run `reset` to restore terminal state.

### Want to run Carbonyl in background
```bash
tmux new-session -d -s carbonyl 'carbonyl --remote-debugging-port=9222 about:blank'
# Then attach: tmux attach -t carbonyl
```
