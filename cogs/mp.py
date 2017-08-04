"""TODO:
    implement coroutine inits, self.playlists, and self.states
"""

__author__ = "dfmai23"

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

from tinytag import TinyTag as TTag
from .utils.chat_formatting import *
from .utils import checks
from .music_player.downloader import Downloader, music_cache_path, music_local_path
from .music_player.playlist import Playlist, playlist_path, playlist_local_path #, default_playlist
from .music_player.song import Song
from .music_player.paths import *

log = logging.getLogger(__name__)

try:
    if not discord.opus.is_loaded():
        discord.opus.load_opus('libopus-0.dll')
except OSError:  # Incorrect bitness
    opus = False
except:         # Missing opus
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
        self.downloader = Downloader()
        self.bot.loop.create_task(self.init_autojoin())   #ensure_future wont block execution (fn always return immediately)
    #joins voice channel by channel id
    #def autojoin_channel(

    """________________Commands Operational________________"""
    @commands.command(pass_context=True)
    async def play(self, ctx): # * = keyword only arg
        """ Plays/resumes the song from current playlist"""
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
        """ Skips current song """
        server = ctx.message.server
        mp = self.get_mp(server)
        pl = self.playlists[server.id]
        self.mp_stop(server)

        #get next song in playlist
        next_song = await self.get_nxt_song(server)
        await self.check_nextnext_song(server)
        if next_song == None:  #reached end of playlist
            await self.bot.say("Reached end of Playlist!~")
            return
        nxt_song_display = next_song.display()
        await self.bot.say('Playing next song!~\n' + box(nxt_song_display))
        self.mp_start(server, next_song)

    @commands.command(pass_context=True)
    async def prev(self, ctx):
        server = ctx.message.server
        mp = self.get_mp(server)
        pl = self.playlists[server.id]
        self.mp_stop(server)

        #get prev song in playlists
        prev_i = pl.order.index(pl.cur_i)
        prev_song = pl.list[prev_i]
        self.mp_start(server, prev_song)

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
    @commands.command(pass_context=True)
    async def dl(self, ctx, url):
        server = ctx.message.server
        dl = Downloader()
        info = await dl.extract(self.bot.loop, url, download=False)

        if ('ext' in info['formats'][0]) and (info['formats'][0]['ext'] == 'm4a'):
            song_path_full = self.bot.loop.create_task(dl.extract_m4a(info))
        else:
            info = await dl.extract(self.bot.loop, url)

    @commands.command(pass_context=True)
    async def inf(self, ctx, url):
        server = ctx.message.server
        info = await self.downloader.extract(self.bot.loop, url, download=False)
        if info != None:
            for key in info:
                if key == 'formats':
                    print(key, info[key])
                    continue
                """
                if key == 'entries':
                    for entry in info['entries']:
                        for key2 in entry:
                            print(key2, entry[key2])
                """
                print(key, info[key])
                """
                if key == 'formats':
                    ext = info[key][0]['ext']   #multiple m4a links, 0=pull first one
                    url = info[key][0]['url']
                    print(ext, url)
                """
        else:
            print('Not able to get info')

    """Adds a song to the playlist
        -Checks if its a url or local song
        -Will add to playlist
        -Autoplay if only one in playlist """
    @commands.command(pass_context=True)
    async def add(self, ctx, song_or_url):
        """ Add a song to the playlist """
        server = ctx.message.server
        pl = self.playlists[server.id]

        is_url = re.compile(r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        if is_url.match(song_or_url):   #download or find in cache
            url = song_or_url
            info = await self.downloader.extract(self.bot.loop, url)    #get info and download song
            song_path_full = music_cache_path + '\\' + info['title'] +'-'+ info['extractor'] +'-'+ info['id'] + '.' + info['ext']
            song = Song(info['title'], info['duration'], song_path_full, info['webpage_url'])
        else:    #find local file in library
            name = song_or_url
            ftype = r'(m4a|mp3|webm)$'  #regular expression, $ = match the end of the string
            song_path_full = self.find_file(name, music_local_path, ftype)
            if song_path_full == None:  #song not in lib
                return 3
            tags = TTag.get(song_path_full)
            song = Song(tags.title, tags.duration, song_path_full, None, artist=tags.artist)

        song_added = pl.add(song)
        if song_added == 3:
            await self.bot.say('Coudn\'t find song in library!~')
        elif song_added == 2:
            await self.bot.say('Song already in playlist!')
        else:
            song_display = song.display()
            await self.bot.say('Added to playlist!~' + box(song_display))

        if len(pl.list) == 1:    #autoplay
            self.mp_start(server, song)

    """Adds a url playlist to the playlist
        - if current playlist is empty, will load it as a new playlist  """
    @commands.command(pass_context=True)
    async def add_p(self, ctx, url):
        """Adds a url playlist to the playlist """
        server = ctx.message.server
        pl = self.playlists[server.id]

        is_url = re.compile(r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        if is_url.match(url):   #download or find in cache
            info = await self.downloader.extract(self.bot.loop, url, download=False, process=False) #process=F less info, alot faster
            if info['extractor_key'] in ['YoutubePlaylist', 'SoundcloudSet', 'BandcampAlbum']:
                await self.bot.say('Adding a playlist!~')
                url_pl = await self.load_url_pl(server, info, pl)
                for song in url_pl:
                   pl.add(song)
                await self.bot.say('Playlist added!~')
        else:
            await self.bot.say('Not a URL playlist!~')
            return

    @commands.command(pass_context=True)
    async def remove(self, ctx, index):     #removes a song from playlist
        server = ctx.message.server
        pl = self.playlists[server.id]
        mp = self.get_mp(server)

        state, song = pl.remove(index)
        if state == 3:
            await self.bot.say("Playlist index not in range!~")
        elif state == 2:
            await self.bot.say("Playlist now empty!")
            mp.stop()
        elif state == 1:
            await self.bot.say("Removed currently playing song! Playing next song~")
            mp.stop()
            mp.start(server, pl.cur_i)
        else:
            await self.bot.say("Removed from playlist!~\n" + box(song.title + ' - ' + song.artist))
        """
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
        """

    @commands.command(pass_context=True)
    async def clear(self, ctx):
        server = ctx.message.server
        mp = self.get_mp(server)
        pl = self.playlists[server.id]
        self.mp_stop(server)
        pl.clear()
        await self.bot.say("Cleared playlist!~")

    @commands.command(pass_context=True)
    async def view(self, ctx):              #View current playlist
        server = ctx.message.server
        pl = self.playlists[server.id]

        if len(pl.list) == 0:
            await self.bot.say("Empty Playlist!~")
            return
        else:
            cur_song, playlist, settings = pl.view()
            settings = 'State: ' + self.states[server.id].value + '\t' + settings
            await self.bot.say( "Settings~\n" + box(settings) + '\n' +
                                "Current Song~\n" + box(cur_song) + '\n' +
                                "Current Playlist:\t%s\n" % italics(pl.title),
                                delete_after=60)
            for pl_section in playlist:
                await self.bot.say(box(pl_section))

    @commands.command(pass_context=True)
    async def repeat(self, ctx, onoff):
        server = ctx.message.server
        pl = self.playlists[server.id]
        if onoff != 'on' and onoff != 'off':
            await self.bot.say('Parameter must be "on" or "off"!~')
            return
        elif onoff == 'on':
            pl.repeat = True
        elif onoff == 'off':
            pl.repeat = False
        pl.set_repeat()
        await self.bot.say("Repeat set to %s!~" % onoff)

    @commands.command(pass_context=True)
    async def shuffle(self, ctx, onoff):
        server = ctx.message.server
        pl = self.playlists[server.id]
        if onoff != 'on' and onoff != 'off':
            await self.bot.say('Parameter must be "on" or "off"!~')
            return
        elif onoff == 'on':
            pl.shuffle = True
        elif onoff == 'off':
            pl.shuffle = False
        pl.set_shuffle()
        await self.bot.say("Shuffle set to %s!~" % onoff)

    @commands.command(pass_context=True)
    async def save_p(self, ctx, new_pl):       #builds own xml
        author = ctx.message.author
        server = ctx.message.server
        pl = self.playlists[server.id]

        pl_saved = pl.save(new_pl, author)
        if pl_saved == 1:
            await self.bot.say("Already have a playlist with same name! Overwrite? Y/N~")
            reply = await self.bot.wait_for_message(author=author, channel=ctx.message.channel, check=self.check_reply)
            if reply.content == 'yes':
                pl_saved = pl.save(new_pl, author, overwrite=1)
            elif reply.content == 'no':   #reply=0
                await self.bot.say('Playlist not saved!~')
                return
        await self.bot.say("Saved playlist: %s!~" % new_pl)

    @commands.command(pass_context=True)
    async def load_p(self, ctx, pl):
        server = ctx.message.server
        pl_loaded = self.load_pl(server, pl, init=False)
        if pl_loaded == 1:
            await self.bot.say("Can't find playlist to load!~")
        else:
            self.mp_start(server, self.playlists[server.id].list[0])    #autoplay

    @commands.command(pass_context=True)
    async def delete_p(self, ctx, pl_name):        #deletes by playlist filename bar ext
        server = ctx.message.server
        pl_path = playlist_path + '\\' + server.id

        ftype = 'xml'
        pl_path_full = self.get_file(pl_name, pl_path, ftype)
        if pl_path_full == None:
            await self.bot.say ("Can't find playlist to delete!~")
        else:
            os.remove(pl_path_full)
            await self.bot.say ("Deleted playlist: %s!~" % pl_name)


    """________________Commands Server________________"""
    @commands.command(pass_context=True)
    @checks.mod_or_permissions(administrator=True)
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
    @checks.mod_or_permissions(administrator=True)
    async def leave_vc(self, ctx):
        server = ctx.message.server

        if self.bot.is_voice_connected(server):
            voice_client = self.bot.voice_client_in(server)
            await voice_client.disconnect()

    @commands.command(pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def rejoin(self, ctx):
        #TODO make bot rejoin its own vc
        server = ctx.message.server
        author = ctx.message.author
        channel = author.voice_channel
        voice_client = self.bot.voice_client_in(server)
        await voice_client.disconnect()
        await self.bot.join_voice_channel(channel)

    @commands.command(pass_context=True)
    async def stat(self, ctx):
        server = ctx.message.server
        vc = self.bot.voice_client_in(server)
        mp = vc.music_player
        pl = self.playlists[server.id]

        #print(music_cache_path + '%(extractor)s' + '-' + '%(exts)s')
        #str = music_cache_path + '%(extractor)s' + '-' + '%(exts)s'

        print(server.id, server.name)

        print("playlist size: " + str(len(pl.list)))
        print("playlist now playing: " + pl.now_playing.title)
        print('playlist current index: ' + str(pl.cur_i))
        print('playlist order: ' + str(pl.order))
        state_msg = "music player state: "
        if mp.is_done() and (not mp.is_playing()):
            state_msg += "stopped"
        elif (not mp.is_done()) and (not mp.is_playing()):
            state_msg += "paused"
        elif (not mp.is_done()) and mp.is_playing():
            state_msg += "playing"
        print(state_msg)
        print('music player state class:', self.states[server.id].value)

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
        else:   #update index
            self.playlists[server.id].cur_i = self.playlists[server.id].get_i(audio)   #accounts for skipping and going back
        print('Playing:', audio.path)
        voice_client.music_player.start()

    def mp_stop(self, server):
        music_player = self.get_mp(server)
        music_player.stop()
        self.states[server.id] = State.STOPPED

    def get_mp(self, server):             #get music player of current server
        voice_client = self.bot.voice_client_in(server)
        music_player = voice_client.music_player
        return music_player

    async def get_nxt_song(self, server):
        pl = self.playlists[server.id]
        if pl.order[pl.cur_i] == None:  #reached end of playlist
            return None

        #print('cur_i: %d \tnext_i: %d' % (pl.cur_i, pl.order[pl.cur_i]))
        next_song_i = pl.order[pl.cur_i]
        next_song = pl.list[next_song_i]
        song_file = os.path.basename(next_song.path)
        base_path = os.path.dirname(next_song.path)
        print('Getting next song:', base_path+song_file)
        if pl.get_file(song_file, base_path) == None:   #file not found, skip or check url
            if next_song.url == None:
                pl.cur_i = next_song_i    # to get next next song
                await self.bot.say('File not found, skipping song!~\n' + box(next_song.title + ' - ' + next_song.artist))
                return await self.get_nxt_song(server)
            else:   #url song
                info = await self.downloader.extract(self.bot.loop, next_song.url)  #download song
        return next_song

    async def check_nextnext_song(self, server):  #preloads the next next song after the current song if it is a url song\
        pl = self.playlists[server.id]
        if pl.order[pl.cur_i] == None:  #reached end of playlist
            return None

        next_song_i = pl.order[pl.cur_i]
        nextnext_song_i = pl.order[next_song_i]    #concurrent, cur_i not updated yet
        nextnext_song = pl.list[nextnext_song_i]
        print('Checking next next song:', nextnext_song.path)
        if nextnext_song.url != None:
            info = await self.downloader.extract(self.bot.loop, nextnext_song.url)

    """Loads a local/saved playlist
        -will create empty Playlist() class
        -if init is on then will search specifically for "saved_playlist.xml" from data/music
        -else will search for playlist with closest name
        -if init is on will also create server playlist path if not found and load the empty playlist
        -processes the playlist """
    def load_pl(self, server, playlist_name, init):          #* = forces keyword arg in caller
        server_cfg = self.server_settings[server.id]
        playlist = Playlist(server.id, server_cfg["REPEAT"], server_cfg["SHUFFLE"])   #creat empty playlist
        try:
            mp_stop(server)
        except:
            pass
        self.playlists[server.id] = playlist.load(playlist_name, init)

    async def load_url_pl(self, server, info, playlist):     #returns a list of Songs
        url_playlist = []
        base_url = info['webpage_url'].split('playlist?list=')[0]
        for entry in info['entries']:
            if entry:       #check deleted vids
                if info['extractor_key'] == 'YoutubePlaylist':
                    song_url = base_url + 'watch?v=%s' % entry['id']
                else:   #'SoundcloudSet', 'BandcampAlbum'
                    song_url = entry['url']
                info = await self.downloader.extract(self.bot.loop, song_url, download=False)
                if info == None:
                    continue
                #print(song_url)
                song_path_full = music_cache_path + '\\' + info['title'] +'-'+ info['extractor'] +'-'+ info['id'] + '.' + info['ext']
                song = Song(info['title'], info['duration'], song_path_full, info['webpage_url'])
                url_playlist.append(song)
        return url_playlist


    """________________Helper Fn's________________"""
    def find_file(self, search_term, base_path, ftype):    #pattern matching
        #r'' string literal to make trivial to have backslashes
        pattern = r'^(.*)' + search_term + r'(.*\.)' + ftype
        for root, dirs, files in os.walk(base_path):
            for name in files:
                if re.search(pattern, name, re.IGNORECASE):            #if pattern matches string
                    file_path_full = os.path.join(root, name)
                    return file_path_full
        return None

    def get_file(self, filename, base_path, ftype):         #get specific file
        file_path_full = os.path.join(base_path, filename + '.' + ftype)
        print(file_path_full)
        if os.path.isfile(file_path_full):
            return file_path_full
        return None

    def check_reply(self, reply):   #reply is a Message class,cant return bool???
        if reply.content.lower() == 'yes' or reply.content.lower() == 'y':
            return 'yes'
        elif reply.content.lower() == 'no' or reply.content.lower() == 'n':
            return 'no'
    """________________Management________________"""
    #basically asynchronously polls music player to see if its playing or not
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
        try:
            mp = vc.music_player
        except AttributeError:
            pass

        pl = self.playlists[server.id]
        try:
            if mp.is_done() and self.states[server.id] != State.STOPPED:    #stopped playing music
                next_song = await self.get_nxt_song(server)
                await self.check_nextnext_song(server)
                #print('t1')
                if next_song == None:  #repeat off, end of playlist
                    print('Next song is NoneType')
                    pass
                else:
                    self.mp_start(server, next_song)
        except:
            pass

            """
            if pl.list[pl.order[pl.cur_i]] == None and self.server_settings[server.id]["REPEAT"] == False:  #reached end of playlist
                pass
            else:   #repeat off
                #print('indexb: ' + str(pl.cur_i+1))
                next_song = pl.list[pl.order[pl.cur_i]]
                self.mp_start(server, next_song)
                #print('playing next song')
            """

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
            print(server.id, server.name)
            self.load_pl(server, default_playlist, init=True)

    def init_states(self):
        print('Loading default states')
        states = {}
        for server in self.bot.servers:
            #print(server.id)
            states[server.id] = State.STOPPED
        self.states = states

    async def init_autojoin(self):
        print('Autojoining Channels')
        states = []
        if self.settings["AUTOJOIN"] == True:
            for c_id in self.settings["AUTOJOIN_CHANNELS"]:
                channel = self.bot.get_channel(c_id)
                server = channel.server
                try:
                    await self.bot.join_voice_channel(channel)
                except:     #already connected to the channel
                    pass
                #await self.bot.say('Hi!~')
                self.mp_start(server, self.playlists[server.id].list[0])    #autoplay
                self.mp_pause(server)
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
    if not os.path.isdir(music_cache_path):
        print('Creating music cache folder')
        os.makedirs(music_cache_path)
    if not os.path.isdir(playlist_path):
        print('Creating /playlists folder')
        os.makedirs(playlist_path)

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

    bot.loop.create_task(music_player.playlist_scheduler())
    print('Starting Music Player with codec: ' + codec)
#fn setup
