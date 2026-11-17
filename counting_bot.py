#!/usr/bin/env python3
"""Lightweight #counting minigame bot for BigBois SMP."""

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

intents = discord.Intents.default()
intents.message_content = True
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
    print(f"Counting bot ready as {client.user}")


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
