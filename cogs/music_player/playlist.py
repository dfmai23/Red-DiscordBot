#from cogs.utils.chat_formatting import *

#from downloader import music_local_path
playlist_path = 'data\music\playlists'
playlist_local_path = 'D:\Music\Playlists'

class Playlist:
    def __init__(self):
        self.list = []          #current playlist for each server
        self.now_playing = None
        self.cur_i = -1;        #current/now playing index
        self.play_order = []

    def search(self, song):     #find song in playlist
        for i, pl_song in enumerate(self.list):
            #print(pl_song)
            if song == pl_song:
                return i        #returning index in playlist
        return None


    """
    def add(self, song):
        if self.search(song) != None:
            return 2    #already in playlist

        self.list.append(song) #add to server's playlist

        if len(self.list) == 1:
            return 1    #autoplay on

        return 0        #autoplay off, song added
    """

    #def load_playlist(self, xmltree)
