# -*- coding: utf-8 -*-
# import discord
import asyncio
from torf import Torrent
import requests
from difflib import SequenceMatcher
from termcolor import cprint
import distutils.util
import urllib
from pprint import pprint

# from pprint import pprint

class BHD():
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
        source_id = await self.get_source(meta['source'])
        type_id = await self.get_type(meta)
        draft = await self.get_live(meta)
        await self.edit_desc(meta)
        custom, edition = await self.get_edition(meta)
        tags = await self.get_tags(meta)

        if meta['bdinfo'] != None:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8')
        else:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt", 'r', encoding='utf-8')
            
        desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[BHD]DESCRIPTION.txt", 'r').read()
        open_torrent = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[BHD]{meta['clean_name']}.torrent", 'rb')
        files = {
            'file': open_torrent,
            'mediainfo' : mi_dump,
            }
        data = {
            'name' : meta['name'].replace("DD+", "DDP"),
            'category_id' : cat_id,
            'type' : type_id,
            'source': source_id,
            'imdb_id' : meta['imdb_id'].replace('tt', ''),    
            'tmdb_id' : meta['tmdb'],
            'description' : desc,
            'anon' : meta['anon'],
            'sd' : meta.get('sd', 0),
            'live' : draft 
            # 'internal' : 0,
            # 'featured' : 0,
            # 'free' : 0,
            # 'double_up' : 0,
            # 'sticky' : 0,
        }
        if meta.get('tv_pack', 0) == 1:
            data['pack'] = 1
        if meta.get('season', None) == "S00":
            data['special'] = 1
        if meta.get('region', "") != "":
            data['region'] = meta['region']
        if custom == True:
            data['custom_edition'] = edition
        elif edition != "":
            data['edition'] = edition
        if len(tags) > 0:
            data['tags'] = ','.join(tags)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:53.0) Gecko/20100101 Firefox/53.0'
        }
        url = f"https://beyond-hd.me/api/upload/{self.config['TRACKERS']['BHD']['api_key']}"
        
        if meta['debug'] == False:
            response = requests.post(url=url, files=files, data=data, headers=headers)
            try:
                # pprint(data)
                print(response.json())
            except:
                cprint("It may have uploaded, go check")
                # cprint(f"Request Data:", 'cyan')
                # pprint(data)
                return 
        else:
            cprint(f"Request Data:", 'cyan')
            pprint(data)
        open_torrent.close()





    async def get_cat_id(self, category_name):
        category_id = {
            'MOVIE': '1', 
            'TV': '2', 
            }.get(category_name, '1')
        return category_id

    async def get_source(self, source):
        sources = {
            "Blu-ray" : "Blu-ray",
            "BluRay" : "Blu-ray",
            "HD-DVD" : "HD-DVD",
            "Web" : "WEB",
            "HDTV" : "HDTV",
            "NTSC DVD" : "DVD",
            "PAL DVD" : "DVD"
        }
        
        source_id = sources.get(source)
        return source_id

    async def get_type(self, meta):
        if meta['is_disc'] == "BDMV":
            bdinfo = meta['bdinfo']
            bd_sizes = [25, 50, 66, 100]
            for each in bd_sizes:
                if bdinfo['size'] < each:
                    bd_size = each
            if meta['uhd'] == "UHD" and bd_size != 25:
                type_id = f"UHD {bd_size}"
            else:
                type_id = f"BD {bd_size}"
        elif meta['is_disc'] == "DVD":
            if "DVD5" in meta['dvd_size']:
                type_id = "DVD 5"
            elif "DVD9" in meta['dvd_size']:
                type_id = "DVD 9"    
        else:
            if meta['type'] == "REMUX":
                if meta['source'] == "BluRay":
                    type_id = "BD Remux"
                if meta['source'] in ("PAL DVD", "NTSC DVD"):
                    type_id = "DVD Remux"
                if meta['uhd'] == "UHD":
                    type_id = "UHD Remux"
            else:
                acceptable_res = ["2160p", "1080p", "1080i", "720p", "576p", "576i", "540p", "480p", "Other"]
                if meta['resolution'] in acceptable_res:
                    type_id = meta['resolution']
                else:
                    type_id = "Other"
        return type_id


   
    async def edit_torrent(self, meta):
        bhd_torrent = Torrent.read(f"{meta['base_dir']}/tmp/{meta['uuid']}/BASE.torrent")
        bhd_torrent.metainfo['announce'] = self.config['TRACKERS']['BHD']['announce_url']
        bhd_torrent.metainfo['info']['source'] = "BHD"
        bhd_torrent.metainfo['comment'] = "Created by L4G's Upload Assistant"
        Torrent.copy(bhd_torrent).write(f"{meta['base_dir']}/tmp/{meta['uuid']}/[BHD]{meta['clean_name']}.torrent")
        return 
        
    async def edit_desc(self, meta):
        base = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'r').read()
        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[BHD]DESCRIPTION.txt", 'w') as desc:
            desc.write(base.replace("[img=250]", "[img=250x250]"))
            images = meta['image_list']
            if len(images) > 0: 
                desc.write("[center]")
                for each in range(len(images)):
                    web_url = images[each]['web_url']
                    img_url = images[each]['img_url']
                    desc.write(f"[url={web_url}][img=350x350]{img_url}[/img][/url]")
                    if (each + 1) % 2 == 0:
                        desc.write("\n")
                desc.write("[/center]")
            desc.write("\n[center][url=https://beyond-hd.me/forums/topic/toolpython-l4gs-upload-assistant.5456]Created by L4G's Upload Assistant[/url][/center]")
            desc.close()
        return
   


    async def search_existing(self, meta):
        dupes = []
        cprint("Searching for existing torrents on site...", 'grey', 'on_yellow')
        data = {
            'tmdb_id' : meta['tmdb'],
            'categories' : meta['category'],
            'types' : await self.get_type(meta),
        }
        if meta['category'] == 'TV':
            if meta.get('tv_pack', 0) == 1:
                data['pack'] = 1
            data['search'] = f"{meta.get('season', '')}{meta.get('episode', '')}"
        url = f"https://beyond-hd.me/api/torrents/{self.config['TRACKERS']['BHD']['api_key']}?action=search"
        response = requests.post(url=url, data=data)
        response = response.json()
        for each in response['results']:
            result = each['name']
            # print(result)
            difference = SequenceMatcher(None, meta['clean_name'].replace('DD+', 'DDP'), result).ratio()
            if difference >= 0.05:
                dupes.append(result)

        return dupes

    async def get_live(self, meta): 
        draft = self.config['TRACKERS']['BHD']['draft_default']
        draft = bool(distutils.util.strtobool(draft)) #0 for send to draft, 1 for live
        if draft:
            draft_int = 0
        else:
            draft_int = 1
        if meta['draft']:
            draft_int = 0
        return draft_int

    async def get_edition(self, meta):
        custom = False
        editions = ['collector', 'cirector', 'extended', 'limited', 'special', 'theatrical', 'uncut', 'unrated']
        for each in editions:
            if each in meta.get('edition'):
                edition = each
            elif meta.get('edition', "") == "":
                edition = ""
            else:
                edition = meta.get('edition')
                custom = True 
        return custom, edition

    async def get_tags(self, meta):
        tags = []
        if meta['type'] == "WEBRIP":
            tags.append("WEBRip")
        if meta['type'] == "WEBDL":
            tags.append("WEBDL")
        if meta.get('3D') == "3D":
            tags.append('3D')
        if "Dual-Audio" in meta.get('audio', ""):
            tags.append('DualAudio')
            tags.append('EnglishDub')
        if "Open Matte" in meta.get('edition', ""):
            tags.append("OpenMatte")
        if meta.get('scene', False) == True:
            tags.append("Scene")
        return tags