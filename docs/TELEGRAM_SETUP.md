# 📱 Telegram Setup for PicoCloth Fleet

## Quick Start

### Step 1: Create Telegram Bots

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Name your first bot (e.g., "PicoCloth Curiosity")
4. Choose a username (e.g., `yourname_curiosity_bot`)
5. **Save the HTTP API token!**
6. Repeat for Node-B (e.g., `yourname_builder_bot`)

### Step 2: Add Tokens to Config

Edit `node-a/config.json`:

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "bot_token": "YOUR_NODE_A_BOT_TOKEN_HERE",
      "allowed_chats": [],
      "auto_approve_chats": true
    }
  }
}
```

Edit `node-b/config.json` similarly with Node-B's token.

### Step 3: Test Connectivity

```bash
# Start the fleet
./scripts/launch-fleet.sh start

# Send a message to @yourname_curiosity_bot
# You should see activity in node-a/node.log
```

## Advanced: Single Bot with Agent Routing

Instead of 2 bots, you can use **ONE bot** and route messages:

```
User -> Telegram Bot -> PicoCloth Router -> Node-A or Node-B
```

This requires a small proxy service (included in future versions).

## Bot Commands

You can set these commands via @BotFather:

```
start - Initialize conversation
status - Show fleet health
spawn - Spawn a subagent
tasks - List active tasks
memory - Query shared memory
```

## Security Notes

- Never commit bot tokens to git
- Use `.security.yml` for sensitive data (PicoClaw v0.2.4+)
- Restrict `allowed_chats` to your own chat ID in production
- Get your chat ID: message @userinfobot

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Bot not responding | Check token, check node logs, verify gateway port |
| Webhook errors | PicoClaw uses long polling by default, no webhook needed |
| Messages delayed | Check `gateway.log_level` = debug for visibility |
| Can't find chat ID | Message @userinfobot on Telegram |
