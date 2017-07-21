import discord
from discord.ext import commands
import os
import threading
import asyncio
import logging
import subprocess
import json
import youtube_dl

from .music_player.downloader import music_cache_path, music_local_path
#from .config import *
log = logging.getLogger(__name__)


config_path = 'data/music/config.json'

try:
    if not discord.opus.is_loaded():
        discord.opus.load_opus('libopus-0.dll')
except OSError:  # Incorrect bitness
    opus = False
except:  # Missing opus
    opus = None
else:
    opus = True



class Music_Player:
    def __init__(self, bot, codec):
        self.bot = bot
        self.settings = json.load(open(config_path, 'r'))
        self.server_settings = ["VOLUME", "REPEAT"]
    #joins voice channel by channel id
    #def autojoin_channel(

    """ Plays a song
    With an argument:
        get song
        get server id

    """
    @commands.command(pass_context=True)
    async def play(self, ctx, *, song): # * = keyword only arg
        server = ctx.message.server
        voice_client = self.bot.voice_client_in(server)
        voice_client.music_player = voice_client.create_ffmpeg_player(music_local_path +
        '/Electropop/tyDi & Col3man ft. Melanie Fontana - That\'s How You Know.m4a')
        voice_client.music_player.start()

    @commands.command(pass_context=True)
    async def stop(self, ctx):
        server = ctx.message.server
        voice_client = self.bot.voice_client_in(server)
        voice_client.music_player.stop()

    #joins owners voice channel only
    @commands.command(pass_context=True)
    async def join_vc(self, ctx):
        author = ctx.message.author     #ctx = context
        server = ctx.message.server
        channel = author.voice_channel  #channel to join,


        if self.bot.is_voice_connected(server):
            voice_client = self.bot.voice_client_in(server)
            if voice_client.channel.id == author.voice_channel.id:
                await self.bot.say("Already connected to your channel!")
                return
            await voice_client.disconnect()
        await self.bot.join_voice_channel(channel)

    @commands.command(pass_context=True)
    async def leave_vc(self, ctx):
        server = ctx.message.server
        if self.bot.is_voice_connected(server):
            voice_client = self.bot.voice_client_in(server)
            await voice_client.disconnect()


    @commands.command()
    async def test(self):
        print(music_cache_path + '%(extractor)s' + '-' + '%(exts)s')
        str = music_cache_path + '%(extractor)s' + '-' + '%(exts)s'
        await self.bot.say(str)

    def start_player(server):
        temp=1
#class Music Player

"""startup checks"""
def check_cfg():
    default_cfg = {"VOLUME": .5,
                "VOTE_RATIO": .5,
                "VOTES_REQUIRED": 3,
                "REPEAT": True,
                "AUTOJOIN": True,
                "AUTOJOIN_CHANNELS": {},
                "SERVER_SETTINGS": {}
            }

    if not os.path.isfile(config_path):         #check and create config file
        print("Creating default audio config.json")
        config_file = open(config_path, 'w')
        json.dump(default_cfg, config_file, indent=4)

def check_ytdl():
    if youtube_dl is None:
        raise RuntimeError("You need to run `pip3 install youtube_dl`")
    if opus is False:
        raise RuntimeError(
            "Your opus library's bitness must match your python installation's"
            " bitness. They both must be either 32bit or 64bit.")
    elif opus is None:
        raise RuntimeError(
            "You need to install ffmpeg and opus. See \"https://github.com/"
            "Twentysix26/Red-DiscordBot/wiki/Requirements\"")

def check_codec():
    try:
        subprocess.call(["ffmpeg", "-version"], stdout=subprocess.DEVNULL)
    except FileNotFoundError:   #try fails, catch it
        player = False
    else:                       #try succeeds
        player = "ffmpeg"

    if not player:
        if os.name == "nt":
            msg = "ffmpeg isn't installed"
        else:
            msg = "Neither ffmpeg nor avconv are installed"
        raise RuntimeError(
          "{}.\nConsult the guide for your operating system "
          "and do ALL the steps in order.\n"
          "https://twentysix26.github.io/Red-Docs/\n"
          "".format(msg))
    return player


def setup(bot):
    check_cfg()
    check_ytdl()
    codec = check_codec()

    music_player = Music_Player(bot, codec=codec)  # Praise 26
    bot.add_cog(music_player)
    print('Starting Music Player with codec: ' + codec)
    """
    bot.add_listener(music_player.voice_state_update, 'on_voice_state_update')
    bot.loop.create_task(n.queue_scheduler())
    bot.loop.create_task(n.disconnect_timer())
    bot.loop.create_task(n.reload_monitor())
    bot.loop.create_task(n.cache_scheduler())
    """
#fn setup
