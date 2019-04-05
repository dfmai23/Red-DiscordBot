
__author__ = "dfmai23"

import discord
from discord.ext import commands
import os
import threading
import asyncio
import logging
import subprocess
import random
import json
import xml.etree.ElementTree as etree
import xml.dom.minidom
import re           #re.compile() and pattern matching
import youtube_dl
import time

from tinytag import TinyTag as TTag
from .utils.chat_formatting import *
from .utils import checks

from .music_player.startup import *
from .music_player.downloader import Downloader, music_cache_path, music_local_path
from .music_player.playlist import Playlist, playlist_path, playlist_local_path #, default_playlist
from .music_player.song import Song
from .music_player.paths import *
from .music_player.state import State

log = logging.getLogger(__name__)



class Music_Player:
    def __init__(self, bot, codec):
        self.bot = bot              #class discord.Client
        self.settings = {}
        self.server_settings = {}   #server specfic settings
        self.playlists = {} #music queues for each server
        self.states = {}    #status of each music player, ie. playing/paused
        self.games = {}
        self.game = None
        self.downloader = Downloader()
        self.bot.loop.create_task(self.init_autojoin())   #ensure_future wont block execution (fn always return immediately)
    #joins voice channel by channel id
    #def autojoin_channel(

    """————————————————————Commands Music Player————————————————————"""
    @commands.command(pass_context=True)
    async def play(self, ctx, *, song_or_url=None): # *args = positional only varargs
        """ Plays/resumes current song or plays new song """

        server = ctx.message.server
        cur_state = self.states[server.id]
        pl = self.playlists[server.id]
        mp = self.get_mp(server)

        #print("play song_or_url: " + song_or_url)
        if song_or_url is not None:
            tasks = [self.add_song(ctx, song_or_url)]   # running it synchornously,
            await asyncio.wait(tasks)                   #can also do with loop.run_until_complete???

            song = pl.list[-1]
            self.mp_stop(server)
            self.mp_start(server, song)
            song_display = str(len(pl.list)-1) + ". " + song.display()
            await self.bot.say('Jumping to song: ' + box(song_display))
            return

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
        """Pauses current song """
        server = ctx.message.server
        self.mp_pause(server)
        await self.bot.say("Pausing music!~")

    @commands.command(pass_context=True)
    async def stop(self, ctx):
        """Stops current song"""
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
        if next_song == None:  #reached end of playlist
            await self.bot.say("Reached end of Playlist!~")
            return
        nxt_song_display = next_song.display()
        self.mp_start(server, next_song)
        await self.bot.say('Playing next song!~\n' + box(nxt_song_display))
        await self.check_nextnext_song(server)

    @commands.command(pass_context=True)
    async def prev(self, ctx):
        """Plays previous song"""
        server = ctx.message.server
        mp = self.get_mp(server)
        pl = self.playlists[server.id]
        self.mp_stop(server)

        prev_i = pl.order.index(pl.cur_i)
        prev_song = pl.list[prev_i]
        self.mp_start(server, prev_song)

    @commands.command(pass_context=True)
    async def replay(self, ctx):
        """Restarts current song"""
        server = ctx.message.server
        mp = self.get_mp(server)
        pl = self.playlists[server.id]
        self.mp_stop(server)
        self.mp_start(server, pl.list[pl.cur_i])

    @commands.command(pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def status(self, ctx):
        """Displays music player status"""
        server = ctx.message.server
        state = self.states[server.id]
        await self.bot.say("Music Player is currently: " + state.value + '~')

    @commands.command(pass_context=True)
    async def volume(self, ctx, decimal=None):    #keyword decimal to display on help
        """Set/Display volume between 0.0 and 1.0"""
        server = ctx.message.server
        voice_client = self.bot.voice_client_in(server)
        mp = voice_client.music_player

        if decimal==None:
            await self.bot.say("Volume is at " + str(mp.volume))
            return

        val = float(decimal)
        if val > 1.0 or val < 0.0:
            await self.bot.say("Volume must be between 0 and 1.0!~")
            return

        if voice_client == None:
            await self.bot.say("Voice client not connected yet! Please join a voice channel and play music!~")
            return
        if not hasattr(voice_client, 'music_player'):
            await self.bot.say("Please play some music!")
            return

        mp.volume = val
        self.server_settings[server.id]["VOLUME"] = val
        await self.bot.say("Music player volume set to:  " + str(val) + '~')

    @commands.command(pass_context=True)
    async def songinfo(self, ctx):
        """ Displays current playing song info """
        server = ctx.message.server
        pl = self.playlists[server.id]
        song = pl.now_playing
        songinfo = song.info()
        await self.bot.say(box(songinfo))


    """————————————————————_Commands Playlist————————————————————"""
    @commands.command(pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def pinfo(self, ctx, url):
        """ DEBUG: Playlist URL info debug"""
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

    @commands.command(pass_context=True)
    async def add(self, ctx, *, song_or_url):   #*, = positional args as single str
        """ Add a song (local or URL) to the playlist """
        await self.add_song(ctx, song_or_url)

    """Adds a url playlist to the playlist
        -if current playlist is empty, will load it as a new playlist  """
    @commands.command(pass_context=True)
    async def add_playlist(self, ctx, url):
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
    #@checks.mod_or_permissions(administrator=True)
    async def remove(self, ctx, name_or_index):     #removes a song from playlist
        """Removes song from playlist by index/searching song name"""
        server = ctx.message.server
        pl = self.playlists[server.id]
        mp = self.get_mp(server)

        result, song = pl.remove(name_or_index)
        if result == 4:
            await self.bot.say("Couldn't find song in playlist!~")
        elif result == 3:
            await self.bot.say("Playlist index not in range!~")
        elif result == 2:
            await self.bot.say("Playlist now empty!")
            mp.stop()
        elif result == 1:
            await self.bot.say("Removed currently playing song! Playing next song~")
            mp.stop()
            mp.start(server, pl.cur_i)
        else:
            song_display = song.display()
            await self.bot.say("Removed from playlist!~\n" + box(song_display))

    @commands.command(pass_context=True)
    async def search(self, ctx, *, searchterm):
        """Searches a song on youtube and gets top result """
        server = ctx.message.server
        channel = ctx.message.channel
        pl = self.playlists[server.id]

        info = await self.downloader.extract(self.bot.loop, searchterm, download=False, process=False)
        if info.get('url', '').startswith('ytsearch'):  # ytdl options allow us to use search strings as input urls
            info = await self.downloader.extract(self.bot.loop, searchterm, download=False,process=True)
            if not all(info.get('entries', [])):
                await self.bot.say('Couldnt find a song!~')
                return
            url = info['entries'][0]['webpage_url']    # TODO: handle 'webpage_url' being 'ytsearch:...' or extractor type
            await self.add_song(ctx, url)
        else:
            await self.bot.say('Couldn\'t search!~')    # *, = positional args as single str

    @commands.command(pass_context=True)
    async def skipto(self, ctx, name_or_index):
        """Skip playlist to index/song name"""
        server = ctx.message.server
        pl = self.playlists[server.id]
        mp = self.get_mp(server)

        if name_or_index.isnumeric():
            i = int(name_or_index)
            if (i + 1) > len(pl.list):
                await self.bot.say('Index out of range!~')
                return
        else:
            searchterm = name_or_index
            song = pl.search_song(searchterm)
            if song is None:
                await self.bot.say("Song not found!~")
                return
            i = pl.get_i(song)

        song = pl.list[i]
        self.mp_stop(server)
        self.mp_start(server, song)
        song_display = str(i) + ". " + song.display()
        await self.bot.say('Jumping to song: ' + box(song_display))

    @commands.command(pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def clear(self, ctx):
        """Clears current playlist"""
        server = ctx.message.server
        mp = self.get_mp(server)
        pl = self.playlists[server.id]
        self.mp_stop(server)
        pl.clear()
        await self.bot.say("Cleared playlist!~")

    @commands.command(pass_context=True)
    async def view(self, ctx):              #View current playlist
        """Views current playlist"""
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
    async def view_playlists(self, ctx, local=None):
        """Views cached or local playlists """
        server = ctx.message.server
        server_pl_path = playlist_path + '\\' + server.id
        pl_cached = ''
        pl_local = ''
        pattern = r'\.(xml|wpl)$'

        if local is None:
            for root, dirs, files in os.walk(server_pl_path):
                for name in files:
                    pl_cached += re.split(pattern, name)[0] + '\n'
            await self.bot.say('Cached playlists:\n' + box(pl_cached))
        elif local == 'local':
            for root, dirs, files in os.walk(playlist_local_path):
                for name in files:
                    pl_local += re.split(pattern, name)[0] + '\n'
            await self.bot.say('Local playlists:\n' + box(pl_local))
        else:
            await self.bot.say('Use "local" parameter to view local playlists!~')

    @commands.command(pass_context=True)
    async def repeat(self, ctx, onoff=None):
        """Set/display repeat"""
        server = ctx.message.server
        pl = self.playlists[server.id]
        if not (onoff in {'on', 'off', None}):
            await self.bot.say('Parameter must be "on" or "off"!~')
            return
        elif onoff == 'on':
            pl.repeat = True
        elif onoff == 'off':
            pl.repeat = False
        else: #display repeat status
            #await self.bot.say('Repeat is ' + ('on' if pl.repeat==True else 'off'))
            await self.bot.say('Repeat is ' + ('on' if pl.repeat == True else 'off'))
            return
        pl.set_repeat()
        await self.bot.say("Repeat set to %s!~" % onoff)

    @commands.command(pass_context=True)
    async def shuffle(self, ctx, onoff=None):
        """Set/Display shuffle"""
        server = ctx.message.server
        pl = self.playlists[server.id]
        if not (onoff in {'on', 'off', None}):
            await self.bot.say('Parameter must be "on" or "off"!~')
            return
        elif onoff == 'on':
            pl.shuffle = True
        elif onoff == 'off':
            pl.shuffle = False
        else: #display shuffle status
            await self.bot.say('Shuffle is ' + ('on' if pl.shuffle==True else 'off'))
            return
        pl.set_shuffle()
        await self.bot.say("Shuffle set to %s!~" % onoff)

    @commands.command(pass_context=True)
    async def save_playlist(self, ctx, *, playlist_name):       #builds own xml
        """Saves current playlist to cache"""
        author = ctx.message.author
        server = ctx.message.server
        pl = self.playlists[server.id]

        pl_saved = pl.save(playlist_name, server, author.name)
        if pl_saved == 1:
            await self.bot.say("Already have a playlist with same name! Overwrite? Y/N~")
            reply = await self.bot.wait_for_message(author=author, channel=ctx.message.channel, check=self.check_reply)
            if reply.content in ['yes', 'y', 'Y']:
                pl_saved = pl.save(playlist_name, server, author.name, overwrite=1)
            elif reply.content in ['no', 'n', 'N']:   #reply=0
                await self.bot.say('Playlist not saved!~')
                return
        await self.bot.say("Saved playlist: %s!~" % playlist_name)

    @commands.command(pass_context=True)    #wrapper
    async def load_playlist(self, ctx, pl):
        """Loads the specified playlist"""
        server = ctx.message.server
        await self.bot.say("Loading playlist please wait!~")
        pl_loaded = self.load_pl(server, pl)
        if pl_loaded == None:
            await self.bot.say("Can't find playlist to load!~")
            return
        #self.mp_reload(server)
        self.mp_stop(server)
        self.mp_start(server, self.playlists[server.id].list[0])    #autoplay

    @commands.command(pass_context=True)
    async def delete_playlist(self, ctx, *, pl_name):        #deletes by playlist filename bar ext
        """Deletes the specified playlist"""
        server = ctx.message.server
        pl_path = playlist_path + '\\' + server.id

        ftype = 'xml'
        pl_path_full = self.get_file(pl_name, pl_path, ftype)
        if pl_path_full == None:
            await self.bot.say ("Can't find playlist to delete!~")
        else:
            os.remove(pl_path_full)
            await self.bot.say ("Deleted playlist: %s!~" % pl_name)


    """————————————————————Commands Server————————————————————"""
    @commands.command(pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def join_vc(self, ctx):
        """ Joins voice channel """
        author = ctx.message.author     #ctx = context
        server = ctx.message.server
        channel = author.voice_channel  #channel to join

        if self.bot.is_voice_connected(server):
            voice_client = self.bot.voice_client_in(server)
            if voice_client.channel.id == author.voice_channel.id:
                await self.bot.say("Already connected to your channel!~")
                return
            await voice_client.disconnect()

        await self.bot.join_voice_channel(channel)          #joins owners voice channel only
        self.mp_reload(server)

    @commands.command(pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def leave_vc(self, ctx):
        """Leave voice channel"""
        server = ctx.message.server
        print("Leaving voice channel of " + server.name)

        if self.bot.is_voice_connected(server):
            voice_client = self.bot.voice_client_in(server)
            await voice_client.disconnect()
        else:
            print("Unable to leave voice channel!")

    @commands.command(pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def rejoin(self, ctx):
        """Rejoin voice channel"""
        server = ctx.message.server
        author = ctx.message.author
        voice_client = self.bot.voice_client_in(server)
        channel = voice_client.channel
        await voice_client.disconnect()
        await self.bot.join_voice_channel(channel)
        self.mp_reload(server)

    @commands.command(pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def stat(self, ctx):
        """DEBUG: media player info debug"""
        server = ctx.message.server
        print("----------FN stat()----------")
        vc = self.bot.voice_client_in(server)
        channel = vc.channel
        mp = vc.music_player
        pl = self.playlists[server.id]
        #print(music_cache_path + '%(extractor)s' + '-' + '%(exts)s')
        #str = music_cache_path + '%(extractor)s' + '-' + '%(exts)s'

        print(server.id, server.name)
        print('  ' + channel.id, channel.name)

        print('playlist name: ' + pl.title)
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


    """————————————————————Generics————————————————————"""
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
        # print (self.bot.is_voice_connected(server))
        # print(voice_client)
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
        self.bot.loop.create_task(self.set_game(audio))

    def mp_stop(self, server):
        music_player = self.get_mp(server)
        music_player.stop()
        self.states[server.id] = State.STOPPED

    def mp_reload(self, server):
        pl = self.playlists[server.id]

        try: self.mp_stop(server)
        except: pass

        #if index==None: song = pl.list[pl.cur_i]
        #else: song = pl.list[index]
        song = pl.list[0]
        self.mp_start(server, song)
        self.mp_pause(server)       #restarts music player in a robust fashion to first song in playlist

    def get_mp(self, server):             #get music player of current server
        voice_client = self.bot.voice_client_in(server)
        music_player = voice_client.music_player
        return music_player

    """Adds a song to the playlist
        -Checks if its a url or local song
        -Will add to playlist
        -Autoplay if only one in playlist """
    async def add_song(self, ctx, song_or_url):
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
            info = await self.downloader.extract(self.bot.loop, url, download=False, process=False)    #get info only
            if info['extractor_key'] in ['YoutubePlaylist', 'SoundcloudSet', 'BandcampAlbum']:
                await self.bot.say('Please use "add_p" command for URL playlists!')
                return
            info = await self.downloader.extract(self.bot.loop, url)    #get info and download song
            pattern = r'\<|\>|\:|\"|\/|\\|\||\?|\*'
            info['title'] = re.sub(pattern, '_', info['title'])
            print(info['title'])
            song_path_full = music_cache_path + '\\' + info['title'] +'-'+ info['extractor'] +'-'+ info['id'] + '.' + info['ext']
            song = Song(info['title'], info['duration'], song_path_full, info['webpage_url'])
        else:    #find local file in library
            name = song_or_url
            ftype = r'(m4a|mp3|webm)$'  #regular expression, $ = match the end of the string
            song_path_full = self.find_file(name, music_local_path, ftype)
            if song_path_full == None:  #song not in lib
                return 3
            tags = TTag.get(song_path_full)
            if tags.title == None:
                pattern = r'\.(mp3|m4a)$'
                tags.title = os.path.basename(song_path_full).strip(pattern)
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

    async def get_nxt_song(self, server):
        pl = self.playlists[server.id]
        # if pl.repeat
        if pl.order[pl.cur_i] == None:  #reached end of playlist
            return None

        #print('cur_i: %d \tnext_i: %d' % (pl.cur_i, pl.order[pl.cur_i]))
        next_song_i = pl.order[pl.cur_i]
        next_song = pl.list[next_song_i]
        song_file = os.path.basename(next_song.path)
        base_path = os.path.dirname(next_song.path)
        print('Getting next song:', base_path+'\\'+song_file)
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

    async def set_game(self, song):
        self.game = list(self.bot.servers)[0].me.game
        status = list(self.bot.servers)[0].me.status
        game = discord.Game(name=song.title)
        await self.bot.change_presence(status=status, game=game)

        """
        if self._old_game is False:
            self._old_game = list(self.bot.servers)[0].me.game
        status = list(self.bot.servers)[0].me.status
        game = discord.Game(name=song.title)
        await self.bot.change_presence(status=status, game=game)
        """

    """Loads a local/saved playlist
        -will create empty Playlist() class
        -if init is on then will search specifically for "saved_playlist.xml" from data/music
        -else will search for playlist with closest name
        -if init is on will also create server playlist path if not found and load the empty playlist
        -processes the playlist """
    def load_pl(self, server, playlist_name, **kwargs):          #** = forces keyword arg in caller
        server_cfg = self.server_settings[server.id]
        print("server_cfg:" + str(server_cfg))
        playlist = Playlist(server.id, server_cfg["REPEAT"], server_cfg["SHUFFLE"])   #create empty playlist
        try:
            self.mp_stop(server)
        except:
            pass
        self.playlists[server.id] = playlist.load(playlist_name, server, **kwargs)

        if self.playlists[server.id] == None:
            return None
        # self.playlists[server.id].view()

    async def load_url_pl(self, server, info, playlist):     #returns a list of Songs
        url_playlist = []
        base_url = info['webpage_url'].split('playlist?list=')[0]
        for entry in info['entries']:
            if entry:       #check deleted vids
                try:        #check blocked vids
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
                except:
                    pass
        return url_playlist


    """————————————————————Helper Fn's————————————————————"""
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


    """————————————————————Management————————————————————"""

    #saves playlists and configs
    async def shutdown_watcher(self, message):  #catch at message before it actually does anything
        prefixes = self.bot.settings.prefixes
        if (message.content in [prefix + 'shutdown' for prefix in prefixes] or
        message.content in [prefix + 'restart' for prefix in prefixes]):
            for server in self.bot.servers:
                try:
                    pl = self.playlists[server.id]
                    pl.save(default_playlist, server, overwrite=1)
                    self.mp_stop(server)
                    print('Saving playlist:', server.id, server.name)
                except:
                    print('Couldn\'t save playlist:', server.id, server.name)
                    pass
            #self.save_config()
            return

    #basically asynchronously polls music player to see if its playing or not
    async def playlist_scheduler(self):
        while self == self.bot.get_cog('Music_Player'): #while music player class is alive
            tasks = []
            #playlists = copy.deepcopy(self.playlists)
            for server_id in self.playlists:             #returns the key for each playlist
                if len(self.playlists[server_id].list) == 0:     #do nothing if playlist empty
                    continue        #skip rest of loop
                #full concurrency, creates task for each server
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
                print(server.id, server.name)
                next_song = await self.get_nxt_song(server)
                if next_song == None:  #repeat off, end of playlist
                    print('repeat off, Next song is NoneType')
                    pass
                else:
                    self.mp_start(server, next_song)
                await self.check_nextnext_song(server)  #last so next song can play first
        except:
            pass

    async def voice_channel_watcher(self):
        while self == self.bot.get_cog('Music_Player'):
            for vc in self.bot.voice_clients:
                server = vc.server
                channel = vc.channel
                if len(channel.voice_members) == 1 and self.states[server.id] != State.STOPPED:
                    self.mp_stop(server)
                    print('Channel empty, stopping music:', server.name, channel.name)
            await asyncio.sleep(5)  #stops music when channel is empty

    def save_config(self):      #save config for current server
        config_file = open(config_path, 'w')
        json.dump(self.settings, config_file, indent=4) #in:self.settings, out:config_file
        print('Saving config for servers')


    """————————————————————MP Initialization's————————————————————"""
    def init_settings(self):
        print('----------Media Player----------')
        print('Loading settings')
        self.settings = json.load(open(config_path, 'r'))
        self.server_settings = self.settings["SERVER_SETTINGS"]
        server_cfg = self.settings["DEFAULT_SERVER_SETTINGS"]

        for server in self.bot.servers:
            if not server.id in self.server_settings:   #create new default server settings
                print(' Server settings for %s %s not found, creating defaults' % (server.id, server.name))
                self.server_settings[server.id] = server_cfg
        self.save_config()

    """Initializes playlists by:
        -creating empty queues for each server
        -reading saved saved playlist
        -loading playlist    """
    """Initializes autojoining by:
        -autojoining channels from settings file and owner channel
        -loading its last playlist
        -starts playing if channel not empty  """
    def init_playlists(self):
        print('Loading Playlists')
        playlists = {}      #map
        for server in self.bot.servers:
            print(' ', server.id, server.name)
            self.load_pl(server, default_playlist, init=True)

    def init_states(self):
        print('Loading default states')
        states = {}
        for server in self.bot.servers:
            states[server.id] = State.STOPPED
        self.states = states

    def init_games(self):
        for server in self.bot.servers:
            self.games[server.id] = None

    async def init_autojoin(self):
        print('Autojoining Channels')
        # for cid in self.settings["AUTOJOIN_CHANNELS"]:
        #     print("channels: " + cid)
        # print("autojoin: " + str(self.settings["AUTOJOIN"]))
        states = []
        if self.settings["AUTOJOIN"] is True:
            try:
                for c_id in self.settings["AUTOJOIN_CHANNELS"]:
                    channel= self.bot.get_channel(c_id) #channel to join
                    server = channel.server
                    try:
                        voice_client = await self.bot.join_voice_channel(channel)
                        print("Voice Client: " + voice_client.user.name)
                        print('  Joining channel:', server.id, server.name, ', ', channel.id, channel.name)
                        #await self.bot.send_message('Hi!~')
                    except Exception as e:
                        print("Exception: " + str(e))
                    except:
                        print('  Already in channel, skipping:', server.id, server.name, ', ', channel.id, channel.name)

                    try:    #autoplay
                        self.mp_start(server, self.playlists[server.id].list[0])
                        #self.mp_pause(server)
                    except:
                        print('Empty playlist, skipping autoplay')
            except Exception as e:
                print("Exception: " + str(e))
                print("Cannot join channels, try reloading cog after initial start!~")
#class Music Player


def setup(bot):
    check_cfg()
    check_ytdl()
    codec = check_codec()

    music_player = Music_Player(bot, codec=codec)  # Praise 26
    bot.add_cog(music_player)

    #Music Player initializations after it has connected to servers
    music_player.init_settings()
    music_player.init_playlists()
    music_player.init_states()
    music_player.init_games()

    bot.add_listener(music_player.shutdown_watcher, 'on_message')
    bot.loop.create_task(music_player.playlist_scheduler())
    bot.loop.create_task(music_player.voice_channel_watcher())
    #bot.loop.create_task(music_player.music_player_watcher())
    print('Starting Music Player with codec: ' + codec)
#fn setup
