import discord
from discord.ext import commands
import asyncio
import os
import json

default_cfg = {
                "DAILY_CHANNELS": {},
                "SERVER_SETTINGS": {}
            }

server_cfg = {"DAILY_CHANNELS": {},
                "SOURCES": {}   #channel id, source pair
                "INIT_TIME": "12:00",
                "INTERVAL": "24:00",
            }

config_path = 'data\daily\config.json'

class Daily:
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.init_dailybot())

    async def init_dailybot(self):
        #start timers here


    def init_settings(self):
        print('Loading dailybot settings')
        self.settings = json.load(open(config_path, 'r'))
        self.server_settings = self.settings["SERVER_SETTINGS"]

        for server in self.bot.servers:
            if not server.id in self.server_settings:   #create new default server settings
                print(' Server settings for %s %s not found, creating defaults' % (server.id, server.name))
                self.server_settings[server.id] = server_cfg
        self.save_config()

    def save_config(self):      #save config for current server
        config_file = open(config_path, 'w')
        json.dump(self.settings, config_file, indent=4)
        print('Saving dailybot config')

def setup(bot):
    dailybot = Daily(bot)
    bot.add_cog(dailybot)

    dailybot.init_settings()



#settings
#server channels to send messages
#time to send messages
#interval
#sources

#add names to ids to for better info
