# -*- coding: utf-8 -*-
# import discord
# import asyncio
from click import decorators
from torf import Torrent
import requests
from difflib import SequenceMatcher
from termcolor import cprint
import urllib
from pprint import pprint

# from pprint import pprint

class Blu():
    """
    Edit for Tracker:
        Edit BASE.torrent with announce and source
        Check for duplicates
        Set type/category IDs
        Upload
    """
    def __init__(self, config):
        self.config = config
        pass
    
    async def upload(self, meta):
        await self.edit_torrent(meta)
        cat_id = await self.get_cat_id(meta['category'])
        type_id = await self.get_type_id(meta['type'])
        resolution_id = await self.get_res_id(meta['resolution'])
        await self.inflate_ego(meta)


        if meta['bdinfo'] != None:
            mi_dump = None
        else:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt", 'r', encoding='utf-8').read()
        desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'r').read()
        open_torrent = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[BLU]{meta['clean_name']}.torrent", 'rb')
        files = {'torrent': open_torrent}
        data = {
            'name' : meta['name'],
            'description' : desc,
            'mediainfo' : mi_dump,
            'category_id' : cat_id,
            'type_id' : type_id,
            'resolution_id' : resolution_id,
            'tmdb' : meta['tmdb'],
            'imdb' : meta['imdb_id'].replace('tt', ''),
            'tvdb' : meta['tvdb_id'],
            'mal' : meta['mal_id'],
            'igdb' : 0,
            'anonymous' : meta['anon'],
            'stream' : meta['stream'],
            'sd' : meta['sd'],
            'keywords' : meta['keywords'],
            # 'internal' : 0,
            # 'featured' : 0,
            # 'free' : 0,
            # 'double_up' : 0,
            # 'sticky' : 0,
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:53.0) Gecko/20100101 Firefox/53.0'
        }
        url = f"https://blutopia.xyz/api/torrents/upload?api_token={self.config['DEFAULT']['blu_api']}"
        
        if meta['debug'] == False:
            response = requests.post(url=url, files=files, data=data, headers=headers)
            open_torrent.close()
            try:
                # pprint(data)
                print(response.json())
                return 
            except:
                cprint("It may have uploaded, go check")
                cprint(f"Request Data:", 'cyan')
                pprint(data)
                return 
        else:
            cprint(f"Request Data:", 'cyan')
            pprint(data)





    async def get_cat_id(self, category_name):
        category_id = {
            'MOVIE': '1', 
            'TV': '2', 
            'FANRES': '3'
            }.get(category_name, '0')
        return category_id

    async def get_type_id(self, type):
        type_id = {
            'DISC': '1', 
            'REMUX': '3',
            'WEBDL': '4', 
            'WEBRIP': '5', 
            'HDTV': '6',
            'ENCODE': '12'
            }.get(type, '0')
        return type_id

    async def get_res_id(self, resolution):
        resolution_id = {
            '8640p':'10', 
            '4320p': '11', 
            '2160p': '1', 
            '1080p': '2',
            '1080i':'3', 
            '720p': '5',  
            '576p': '6', 
            '576i': '7',
            '480p': '8', 
            '480i': '9'
            }.get(resolution, '10')
        return resolution_id




    async def edit_torrent(self, meta):
        blu_torrent = Torrent.read(f"{meta['base_dir']}/tmp/{meta['uuid']}/BASE.torrent")
        blu_torrent.metainfo['announce'] = self.config['DEFAULT']['blu_announce']
        blu_torrent.metainfo['info']['source'] = "BLU"
        blu_torrent.metainfo['comment'] = "Created by L4G's Upload Assistant"
        Torrent.copy(blu_torrent).write(f"{meta['base_dir']}/tmp/{meta['uuid']}/[BLU]{meta['clean_name']}.torrent")
        return 
        
    async def inflate_ego(self, meta):
        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'a') as desc:
            desc.write("\n[center][url=https://blutopia.xyz/forums/topics/3087]Created by L4G's Upload Assistant[/url][/center]")
            desc.close()

   


    async def search_existing(self, meta):
        dupes = []
        cprint("Searching for existing torrents on site...", 'grey', 'on_yellow')
        url = f"https://blutopia.xyz/api/torrents/filter?name={urllib.parse.quote(meta['clean_name'])}&api_token={self.config['DEFAULT']['blu_api']}"
        response = requests.get(url=url)
        response = response.json()
        for each in response['data']:
            result = [each][0]['attributes']['name']
            # print(result)
            difference = SequenceMatcher(None, meta['clean_name'], result).ratio()
            if difference >= 0.05:
                dupes.append(result)

        return dupes