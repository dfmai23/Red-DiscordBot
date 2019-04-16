import discord
from discord.ext import commands
import traceback
import os
import asyncio
import json
import time
import urllib.request
import re

from .utils.chat_formatting import *
from .utils import checks

default_cfg = {
    "SERVER_SETTINGS": {}
}

default_server_cfg = {
    "server_name": "undefined",
    "EMBEDDEDS": {}
}

#format
test = {
    "SERVER_SETTINGS": {
        "server_id": {
            "server_name": "name",
            "EMBEDDEDS": {
                "embed_name": "location"
            }
        }
    }
}
config_path = 'data\gif\\'
config_file = 'config.json'

class GIF:
    def __init__(self, bot):
        self.bot = bot
        self.settings = {}
        self.server_settings = {}

    @commands.command(pass_context=True)
    async def set_gif(self, ctx, gifname, link):
        """ Add an embedded gifs"""
        server = ctx.message.server
        gifs = self.server_settings[server.id]["EMBEDDEDS"]

        is_url = re.compile(r'^(?:http)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?))' #domain
        r'(?:/?(.*\.(gif)?))$', re.IGNORECASE)  #gif sub path
        sub_pattern = r'(webm|gifv)$'

        match = re.match(is_url, link)
        if match is None:
            print('could not find a valid link: ' + link)
            await self.bot.say('Could not find a valid link. Try Again!~')
            return

        if gifname not in gifs:
            #will download the link locally
            # if match.group(2) != 'gif': #convert non gif formats to gif
            #     print('link not given in gif format, attempting to convert')
            #     newlink = re.sub(sub_pattern, 'gif', link)
            #     match = re.match(is_url, newlink)
            #     print('oldlink: %s\nnewlink: %s' % (link, newlink))
            filename = match.group(1)  # get gif file, https://regex101.com/r/6uKlDz/2/
            location = config_path + server.id + '\\' + filename
            # file, headers = urllib.request.urlretrieve(link, location)
            gifs[gifname] = location
            print('added gif, gifname: %s   link: %s\npath: %s' % (gifname, link, location))
            # print('headers: ' + str(headers)) #html headers
            await self.bot.say('Saved the gif %s!~' % gifname)
        else:
            print('key already found: ' + gifname)
            print(gifs[gifname])
            await self.bot.say('GIF already saved! Use a different name!~')

    @commands.command(pass_context=True)
    async def gif(self, ctx, gifname):
        """ Use the embedded gif"""
        server = ctx.message.server
        channel = ctx.message.channel

        gifs = self.server_settings[server.id]["EMBEDDEDS"]
        if gifname not in gifs:
            await self.bot.say('Could not find gif!~')
            return
        gif_loc = gifs[gifname]
        await self.bot.send_file(channel, gif_loc)

    @commands.command(pass_context=True)
    async def view_gifs(self, ctx):
        """ List the embedded gifs"""
        server = ctx.message.server

        print("--------------------view gifs--------------------")
        gifs = self.server_settings[server.id]["EMBEDDEDS"]
        gifs_display = []
        print(gifs)
        for gifname, giflink in gifs.items():
            gifs_display.append(gifname)
        await self.bot.say('The current gifs are: ' + box('') if len(gifs)==0 else box(', '.join(gifs_display)), delete_after=60)


    """————————————————————Helper Fn's————————————————————"""
    def save_config(self):      #save config for current server
        cfg_file = open(config_path + config_file, 'w')
        json.dump(self.settings, cfg_file, indent=4) #in:self.settings, out:file
        print('Saving GIFBot config')


    """————————————————————INIT————————————————————"""
    def init_settings(self):
        print('--------------------GIF Bot--------------------')
        print('Loading GIFBot ettings')
        fullpath = config_path + config_file
        if not os.path.isdir(config_path):  #check directory
            print('  config path: \'%s\' not found creating new one' % config_path)
            os.makedirs(config_path)
        if not os.path.isfile(fullpath):    #check file
            file = open(fullpath, 'w')
            file.close()
        if os.path.getsize(fullpath) == 0:  #check if file empty
            print('  config SETTINGS in file: \'%s\' not found creating them' % fullpath)
            file = open(fullpath, 'w')
            self.settings = default_cfg
            file.close()
            self.save_config()

        file = open(fullpath, 'r+')
        self.settings = json.load(file)
        self.server_settings = self.settings["SERVER_SETTINGS"]
        file.close()

        for server in self.bot.servers:
            if not os.path.isdir(config_path + server.id): #check server directory
                print('  Server folder for %s not found, creating default: %s' % (server.name, config_path + server.id))
                os.makedirs(config_path + server.id)
            if not server.id in self.server_settings:   #create new default server settings
                print('  Server settings for %s %s not found, creating defaults' % (server.id, server.name))
                self.server_settings[server.id] = default_server_cfg
                self.server_settings[server.id]["server_name"] = server.name
        self.save_config()


def setup(bot):
    gif = GIF(bot)
    bot.add_cog(gif)

    try:
        gif.init_settings()
        # bot.loop.create_task(gif.init_scheduler())
    except Exception as e:
        time_string = time.strftime("%H:%M:%S", time.localtime())  # strip using time
        traceback.print_exc()
        print("[%s] Exception: %s" % (time_string, (str(e))))
# setup