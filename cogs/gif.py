import discord
from discord.ext import commands
import traceback
import os
import asyncio
import json
import time
import urllib.request
import re
import pprint
import copy

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
    async def add_gif(self, ctx, gifname, link):
        """ Add an embedded gifs """
        server = ctx.message.server
        gifs = self.server_settings[server.id]["EMBEDDEDS"]

        print("--------------------set gifs--------------------")
        is_url = re.compile(r'^(?:http)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?))' #domain
        r'(?:/?(.*\.(gif|webm)?))$', re.IGNORECASE)  #gif sub path
        # r'(?:/?|[/?]\S+)$', re.IGNORECASE)  # any sub-path
        # sub_pattern = r'(webm|gifv)$'
        sub_pattern = re.compile(r'(webm)$')

        match = re.match(is_url, link)
        if match is None:
            print('could not find a valid link: ' + link)
            await self.bot.say('Could not find a valid link. Try Again!~')
            return

        if gifname not in gifs:
            #will download the link locally
            newlink=link
            if match.group(2) != 'gif': #convert webm formats to gif
                print('link not given in gif format, attempting to convert')
                newlink = re.sub(sub_pattern, 'gif', link)
                match = re.match(is_url, newlink)
                print('oldlink: %s\nnewlink: %s' % (link, newlink))
            # filename = match.group(1)  # get gif file, https://regex101.com/r/6uKlDz/2/
            # location = config_path + server.id + '\\' + filename

            location = match.string
            # file, headers = urllib.request.urlretrieve(link, location)
            gifs[gifname] = location
            print('added gif, gifname: %s   link: %s' % (gifname, newlink))
            # print('added gif, gifname: %s   link: %s\npath: %s' % (gifname, link, location))    #for local files
            # print('headers: ' + str(headers)) #html headers
            await self.bot.say('Saved the gif %s!~' % gifname)
        else:
            print('key already found: ' + gifname)
            print(gifs[gifname])
            await self.bot.say('GIF already saved! Use a different name!~')

    @commands.command(pass_context=True)
    async def remove_gif(self, ctx, gifname):
        """ Removes gif from server """
        print("--------------------REMOVE GIF--------------------")
        server = ctx.message.server

        gifs = self.server_settings[server.id]["EMBEDDEDS"]
        if gifname not in gifs:
            print('key not found: ' + gifname)
            await self.bot.say('GIF not found!~')
        else:
            print('removed gif: %s %s' %(gifname, str(gifs[gifname])))
            gifs.pop(gifname)
            await self.bot.say('GIF successfully removed!~')

    @commands.command(pass_context=True)
    async def gif(self, ctx, gifname):
        """ Use the embedded gif """
        server = ctx.message.server
        channel = ctx.message.channel

        gifs = self.server_settings[server.id]["EMBEDDEDS"]
        if gifname not in gifs:
            await self.bot.say('Could not find gif!~')
            return
        link = gifs[gifname]
        embed = discord.Embed()
        embed.set_image(url=link)
        await self.bot.send_message(channel, embed=embed)
        # await self.bot.send_file(channel, gif_loc)

    @checks.mod_or_permissions(administrator=True)
    @commands.command(pass_context=True)
    async def sayg(self, ctx, link):
        """ DEBUG: post gif """
        server = ctx.message.server
        channel = ctx.message.channel

        time_string = time.strftime("%H:%M:%S", time.localtime())  # strip using time
        print("[%s]------------SAYG--------------------" % time_string)
        print('link: ' + link)
        embed = discord.Embed()
        embed.set_image(url=link)
        print('title: ' + str(embed.title))
        print('type: ' + str(embed.type))
        print('url: ' + str(embed.url))
        print('descr: ' + str(embed.description))
        print('image: ' + str(embed.image))
        print('image.url: ' + str(embed.image.url))
        print('proxy.url: ' + str(embed.image.proxy_url))
        print('dim: %s x %s' % (str(embed.image.height), str(embed.image.width)))
        print('thumbnail.url: ' + str(embed.thumbnail.url))
        print('video: ' + str(embed.video))
        message = await self.bot.send_message(channel, embed=embed)
        # message = await self.bot.send_message(channel, content=link)

        # message = await self.bot.get_message(channel, link)
        print('\ntimestamp: ' + str(message.timestamp))
        print('content: ' + message.content)
        print('embeds: ')
        for emb in message.embeds:
            for field in emb.items():
                print('  ' + str(field))

    @commands.command(pass_context=True)
    async def view_gifs(self, ctx):
        """ List the embedded gifs """
        server = ctx.message.server

        print("--------------------view gifs--------------------")
        gifs = self.server_settings[server.id]["EMBEDDEDS"]
        gifs_display = []
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(gifs)
        for gifname, giflink in gifs.items():
            gifs_display.append(gifname)
        await self.bot.say('The current gifs are: ' + box('') if len(gifs)==0 else box(', '.join(gifs_display)), delete_after=60)

    @checks.mod_or_permissions(administrator=True)
    @commands.command(pass_context=True)
    async def save_gifs(self, ctx):
        """ Save the current embedded gifs """
        self.save_config()
        print("--------------------SAVE GIFS--------------------")
        await self.bot.say('Saved gif bot settings!~')

    @checks.mod_or_permissions(administrator=True)
    async def gstat(self, ctx):
        """ DEBUG, show settings """
        print("--------------------G STAT--------------------")
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(self.settings)


    """————————————————————Helper Fn's————————————————————"""
    def save_config(self):      #save config for current server
        cfg_file = open(config_path + config_file, 'w')
        json.dump(self.settings, cfg_file, indent=4) #in:self.settings, out:file
        print('Saving GIFBot config')

    def get_timeformatted(self):
        return time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())

    """————————————————————WATCHERS————————————————————"""
    async def shutdown_watcher(self, message):  #catch at message before it actually does anything
        prefixes = self.bot.settings.prefixes
        if (message.content in [prefix + 'shutdown' for prefix in prefixes] or
        message.content in [prefix + 'restart' for prefix in prefixes]):
            for server in self.bot.servers:
                print('saving gif bot settings:', server.id, server.name)
            self.save_config()
            return


    """————————————————————INIT————————————————————"""
    def init_settings(self):
        print('[%s]----------GIF Bot--------------------' % self.get_timeformatted())
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
            # if not os.path.isdir(config_path + server.id): #check server directory for local embedds
            #     print('  Server folder for %s not found, creating default: %s' % (server.name, config_path + server.id))
            #     os.makedirs(config_path + server.id)
            if not server.id in self.server_settings:   #create new default server settings
                print('  Server settings for %s %s not found, creating defaults' % (server.id, server.name))
                self.server_settings[server.id] = copy.deepcopy(default_server_cfg)
                self.server_settings[server.id]["server_name"] = server.name
        self.save_config()


def setup(bot):
    gif = GIF(bot)
    bot.add_cog(gif)

    try:
        gif.init_settings()
        bot.add_listener(gif.shutdown_watcher, 'on_message')
    except Exception as e:
        time_string = gif.get_timeformatted()  # strip using time
        traceback.print_exc()
        print("[%s] Exception: %s" % (time_string, (str(e))))
# setup