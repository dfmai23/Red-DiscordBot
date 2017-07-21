import sys
import threading
#from config import *

music_cache_path = 'data\music\cache'
music_local_path = 'D:\Music'

youtube_dl_options = {
    'source_address': '0.0.0.0',
    'format': 'bestaudio/best',
    'extractaudio': True,
    #'audioformat': "mp3",
    #'restrictfilenames': True,
    #'noplaylist': True,
    'nocheckcertificate': True,
	#'ignoreerrors': False,
    'ignoreerrors': True,
	#'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    #'outtmpl': "data/audio/cache/%(id)s",
    'outtmpl': music_cache_path + '%(extractor)s-%(title)s-%(id)s.%(ext)s',
    'default_search': 'auto'
}


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
