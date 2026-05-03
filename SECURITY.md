# 🛡️ Security Policy

> *"Safety first. Curiosity second. Build third."* — Fleet Constitution, Rule 4

---

## API Keys and Credentials

**PicoCloth requires API keys to function.** These are stored in `node-*/config.json` files.

### ⚠️ CRITICAL: Before Making This Repo Public

1. **Verify `.gitignore` is working:**
   ```bash
   git check-ignore -v node-a/config.json
   # Should output: .gitignore:25:node-*/config.json node-a/config.json
   ```

2. **Do NOT commit real configs:**
   ```bash
   git status
   # node-*/config.json should NOT appear as "new file" or "modified"
   ```

3. **Use templates to generate configs:**
   ```bash
   cp node-a/config.json.example node-a/config.json
   # Edit node-a/config.json with your API key
   ```

4. **Rotate any exposed keys immediately** if they were ever committed.

### What Contains Secrets

| File | Secret Type | Gitignored? |
|------|-------------|-------------|
| `node-*/config.json` | xAI API keys | ✅ Yes |
| `node-*/home/config.json` | xAI API keys (copy) | ✅ Yes |
| `shared/state/langfuse-credentials.json` | Langfuse API keys | ✅ Yes |
| `linkedin-scraper/.env` | LinkedIn cookies | ✅ Yes |
| `shared/project/outreach/.env` | LinkedIn cookies | ✅ Yes |
| `linkedin-scraper/.env.example` | Template (no secrets) | ✅ Tracked |

---

## Reporting Security Issues

If you discover a security vulnerability in PicoCloth:

1. **DO NOT** open a public issue.
2. Email: `security@picocloth.dev` (or open a private security advisory on GitHub)
3. We will respond within 48 hours.
4. We follow responsible disclosure.

---

## Fleet Constitution Safety Rules

The fleet has built-in safety guardrails in `shared/doctrine/policies/fleet-constitution.md`:

- **Node Sovereignty:** No node can override another without approval
- **Append-Only Project Memory:** Facts cannot be deleted, only superseded
- **Safety First:** Dangerous operations require explicit approval
- **Subagent Limits:** Max depth 3, max concurrency 5, 30-second semaphore timeout
- **Graceful Degradation:** If a node fails, the fleet continues

---

## Shell Command Approval

By default, `shell` tool executions in PicoClaw require human approval. This is configured per-node in `config.json`:

```json
{
  "agents": {
    "defaults": {
      "approval_required_for_tools": ["shell", "spawn"]
    }
  }
}
```

Do not disable this in production without additional safeguards.

---

## Budget Guards

Per-node limits prevent runaway costs:

```json
{
  "agents": {
    "defaults": {
      "max_tokens": 2048,
      "max_tool_iterations": 3,
      "context_window": 32768
    }
  }
}
```

The `ram-optimized-launch.py` script sets conservative defaults. Increase only with intention.

---

> *"The safest fleet is one that assumes it will make mistakes."* 🛡️
