import discord
import os
import subprocess
import json
import youtube_dl

from .paths import *

"""startup checks"""
def check_cfg():
    if not os.path.isfile(config_path):         #check and create config file
        print("Creating default music player config.json")
        config_file = open(config_path, 'w')
        json.dump(default_cfg, config_file, indent=4)
    if not os.path.isdir(music_cache_path):
        print('Creating music cache folder')
        os.makedirs(music_cache_path)
    if not os.path.isdir(playlist_path):
        print('Creating /playlists folder')
        os.makedirs(playlist_path)

def check_ytdl():
    try:
        if not discord.opus.is_loaded():
            discord.opus.load_opus('libopus-0.dll')
    except OSError:  # Incorrect bitness
        opus = False
    except:  # Missing opus
        opus = None
    else:
        opus = True

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
