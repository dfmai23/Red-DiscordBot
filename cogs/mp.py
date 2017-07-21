"""TODO:
    implement coroutine inits, self.playlists, and self.states
"""


import discord
from discord.ext import commands
import os
import threading
import asyncio
import logging
import subprocess
import enum
import random
import json
import xml.etree.ElementTree as etree
import xml.dom.minidom
import re           #re.compile() and pattern matching
import youtube_dl

from cogs.utils.chat_formatting import *
from .music_player.downloader import music_cache_path, music_local_path
from .music_player.playlist import Playlist, playlist_path, playlist_local_path
from .music_player.song import Song
from tinytag import TinyTag as TTag
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

class State(enum.Enum):
    STOPPED =   "Stopped"   # not playing anything
    PLAYING =   "Playing"   # playing music
    PAUSED  =   "Paused"    # paused
    #WAITING =   "Waiting"   # The player has finished its song but is still downloading the next one
    DONE    =   "Done"      # done playing current song

    def __str__(self):
        return self.name
#class State


class Music_Player:
    def __init__(self, bot, codec):
        self.bot = bot              #class discord.Client
        self.settings = json.load(open(config_path, 'r'))
        self.server_settings = self.settings["SERVER_SETTINGS"] #server specfic settings
        self.playlists = {} #music queues for each server
        self.states = {}    #status of each music player, ie. playing/paused
        self.bot.loop.create_task(self.init_autojoin())   #ensure_future wont block execution (fn always return immediately)
    #joins voice channel by channel id
    #def autojoin_channel(

    """________________Commands Operational________________"""
    """ Plays/resumes the song from current playlist"""
    @commands.command(pass_context=True)
    async def play(self, ctx): # * = keyword only arg
        server = ctx.message.server
        cur_state = self.states[server.id]
        pl = self.playlists[server.id]

        if cur_state == State.PAUSED:
            self.mp_play(server)
            await self.bot.say("Playing music!~")
        elif cur_state == State.PLAYING:
            self.mp_pause(server)
            await self.bot.say("Pausing music!~")
        elif cur_state == State.STOPPED:        #restart song
            self.mp_start(server, pl.list[pl.cur_i])
            await self.bot.say("Playing music!~")

    @commands.command(pass_context=True)
    async def pause(self, ctx):
        server = ctx.message.server
        self.mp_pause(server)
        await self.bot.say("Pausing music!~")

    @commands.command(pass_context=True)
    async def stop(self, ctx):
        server = ctx.message.server
        mp = self.get_mp(server)
        self.mp_stop(server)
        await self.bot.say("Stopping music!~")

    @commands.command(pass_context=True)
    async def skip(self, ctx):
        server = ctx.message.server
        mp = self.get_mp(server)
        self.mp_stop(server)

        #get next song in playlist
        pl = self.playlists[server.id]
        if (pl.cur_i+1) == len(pl.list):  #reached end of playlist
            await self.bot.say("Reached end of Playlist!~")
            return

        next_song = pl.list[pl.cur_i+1]
        self.mp_start(server, next_song)

        tags = TTag.get(next_song.path)
        nxt_song = tags.title + ' - ' + tags.artist
        await self.bot.say('Playing next song!~\n' + box(nxt_song))

    @commands.command(pass_context=True)
    async def replay(self, ctx):
        server = ctx.message.server
        mp = self.get_mp(server)
        pl = self.playlists[server.id]
        self.mp_stop(server)
        self.mp_start(server, pl.list[pl.cur_i])

    @commands.command(pass_context=True)
    async def status(self, ctx):
        server = ctx.message.server
        state = self.states[server.id]
        await self.bot.say("Music Player is currently: " + state.value + '~')

    @commands.command(pass_context=True)
    async def volume(self, ctx, *, decimal):    #keyword decimal to display on help
        server = ctx.message.server

        val = float(decimal)
        if val > 1.0 or val < 0.0:
            await self.bot.say("Volume must be between 0 and 1.0!~")
            return

        voice_client = self.bot.voice_client_in(server)
        if voice_client == None:
            await self.bot.say("Voice client not connected yet! Please join a voice channel and play music!~")
            return
        if not hasattr(voice_client, 'music_player'):
            await self.bot.say("Please play some music!")
            return
        mp = voice_client.music_player
        mp.volume = val
        self.server_settings[server.id]["VOLUME"] = val
        await self.bot.say("Music player volume set to:  " + str(val) + '~')


    """________________Commands Playlist________________"""
    """Adds a song to the playlist
        -Checks if its a url or local song
        -Will add to playlist
        -Autoplay if only one in playlist """
    @commands.command(pass_context=True)
    async def add(self, ctx, song_or_url):
        server = ctx.message.server
        name = song_or_url
        #django url validation regex
        is_url = re.compile(r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        if is_url.match(name):
            pass
        else:    #find local file in library
            ftype = r'(m4a|mp3)$'           #regular expression, $ = match the end of the string
            song_path_full = self.find_file(name, music_local_path, ftype)
            print(song_path_full)
            if song_path_full == None:
                await self.bot.say('Coudn\'t find song in library!~')
                return
            tags = TTag.get(song_path_full)
            song = Song(tags.title, tags.duration, song_path_full, None, tags.artist)

        pl = self.playlists[server.id]  #current playlist for server
        """state = pl.add(song)

        if state == 2:
            await self.bot.say('Song already in playlist!')
        elif state == 1 or result == 0:
            await self.bot.say('Added to playlist!~' + box(song.title + ' - ' + song.artist))

        if state == 1:
            self.mp_start(server, song)
        """

        if pl.search(song) != None:
            await self.bot.say('Song already in playlist!~')
            return

        pl.list.append(song)    #add to server's playlist
        await self.bot.say('Added to playlist!~' + box(song.title + ' - ' + song.artist))

        if len(pl.list) == 1:    #autoplay
            self.mp_start(server, song)

    @commands.command(pass_context=True)
    async def remove(self, ctx, *, index):  #removes a song from playlist
        server = ctx.message.server
        pl = self.playlists[server.id]
        mp = self.get_mp(server)

        i = int(index)

        if (i+1) > len(pl.list):
            await self.bot.say("Playlist index not in range!~")
            return

        song = pl.list.pop(i)
        if len(pl.list) == 0:
            mp.stop()
            pl.cur_i = -1
            await self.bot.say("Playlist now empty!")
            return
        elif i < pl.cur_i:   #removed a song before now playing, have to shift index one back
            pl.cur_i -= 1
        elif i == pl.cur_i:    #removed current playing song from playlist
            mp.stop()
            pl.cur_i = -1       #mp_start will move it to first song in playlist
            await self.bot.say("Removed currently playing song! Playing first song~")
            self.mp_start(server, pl.list[0])
            return

        if song == None:
            await self.bot.say("Not in playlist!~")
            return
        await self.bot.say("Removed from playlist!~\n" + box(song.title + ' - ' + song.artist))

    @commands.command(pass_context=True)
    async def clear(self, ctx):
        server = ctx.message.server
        mp = self.get_mp(server)
        pl = self.playlists[server.id]
        pl.list = []
        pl.cur_i = -1
        self.mp_stop(server)
        await self.bot.say("Cleared playlist!~")

    @commands.command(pass_context=True)
    async def view(self, ctx):              #View current playlist
        server = ctx.message.server
        pl = self.playlists[server.id]

        if len(pl.list) == 0:
            await self.bot.say("Empty Playlist!~")
            return

        playlist = ""
        for i, song in enumerate(pl.list):   #enumerate for index
            print(song)
            if song.url == None:            #local file
                if i == pl.cur_i:            #currently playing song
                    cur_song = str(i)+'. ' + song.title + ' - ' + song.artist
                playlist+=(str(i)+'. ' + song.title + ' - ' + song.artist + '\n')

        await self.bot.say("Currently Playing~\n" + box(cur_song) + '\n' + "Current Playlist~\n" + box(playlist))

    @commands.command(pass_context=True)
    async def repeat(self, ctx, onoff):
        server = ctx.message.server
        if onoff == 'on':
            self.server_settings[server.id]["REPEAT"] = True
        elif onoff == 'off':
            self.server_settings[server.id]["REPEAT"] = False
        else:
            await self.bot.say('Parameter must be "on" or "off"!')

    @commands.command(pass_context=True)
    async def save_pl(self, ctx, new_pl):       #will build own xml doc
        server = ctx.message.server
        pl = self.playlists[server.id]

        ftypes = r'(xml)$'
        server_pl_path = playlist_path + "\\" + server.id
        if self.get_file(new_pl, server_pl_path, ftypes) != None:
            await self.bot.say("Already have a playlist with same name!~")
            return

        root = etree.Element('smil')
        head = etree.SubElement(root, 'head')
        body = etree.SubElement(root, 'body')
        seq  = etree.SubElement(body, 'seq')

        head_gen = etree.SubElement(head, 'meta', name="Generator", content="Greedie_Bot v1.0")
        head_author = etree.SubElement(head, 'author', name=ctx.message.author.name)
        head_title = etree.SubElement(head, 'title')
        head_title.text = new_pl        #default title will be same as file name

        for song in pl.list:            #for every song in playlist, make new sub element
            seq_media = etree.SubElement(seq, 'media', src=song.path)
            print(seq_media)

        pl_path_full = playlist_path + '\\' + server.id + '\\' + new_pl + '.xml'
        f = open(pl_path_full, 'wb')      #b=binary mode, read docs, has conflict depending on encoding
        #hierarchy = etree.ElementTree(root)
        #hierarchy.write(f, encoding='utf-8', xml_declaration=True)

        #xml_str = xml.dom.minidom.parseString(etree.tostring(root)).toprettyxml()
        xml_str = etree.tostring(root)                          #print element type to a string
        xml_str_parsed = xml.dom.minidom.parseString(xml_str)   #reparse with minidom
        xml_str_pretty = xml_str_parsed.toprettyxml()           #make it pretty
        f.write(xml_str.encode('utf-8'))                        #convert it back to xml
        f.close()

    @commands.command(pass_context=True)
    async def load_pl(self, ctx, pl):
        server = ctx.message.server
        ftypes = r'(xml|wpl)$'
        pl_path = playlist_path + '\\' + server.id
        pl_path_full = self.find_file(pl, pl_path, ftypes)
        #print(pl_path_full)
        if pl_path_full == None:
            await self.bot.say ("Can't find playlist to load!~")
        tree = xml.etree.ElementTree.parse(pl_path_full)
        root = tree.getroot()
        #print(root[0])     #<head/>
        #print(root[1])     #<body/>
        #print(root[1][0])  #<seq/>

        for i, media in enumerate(root[1][0]):
            media_src = media.get('src')
            #print(i, media_src)
            pattern = r'^(\.{2})'       # ".."  local music library base path
            if re.match(pattern, media_src):  #if the string matches the pattern, find song in local library
                media_path_full = re.sub(pattern, music_local_path, media_src, count=1)
            else:
                media_path_full = media_src
            print(i, media_path_full)
            tags = TTag.get(media_path_full)
            song = Song(tags.title, tags.duration, media_path_full, None, tags.artist)
            if i==0:
                init_song = song
            self.playlists[server.id].list.append(song)
        self.mp_start(server, init_song)

    @commands.command(pass_context=True)
    async def delete_pl(self, ctx, pl_name):        #deletes by playlist filename
        server = ctx.message.server
        pl_path = playlist_path + '\\' + server.id

        ftypes = r'(xml|wpl)$'
        pl_path_full = self.find_file_exact(pl_name, playlist_path, ftypes)
        if pl_path_pull == None:
            await self.bot.say ("Can't find playlist to delete!~")
            return
        else:
            os.remove(pl_path_full)


    """________________Commands Server________________"""

    @commands.command(pass_context=True)
    async def join_vc(self, ctx):
        """ Joins voice channel """
        author = ctx.message.author     #ctx = context
        server = ctx.message.server
        channel = author.voice_channel  #channel to join,

        if self.bot.is_voice_connected(server):
            voice_client = self.bot.voice_client_in(server)
            if voice_client.channel.id == author.voice_channel.id:
                await self.bot.say("Already connected to your channel!~")
                return
            await voice_client.disconnect()
        await self.bot.join_voice_channel(channel)          #joins owners voice channel only

    @commands.command(pass_context=True)
    async def leave_vc(self, ctx):
        server = ctx.message.server
        if self.bot.is_voice_connected(server):
            voice_client = self.bot.voice_client_in(server)
            await voice_client.disconnect()

    @commands.command(pass_context=True)
    async def stat(self, ctx):
        server = ctx.message.server
        vc = self.bot.voice_client_in(server)
        mp = vc.music_player
        pl = self.playlists[server.id]

        #print(music_cache_path + '%(extractor)s' + '-' + '%(exts)s')
        #str = music_cache_path + '%(extractor)s' + '-' + '%(exts)s'
        """
        for server_id in self.playlists:
            print(server_id)
            #await self.bot.say(server.id)
        """

        print("playlist size: " + str(len(pl.list)))
        print("playlist now playing: " + pl.now_playing.title)
        print('playlist current index: ' + str(pl.cur_i))

        #mp_state
        state_msg = "music player state: "
        if mp.is_done() and (not mp.is_playing()):
            state_msg += "stopped"
        elif (not mp.is_done()) and (not mp.is_playing()):
            state_msg += "paused"
        elif (not mp.is_done()) and mp.is_playing():
            state_msg += "playing"
        print(state_msg)

        for key, val in self.server_settings[server.id].items():
            print(key, val)



    """________________Generics________________"""
    #play/resume
    def mp_play(self, server):
        music_player = self.get_mp(server)
        music_player.resume()
        self.states[server.id] = State.PLAYING

    def mp_pause(self, server):
        music_player = self.get_mp(server)
        if music_player.is_playing():
            music_player.pause()
            self.states[server.id] = State.PAUSED

    def mp_start(self, server, audio):  #audio=song object
        voice_client = self.bot.voice_client_in(server)
        options = '-b:a 64k -bufsize 64k'
        voice_client.music_player = voice_client.create_ffmpeg_player(audio.path, options=options)
        voice_client.music_player.volume = self.server_settings[server.id]["VOLUME"]
        self.states[server.id] = State.PLAYING
        self.playlists[server.id].now_playing = audio

        if self.playlists[server.id].cur_i == -1:
            self.playlists[server.id].cur_i = 0    #new playlist
        else:
            #self.playlists[server.id].cur_i += 1   #is playing next song
            self.playlists[server.id].cur_i   = self.playlists[server.id].search(audio)
        voice_client.music_player.start()

    def mp_stop(self, server):
        music_player = self.get_mp(server)
        music_player.stop()
        self.states[server.id] = State.STOPPED

    def get_mp(self, server):             #get music player of current server
        voice_client = self.bot.voice_client_in(server)
        music_player = voice_client.music_player
        return music_player




    """________________Helper Fn's________________"""
    def find_file(self, search_term, base_path, ftype):    #pattern matching
        #r'' string literal to make trivial to have backslashes
        pattern = r'^(.*)' + search_term + r'(.*\.)' + ftype
        for root, dirs, files in os.walk(base_path):
            for name in files:
                if re.search(pattern, name, re.IGNORECASE):            #if pattern matches string
                    #print(name)
                    file_path_full = os.path.join(root, name)
                    return file_path_full
        return None

    def get_file(self, filename, base_path, ftype):
        for root, dirs, files in os.walk(base_path):
            for name in files:
                if os.path.isfile(filename):
                    file_path_full = os.path.join(root, name)
                    return file_path_full
        return None

    """________________Management________________"""
    #basically polls music player to see if its playing or not
    async def playlist_scheduler(self):
        while self == self.bot.get_cog('Music_Player'): #while music player class is alive
            tasks = []
            #playlists = copy.deepcopy(self.playlists)
            for server_id in self.playlists:             #returns the key for each playlist
                if len(self.playlists[server_id].list) == 0:     #do nothing if playlist empty
                    continue        #skip rest of loop
                #full concurrency, create task for each server
                tasks.append(self.bot.loop.create_task(self.playlist_manager(server_id)))
            completed = [t.done() for t in tasks]
            while not all(completed):
                completed = [t.done() for t in tasks]   #schedule it
                await asyncio.sleep(0.5)
            await asyncio.sleep(3)  #reload every x seconds

    async def playlist_manager(self, server_id):
        server = self.bot.get_server(server_id)
        vc = self.bot.voice_client_in(server)
        mp = vc.music_player

        pl = self.playlists[server.id]
        #print('indexa: ' + str(pl.cur_i))
        #if mp.is_done():
        if mp.is_done() and self.states[server.id] != State.STOPPED:
            if (pl.cur_i+1) == len(pl.list):  #reached end of playlist
                if ("REPEAT" in self.server_settings[server.id]) and (self.server_settings[server.id].get("REPEAT") == True):
                    pl.cur_i = -1
                    next_song = pl.list[pl.cur_i+1]
                    self.mp_start(server, next_song)
                #self.bot.loop.create_task(self.bot.say("Reached end of Playlist!~"))
                pass
            else:
                #print('indexb: ' + str(pl.cur_i+1))
                next_song = pl.list[pl.cur_i+1]
                self.mp_start(server, next_song)
                #print('playing next song')

    def save_config(self):      #save config for current server
        config_file = open(config_path, 'w')
        json.dump(self.settings, config_file, indent=4)


    """________________Initialization's________________"""
    """Initializes playlists by:
        -creating empty queues for each server
        -reading saved saved playlist
        -loading playlist    """
    """Initializes autojoining by:
        -autojoining channels from settings file and owner channel
        -loading its last playlist
        -starts playing if channel no empty  """
    def init_playlists(self):
        print('Loading Playlists')
        playlists = {}      #map
        for server in self.bot.servers:
            playlists[server.id] = Playlist()   #list
            pl_path_full = playlist_path + '\\' + server.id + '\saved_playlist.xml'
            #print(pl_path_full)
            if os.path.isfile(pl_path_full):
                temp_pl = json.load(open(pl_path_full, 'r'))
                for song in temp_pl["PLAYLIST"]:
                    playlists[server.id].list.append(song)  #add song to playlist
            else:
                pl_path = playlist_path + '\\' + server.id
                if not os.path.exists(pl_path):
                    os.makedirs(pl_path)
        self.playlists = playlists

    def init_states(self):
        print('Loading default states')
        states = {}
        for server in self.bot.servers:
            print(server.id)
            states[server.id] = State.STOPPED
        self.states = states

    async def init_autojoin(self):
        print('Autojoining Channels')
        states = []
        if self.settings["AUTOJOIN"] == True:
            for c_id in self.settings["AUTOJOIN_CHANNELS"]:
                channel = self.bot.get_channel(c_id)
                await self.bot.join_voice_channel(channel)
                #self.autoplay(bot.voice_client_in(channel.server))
#class Music Player

"""startup checks"""
def check_cfg():
    default_cfg = {"VOLUME": .5,
                "REPEAT": True,
                "SHUFFLE": False,
                "VOTE_RATIO": .5,
                "VOTES_REQUIRED": 3,
                "SAVE_PLAYLISTS": True,
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

    #Music Player initializations after it has connected to servers
    music_player.init_playlists()
    music_player.init_states()
    print('Starting Music Player with codec: ' + codec)

    #bot.add_listener(music_player.voice_state_update, 'on_voice_state_update')
    bot.loop.create_task(music_player.playlist_scheduler())
    """
    bot.loop.create_task(n.disconnect_timer())
    bot.loop.create_task(n.reload_monitor())
    bot.loop.create_task(n.cache_scheduler())
    """
#fn setup
