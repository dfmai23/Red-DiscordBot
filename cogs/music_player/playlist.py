
import os
import enum
import copy
import asyncio
from random import *
import json
import xml.etree.ElementTree as etree
import xml.dom.minidom
import re           #re.compile() and pattern matching
import youtube_dl

from tinytag import TinyTag as TTag
from .downloader import Downloader, music_cache_path, music_local_path
from .song import Song
from .paths import playlist_path, playlist_local_path, MAX_CHAR_LIMIT

author_name = 'Greedie_Bot'


class Playlist:
    def __init__(self, server_id, repeat, shuffle):
        self.title =  'Now Playing'
        self.list = []          #current playlist for each server
        self.now_playing = None
        self.cur_i = -1;        #current/now playing index
        self.order = []         #for when list is shuffled(or not)
        self.server_id = server_id  #id of server that playlist belongs tof
        self.repeat = repeat
        self.shuffle = shuffle

    def get_i(self, song):     #find song in playlist
        for i, pl_song in enumerate(self.list):
            #print(song.path, pl_song.path)
            #print(song, pl_song)
            if song.path == pl_song.path:
                return i        #returning index in playlist
        return None

    def in_playlist(self, song):     #find song in playlist
        for pl_song in self.list:
            if song.path == pl_song.path:
                return True
        return False

    def add(self, song):
        if self.in_playlist(song):   #song already in playlist
            return 2

        self.list.append(song)    #add to server's playlist
        self.order.insert(-1, len(self.list)-1) #add index at second to last element
        if self.shuffle: self.set_shuffle()
        return song #await self.bot.say('Added to playlist!~' + box(song.title + ' - ' + song.artist))

    def remove(self, name_or_index):
        #only index right now
        #if name_or_index.isnumeric():
        #    i = int(name_or_index)
        #elif self.in_playlist(name_or_index):

        i = int(name_or_index)
        if (i+1) > len(self.list):  #index to out of range
            return [3, None]
        song = self.list.pop(i)
        print(song.title, song.artist)
        if len(self.list) == 0:       #empty playlist, stop
            self.cur_i = -1
            return [2, song]
        elif i != self.cur_i:       #removed a song
            self.order.pop(-2)      #second to last element
            if i < self.cur_i:
                self.cur_i -= 1     #removed a song before now playing, have to shift index one back
            return [0, song]        #keep playing though
        elif i == self.cur_i:       #removed current playing song from playlist
            self.order.pop(-2)
            return [1, song]        #play next song which is now the current index so dont have to change it

    def clear(self):
        self.list = []
        self.cur_i = -1
        self.order = []
        self.now_playing = None

    def view(self):
        playlist = []
        temp_playlist = ""
        for i, song in enumerate(self.list):   #enumerate for index
            print(str(i), song.title)
            if len(temp_playlist) > MAX_CHAR_LIMIT: #discord max message limit
                playlist.append(temp_playlist)
                temp_playlist = ""
            song_display = str(i)+'. ' + song.display()
            if i == self.cur_i:            #currently playing song
                cur_song = song_display
            temp_playlist += (song_display + '\n')
        playlist.append(temp_playlist)
        settings = "Repeat: " +  str(self.repeat) + '\tShuffle: ' + str(self.shuffle)
        return [cur_song, playlist, settings]

    def set_repeat(self):       #check if repeat and updates order accordingly
        if self.repeat:     #finds index which points to i=None
            i = self.order.index(None)
            self.order[i] = 0
        else:       #repeat off
            i = self.order.index(0)
            self.order[i] = None

    def set_shuffle(self):
        if self.shuffle:        #have to make it noncyclic
            seed()
            unused = copy.deepcopy(self.order)
            new_order = []
            i = 0

            while i < len(self.order):            #randomizing list one at a time
                randval = choice(unused)     #grab random val
                #print('rand:', randval, '\ti:', i, '\tnew_ord:', new_order, '\tunused:', unused, len(self.order))
                #val does not index back to itself and val does not point to an old index which points back to the new index(i)
                if randval != i:
                    try:
                        if randval < i and new_order[randval] == i:
                            continue
                    except TypeError:   #for NoneType
                        pass
                    new_order.append(randval)
                    unused.remove(randval)
                    i+=1

            self.order = new_order
        else:   #normal order
            self.order = sorted(
                self.order, key=lambda x: (x is None or x is 0, x))  #0 or none put to the end   htts://stackoverflow.com/questions/18411560

    def save(self, playlist_name, server, author=author_name, overwrite=0):
        ftypes = r'(xml)$'
        if '.xml' in playlist_name:
            playlist_name = playlist_name.strip('.xml')

        server_pl_path = playlist_path + "\\" + self.server_id
        pl_path_full = self.get_file(playlist_name+'.xml', server_pl_path)
        if  pl_path_full != None and overwrite==0:
            return 1
        elif pl_path_full != None and overwrite==1:
            os.remove(pl_path_full)

        root = etree.Element('smil')
        head = etree.SubElement(root, 'head')
        body = etree.SubElement(root, 'body')
        seq  = etree.SubElement(body, 'seq')

        head_gen = etree.SubElement(head, 'meta', name="Generator", content="Greedie_Bot v1.0")
        head_server = etree.SubElement(head, 'server', server=server.name, id=server.id)
        head_author = etree.SubElement(head, 'author', name=author)
        head_title = etree.SubElement(head, 'title')
        head_title.text = playlist_name        #default title will be same as file name

        for song in self.list:            #for every song in playlist, make new sub element
            if song.url == None:
                seq_media = etree.SubElement(seq, 'media', src=song.path)
            else:
                seq_meda = etree.SubElement(seq, 'media', src=song.path, url=song.url, vlength=str(song.length))
            #print(seq_media)

        pl_path_full = playlist_path + '\\' + self.server_id + '\\' + playlist_name + '.xml'
        f = open(pl_path_full, 'wb')      #b=binary mode, read docs, has conflict depending on encoding
        #hierarchy = etree.ElementTree(root)
        #hierarchy.write(f, encoding='utf-8', xml_declaration=True)

        xml_str = etree.tostring(root)                          #print element type to a string
        xml_str_parsed = xml.dom.minidom.parseString(xml_str)   #reparse with minidom
        xml_str_pretty = xml_str_parsed.toprettyxml()           #make it pretty
        f.write(xml_str_pretty.encode('utf-8'))                 #convert it back to xml
        f.close()
        return 0

    def load(self, playlist_name, server, **kwargs):
        init = kwargs.get('init')   #default is None
        server_pl_path = playlist_path + '\\' + self.server_id
        ftypes = r'(xml|wpl)$'
        if not init:    #searches bot path first, then local path
            pl_path_full = self.find_file(playlist_name, server_pl_path, ftypes)
            if pl_path_full == None:
                pl_path_full = self.find_file(playlist_name, playlist_local_path, ftypes)
        else:
            pl_path_full = self.get_file(playlist_name, server_pl_path)    #saved_playlist.xml
        #print(pl_path_full)

        if pl_path_full == None and init == True:   #couldnt find default playlist make new one
            if not os.path.isdir(server_pl_path):
                os.makedirs(server_pl_path)
            self.save(playlist_name, server)
            return self
        elif pl_path_full == None:                  #couldnt find playlist from command
            return 1
        tree = xml.etree.ElementTree.parse(pl_path_full)
        root = tree.getroot()
        #print(root[0])     #<head/>
        #print(root[1])     #<body/>
        #print(root[1][0])  #<seq/>
        self.title = root[0][2].text #title

        for i, media in enumerate(root[1][0]):
            media_src = media.get('src')
            media_url = media.get('url')

            print('  ', i, media_src)
            pattern = r'^(\.{2})'       # ".."  local music library base path
            if re.match(pattern, media_src):  #if the string matches the pattern, find song in local library
                media_path_full = re.sub(pattern, music_local_path, media_src, count=1)
                media_path_full = '\\' + media_path_full #hackish, re.sub removes the first backslash for some reason
            else:
                media_path_full = media_src
            #print(i, media_path_full)

            song_file = os.path.basename(media_path_full)
            base_path = os.path.dirname(media_path_full)
            if self.get_file(song_file, base_path) == None and media_url == None:
                print("\tFile not found, skipping: %s" % media_path_full)
                continue
            elif media_url != None:
                after_title = r'-(youtube|bandcamp|soundcloud)(.*)$'
                media_title = re.split(after_title, media_src)[0]
                media_title = media_title.strip(music_cache_path+'\\')  #before title
                #print('  ', media_title)
                song = Song(media_title, int(media.get('vlength')), media_path_full, media_url)
            else:
                tags = TTag.get(media_path_full)
                if tags.title == None:
                    pattern = r'\.(mp3|m4a)$'
                    tags.title = song_file.strip(pattern)
                if tags.artist == None:
                    tags.artist = ''
                song = Song(tags.title, tags.duration, media_path_full, None, tags.artist)
            self.list.append(song)
            self.order.append(len(self.list))

        if len(self.list) > 0:  #not empty playlist
            if self.repeat:     #init repeat/end of list
                self.order[-1] = 0
            else:               #no REPEAT
                self.order[-1] = None
            if self.shuffle:
                self.set_shuffle()
        return self


    """________________Helper Fn's________________"""
    def find_file(self, search_term, base_path, ftype):    #pattern matching
        #r'' string literal to make trivial to have backslashes
        pattern = r'^(.*)' + search_term + r'(.*\.)' + ftype
        for root, dirs, files in os.walk(base_path):
            for name in files:
                if re.search(pattern, name, re.IGNORECASE):            #if pattern matches string (name)
                    file_path_full = os.path.join(root, name)
                    return file_path_full
        return None

    def get_file(self, filename, base_path):         #get specific file
        file_path_full = os.path.join(base_path, filename)
        #print(file_path_full)
        if os.path.isfile(file_path_full):
            return file_path_full
        return None
