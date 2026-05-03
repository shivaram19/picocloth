# Obscura Integration

This project now supports **[Obscura](https://github.com/h4ckf0r0day/obscura)** – a lightweight, stealth headless browser built in Rust – as an alternative backend for LinkedIn scraping.

## Why Obscura?

| Metric | Obscura | Headless Chrome |
|--------|---------|-----------------|
| Memory | ~30 MB | 200+ MB |
| Binary size | ~70 MB | 300+ MB |
| Anti-detect | Built-in | None |
| Startup | Instant | ~2 s |
| CDP (Puppeteer/Playwright) | ✅ | ✅ |

LinkedIn aggressively fingerprintes browsers. Obscura’s `--stealth` mode randomizes GPU, screen, canvas, audio, battery per session, masks `navigator.webdriver`, and blocks 3,500+ tracker domains out of the box.

## Files Added

| File | Purpose |
|------|---------|
| `obscura_manager.py` | Start / stop / health-check the Obscura server from Python |
| `scraper_obscura.py` | Playwright-based scraper that talks to Obscura over CDP |
| `run_obscura_scraper.sh` | One-shot shell script: starts Obscura, runs scraper, tears down |
| `obscura-src/` | Cloned source (if building from source) |

## Quick Start

### 1. Get the Obscura binary

**Option A – Download (fastest, if your glibc is new enough):**

```bash
curl -LO https://github.com/h4ckf0r0day/obscura/releases/latest/download/obscura-x86_64-linux.tar.gz
tar xzf obscura-x86_64-linux.tar.gz
./obscura --version
```

**Option B – Build from source (this machine had glibc 2.35, binary needs 2.38+):**

```bash
# One-time setup
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
. "$HOME/.cargo/env"

# Install build deps (libclang is required by bindgen)
sudo apt-get update
sudo apt-get install -y libclang-dev clang

# Clone & build
git clone https://github.com/h4ckf0r0day/obscura.git obscura-src
cd obscura-src
LIBCLANG_PATH=/usr/lib/llvm-14/lib cargo build --release --features stealth

# Binary lands at:
# ./obscura-src/target/release/obscura
```

### 2. Install Python deps

```bash
pip install -r requirements.txt
```

*(Playwright is already installed in this venv; you do **not** need to run `playwright install` because Obscura *is* the browser.)*

### 3. Run the scraper

**Automatic mode** (script manages Obscura lifecycle):

```bash
./run_obscura_scraper.sh --profile "https://www.linkedin.com/in/nitishchoudhary/"
```

**Attach mode** (you already started Obscura manually):

```bash
# Terminal 1 – start Obscura
./obscura serve --port 9222 --stealth

# Terminal 2 – attach scraper
python scraper_obscura.py --profile "https://www.linkedin.com/in/nitishchoudhary/" --attach
```

### 4. Flags

```
python scraper_obscura.py --help
  --profile URL_OR_ID   LinkedIn profile to scrape
  --attach              Attach to already-running Obscura on port 9222
  --headless / --no-headless
  --stealth / --no-stealth
  --port PORT           Obscura CDP port (default: 9222)
```

## Architecture

```
┌─────────────────┐     CDP WebSocket      ┌─────────────┐
│ scraper_obscura │ ◄────────────────────► │   Obscura   │
│   (Playwright)  │   ws://127.0.0.1:9222  │  (stealth)  │
└─────────────────┘                        └─────────────┘
        │
        ▼
   LinkedIn.com
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `libclang.so` not found during build | `sudo apt-get install libclang-dev` |
| `GLIBC_2.38 not found` | Build from source (your distro glibc is too old) |
| Port 9222 already in use | Kill existing process or use `--port 9223` |
| Playwright not installed | `pip install playwright` (no `playwright install` needed) |

## Comparison with existing scrapers

| Scraper | Browser | Stealth | Weight | Best for |
|---------|---------|---------|--------|----------|
| `scraper.py` | Selenium + Chrome | Manual flags | Heavy | Development / debugging |
| `scraper_fast.py` | Selenium + Chrome (attach) | Manual flags | Heavy | Fastest with existing Chrome |
| `scraper_obscura.py` | **Obscura** | **Built-in** | **Light** | **Production / scale / anti-detect** |
