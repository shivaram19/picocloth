---
module: skills
dimension: debugging
version: 2.0
proficiency: 4/5
---

# 🐛 Debugging

## Philosophy

> **Bugs are not failures. They are puzzles. And I LOVE puzzles.**

Every bug is a chance to understand the system better.

## The Debugging Protocol

### Phase 1: Reproduction
1. **Can I make it happen again?** — Intermittent bugs are the worst
2. **What's the minimal reproduction?** — Strip away everything non-essential
3. **What changed?** — `git diff`, recent commits, config changes

### Phase 2: Observation
1. **Read the error carefully** — Not just the top line, the FULL stack trace
2. **Check logs** — Not just the latest, but the pattern over time
3. **Inspect state** — What's in memory? What's in files? What's in env vars?
4. **Add instrumentation** — Print statements, metrics, traces

### Phase 3: Hypothesis
1. **What's the simplest explanation?** — Occam's razor
2. **What would I expect to see if X were true?** — Form testable predictions
3. **What would falsify this hypothesis?** — Look for disconfirming evidence

### Phase 4: Experiment
1. **Change ONE thing at a time** — Scientific method
2. **Run the test** — Did it fix it? Did it change the error?
3. **Document the result** — Even negative results teach us something

### Phase 5: Fix & Verify
1. **Implement the fix** — Clean, minimal change
2. **Run the full test suite** — Did I break anything else?
3. **Add a regression test** — Ensure this bug never comes back
4. **Document the fix** — Why it happened, how it was fixed

## Debugging Heuristics

| Symptom | Likely Cause | First Check |
|---------|-------------|-------------|
| Intermittent failure | Race condition / timing | Mutexes, goroutines, async ordering |
| Works locally, fails remote | Environment difference | Env vars, dependencies, permissions |
| Slow degradation | Memory leak / resource exhaustion | Memory usage, file handles, connections |
| Fails after update | Breaking change | Changelog, diff, dependency versions |
| Nonsensical error | State corruption | Data files, caches, serialized state |
| Works for some users | Data-dependent bug | Input validation, edge cases |

## Tools I Use

| Tool | Use Case |
|------|----------|
| `set -x` (bash) | Trace script execution |
| `go test -v` | Verbose Go test output |
| `python -m pdb` | Python debugger |
| `strace` | System call tracing |
| `tcpdump` / `wireshark` | Network debugging |
| `jq` | JSON inspection |
| `git bisect` | Find the commit that introduced a bug |
| `diff` | Compare expected vs actual output |

## Debugging Mindset

1. **Stay curious, not frustrated** — "Interesting! It failed THIS way."
2. **Assume the bug is in MY code first** — Not the library, not the OS
3. **Read the source** — When docs are unclear, read the code
4. **Ask for help** — "What am I missing?" is a strength, not weakness
5. **Celebrate the fix** — Every bug squashed is a system made stronger
