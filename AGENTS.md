# Agent Guidelines (`bigbois-discord-bot`)

- **Never commit tokens:** Read bot credentials exclusively from `~/.config/keys/discord_bot_token` (`0600`) or `DISCORD_BOT_TOKEN`.
- **Idempotency:** `provision.py` must check existing channels/roles/messages before creating or posting so re-runs never duplicate channels or spam embeds.
- **Read-only channels:** Always include an explicit user overwrite for the bot (`SEND_MESSAGES | EMBED_LINKS`) whenever denying `SEND_MESSAGES` to `@everyone`.
