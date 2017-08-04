
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
import asyncio
import functools
import urllib.request
import youtube_dl
#from config import *

from .paths import music_cache_path, music_local_path

class Logger(object):
    def debug(self, msg):
        print(msg)
    def warning(self, msg):
        pass
    def error(self, msg):
        print(msg)

ydl_options = {
    'source_address': '0.0.0.0',
    'format': '139/bestaudio/best', #priority 139=lightweight m4a
    'extractaudio': True,
    #'audioformat': "mp3",
    #'restrictfilenames': True,
    #'noplaylist': True,
    'nocheckcertificate': True,
	#'ignoreerrors': False,
    'ignoreerrors': True,
	#'logtostderr': False,
    'logger': Logger(),
    'quiet': True,
    'no_warnings': True,
    #'outtmpl': "data/audio/cache/%(id)s",
    'outtmpl': music_cache_path + '\\' + '%(title)s-%(extractor)s-%(id)s.%(ext)s',
    'default_search': 'auto'
}


class Downloader:
    def __init__(self):
        self.threadpool = ThreadPoolExecutor(max_workers=2)
        self.ydl = youtube_dl.YoutubeDL(ydl_options)

    async def extract(self, loop, url, **kwargs):
        #functools creates a callable
        return await loop.run_in_executor(self.threadpool,
        functools.partial(self.ydl.extract_info, url, **kwargs))    #ret callable dict

    """
    async def extract_m4a(self, loop, info):  #custom m4a extractor
        return await loop.run_in_executor(self.threadpool,
        functools.partial(self.extract_info_m4a, info))             #ret callable str 'filename'

    def extract_info_m4a(self, info):
        url_m4a = info['formats'][0]['url']
        filename = music_cache_path + '\\' + info['title'] +'-'+ info['extractor'] +'-'+ info['id'] + '.m4a'
        if os.path.isfile(filename):    #already downloaded
            print('Song already downloaded')
            pass
        else:   #dl file
            m4a = urllib.request.urlopen(url_m4a)
            f = open(filename, 'wb')
            f.write(m4a.read())
            f.close()
        return filename
    """
"""
class Downloader(threading.Thread):
    def __init__(self, url, max_duration=None, downloaded=False,
                 music_cache_path=music_cache_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url
        self.done = threading.Event()
        self.song = None
        self.failed = False
        self.downloaded = downloaded
        self.hit_max_length = threading.Event()
        self.yt = youtube_dl.YoutubeDL(youtube_dl_options)

    def run(self):
        try:
            self.get_info()
            if self.downloaded:
                self.download()
        except MaximumLength:
            self.hit_max_length.set()
        except:
            self.failed = True
        self.done.set()

    def get_info(self):
        video = self.yt.extract_info(self.url, download=False, process=False)
        self.song = Song(**video)

    def download(self):
        if not os.path.isfile(
            music_cache_path + '%(extractor)s' + '-' + self.song.title + '-' + self.song.id + '.' + '%(exts)s'):
            video = self.yt.extract_info(self.url)
            self.song = Song(**video)

#class Downloader
"""
