#!/usr/bin/env python3
"""Idempotent Discord server provisioner for BigBois SMP."""

import json
import os
import urllib.request
from pathlib import Path

GUILD_ID = os.environ.get("DISCORD_GUILD_ID", "1572300325786747040")
TOKEN = (
    os.environ.get("DISCORD_BOT_TOKEN")
    or Path(os.environ.get("DISCORD_TOKEN_FILE", "/etc/bigbois-counting/token")).read_text().strip()
    if Path(os.environ.get("DISCORD_TOKEN_FILE", "/etc/bigbois-counting/token")).exists()
    else Path.home().joinpath(".config/keys/discord_bot_token").read_text().strip()
)
API = "https://discord.com/api/v10"
GITHUB_RELEASE_API = "https://api.github.com/repos/Acidburn0x90/bigbois-mc-server/releases/latest"


def get_latest_release_assets() -> tuple[str, dict[str, str]]:
    r = urllib.request.Request(GITHUB_RELEASE_API, headers={"User-Agent": "BigBoisSMP/1.0"})
    with urllib.request.urlopen(r, timeout=15) as resp:
        data = json.loads(resp.read())
    tag = data.get("tag_name", "v26.3-1.0.0")
    assets = {a["name"]: a["browser_download_url"] for a in data.get("assets", [])}
    return tag, assets


def req(method: str, path: str, payload: dict | None = None) -> dict | list:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "User-Agent": "BigBoisSMP/1.0",
        "Content-Type": "application/json",
    }
    r = urllib.request.Request(f"{API}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=20) as resp:
        body = resp.read()
        return json.loads(body) if body else {}


def replace_bot_embed(channel_id: str, embed: dict) -> None:
    """Delete previous bot messages in channel so only the latest message remains."""
    for m in req("GET", f"/channels/{channel_id}/messages?limit=25"):
        if m.get("author", {}).get("bot"):
            try:
                req("DELETE", f"/channels/{channel_id}/messages/{m['id']}")
            except urllib.error.HTTPError:
                pass
    req("POST", f"/channels/{channel_id}/messages", {"embeds": [embed]})


def main() -> None:
    guild = req("GET", f"/guilds/{GUILD_ID}")
    if guild.get("name") != "Minecraft Server":
        try:
            req("PATCH", f"/guilds/{GUILD_ID}", {"name": "Minecraft Server"})
        except urllib.error.HTTPError:
            pass

    existing_channels = req("GET", f"/guilds/{GUILD_ID}/channels")
    by_name = {c["name"]: c for c in existing_channels}

    existing_roles = req("GET", f"/guilds/{GUILD_ID}/roles")
    roles_by_name = {r["name"]: r for r in existing_roles}
    everyone_id = roles_by_name["@everyone"]["id"]

    for rname, color in [
        ("Player", 0x3BA55D),
        ("Java", 0xE67E22),
        ("Bedrock", 0x5865F2),
        ("Console", 0x9B59B6),
        ("Updates", 0x1ABC9C),
    ]:
        if rname not in roles_by_name:
            req("POST", f"/guilds/{GUILD_ID}/roles", {"name": rname, "color": color, "mentionable": True})

    bot_id = req("GET", "/users/@me")["id"]
    # Read-only for @everyone (deny SEND_MESSAGES=2048); allow bot SEND_MESSAGES+EMBED_LINKS (18432)
    ro_overwrites = [
        {"id": everyone_id, "type": 0, "allow": "0", "deny": "2048"},
        {"id": bot_id, "type": 1, "allow": "18432", "deny": "0"},
    ]

    def ensure_cat(name: str, pos: int) -> str:
        if name in by_name and by_name[name]["type"] == 4:
            return by_name[name]["id"]
        c = req("POST", f"/guilds/{GUILD_ID}/channels", {"name": name, "type": 4, "position": pos})
        by_name[name] = c
        return c["id"]

    def ensure_ch(name: str, ctype: int, parent_id: str, topic: str = "", ro: bool = False, pos: int | None = None) -> str:
        if name in by_name and by_name[name]["type"] == ctype:
            patch = {}
            if by_name[name].get("parent_id") != parent_id:
                patch["parent_id"] = parent_id
            if pos is not None and by_name[name].get("position") != pos:
                patch["position"] = pos
            if patch:
                req("PATCH", f"/channels/{by_name[name]['id']}", patch)
            return by_name[name]["id"]
        payload = {"name": name, "type": ctype, "parent_id": parent_id}
        if topic:
            payload["topic"] = topic
        if ro:
            payload["permission_overwrites"] = ro_overwrites
        if pos is not None:
            payload["position"] = pos
        c = req("POST", f"/guilds/{GUILD_ID}/channels", payload)
        by_name[name] = c
        return c["id"]

    cat_start = ensure_cat("👋 START HERE", 0)
    ch_welcome = ensure_ch("welcome-and-info", 0, cat_start, "Server IP, cross-play setup & quick start", ro=True, pos=0)
    ch_rules = ensure_ch("rules", 0, cat_start, "Community & SMP rules", ro=True, pos=1)
    ch_roles = ensure_ch("roles", 0, cat_start, "Grab your Java / Bedrock / Console / Updates roles", ro=True, pos=2)
    ensure_ch("announcements", 0, cat_start, "Server updates & maintenance notices", ro=True, pos=3)

    cat_packs = ensure_cat("📦 MODPACKS & GUIDES", 1)
    ch_modpacks = ensure_ch("modpacks", 0, cat_packs, "Direct downloads for Lite / Standard / Ultra 26.3 packs", ro=True, pos=0)
    ch_crossplay = ensure_ch("crossplay-guide", 0, cat_packs, "How to join from Switch, Xbox, PlayStation, Mobile & PC", ro=True, pos=1)
    ch_changes = ensure_ch("server-changes", 0, cat_packs, "Every non-vanilla tweak, recipe, mod, and command on the server", ro=True, pos=2)

    cat_mc = ensure_cat("⛏️ MINECRAFT", 2)
    ensure_ch("mc-chat", 0, cat_mc, "Live 2-way chat bridge with BigBois Fabric 26.3", pos=0)
    ensure_ch("mc-status", 0, cat_mc, "Server start/stop notifications", ro=True, pos=1)
    ensure_ch("coords-and-builds", 0, cat_mc, "Base coordinates, farms & screenshots", pos=2)
    ensure_ch("suggestions", 0, cat_mc, "Mod, plugin, and server ideas", pos=3)
    ensure_ch("bug-reports", 0, cat_mc, "Connection, mod, or cross-play issues", pos=4)

    cat_games = ensure_cat("🎮 GAMES & BOTS", 3)
    ch_bots = ensure_ch("bot-commands", 0, cat_games, "Bot commands & game-bot setup", pos=0)
    ensure_ch("counting", 0, cat_games, "Count up from 1 without breaking the streak", pos=1)
    ensure_ch("trivia-and-games", 0, cat_games, "Discord minigames & trivia", pos=2)

    cat_comm = ensure_cat("💬 COMMUNITY", 4)
    ensure_ch("general", 0, cat_comm, "General hangout", pos=0)
    ensure_ch("clips-and-highlights", 0, cat_comm, "Clips and highlights", pos=1)
    ensure_ch("memes", 0, cat_comm, "Memes and screenshots", pos=2)

    cat_vc = by_name["Voice Channels"]["id"]
    ensure_ch("Minecraft VC", 2, cat_vc)
    afk_id = ensure_ch("AFK", 2, cat_vc)
    try:
        req("PATCH", f"/guilds/{GUILD_ID}", {"afk_channel_id": afk_id, "afk_timeout": 900})
    except urllib.error.HTTPError:
        pass

    replace_bot_embed(ch_rules, {
        "title": "BigBois SMP Rules",
        "color": 0xE74C3C,
        "description": (
            "1. **Be respectful** — no harassment, hate speech, or drama.\n"
            "2. **No griefing or stealing** — respect builds, chests, and farms.\n"
            "3. **No cheating/exploits** — X-ray, duping, or lag machines will get you banned.\n"
            "4. **Keep it clean** — use the right channels (`#mc-chat` bridges directly into in-game chat!)."
        ),
    })

    replace_bot_embed(ch_crossplay, {
        "title": "How to Join (Java, Bedrock & Consoles)",
        "color": 0x9B59B6,
        "description": (
            "**PC — Java Edition (`1.8` – `26.3`):**\n"
            "• Multiplayer → Add Server → **`mc.bigbois.live`**\n\n"
            "**Mobile / Windows Bedrock:**\n"
            "• Play → Servers → Add Server → Address: **`mc.bigbois.live`** | Port: **`19132`**\n\n"
            "**Nintendo Switch / Xbox / PlayStation:**\n"
            "• Set your console's primary DNS to **BedrockConnect** (`104.238.130.180`, secondary `1.1.1.1`), join any featured server, and enter **`mc.bigbois.live`** port **`19132`**.\n"
            "• No Java account needed (Floodgate handles login)."
        ),
    })

    tag, assets = get_latest_release_assets()
    def link(name: str, fallback: str) -> str:
        return assets.get(name, f"https://github.com/Acidburn0x90/bigbois-mc-server/releases/download/{tag}/{fallback}")

    replace_bot_embed(ch_modpacks, {
        "title": f"Download BigBois Modpacks ({tag})",
        "color": 0x5865F2,
        "description": (
            "**1. Lite (`28` mods · `32 MiB`)** — Max FPS + JEI, Jade, AppleSkin, JourneyMap:\n"
            f"• [CurseForge (.zip)]({link('bigbois-lite-26.3.zip', 'bigbois-lite-26.3.zip')}) · [Modrinth / Prism (.mrpack)]({link('bigbois-lite-26.3.mrpack', 'bigbois-lite-26.3.mrpack')})\n\n"
            "**2. Standard (`53` mods · `46 MiB`)** — Lite + Continuity, BetterGrassify, Dynamic Lights, Zoomify:\n"
            f"• [CurseForge (.zip)]({link('bigbois-standard-26.3.zip', 'bigbois-standard-26.3.zip')}) · [Modrinth / Prism (.mrpack)]({link('bigbois-standard-26.3.mrpack', 'bigbois-standard-26.3.mrpack')})\n\n"
            "**3. Ultra DH+Shaders (`55` mods · `75 MiB`)** — Standard + Distant Horizons (`128` dynamic LODs) + Iris + MakeUp-UltraFast:\n"
            f"• [CurseForge (.zip)]({link('bigbois-ultra-dh-shaders-26.3.zip', 'bigbois-ultra-dh-shaders-26.3.zip')}) · [Modrinth / Prism (.mrpack)]({link('bigbois-ultra-dh-shaders-26.3.mrpack', 'bigbois-ultra-dh-shaders-26.3.mrpack')})\n\n"
            "*How to import:* In CurseForge click **Import** → select the `.zip` (or in Prism Launcher drag-and-drop the `.mrpack`)."
        ),
    })

    replace_bot_embed(ch_roles, {
        "title": "Self-Assignable Roles",
        "color": 0x1ABC9C,
        "description": (
            "Roles created: `@Player`, `@Java`, `@Bedrock`, `@Console`, `@Updates`.\n"
            "Once you invite **Carl-bot** (see `#bot-commands`), bind reaction roles to this message!"
        ),
    })

    replace_bot_embed(ch_bots, {
        "title": "Installed Bots & Features",
        "color": 0xF1C40F,
        "description": (
            "• **Carl-bot** — Reaction Roles in `#roles` & Welcome Cards\n"
            "• **Pokétwo** — Catch Pokémon in `#trivia-and-games`\n"
            "• **BigBois Bot** — `#mc-chat` 2-way Minecraft bridge & `#counting` minigame"
        ),
    })

    replace_bot_embed(ch_changes, {
        "title": "Non-Vanilla Server Changes & Features",
        "color": 0x2ECC71,
        "description": (
            "**Gameplay & Custom Recipes**\n"
            "• **Smoker Recipe:** Cook `Rotten Flesh` in a **Smoker** → `Leather` (`100` ticks, `0.1` XP, visible in JEI)\n"
            "• **Veinminer:** Mine entire ore veins at once (works with Fortune/Silk Touch; **only** initial ore costs durability, `0` extra hunger)\n"
            "• **Tree Harvester:** Fell whole trees with fast leaf decay & auto-replanted saplings (**only** initial log costs durability, `0` extra hunger)\n"
            "• **World Rules:** **Hard** difficulty · **Keep Inventory** enabled in all dimensions · **1-Player Sleep** (`players_sleeping_percentage = 0`)\n\n"
            "**Cross-Play, LODs & Discord**\n"
            "• **Any Version / Any Console:** Java `1.8`–`26.3` (`ViaFabric` + `ViaBackwards` + `ViaRewind`) & Bedrock/Switch/Xbox/PS (`Geyser` + `Floodgate`)\n"
            "• **World & LODs:** `100`-chunk spawn pre-generated + **Distant Horizons `128`-chunk** dynamic per-player LOD streaming + **JourneyMap** world sync\n"
            "• **Voice & Tab:** **Simple Voice Chat** (`24454/udp`, optional client mod) + **TabTPS** (live TPS/MSPT/ping in Tab)\n"
            "• **Discord Link:** Run **`/dmcc link`** in Discord to link your Minecraft IGN for in-game `@mention` pings\n"
            "• **Protection:** `Ledger` block/chest logging + daily `04:00` backups (3-backup rotation)"
        ),
    })

    print("Provisioned BigBois SMP successfully.")


if __name__ == "__main__":
    main()
