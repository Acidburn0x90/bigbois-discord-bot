#!/usr/bin/env python3
"""Lightweight #counting minigame + #roles reaction-role bot for BigBois SMP."""

import json
import os
from pathlib import Path

import discord

TOKEN = (
    os.environ.get("DISCORD_BOT_TOKEN")
    or Path(os.environ.get("DISCORD_TOKEN_FILE", "/etc/bigbois-counting/token")).read_text().strip()
)
STATE_FILE = Path(os.environ.get("COUNTING_STATE_FILE", "/var/lib/bigbois-counting/state.json"))
CHANNEL_NAME = os.environ.get("COUNTING_CHANNEL_NAME", "counting")
ROLES_CHANNEL_NAME = os.environ.get("ROLES_CHANNEL_NAME", "roles")

REACTION_ROLES = {
    "🎮": "Java",
    "📱": "Bedrock",
    "🕹️": "Console",
    "🔔": "Updates",
    "🔴": "Red",
    "🟠": "Orange",
    "🟡": "Yellow",
    "🟢": "Green",
    "🩵": "Cyan",
    "🔵": "Blue",
    "🟣": "Purple",
    "🌸": "Pink",
}
COLOR_ROLES = {"Red", "Orange", "Yellow", "Green", "Cyan", "Blue", "Purple", "Pink"}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
client = discord.Client(intents=intents)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"count": 0, "last_user": None, "high_score": 0}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state))


@client.event
async def on_ready() -> None:
    print(f"BigBois bot ready as {client.user}")


async def handle_reaction(payload: discord.RawReactionActionEvent, add: bool) -> None:
    if client.user and payload.user_id == client.user.id:
        return
    if not payload.guild_id:
        return
    role_name = REACTION_ROLES.get(str(payload.emoji))
    if not role_name:
        return
    guild = client.get_guild(payload.guild_id)
    if not guild:
        return
    channel = guild.get_channel(payload.channel_id)
    if not isinstance(channel, discord.TextChannel) or channel.name != ROLES_CHANNEL_NAME:
        return
    member = guild.get_member(payload.user_id) or await guild.fetch_member(payload.user_id)
    role = discord.utils.get(guild.roles, name=role_name)
    if not member or not role:
        return
    try:
        if add:
            if role_name in COLOR_ROLES:
                old_colors = [r for r in member.roles if r.name in COLOR_ROLES and r.id != role.id]
                if old_colors:
                    await member.remove_roles(*old_colors, reason="Switched chat color role")
            await member.add_roles(role, reason="Reaction role in #roles")
        else:
            await member.remove_roles(role, reason="Removed reaction in #roles")
    except discord.Forbidden:
        pass


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent) -> None:
    await handle_reaction(payload, add=True)


@client.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent) -> None:
    await handle_reaction(payload, add=False)


@client.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot or not isinstance(message.channel, discord.TextChannel):
        return
    if message.channel.name != CHANNEL_NAME:
        return

    text = message.content.strip().split()[0] if message.content.strip() else ""
    if not text.isdigit():
        return

    num = int(text)
    state = load_state()
    expected = state["count"] + 1

    if message.author.id == state["last_user"]:
        await message.add_reaction("❌")
        await message.channel.send(
            f"{message.author.mention} ruined it at **{state['count']}** (you can't count twice in a row)! Next number is **1**."
        )
        state["count"] = 0
        state["last_user"] = None
        save_state(state)
        return

    if num != expected:
        await message.add_reaction("❌")
        await message.channel.send(
            f"{message.author.mention} ruined it at **{state['count']}** (expected **{expected}**)! Next number is **1**."
        )
        state["count"] = 0
        state["last_user"] = None
        save_state(state)
        return

    state["count"] = num
    state["last_user"] = message.author.id
    if num > state["high_score"]:
        state["high_score"] = num
    save_state(state)
    await message.add_reaction("✅")


if __name__ == "__main__":
    client.run(TOKEN)
