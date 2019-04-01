# do i need vol, repeat ... save_playlists???


#media player global settings

default_cfg = { "AUTOJOIN": True,
                "AUTOJOIN_CHANNELS": {},
                "DEFAULT_SERVER_SETTINGS": {
                        "VOLUME": 0.5,
                        "REPEAT": True,
                        "SHUFFLE": False,
                        "VOTE_RATIO": 0.5,
                        "VOTES_REQUIRED": 3,
                        "SAVE_PLAYLIST": True,
                },
                "SERVER_SETTINGS": {}
            }

config_path = 'data\music\config.json'
default_playlist = 'Now Playing.xml'

music_cache_path = 'data\music\cache'
music_local_path = 'D:\Music'
#music_local_path = '\\' + '\\' + 'MAI-PC\Music'

playlist_path = 'data\music\playlists'
playlist_local_path = 'D:\Music\Playlists'
#playlist_local_path = '\\\\MAI-PC\Music\Playlists'

MAX_CHAR_LIMIT = 1900

