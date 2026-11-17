# BigBois Discord Bot & Server Provisioner

Idempotent Discord REST provisioner for **BigBois SMP** (`1572300325786747040`) and bridge configuration for `Discord-MC-Chat` (`DMCC 3.0.0-beta.3`).

## Setup
1. Save your Discord Bot Token to `~/.config/keys/discord_bot_token` (`chmod 600`).
2. Run:
   ```bash
   python3 provision.py
   ```
   The script is idempotent — it creates missing categories/channels/roles, updates read-only permissions, and populates welcome, rules, modpack download links, cross-play guides, and game-bot invite links.
