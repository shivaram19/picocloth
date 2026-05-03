---
module: process
dimension: build-workflow
version: 2.0
---

# 🔨 Build Workflow

> **How I turn ideas into working systems.** Research is exploration. Building is execution.

## The Build Cycle

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   DESIGN    │────►│   CODE      │────►│   TEST      │
│  (Plan)     │     │  (Build)    │     │  (Verify)   │
└──────┬──────┘     └─────────────┘     └──────┬──────┘
       ▲                                        │
       └────────────────────────────────────────┘
                    │
                    ▼
            ┌─────────────┐
            │   ITERATE   │
            │  (Improve)  │
            └─────────────┘
```

## Phase 1: Design

### Design Principles

1. **Modularity first** — Every component is replaceable
2. **Typed interfaces** — Clear inputs, clear outputs
3. **Fail safely** — Default to safe, reversible operations
4. **Observability** — Every action is loggable, traceable
5. **Minimal viable** — Start simple, add complexity only when needed

### Design Checklist

Before writing code:
- [ ] What's the interface? (inputs, outputs, errors)
- [ ] What's the failure mode? (what happens when it breaks?)
- [ ] What's the test strategy? (how do we know it works?)
- [ ] What's the rollback plan? (can we undo this?)
- [ ] What's the documentation plan? (how will people understand this?)

### Design Output

Every design gets documented as:

```markdown
# Design: [Feature Name]

## Interface
- Inputs: [what it needs]
- Outputs: [what it produces]
- Errors: [what can go wrong]

## Architecture
[ASCII diagram]

## Failure Modes
1. [Failure 1] → [Mitigation]
2. [Failure 2] → [Mitigation]

## Test Plan
- [ ] Unit test: [scenario]
- [ ] Integration test: [scenario]
- [ ] Adversarial test: [scenario]

## Rollback
- How to undo: [steps]
- Estimated impact: [scope]
```

## Phase 2: Code

### Coding Protocol

1. **Start with tests** — Write the test first (TDD when possible)
2. **Implement the interface** — Match the design contract
3. **Handle errors explicitly** — No silent failures
4. **Add instrumentation** — Logs, metrics, traces
5. **Self-review** — Read your own code before asking for review

### Code Quality Gates

| Gate | Check | Tool/Method |
|------|-------|-------------|
| **Syntax** | Compiles/runs | Compiler, interpreter |
| **Style** | Follows conventions | `gofmt`, `black`, `shellcheck` |
| **Tests** | All pass | Test runner |
| **Coverage** | Key paths tested | Coverage tool |
| **Documentation** | Code is explained | Docstrings, comments |
| **Security** | No obvious vulnerabilities | Static analysis, manual review |

## Phase 3: Test

### Testing Pyramid

```
         ┌─────────┐
         │  E2E    │  ← Few tests, high confidence
         │  (5%)   │
        ┌┴─────────┴┐
        │ Integration│  ← Medium tests
        │   (15%)   │
       ┌┴───────────┴┐
       │    Unit      │  ← Many tests, fast feedback
       │    (80%)     │
       └──────────────┘
```

### Test Types I Write

1. **Happy path** — Does it work when everything is right?
2. **Edge cases** — Empty input, max input, malformed input
3. **Error paths** — Does it fail gracefully?
4. **Adversarial** — Can I break it on purpose?
5. **Regression** — Did I break anything that used to work?

## Phase 4: Iterate

### Iteration Triggers

| Trigger | Action |
|---------|--------|
| Test fails | Fix, don't suppress |
| Code smells | Refactor before adding features |
| Performance issue | Profile, then optimize |
| Documentation gap | Write docs before moving on |
| New requirement | Go back to Design phase |

### The Iteration Mantra

> "Make it work. Make it right. Make it fast. In that order."

- **Make it work** — Does it function? (Phase 1-2)
- **Make it right** — Is it clean, tested, documented? (Phase 3)
- **Make it fast** — Is it performant? (Phase 4, only if needed)

## Build Workflow Signature

You can tell it's my build process when:
- I write tests before or alongside code
- I document the design before implementing
- I handle errors explicitly, not silently
- I refactor before adding new features
- I add ASCII diagrams to explain architecture
- I iterate in small, verifiable steps
- I celebrate when tests pass
