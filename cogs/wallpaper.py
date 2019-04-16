import discord
from discord.ext import commands
import traceback
import asyncio
import os
import json
import sqlite3
import pprint

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import time
import datetime

from .utils.chat_formatting import *
from .utils import checks

default_server_cfg = {
    "server_name": "undefined",
    "CHANNEL": "undefined",     #channel to post to
    "CHANNEL_NAME": "undefined",
    "TIME_POST": "12:00",       #default time to post wp everyday
    "CATEGORIES": []
}

default_cfg = {
    "SERVER_SETTINGS": {}
}

config_path = 'data\wallpaper\\'
config_file = 'config.json'
dbread_path = 'data\wallpaper\\'
dbread_file = 'WallpaperMaster.db3'
dbwrite_path = 'data\Wallpaper\\'
dbwrite_file = 'WallpaperBot.db3'

class Wallpaper:
    def __init__(self, bot):
        self.bot = bot
        self.settings = {}          #global settings
        self.server_settings= {}    #server specific settings

    """————————————————————TESTING————————————————————"""

    @checks.mod_or_permissions(administrator=True)
    @commands.command(pass_context=True)
    async def set_wpchannel(self, ctx, channel_id):
        """ Set the channel to schedule posts to """
        server = ctx.message.server
        channel = server.get_channel(channel_id)
        print("channel: %s  type: %s " % (channel.id, str(type(channel.id))))

        self.server_settings[server.id]["CHANNEL"] = channel.id
        self.server_settings[server.id]["CHANNEL_NAME"] = channel.name
        self.save_config()
        await self.bot.say("Assigned channel: %s to post daily wallpapers!~" % channel.name)

    @commands.command(pass_context=True)
    async def add_cats(self, ctx, *cats):
        """ Add the categories to pull pictures from """
        server = ctx.message.server

        if len(cats) == 0:
            await self.bot.say('Please add categories!~')
            return

        print("--------------------ADD CATS--------------------")
        print("adding categories")
        print("selected categories input: " + str(cats))
        conn = sqlite3.connect(dbread_path + dbread_file)
        rows = self.getcats_all(conn)

        dbcats = []
        cats_old = self.server_settings[server.id]["CATEGORIES"]
        cats_notfound = []
        cats_alreadyfound = []
        cats_new = []

        for row in rows:
            dbcats.append(row[0])
        for cat in cats:
            if cat not in dbcats:
                print('cat not found in db: ' + cat)
                cats_notfound.append(cat)
            elif cat not in cats_old:
                cats_new.append(cat)
            elif cat in cats_old:  # will skip cats already in the selected categories
                cats_alreadyfound.append(cat)
                pass
        self.server_settings[server.id]["CATEGORIES"] = cats_old + cats_new
        addcats = cats_old + cats_new

        print('DBCATS: ' + str(dbcats))
        print('ADDCATS_OLD: ' + str(cats_old))
        print('ADDCATS_NEW: ' + str(cats_new))
        print('ADDCATS: ' + str(addcats))
        print('CATS_NOTFOUND: ' + str(cats_notfound))
        print('CATS_ALREADYFOUND: ' + str(cats_alreadyfound))

        if len(cats_notfound) > 0:
            await self.bot.say('The following categories were not found and not added!~: ' + box(', '.join(cats_notfound)))
        if len(cats_alreadyfound) > 0:
            await self.bot.say('The following categories were already selected!~: ' + box(', '.join(cats_alreadyfound)))
        if len(cats_new) > 0:
            await self.bot.say('The following categories were added!~: ' + box(', '.join(cats_new)))
        await self.bot.say('The following categories now selected!~: ' + box(', '.join(addcats)))
        conn.close()

    @commands.command(pass_context=True)
    async def remove_cats(self, ctx, *cats):
        """ Remove the selected categories that pictures are pulled from """
        server = ctx.message.server
        if len(cats) == 0:
            await self.bot.say('Please select categories to remove!~')
            return

        print("--------------------REMOVE CATS--------------------")
        print("removing categories")
        print("selected categories input: " + str(cats))

        cats_old = self.server_settings[server.id]["CATEGORIES"]
        cats_notfound = []
        cats_removed = []

        for cat in cats:
            if cat not in cats_old:
                print('cat not found in settings: ' + cat)
                cats_notfound.append(cat)
            elif cat in cats_old:
                cats_removed.append(cat)
                cats_old.remove(cat)
        self.server_settings[server.id]["CATEGORIES"] = cats_old

        print('CATS_OLD: ' + str(cats_old))
        print('CATS_NOTFOUND: ' + str(cats_notfound))
        print('CATS_REMOVED: ' + str(cats_removed))
        if len(cats_notfound) > 0:
            await self.bot.say('The following categories were not found and not removed!~: ' + box(', '.join(cats_notfound)))
        if len(cats_removed) > 0:
            await self.bot.say('The following categories were removed!~: ' + box(', '.join(cats_removed)))
        await self.bot.say('The following categories now selected!~: ' + box(', '.join(self.server_settings[server.id]["CATEGORIES"])))

    @commands.command(pass_context=True)
    async def view_cats(self, ctx, cat_src=None):  #whether viewing categories from db or selected ones to pull from
        """ List the selected categories to pull pictures from or DB to choose from"""
        server = ctx.message.server

        if cat_src is None or cat_src in {'selected', 'set'}:   #no args = view selected ones
            print("--------------------view cats selected--------------------")
            cats_sel = self.server_settings[server.id]["CATEGORIES"]
            cat_display = []
            print(cats_sel)
            for cat in cats_sel:
                cat_display.append(cat)
            await self.bot.say('The selected categories are: ' + box('') if len(cats_sel)==0 else box(', '.join(cat_display)), delete_after=60)
            return
        elif cat_src == 'db':
            conn = sqlite3.connect(dbread_path + dbread_file)
            rows = self.getcats_all(conn)
            cat_display = ''

            print("--------------------view cats db-------------------")
            for row in rows:
                print(row[0])  # row still type: list
                # print(str(type(row[0])))
                cat_display += row[0] + '\n'

            await self.bot.say('The following categories are!~: ' + box(cat_display), delete_after=60)
            conn.close()
            return
        else:
            await self.bot.say('Please add either \'db\' or \'selected\'')

    @checks.mod_or_permissions(administrator=True)
    @commands.command(pass_context=True)
    async def save_cats(self, ctx):
        """ Save current wallpaper categories"""
        server = ctx.message.server

        print("--------------------SAVE CATS--------------------")
        print('cats: ' + str(self.server_settings[server.id]["CATEGORIES"]))
        cats = self.server_settings[server.id]["CATEGORIES"]

        try:
            self.save_config()
            await self.bot.say('Successfuly saved selected categories!~')
        except Exception as e:
            print("Exception: " + str(e))
            await self.bot.say('Unable to save selected categories!~')

    """ openS db
	    sql - get selected cats and respective id from db
	    sql - get random row which is in one of the selected cats
	    get the image location and post
	    save the image location to writable db and mark as posted 
	"""
    @checks.mod_or_permissions(administrator=True)
    @commands.command(pass_context=True)
    async def post_wp(self, ctx):  # *args = positional only varargs
        """ DEBUG, posts a wallpaper """
        server = ctx.message.server
        channel_id = self.server_settings[server.id]["CHANNEL"]
        channel = server.get_channel(channel_id)

        time_string = time.strftime("%H:%M:%S", time.localtime())
        print("[%s]----------POST--------------------" % time_string)
        print("posting to:")
        print("server:  %s   name: %s" % (server.id, server.name))
        print("channel: %s   name: %s" % (channel.id, channel.name))

        try:    #get db connections
            server_cats = self.server_settings[server.id]["CATEGORIES"]
            print('server categories: ' + str(server_cats))

            conn_read = sqlite3.connect(dbread_path + dbread_file)
            conn_read.row_factory = sqlite3.Row  # to make a row an Row object
            csr_read = conn_read.cursor()
            conn_write = sqlite3.connect(dbwrite_path + dbwrite_file)
            conn_write.row_factory = sqlite3.Row  # to make a row an Row object
            csr_write = conn_write.cursor()

            is_repeat = True;   count = 0;  num_tries = 5;
            while is_repeat == True and count < num_tries:  #until new image is found or 5 tries are done
                row = self.get_read_image(csr_read, server_cats)    #get random image
                checkrow = self.get_writeread_image(csr_write, row) #get same image if already in writeDB
                if checkrow is None:  #check if image found in writeDB
                    is_repeat = False       #not a repeat
                    print('TRY #%d, image not a duplicate, posting' % count)
                else:
                    count+=1
                    print('TRY #%d, image is a duplicate, getting another image' % count)
                await asyncio.sleep(.5)
            #while
            if count >= num_tries:
                print('unable to get image after %d tries, aborting' % count)
                return

            self.insert_image(csr_write, row)   #write image to writeDB

            filepath = row[2] + '\\' + row[3]
            print('filepath: '+ filepath)
            # await self.bot.send_file(channel, filepath)
            print('posted image: ' + filepath)

            #close connections
            conn_write.commit()
            conn_write.close()
            conn_read.close()
            print('saved posted image to writeDB')

        except discord.HTTPException as e:  #for send_file
            print('HTTPException: ' + str(e))
        except Exception as e:
            traceback.print_exc()   #print stack
            print('Exception: ' + str(e))
            await self.bot.say("Error! Unable to post!~")

    @commands.command(pass_context=True)
    async def wpstat(self, ctx):
        """ DEBUG, show settings """
        print("--------------------WP STAT--------------------")
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(self.settings)

    async def post_auto(self, server):
        channel_id = self.server_settings[server.id]["CHANNEL"]
        channel = server.get_channel(channel_id)

        time_string = time.strftime("%H:%M:%S", time.localtime())
        print("[%s]----------AUTO POST--------------------" % time_string)
        print("posting to:")
        print("server:  %s   name: %s" % (server.id, server.name))
        print("channel: %s   name: %s" % (channel.id, channel.name))

        try:    # get db connections
            server_cats = self.server_settings[server.id]["CATEGORIES"]
            print('server categories: ' + str(server_cats))

            conn_read = sqlite3.connect(dbread_path + dbread_file)
            conn_read.row_factory = sqlite3.Row     # to make a row an Row object
            csr_read = conn_read.cursor()
            conn_write = sqlite3.connect(dbwrite_path + dbwrite_file)
            conn_write.row_factory = sqlite3.Row    # to make a row an Row object
            csr_write = conn_write.cursor()

            is_repeat = True;
            count = 0;
            num_tries = 5;
            while is_repeat == True and count < num_tries:  # until new image is found or 5 tries are done
                row = self.get_read_image(csr_read, server_cats)    # get random image
                checkrow = self.get_writeread_image(csr_write, row) # get same image if already in writeDB
                if checkrow is None:    # check if image found in writeDB
                    is_repeat = False   # not a repeat
                    print('TRY #%d, image not a duplicate, posting' % count)
                else:
                    count += 1
                    print('TRY #%d, image is a duplicate, getting another image' % count)
                await asyncio.sleep(.5)
            # while
            if count >= num_tries:
                print('unable to get image after %d tries, aborting' % count)
                return

            self.insert_image(csr_write, row)  # write image to writeDB

            filepath = row[2] + '\\' + row[3]
            print('filepath: ' + filepath)
            # await self.bot.send_file(channel, filepath)
            print('posted image: ' + filepath)

            # close connections
            conn_write.commit()
            conn_write.close()
            conn_read.close()
            print('saved posted image to writeDB')

        except discord.HTTPException as e:  # for send_file
            print('HTTPException: ' + str(e))
        except Exception as e:
            traceback.print_exc()  # print stack
            print('Exception: ' + str(e))
            self.bot.say("Error! Unable to post!~")


    """————————————————————HELPERS————————————————————"""
    def getcats_all(self, conn):
        csr = conn.cursor()
        # csr.execute('''SELECT "name" FROM "main"."CategoriesTbl" ORDER BY "sorting" ASC LIMIT 0, 49999;''')
        csr.execute('SELECT name FROM main.CategoriesTbl ORDER BY sorting ASC LIMIT 0, 49999;')
        return csr.fetchall()

    def get_read_image(self, csr_read, server_cats):
        # FIND categories WHERE IN to ones in json, pick random image in any category
        sqlex = '''SELECT id, name 
                    FROM main.CategoriesTbl 
                    WHERE name in ({s}) 
                    ORDER BY sorting ASC;'''. \
                    format(s={', '.join('?' * len(server_cats))}). \
                    replace('{', '').replace('}', '').replace('\'', '')

        sql_read = '''select wp.id, wp.CategoryId, wp.Path, wp.Filename, cats.name as CategoryName 
                    from main.WallpapersTbl wp
                    inner join main.CategoriesTbl cats on cats.id = wp.CategoryId 
                    where cats.name in ({s}) 
                    order by random() limit 1';'''. \
                    format(s={', '.join('?' * len(server_cats))}). \
                    replace('{', '').replace('}', '').replace('\'', '')
                    # print(sql)
        csr_read.execute(sql_read, server_cats)

        # rows = csr_read.fetchall()
        # for row in rows:
        #     print(row)
        row = csr_read.fetchone()  # fetchall and fetch both still return a tuple for Row object
        print('read db, columns  : ' + str(row.keys()))
        print('read db, retrieved: ' + str(list(row)))
        return row

    def get_writeread_image(self, csr_write, row):  #db row from get_read_image, readDB
        #FIND image where EQUAL to one found in readDB
        sql_writeread = '''select * from main.Posted 
                            where pid = (?)'''

        csr_write.execute(sql_writeread, (row[0],)) #exc requires it to be a sequence (x,)
        checkrow = csr_write.fetchone()
        print('checkrow type: ' + str(type(checkrow)))
        # print(checkrow[0], checkrow[1], checkrow[2], checkrow[3], checkrow[4], checkrow[5])
        # print('checkrow: ' + str(list(checkrow)))
        if checkrow is None:    #not in DB
            return None
        print('write db, columns  : ' + str(checkrow.keys()))
        print('write db, retrieved: ' + str(list(checkrow)))
        return checkrow

    def insert_image(self, csr_write, row):     # write to db
        sql_write = '''insert into main.Posted
                        values (NULL, ?, ?, ?, ?, ?, ?)'''

        writerow = list(row)
        writerow.insert(2, row[4])
        writerow.pop()
        writerow.append(1)  # moves cat to middle and adds 1 to new col at eol
        print('writerow: ' + str(writerow))
        csr_write.execute(sql_write, writerow)


    """————————————————————WATCHERS————————————————————"""
    async def shutdown_watcher(self, message):  #catch at message before it actually does anything
        prefixes = self.bot.settings.prefixes
        if (message.content in [prefix + 'shutdown' for prefix in prefixes] or
        message.content in [prefix + 'restart' for prefix in prefixes]):
            for server in self.bot.servers:
                print('saving wallpaper settings and categories:', server.id, server.name)
            #self.save_config()
            # schedstop.set()
            return


    """————————————————————INIT————————————————————"""
    def init_settings(self):
        print('--------------------Wallpaper--------------------')
        print('Loading WallpaperBot settings')
        fullpath = config_path + config_file
        if not os.path.isdir(config_path):  #check directory
            print('config path: \'%s\' not found creating new one' % config_path)
            os.makedirs(config_path)
        if not os.path.isfile(fullpath):    #check file
            file = open(fullpath, 'w')
            file.close()
        if os.path.getsize(fullpath) == 0:  #check if file empty
            print('config SETTINGS in file: \'%s\' not found creating them' % fullpath)
            file = open(fullpath, 'w')
            self.settings = default_cfg
            file.close()
            self.save_config()

        file = open(fullpath, 'r+')
        self.settings = json.load(file)
        self.server_settings = self.settings["SERVER_SETTINGS"]
        file.close()

        for server in self.bot.servers:
            if not server.id in self.server_settings:   #create new default server settings
                print(' Server settings for %s %s not found, creating defaults' % (server.id, server.name))
                self.server_settings[server.id] = default_server_cfg
                self.server_settings[server.id]["server_name"] = server.name
        self.save_config()

    async def init_scheduler(self):
        print('initializing scheduler')
        scheduler = AsyncIOScheduler()
        for server in self.bot.servers:
            print("server: %s %s" % (server.id, server.name))
            # post_time = self.server_settings[server.id]["TIME_POST"]
            # time= datetime.datetime.strptime(post_time, '%H:%M') #strip using datetime
            # scheduler.add_job(self.post_auto, 'cron', server, hour=time.hour, minute=time.minute)
            scheduler.add_job(self.post_auto, 'interval', [server], seconds=10) #for testing
            print('scheduling done for server')
        scheduler.start()

    def save_config(self):      #save config for current server
        cfg_file = open(config_path+config_file, 'w')
        json.dump(self.settings, cfg_file, indent=4)
        print('Saving WallpaperBot config')


def setup(bot):
    wp = Wallpaper(bot)
    bot.add_cog(wp)

    try:
        wp.init_settings()
        # bot.loop.create_task(wp.init_scheduler())
    except Exception as e:
        time_string = time.strftime("%H:%M:%S", time.localtime())  # strip using time
        traceback.print_exc()
        print("[%s] Exception: %s" % (time_string, (str(e))))
#setup
