"""Basic automod: banned-word filter, invite-link filter, mention-spam filter."""

import re

import discord
from discord.ext import commands

import db
from utils import is_staff, styled_embed, success_embed

INVITE_RE = re.compile(r"(discord\.gg|discord(?:app)?\.com/invite)/\S+", re.IGNORECASE)


class AutoMod(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    automod = discord.SlashCommandGroup("automod", "Configure automatic moderation")

    @automod.command(name="toggle", description="Enable or disable the banned-word filter")
    @is_staff()
    async def toggle(self, ctx: discord.ApplicationContext, enabled: bool):
        await db.update_guild_settings(ctx.guild.id, automod_enabled=enabled)
        await ctx.respond(embed=success_embed(f"Automod word filter is now {'enabled' if enabled else 'disabled'}."))

    @automod.command(name="anti_invite", description="Enable or disable blocking Discord invite links")
    @is_staff()
    async def anti_invite(self, ctx: discord.ApplicationContext, enabled: bool):
        await db.update_guild_settings(ctx.guild.id, anti_invite=enabled)
        await ctx.respond(embed=success_embed(f"Invite-link blocking is now {'enabled' if enabled else 'disabled'}."))

    @automod.command(name="anti_mention_spam", description="Enable or disable blocking messages with too many mentions")
    @is_staff()
    async def anti_mention_spam(self, ctx: discord.ApplicationContext, enabled: bool, threshold: int = 5):
        await db.update_guild_settings(
            ctx.guild.id, anti_mention_spam=enabled, mention_spam_threshold=threshold
        )
        await ctx.respond(
            embed=success_embed(
                f"Mention-spam blocking is now {'enabled' if enabled else 'disabled'} (threshold: {threshold})."
            )
        )

    @automod.command(name="addword", description="Add a word to the banned-word list")
    @is_staff()
    async def addword(self, ctx: discord.ApplicationContext, word: str):
        settings = await db.get_guild_settings(ctx.guild.id)
        words = set(settings["banned_words"] or [])
        words.add(word.lower())
        await db.update_guild_settings(ctx.guild.id, banned_words=list(words))
        await ctx.respond(embed=success_embed(f"Added `{word}` to the banned-word list."), ephemeral=True)

    @automod.command(name="removeword", description="Remove a word from the banned-word list")
    @is_staff()
    async def removeword(self, ctx: discord.ApplicationContext, word: str):
        settings = await db.get_guild_settings(ctx.guild.id)
        words = set(settings["banned_words"] or [])
        words.discard(word.lower())
        await db.update_guild_settings(ctx.guild.id, banned_words=list(words))
        await ctx.respond(embed=success_embed(f"Removed `{word}` from the banned-word list."), ephemeral=True)

    @automod.command(name="listwords", description="List the current banned words")
    @is_staff()
    async def listwords(self, ctx: discord.ApplicationContext):
        settings = await db.get_guild_settings(ctx.guild.id)
        words = settings["banned_words"] or []
        await ctx.respond(
            embed=styled_embed("Banned words", ", ".join(f"`{w}`" for w in words) or "None set."),
            ephemeral=True,
        )

    async def _log(self, guild: discord.Guild, description: str) -> None:
        settings = await db.get_guild_settings(guild.id)
        if settings["log_channel_id"]:
            channel = guild.get_channel(settings["log_channel_id"])
            if channel:
                await channel.send(embed=styled_embed("Automod Log", description))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.author.guild_permissions.manage_messages:
            return

        settings = await db.get_guild_settings(message.guild.id)

        if settings["automod_enabled"]:
            banned = settings["banned_words"] or []
            lowered = message.content.lower()
            if any(word in lowered for word in banned):
                await message.delete()
                await self._log(message.guild, f"Deleted banned word from {message.author} in {message.channel.mention}")
                try:
                    await message.author.send(
                        embed=styled_embed("Message removed", "Your message contained a word that isn't allowed here.")
                    )
                except discord.Forbidden:
                    pass
                return

        if settings["anti_invite"] and INVITE_RE.search(message.content):
            await message.delete()
            await self._log(message.guild, f"Deleted invite link from {message.author} in {message.channel.mention}")
            return

        if settings["anti_mention_spam"] and len(message.mentions) >= settings["mention_spam_threshold"]:
            await message.delete()
            await self._log(message.guild, f"Deleted mention-spam message from {message.author} ({len(message.mentions)} mentions)")
            return


def setup(bot: discord.Bot):
    bot.add_cog(AutoMod(bot))
