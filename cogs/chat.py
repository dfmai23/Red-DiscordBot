import discord
from discord.ext import commands
import asyncio
import os
import copy

from cleverwrap import CleverWrap
from chatterbot import ChatBot
from .music_player.paths import chat_path, chat_file
#chatbot = commands.Bot(command_prefix='@Bot')

"""
#using cleverwrap
class Chat:
    def __init__(self, bot):
        self.bot = bot  #discord.Client()
        self.cbot = CleverWrap("CC3pbSYwSb0er-gRoQX9Kc3b9ug")
        self.messages = {}
        self.init_messages()

    async def my_on_message(self, message):
        if self.bot.user.mentioned_in(message):
            reply = self.parse(message)
            try:
                await self.bot.send_message(message.channel, content=reply)
            except discord.errors.HTTPException:
                pass

    @commands.command(pass_context=True)
    async def stat_chat(self, ctx):
        server = ctx.message.server

        for key in self.messages:
            print(key, self.bot.get_server(key).name)
            for key2 in self.messages[key]:
                print(' ', key2, self.messages[key][key2])

    def parse(self, message):
        reply = self.cbot.say(message.content)
        #print(message.content, '|', reply)
        return reply

    def parse2(self, server, message):
        msg = ''
        msg = message.content   #str
        msg = msg.strip(self.bot.user.mention + ' ')
        msg = msg.lower()
        if msg in self.messages[server.id]:
            return self.messages[server.id][msg]


    def init_chat(self):
        f = open(chat_path +'\\'+ chat_file, 'r')
        messages = {}
        messages_list = []
        messages_list = f.readlines()

        for line in messages_list:
            #print(line)
            line = line.replace('\n', '')
            line = line.split('|')
            messages[line[0].lower()] = line[1]
            #print(line[0] + ' | ' + messages[line[0].lower()])
        return messages

    def init_messages(self):
        global_msgs = self.init_chat()

        for server in self.bot.servers:
            self.messages[server.id] = {}
            self.messages[server.id] = copy.deepcopy(global_msgs)

            server_chat_path = chat_path + '\\' + server.id
            if not os.path.isdir(server_chat_path):
                os.mkdir(server_chat_path)
            server_chat_path_full = server_chat_path +'\\'+ chat_file
            if not os.path.isfile(server_chat_path_full):
                f = open(server_chat_path_full, 'w')
                f.close()

            #print(server_chat_path_full)
            f = open(server_chat_path_full, 'r')
            svr_msgs = {}
            msgs_list = []
            msgs_list = f.readlines()

            for line in msgs_list:
                line = line.replace('\n', '')
                line = line.split('|')
                self.messages[server.id][line[0].lower()] = line[1]
            f.close()
"""

#using chatterbot
class Chat:
    def __init__(self, bot):
        self.bot = bot  #discord.Client()
        self.chatbot = None
        self.messages = {}
        self.bot.loop.create_task(self.init_chatbot())
        self.init_messages()

    async def my_on_message(self, message):
        if self.bot.user.mentioned_in(message):
            reply = self.parse(message)
            try:
                await self.bot.send_message(message.channel, content=reply)
            except discord.errors.HTTPException:
                pass

    @commands.command(pass_context=True)
    async def stat_chat(self, ctx):
        server = ctx.message.server

        for key in self.messages:
            print(key, self.bot.get_server(key).name)
            for key2 in self.messages[key]:
                print(' ', key2, self.messages[key][key2])

    def parse(self, message):
        reply = self.chatbot.get_response(message.content)
        print(message.content, '|', reply)
        return reply

    #from txt file
    def parse2(self, server, message):
        msg = ''
        msg = message.content   #str
        msg = msg.strip(self.bot.user.mention + ' ')
        msg = msg.lower()
        if msg in self.messages[server.id]:
            return self.messages[server.id][msg]

    def init_chat(self):
        f = open(chat_path +'\\'+ chat_file, 'r')
        messages = {}
        messages_list = []
        messages_list = f.readlines()

        for line in messages_list:
            #print(line)
            line = line.replace('\n', '')
            line = line.split('|')
            messages[line[0].lower()] = line[1]
            #print(line[0] + ' | ' + messages[line[0].lower()])
        return messages

    def init_messages(self):
        global_msgs = self.init_chat()

        for server in self.bot.servers:
            self.messages[server.id] = {}
            self.messages[server.id] = copy.deepcopy(global_msgs)

            server_chat_path = chat_path + '\\' + server.id
            if not os.path.isdir(server_chat_path):
                os.mkdir(server_chat_path)
            server_chat_path_full = server_chat_path +'\\'+ chat_file
            if not os.path.isfile(server_chat_path_full):
                f = open(server_chat_path_full, 'w')
                f.close()

            #print(server_chat_path_full)
            f = open(server_chat_path_full, 'r')
            svr_msgs = {}
            msgs_list = []
            msgs_list = f.readlines()

            for line in msgs_list:
                line = line.replace('\n', '')
                line = line.split('|')
                self.messages[server.id][line[0].lower()] = line[1]
            f.close()

    async def init_chatbot(self):
        self.chatbot = ChatBot(
        'Greedie_Bot',
        trainer='chatterbot.trainers.ChatterBotCorpusTrainer',
        storage_adapter='chatterbot.storage.SQLStorageAdapter', #sql is defualt
        database='data/chat/chatdb_sqlite3',
        logic_adapters=["chatterbot.logic.BestMatch"])
        #self.chatbot.train("chatterbot.corpus.english")

def setup(bot):
    chat_bot = Chat(bot)  # Praise 26
    bot.add_cog(chat_bot)
    bot.add_listener(chat_bot.my_on_message, 'on_message') #when on_message fires so will my_on_message
    #print('Starting chat cog')
