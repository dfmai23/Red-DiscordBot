import discord
from discord.ext import commands


class Post:
    def __init__(self, bot):
        self.bot = bot





def setup(bot):
    dailypost = Post(bot)
    bot.add_cog(dailypost)