#!/usr/bin/env python3
"""
🎛️ The Orchestrator — Fleet Commander

Coordinates the PicoCloth Outreach Engine pipeline:

    Scout ──► Messenger ──► Courier ──► Archivist
       │          │            │            │
       └──────────┴────────────┴────────────┘
                    ▲
                    │
              Orchestrator

The Orchestrator is the nervous system. It decides which archetype
activates when. It handles failures. It retries. It never loses state.

NEW: Session Acquisition Mode
  When no valid LinkedIn session exists, the Orchestrator enters
  "Session Acquisition Mode" — it GUIDES the human through exporting
  a session, then automatically picks it up and continues.

  This is NOT a manual step. It is an ORCHESTRATED human-in-the-loop
  task managed by the Fleet Commander.

Archetype: Fleet Commander (Guardian + Explorer + Craftsman hybrid)
  - Protective of the mission (Guardian)
  - Adaptable when things go wrong (Explorer)
  - Builds robust pipelines (Craftsman)

Author: PicoCloth Fleet
Date: 2026-04-23
Purpose: Coordinate the Outreach Engine end-to-end.
"""

import json
import argparse
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

from archivist import Archivist, Decision
from node_a import run_node_a
from node_b import run_node_b

load_dotenv()

SESSION_FILE = Path(__file__).parent / "state" / "sessions" / "linkedin_state.json"
SESSION_TIMEOUT_SECONDS = 300  # 5 minutes to upload session


class Orchestrator:
    """
    The Orchestrator manages the full outreach pipeline.

    Pipeline Stages:
      1. INGEST    → Read targets.csv
      2. RESEARCH  → Scout enriches each target
      3. CRAFT     → Messenger writes personalized notes
      4. DELIVER   → Courier sends connection requests
      5. ARCHIVE   → Archivist records everything

    Session Acquisition Flow (NEW):
      If no session exists before DELIVER:
        a. Check if local display available
        b. If yes → auto-spawn Session Exporter
        c. If no  → print instructions, poll for upload
        d. Validate session once received
        e. Continue pipeline automatically

    Failure Handling:
      - If research fails for a target → skip it, log why, continue
      - If session expires mid-delivery → save state, pause, resume later
      - If daily limit reached → graceful stop, queue remaining
    """

    def __init__(self):
        self.archivist = Archivist()
        self.session_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        self.stage = "idle"
        print("\n" + "=" * 70)
        print("🎛️  PICOLOTH OUTREACH ORCHESTRATOR")
        print("=" * 70)
        print(f"Session: {self.session_id}")
        print("Archetypes: Scout + Messenger + Courier + Archivist")
        print("=" * 70 + "\n")

    def _log(self, msg: str):
        print(f"🎛️  [Orchestrator] {msg}")

    def _session_exists(self) -> bool:
        """Check if a session file exists."""
        return SESSION_FILE.exists() and SESSION_FILE.stat().st_size > 100

    def _display_available(self) -> bool:
        """Check if a display server is available for visible browser."""
        display = os.environ.get("DISPLAY")
        if display:
            return True
        # Check for Wayland
        if os.environ.get("WAYLAND_DISPLAY"):
            return True
        return False

    def _acquire_session(self, email: Optional[str], password: Optional[str]) -> bool:
        """
        Session Acquisition Mode.

        The Orchestrator manages the entire human-in-the-loop flow:
          - Detects no session
          - Provides instructions
          - Waits for session file
          - Validates automatically
          - Continues pipeline

        This is the GUIDE archetype in action: patient, clear, protective.
        """
        self._log("=" * 60)
        self._log("SESSION ACQUISITION MODE")
        self._log("=" * 60)
        self._log("No valid LinkedIn session found. The Orchestrator will")
        self._log("guide you through creating one. This takes ~2 minutes.")
        self._log("")

        # Record decision
        self.archivist.record_decision(Decision(
            decision_id=f"session-acq-{self.session_id}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            archetype="Orchestrator-Guide",
            context="No valid LinkedIn session before DELIVER stage",
            choice="Enter Session Acquisition Mode",
            rationale="Human-in-the-loop is required for initial session creation",
            expected_outcome="Valid session file appears in state/sessions/"
        ))

        # Check if we can auto-spawn exporter locally
        if self._display_available():
            self._log("🖥️  Display detected! Auto-spawning Session Exporter...")
            return self._spawn_local_exporter(email, password)

        # Remote server — provide instructions
        self._log("🌐 Remote server detected. Display not available.")
        self._log("")
        self._log("┌────────────────────────────────────────────────────────────┐")
        self._log("│  STEP 1: On your LOCAL machine, run this command:          │")
        self._log("│                                                            │")
        self._log("│  python3 session_exporter.py --output linkedin_state.json  │")
        self._log("│                                                            │")
        self._log("│  This will open Chrome. Log into LinkedIn, then press      │")
        self._log("│  ENTER. A file called 'linkedin_state.json' will be saved. │")
        self._log("│                                                            │")
        self._log("│  STEP 2: Upload the file to this server:                   │")
        self._log("│                                                            │")
        exporter_path = Path(__file__).parent / "session_exporter.py"
        session_dest = SESSION_FILE
        self._log(f"│  scp linkedin_state.json user@server:{session_dest}         │")
        self._log("│                                                            │")
        self._log("│  STEP 3: The Orchestrator will auto-detect the file        │")
        self._log("│          and continue the pipeline.                        │")
        self._log("└────────────────────────────────────────────────────────────┘")
        self._log("")

        # Also copy the exporter script to a known location for the user
        self._log(f"📄 Session Exporter script: {exporter_path}")
        self._log("")

        # Poll for session file
        return self._poll_for_session()

    def _spawn_local_exporter(self, email: Optional[str], password: Optional[str]) -> bool:
        """Spawn the Session Exporter locally (requires display)."""
        exporter_path = Path(__file__).parent / "session_exporter.py"
        if not exporter_path.exists():
            self._log(f"❌ Session Exporter not found: {exporter_path}")
            return False

        cmd = [
            "python3", str(exporter_path),
            "--output", str(SESSION_FILE),
        ]
        if email:
            cmd.extend(["--email", email])
        if password:
            cmd.extend(["--password", password])

        self._log("🚀 Spawning Session Exporter...")
        try:
            result = subprocess.run(cmd, timeout=120)
            if result.returncode == 0 and self._session_exists():
                self._log("✅ Session exported successfully!")
                return True
        except subprocess.TimeoutExpired:
            self._log("⏰ Session Exporter timed out.")
        except Exception as e:
            self._log(f"❌ Session Exporter failed: {e}")

        return False

    def _poll_for_session(self) -> bool:
        """Poll for session file upload. The Orchestrator waits patiently."""
        self._log(f"⏳ Polling for session file: {SESSION_FILE}")
        self._log(f"   Timeout: {SESSION_TIMEOUT_SECONDS}s")
        self._log("")

        start = time.time()
        dots = 0
        while time.time() - start < SESSION_TIMEOUT_SECONDS:
            if self._session_exists():
                self._log("")
                self._log("🎉 SESSION FILE DETECTED!")
                self._log("🔍 Validating session...")

                # Quick validation: check if it has cookies
                try:
                    with open(SESSION_FILE, "r") as f:
                        state = json.load(f)
                    cookie_count = len(state.get("cookies", []))
                    if cookie_count > 0:
                        self._log(f"✅ Session valid! {cookie_count} cookies found.")
                        return True
                    else:
                        self._log("⚠️  Session file has no cookies. Waiting for correct file...")
                except json.JSONDecodeError:
                    self._log("⚠️  Invalid session file. Waiting for correct file...")

            # Progress indicator
            dots = (dots + 1) % 4
            print(f"\r🎛️  [Orchestrator] Waiting for session upload{'.' * dots}{' ' * (3-dots)}", end="", flush=True)
            time.sleep(2)

        self._log("")
        self._log("⏰ Session acquisition timed out.")
        self._log("   Please upload the session file and re-run.")
        return False

    def run(self, targets_csv: str, limit: int = 0,
            headless: bool = True, dry_run: bool = False,
            email: Optional[str] = None, password: Optional[str] = None) -> dict:
        """
        Run the complete outreach pipeline.

        Returns a summary dict for the Archivist to record.
        """
        start_time = datetime.now(timezone.utc)
        self._log(f"Pipeline starting. Targets: {targets_csv} | Limit: {limit or 'all'} | Dry run: {dry_run}")

        # ── Stage 1: INGEST ──────────────────────────────────────────────────
        self.stage = "ingest"
        self._log("Stage 1: INGEST — Reading targets...")

        if not Path(targets_csv).exists():
            self._log(f"❌ Targets file not found: {targets_csv}")
            return {"status": "failed", "error": f"File not found: {targets_csv}"}

        # ── Stage 2: RESEARCH + CRAFT (Node-A) ───────────────────────────────
        self.stage = "research"
        self._log("Stage 2: RESEARCH + CRAFT — Activating Scout & Messenger...")

        enriched = run_node_a(targets_csv, self.archivist, limit=limit)

        if not enriched:
            self._log("❌ No targets enriched. Pipeline halted.")
            return {"status": "failed", "error": "No targets enriched"}

        self._log(f"✅ {len(enriched)} targets enriched and messaged.")
        self.archivist.update_stats(messaged=len(enriched))

        # ── Stage 2.5: SESSION ACQUISITION (if needed) ───────────────────────
        if not dry_run:
            self._log("Stage 2.5: SESSION CHECK — Ensuring Courier has keys...")
            if not self._session_exists():
                self._log("🔑 No session found. Entering Session Acquisition Mode.")
                acquired = self._acquire_session(email, password)
                if not acquired:
                    self._log("❌ Session acquisition failed. Cannot proceed to DELIVER.")
                    self._log("   Research results are saved. You can re-run once session is available.")
                    # Still return partial success since research completed
                    return {
                        "status": "partial",
                        "stage_reached": "session_acquisition_failed",
                        "targets_researched": len(enriched),
                        "note": "Research complete. Session needed for delivery."
                    }
            else:
                self._log("✅ Existing session found. Courier is ready.")

        # ── Stage 3: DELIVER (Node-B) ────────────────────────────────────────
        self.stage = "deliver"
        self._log("Stage 3: DELIVER — Activating Courier...")

        if dry_run:
            self._log("🧪 DRY RUN MODE: No actual messages sent.")

        results = run_node_b(
            enriched,
            self.archivist,
            email=email,
            password=password,
            headless=headless,
            dry_run=dry_run
        )

        # ── Stage 4: ARCHIVE ─────────────────────────────────────────────────
        self.stage = "archive"
        self._log("Stage 4: ARCHIVE — Recording final state...")

        # Calculate summary
        success = sum(1 for r in results if r.status == "success")
        failed = sum(1 for r in results if r.status == "failed")
        skipped = sum(1 for r in results if r.status in ["skipped", "already_connected"])
        dry = sum(1 for r in results if r.status == "dry_run")

        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        summary = {
            "session_id": self.session_id,
            "started_at": start_time.isoformat(),
            "finished_at": end_time.isoformat(),
            "duration_seconds": duration,
            "status": "success" if success > 0 else "partial" if dry_run else "failed",
            "targets_total": len(enriched),
            "sent_success": success,
            "sent_failed": failed,
            "skipped": skipped,
            "dry_run": dry_run,
            "daily_sent": self.archivist.get_sent_count_today(),
        }

        self.archivist.update_stats(
            sent=success,
            failed=failed,
            connected=success
        )

        # Write final summary to state
        summary_file = Path(__file__).parent / "state" / "last_run_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        self._log(f"✅ Pipeline complete in {duration:.1f}s")
        self._log(f"   Success: {success} | Failed: {failed} | Skipped: {skipped}")

        # Print Archivist summary
        self.archivist.print_summary()

        self.stage = "complete"
        return summary


def main():
    parser = argparse.ArgumentParser(
        description="🪶 PicoCloth Outreach Engine — Fleet-Powered LinkedIn Outreach"
    )
    parser.add_argument("--targets", default="targets.csv",
                        help="Path to targets CSV file")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max targets to process (0 = all)")
    parser.add_argument("--headless", action="store_true", default=True,
                        help="Run browser headless (default: True)")
    parser.add_argument("--visible", action="store_true",
                        help="Run browser visible (overrides --headless)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Research and craft messages but don't send")
    parser.add_argument("--email", default=os.getenv("LINKEDIN_EMAIL"),
                        help="LinkedIn email (or set LINKEDIN_EMAIL env var)")
    parser.add_argument("--password", default=os.getenv("LINKEDIN_PASSWORD"),
                        help="LinkedIn password (or set LINKEDIN_PASSWORD env var)")
    parser.add_argument("--session", default=None,
                        help="Path to saved session JSON (skips session acquisition)")
    args = parser.parse_args()

    headless = not args.visible

    # If session provided, copy it to expected location
    if args.session:
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy(args.session, SESSION_FILE)
        print(f"🎛️  Session copied: {args.session} → {SESSION_FILE}")

    # Run the pipeline
    orch = Orchestrator()
    result = orch.run(
        targets_csv=args.targets,
        limit=args.limit,
        headless=headless,
        dry_run=args.dry_run,
        email=args.email,
        password=args.password
    )

    # Exit code based on result
    if result.get("status") == "success":
        return 0
    elif result.get("status") == "partial":
        return 0
    else:
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
