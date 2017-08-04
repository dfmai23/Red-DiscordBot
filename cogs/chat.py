import discord
from discord.ext import commands
import asyncio
import os

chat_path = 'data\chat\chat.txt'
#chatbot = commands.Bot(command_prefix='@Bot')

class Chat:
    def __init__(self, bot):
        self.bot = bot  #discord.Client()
        self.messages = self.init_chat()

    def init_chat(self):
        f = open(chat_path, 'r')
        messages = {}
        messages_list = []
        messages_list = f.readlines()

        for line in messages_list:
            line = line.replace('\n', '')
            line = line.split('|')
            messages[line[0].lower()] = line[1]
            #print(line[0] + ' | ' + messages[line[0].lower()])
        return messages

    async def my_on_message(self, message):
        if self.bot.user.mentioned_in(message):
            reply = self.parse(message)
            try:
                await self.bot.send_message(message.channel, content=reply)
            except discord.errors.HTTPException:
                pass

    def parse(self, message):
        msg = ''
        msg = message.content   #str
        msg = msg.strip(self.bot.user.mention + ' ')
        msg = msg.lower()
        if msg in self.messages:
            return self.messages[msg]

def setup(bot):
    chat_bot = Chat(bot)  # Praise 26
    bot.add_cog(chat_bot)
    bot.add_listener(chat_bot.my_on_message, 'on_message') #when on_message fires so will my_on_message
    print('Starting chat cog')
