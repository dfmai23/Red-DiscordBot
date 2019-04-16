import discord
from discord.ext import commands
import traceback
import os
import asyncio
import json
import pprint

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import time
import datetime

from .utils.chat_formatting import *
from .utils import checks

default_server_cfg = {
    "server_name": "undefined",
    "CHANNEL": "undefined",     #channel to post to
    "CHANNEL_NAME": "undefined",
    "TIME_POST": "12:00",       #default time to post everyday
    "POSTS": {}
}

# post format
default_post_cfg = {
    "CHANNEL": "undefined",
    "CHANNEL_NAME": "undefined",
    "TIME_POST": "12:00",
    "CONTENT": ''
}

default_cfg = {
    "SERVER_SETTINGS": {}
}

config_path = 'data\dailypost\\'
config_file = 'config.json'

class Post:
    def __init__(self, bot):
        self.bot = bot
        self.settings = {}
        self.server_settings = {}


    @commands.command(pass_context=True)
    async def set_post(self, ctx, chnl, postname, *cntnt):
        """ Sets a post for server to message daily"""
        print("--------------------SET POST--------------------")
        server = ctx.message.server
        channel = server.get_channel(chnl)
        author = ctx.message.author
        content = ' '.join(cntnt)

        #only checks postname for now
        server_posts = self.server_settings[server.id]["POSTS"]
        if postname not in server_posts:
            server_posts[postname] = default_post_cfg
            server_posts[postname]["CHANNEL"] = channel.id
            server_posts[postname]["CHANNEL_NAME"] = channel.name
            server_posts[postname]["CONTENT"] = content

            print('added postname: %s %s' % (postname, str(server_posts[postname])))
            await self.bot.say('Saved post: %s to post the daily message: %s!~ into channel: %s'
                % (postname, content, channel.name))
        else:
            print('key already found: ' + postname)
            print(server_posts[postname])
            await self.bot.say('Post already saved! Use a different name!~')

    @commands.command(pass_context=True)
    async def remove_post(self, ctx, postname):
        """ Removes post from server to message"""
        print("--------------------REMOVE POST--------------------")
        server = ctx.message.server

        server_posts = self.server_settings[server.id]["POSTS"]
        if postname not in server_posts:
            print('key not found: ' + postname)
            await self.bot.say('Post not found!~')
        else:
            print('removed postname: %s %s' %(postname, str(server_posts[postname])))
            server_posts.pop(postname)
            await self.bot.say('Post successfully removed!~')

    @checks.mod_or_permissions(administrator=True)
    @commands.command(pass_context=True)
    async def save_posts(self, ctx):
        """ Save current posts"""
        server = ctx.message.server

        print("--------------------SAVE POSTS--------------------")
        print('posts: ' + str(self.server_settings[server.id]["POSTS"]))
        cats = self.server_settings[server.id]["POSTS"]

        try:
            self.save_config()
            await self.bot.say('Successfuly saved current posts!~')
        except Exception as e:
            print("Exception: " + str(e))
            await self.bot.say('Unable to save current posts!~')

    @checks.mod_or_permissions(administrator=True)
    @commands.command(pass_context=True)
    async def say(self, ctx, *content):
        str = ' '.join(content)
        await self.bot.say('posting: ' + str)

    @commands.command(pass_context=True)
    async def dstat(self, ctx):
        """ DEBUG, show settings """
        print("--------------------DSTAT--------------------")
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(self.settings)


    """————————————————————Helper Fn's————————————————————"""
    def save_config(self):      #save config for current server
        cfg_file = open(config_path + config_file, 'w')
        json.dump(self.settings, cfg_file, indent=4) #in:self.settings, out:file
        print('Saving DailyPostBot config')


    """————————————————————INIT————————————————————"""
    def init_settings(self):
        print('--------------------Daily Post--------------------')
        print('Loading DailyPostBot settings')
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
            if not server.id in self.server_settings:   #create new default server settings
                print(' Server settings for %s %s not found, creating defaults' % (server.id, server.name))
                self.server_settings[server.id] = default_server_cfg
                self.server_settings[server.id]["server_name"] = server.name
        self.save_config()
#Post


def setup(bot):
    dailypost = Post(bot)
    bot.add_cog(dailypost)

    try:
        dailypost.init_settings()
        # bot.loop.create_task(dailypost.init_scheduler())
    except Exception as e:
        time_string = time.strftime("%H:%M:%S", time.localtime())  # strip using time
        traceback.print_exc()
        print("[%s] Exception: %s" % (time_string, (str(e))))
#setup