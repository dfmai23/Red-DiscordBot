import discord
from discord.ext import commands


class GIF:
    def __init__(self, bot):
        self.bot = bot




def setup(bot):
    gif = GIF(bot)
    bot.add_cog(gif)