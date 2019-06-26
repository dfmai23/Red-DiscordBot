import discord
from discord.ext import commands
import asyncio
import os
import copy
import re
import time

# from cleverwrap import CleverWrap
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer
chatbot = commands.Bot(command_prefix='@Bot')

import logging
logging.basicConfig(level=logging.INFO)

chat_path = 'data\chat\\'
chat_file = 'chat.txt'  #global chat file for manual messages


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
    async def cstat(self, ctx):
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
        # self.bot.loop.create_task(self.init_chatbot())  #done during bot is initialized
        # self.init_messages()

    async def my_on_message(self, message):
        if self.bot.user.mentioned_in(message):
            reply = self.parse(message)
            try:
                await self.bot.send_message(message.channel, content=reply)
            except discord.errors.HTTPException:
                pass

    @commands.command(pass_context=True)
    async def cstat(self, ctx):
        server = ctx.message.server

        for key in self.messages:
            print(key, self.bot.get_server(key).name)
            for key2 in self.messages[key]:
                print(' ', key2, self.messages[key][key2])

    def parse(self, message):
        time_string = self.get_timeformatted()
        print('[%s]----------Chatbot Message--------------------' % time_string)
        if '@everyone' in message.content:
            print('contains @everyone, skipping message')
            return

        pattern= re.compile(r'^(<@\d*>|@everyone)')
        content = re.sub(pattern, '', message.content)  #remove the ping @bot from message before parse
        reply = self.chatbot.get_response(content)

        print('message content: ' + message.content)
        print('editted content: ' + content)
        print('REPLY', message.content, '|', reply)
        return reply

    def parse2(self, server, message):  #from txt file
        msg = ''
        msg = message.content   #str
        msg = msg.strip(self.bot.user.mention + ' ')
        msg = msg.lower()
        if msg in self.messages[server.id]:
            return self.messages[server.id][msg]


    """————————————————————Helper Fn's————————————————————"""
    def check_trained(self):
        trained = False
        chat_train_loc = chat_path + 'trained.txt'
        if not os.path.isfile(chat_train_loc):
            f = open(chat_train_loc, 'w')
            f.write('1')
            trained = False
            print('trained.txt not found creating it and training chatbot')
        else:
            f = open(chat_train_loc, 'r+')
            line = f.readline()
            if line == '1':
                print('trained.txt read: %s, not training chatbot' % line)
                trained = True
            else:
                print('trained.txt read: %s, training chatbot' % line)
                f = open(chat_train_loc, 'w')
                f.write('1')
                trained = False
        f.close()
        return trained

    def get_timeformatted(self):
        return time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())

    """————————————————————Initializations————————————————————"""
    def init_chat(self):
        f = open(chat_path + chat_file, 'r')
        messages = {}
        messages_list = []
        messages_list = f.readlines()

        for line in messages_list:
            #print(line)
            line = line.replace('\n', '')
            line = line.split('|')
            messages[line[0].lower()] = line[1]
            #print(line[0] + ' | ' + messages[line[0].lower()])
        f.close()
        return messages

    def init_messages(self):
        if not os.path.isdir(chat_path):    #root chat dir
            os.mkdir(chat_path)
        global_chat_loc = chat_path + chat_file
        if not os.path.isfile(global_chat_loc):
            f = open(global_chat_loc, 'w')
            f.close()
        global_msgs = self.init_chat()

        for server in self.bot.servers:
            self.messages[server.id] = {}
            self.messages[server.id] = copy.deepcopy(global_msgs)   #copy global messages to each server

            server_chat_path = chat_path + server.id + '\\'
            if not os.path.isdir(server_chat_path):
                os.mkdir(server_chat_path)
            server_chat_loc = server_chat_path + chat_file
            if not os.path.isfile(server_chat_loc):
                f = open(server_chat_loc, 'w')
                f.close()

            #print(server_chat_loc)
            f = open(server_chat_loc, 'r')
            svr_msgs = {}
            msgs_list = []
            msgs_list = f.readlines()

            for line in msgs_list:
                line = line.replace('\n', '')
                line = line.split('|')
                self.messages[server.id][line[0].lower()] = line[1]
            f.close()

    async def init_chatbot(self):
        print('[%s]----------Chat Bot--------------------' % self.get_timeformatted())
        self.chatbot = ChatBot(
        'Greedie_Bot',
        storage_adapter='chatterbot.storage.SQLStorageAdapter', #sql is defualt
        database='data/chat/chatdb.sqlite3',
        logic_adapters=["chatterbot.logic.BestMatch"])

    async def init_training(self):
        trained = self.check_trained()
        if not trained:
            print('training')
            trainer = ChatterBotCorpusTrainer(self.chatbot)
            trainer.train('chatterbot.corpus.english')
            print('training done')

def setup(bot):
    chat_bot = Chat(bot)  # Praise 26
    bot.add_cog(chat_bot)

    bot.loop.create_task(chat_bot.init_chatbot())
    chat_bot.init_messages()
    bot.loop.create_task(chat_bot.init_training())
    bot.add_listener(chat_bot.my_on_message, 'on_message') #when on_message fires so will my_on_message
    #print('Starting chat cog')
