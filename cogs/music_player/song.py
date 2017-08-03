
class Song:
    def __init__(self, title, length, path, url, artist=''):
        self.title = title
        self.length = length
        self.path = path        #path as unique id
        self.url = url          #url also determines type, local or from url
        self.artist = artist    #no url ->no artist

    def display(self):   #formats song chat printing, mainly checking if is a urlsong
        song_display = self.title
        if self.url == None: #is local song
            song_display = song_display + ' - ' + self.artist
        return song_display
#class Song
