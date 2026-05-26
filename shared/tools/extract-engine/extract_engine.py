#!/usr/bin/env python3
"""
PicoCloth Extract Engine — Standalone Compatibility Shim
=========================================================
This file provides backward compatibility for direct execution.
The canonical implementation lives in picocloth_cli.tools.extract.

If picocloth-cli is installed, this shim imports and delegates.
Otherwise, it falls back to an inline minimal engine.

Usage:
  python extract_engine.py --input search-results.json --topic "AI market" --output facts.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Try canonical import first
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "picocloth-cli" / "src"))
    from picocloth_cli.tools.extract import ExtractEngine
    HAS_CANONICAL = True
except ImportError:
    HAS_CANONICAL = False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PicoCloth Extract Engine — structured knowledge extraction",
    )
    parser.add_argument("--input", "-i", required=True, help="Input JSON file")
    parser.add_argument("--output", "-o", default="facts.jsonl", help="Output file")
    parser.add_argument("--topic", "-t", default="", help="Query topic")
    parser.add_argument("--tier", default="hybrid", choices=["fast", "deep", "hybrid"])
    parser.add_argument("--min-confidence", type=float, default=0.0)
    parser.add_argument("--md", action="store_true", help="Output Markdown")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    results = data if isinstance(data, list) else data.get("results", data.get("organic", []))

    if HAS_CANONICAL:
        engine = ExtractEngine(tier=args.tier)
        facts, report = engine.run(results, query_topic=args.topic)
        facts = [f for f in facts if f.confidence >= args.min_confidence]
        engine.facts = facts
        if args.md:
            engine.to_markdown(args.output)
        else:
            engine.to_jsonl(args.output)
        print(json.dumps({
            "extracted": len(facts),
            "avg_confidence": report.avg_confidence,
            "elapsed_seconds": report.elapsed_seconds,
        }))
    else:
        # Minimal fallback: just echo structured snippets
        out_facts = []
        for r in results:
            url = r.get("href") or r.get("link") or r.get("url", "")
            snippet = r.get("body", r.get("snippet", r.get("description", "")))
            out_facts.append({
                "fact_id": str(hash(snippet + url))[:16],
                "topic": args.topic,
                "triple": {"entity": args.topic, "relation": "mentions", "claim": snippet[:200]},
                "confidence": 0.3,
                "extraction_tier": "fallback",
            })
        with open(args.output, "w", encoding="utf-8") as f:
            for fact in out_facts:
                f.write(json.dumps(fact) + "\n")
        print(json.dumps({"extracted": len(out_facts), "engine": "fallback"}))

    return 0


if __name__ == "__main__":
    sys.exit(main())
