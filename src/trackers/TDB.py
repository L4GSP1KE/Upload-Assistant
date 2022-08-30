# -*- coding: utf-8 -*-
# import discord
import asyncio
import requests
import distutils.util
import os
import json 
import re

from src.trackers.COMMON import COMMON
from src.console import console


class TDB():
    """
    Edit for Tracker:
        Edit BASE.torrent with announce and source
        Check for duplicates
        Set type/category IDs
        Upload
    """

    ###############################################################
    ########                    EDIT ME                    ########
    ###############################################################

    # ALSO EDIT CLASS NAME ABOVE

    def __init__(self, config):
        self.config = config
        self.tracker = 'TDB'
        self.source_flag = 'TorrentDB.net'
        self.upload_url = 'https://torrentdb.net/api/torrent/upload'
        self.search_url = 'https://torrentdb.net/api/torrent/search'
        self.passkey = self.config['TRACKERS'][self.tracker].get('passkey')
        self.signature = "[center][url=https://github.com/L4GSP1KE/Upload-Assistant]Created by L4G's Upload Assistant[/url][/center]"
        pass
    
    async def get_cat_id(self, category_name):
        category_id = {
            'MOVIE': '1', 
            'TV': '2', 
            }.get(category_name, '0')
        return category_id

    async def get_source_id(self, type):
        type_id = {
            'DISC': '1', 
            'REMUX': '2',
            'ENCODE': '3',
            'WEBDL': '4', 
            'WEBRIP': '5', 
            'HDTV': '6',
            'SDTV' : '7'
            }.get(type, '0')
        return type_id

    async def get_res_id(self, resolution):
        resolution_id = {
            '8640p':'Other/Mixed', 
            '4320p': '4320p (8k)', 
            '2160p': '2160p (4k)', 
            '1440p': '2160p (4k)',
            '1080p': '1080p',
            '1080i': '1080p', 
            '720p': '720p',  
            '576p': '576p', 
            '576i': '576p',
            '480p': '480p', 
            '480i': '480p'
            }.get(resolution, 'Other/Mixed')
        return resolution_id
    
    async def get_type_id(self, meta):
        if meta['category'] == 'MOVIE':
            type_id = {
            'DISC': '54', 
            'REMUX': '56',
            'ENCODE': '57',
            'WEBDL': '6', 
            'WEBRIP': '55', 
            'HDTV': '58',
            'SDTV' : '59'
            }.get(meta['type'], '0')
        elif meta['category'] == 'TV':
            type_id = {
                'DISC' : '54',
                'WEBDL' : '21',
                'WEBRIP' : '61',
                'REMUX' : '62',
                'ENCODE' : '63',
                'HDTV' : '64',
                'SDTV' : '65',
            }.get(meta['type'], '0')
            if meta['anime'] == True:
                type_id = '53'
            # SPORTS = 52
        return type_id

    ###############################################################
    ######   STOP HERE UNLESS EXTRA MODIFICATION IS NEEDED   ######
    ###############################################################

    async def upload(self, meta):
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        cat_id = await self.get_cat_id(meta['category'])
        source_id = await self.get_source_id(meta['type'])
        resolution_id = await self.get_res_id(meta['resolution'])
        type_id = await self.get_type_id(meta)

        await self.edit_desc(meta)
        tdb_name, is_foreign = await self.edit_name(meta)
        tdb_screens = await self.get_screen_array(meta)

        if meta['anon'] == 0 and bool(distutils.util.strtobool(str(self.config['TRACKERS'][self.tracker].get('anon', "False")))) == False:
            anon = 0
        else:
            anon = 1

        if meta['bdinfo'] != None:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8').read()
        else:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt", 'r', encoding='utf-8').read()
        desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'r').read().strip()
        open_torrent = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]{meta['clean_name']}.torrent", 'rb')
        files = {'torrent': open_torrent}
        data = {
            'name' : tdb_name,
            'media_info' : mi_dump,
            # 'bdinfo' : bd_dump, 
            'screenshot_urls[]' : tdb_screens,
            'description' : desc,

            'category_id' : cat_id,
            'source' : source_id,
            'type_id' : type_id,
            'resolution' : resolution_id,
            'threeD' : '0',
            'skip_duplicate_check' : '1',
            'foreign' : is_foreign,
            'tmdb' : meta['tmdb'],
            'imdb' : meta['imdb_id'].replace('tt', ''),
            'tvdb' : meta['tvdb_id'],
            'mal' : meta['mal_id'],
            
            'anon' : anon, 
            'internal' : 0,
            'featured' : 0,
            'free' : 0,
            'doubleup' : 0,
            'sticky' : 0,
        }
        # Internal
        if self.config['TRACKERS'][self.tracker].get('internal', False) == True:
            if meta['tag'] != "" and (meta['tag'][1:] in self.config['TRACKERS'][self.tracker].get('internal_groups', [])):
                data['internal'] = 1
                
        if meta.get('category') == "TV":
            data['season'] = meta.get('season_int', '0')
            data['episode'] = meta.get('episode_int', '0')
            data['complete_season'] = meta.get('tv_pack', '0')

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:53.0) Gecko/20100101 Firefox/53.0',
            'Authorization' : f'Bearer {self.passkey}'
        }
        
        
        if meta['debug'] == False:
            response = requests.post(url=self.upload_url, files=files, data=data, headers=headers)
            try:
                console.print(response.json())
            except:
                console.print("It may have uploaded, go check")
                return 
        else:
            console.print(f"[cyan]Request Data:")
            console.print(data)
        open_torrent.close()


   


    async def search_existing(self, meta):
        dupes = []
        console.print("[yellow]Searching for existing torrents on site...")
        if int(meta.get('imdb_id', '0').replace('tt', '')) != 0:
            search_for = meta['imdb_id']
        else:
            search_for = f"{meta['title']} {meta['year']}"
        params = {
            'search' : search_for
        }
        headers = {
            'Authorization' : f"Bearer {self.passkey}"
        }
        try:
            response = requests.post(url=self.search_url, params=params, headers=headers)
            response = response.json()
            for each in response:
                result = each['name']
                # difference = SequenceMatcher(None, meta['clean_name'], result).ratio()
                # if difference >= 0.05:
                dupes.append(result)
        except:
            console.print('[bold red]Unable to search for existing torrents on site. Either the site is down or your API key is incorrect')
            await asyncio.sleep(5)

        return dupes


    async def edit_desc(self, meta):
        base = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'r').read()
        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'w') as descfile:
            from src.bbcode import BBCODE
            bbcode = BBCODE()
            if meta.get('discs', []) != []:
                discs = meta['discs']
                if discs[0]['type'] == "DVD":
                    descfile.write(f"[spoiler=VOB MediaInfo][code]{discs[0]['vob_mi']}[/code][/spoiler]\n")
                    descfile.write("\n")
                if len(discs) >= 2:
                    for each in discs[1:]:
                        if each['type'] == "BDMV":
                            descfile.write(f"[spoiler={each.get('name', 'BDINFO')}][code]{each['summary']}[/code][/spoiler]\n")
                            descfile.write("\n")
                        if each['type'] == "DVD":
                            descfile.write(f"{each['name']}:\n")
                            descfile.write(f"[spoiler={os.path.basename(each['vob'])}][code][{each['vob_mi']}[/code][/spoiler] [spoiler={os.path.basename(each['ifo'])}][code][{each['ifo_mi']}[/code][/spoiler]\n")
                            descfile.write("\n")
            desc = base
            desc = bbcode.convert_pre_to_code(desc)
            desc = bbcode.convert_hide_to_spoiler(desc)
            desc = bbcode.convert_comparison_to_collapse(desc, 1000)
            desc = desc.replace('[img]', '[img=300]')
            descfile.write(desc)
            if self.signature != None:
                descfile.write(self.signature)
            descfile.close()
        return 

    async def get_screen_array(self, meta):
        screen_array = []
        images = meta['image_list']
        if len(images) > 0: 
            for each in range(len(images[:int(meta['screens'])])):
                screen_array.append(images[each]['raw_url'])
        return screen_array

    async def edit_name(self, meta):
        type = meta.get('type', "")
        title = meta.get('title',"")
        alt_title = meta.get('aka', "")
        if alt_title.strip() != "":
            alt_title = f'{alt_title.strip().replace("AKA", "(aka")})'
        year = meta.get('year', "")
        resolution = meta.get('resolution', "")
        if resolution == "OTHER":
            resolution = ""
        audio = meta.get('audio', "").replace('DD+', 'DDP').replace('Dual-Audio', 'DualAudio')
        service = meta.get('service', "")
        season = meta.get('season', "")
        episode = meta.get('episode', "")
        repack = meta.get('repack', "")
        three_d = meta.get('3D', "")
        tag = meta.get('tag', "")
        source = meta.get('source', "")
        uhd = meta.get('uhd', "")
        hdr = meta.get('hdr', "")
        episode_title = meta.get('episode_title', '')
        if meta.get('is_disc', "") == "BDMV": #Disk
            video_codec = meta.get('video_codec', "")
            region = meta.get('region', "")
            bd_size = self.get_bdsize(meta)
        elif meta.get('is_disc', "") == "DVD":
            region = meta.get('region', "")
            dvd_size = meta.get('dvd_size', "")
        else:
            video_codec = meta.get('video_codec', "")
            video_encode = meta.get('video_encode', "").replace('Hi10P', '')
            if meta.get('bit_depth', '0') == '10':
                video_encode = f"10Bit {video_encode}"
        edition = meta.get('edition', "")
        hybrid = ""
        if 'hybrid' in edition.lower():
            edition = re.sub('hybrid', '', edition, flags=re.IGNORECASE)
            hybrid = 'Hybrid'

        if meta['category'] == "TV":
            if meta['search_year'] != "":
                year = meta['year']
            else:
                year = ""
        if meta.get('no_year', False) == True:
            year = ''
        if meta.get('no_aka', False) == True:
            alt_title = ''

        #YAY NAMING FUN
        if meta['category'] == "MOVIE": #MOVIE SPECIFIC
            if type == "DISC": #Disk
                if meta['is_disc'] == 'BDMV':
                    name = f"{title} {alt_title} {year} {three_d} {edition} {repack} {resolution} {hybrid} {region} {uhd} {bd_size} {source} {hdr} {video_codec} {audio}"
                elif meta['is_disc'] == 'DVD': 
                    name = f"{title} {alt_title} {year} {edition} {repack} {resolution} {hybrid} {source} {dvd_size} {audio}"
                elif meta['is_disc'] == 'HDDVD':
                    name = f"{title} {alt_title} {year} {edition} {repack} {resolution} {hybrid} {source} {audio}"
            elif type == "REMUX":
                name = f"{title} {alt_title} {year} {three_d} {edition} {repack} {resolution} {uhd} {hybrid} {source} Remux {hdr} {video_codec} {audio}" 
            elif type == "ENCODE": #Encode
                name = f"{title} {alt_title} {year} {edition} {repack} {resolution} {uhd} {hybrid} {source} {hdr} {video_encode} {audio}"  
            elif type == "WEBDL": #WEB-DL
                name = f"{title} {alt_title} {year} {edition} {repack} {resolution} {uhd} {hybrid} {service} WEB-DL {hdr} {video_encode} {audio}"
            elif type == "WEBRIP": #WEBRip
                name = f"{title} {alt_title} {year} {edition} {repack} {resolution} {uhd} {hybrid} {service} WEBRip {hdr} {video_encode} {audio}"
            elif type == "HDTV": #HDTV
                name = f"{title} {alt_title} {year} {edition} {repack} {resolution} {hybrid} HDTV {video_encode} {audio}"
        elif meta['category'] == "TV": #TV SPECIFIC
            if type == "DISC": #Disk
                if meta['is_disc'] == 'BDMV':
                    name = f"{title} {year} {alt_title} {season}{episode} {three_d} {edition} {repack} {resolution} {hybrid} {region} {uhd} {bd_size} {source} {hdr} {video_codec} {audio}"
                if meta['is_disc'] == 'DVD':
                    name = f"{title} {alt_title} {season}{episode}{three_d} {edition} {repack} {resolution} {hybrid} {source} {dvd_size} {audio}"
                elif meta['is_disc'] == 'HDDVD':
                    name = f"{title} {alt_title} {year} {edition} {repack} {source} {audio}"
            elif type == "REMUX":
                name = f"{title} {year} {alt_title} {season}{episode} {episode_title} {three_d} {edition} {repack} {resolution} {hybrid} {uhd} {source} REMUX {hdr} {video_codec} {audio}" #SOURCE
            elif type == "ENCODE": #Encode
                name = f"{title} {year} {alt_title} {season}{episode} {episode_title} {edition} {repack} {resolution} {uhd} {hybrid} {source} {hdr} {video_encode} {audio}" #SOURCE
            elif type == "WEBDL": #WEB-DL
                name = f"{title} {year} {alt_title} {season}{episode} {episode_title} {edition} {repack} {resolution} {uhd} {hybrid} {service} WEB-DL {hdr} {video_encode} {audio}"
            elif type == "WEBRIP": #WEBRip
                name = f"{title} {year} {alt_title} {season}{episode} {episode_title} {edition} {repack} {resolution} {uhd} {hybrid} {service} WEBRip {hdr} {video_encode} {audio}"
            elif type == "HDTV": #HDTV
                name = f"{title} {year} {alt_title} {season}{episode} {episode_title} {edition} {repack} {resolution} {hybrid} HDTV {hdr} {video_encode} {audio}"


    
        name = ' '.join(name.split())
        name_notag = name
        name = name_notag + tag
        is_foreign = '0'
        has_eng_audio = False
        if meta['is_disc'] != "BDMV":
            with open(f"{meta.get('base_dir')}/tmp/{meta.get('uuid')}/MediaInfo.json", 'r', encoding='utf-8') as f:
                mi = json.load(f)
            
            for track in mi['media']['track']:
                if track['@type'] == "Audio":
                    if track.get('Language', 'None') == 'en':
                        has_eng_audio = True
            if not has_eng_audio:
                audio_lang = mi['media']['track'][2].get('Language_String', "")
                if audio_lang != "":
                    is_foreign = '1'
                    name = name.replace(meta['resolution'], f"{audio_lang} {meta['resolution']}")
        else:
            for audio in meta['bdinfo']['audio']:
                if audio['language'] == 'English':
                    has_eng_audio = True
            if not has_eng_audio:
                audio_lang = meta['bdinfo']['audio'][0]['language']
                if audio_lang != "":
                    is_foreign = '1'
                    name = name.replace(meta['resolution'], f"{audio_lang} {meta['resolution']}")

        return name, is_foreign


    def get_bdsize(self, meta):
        bd_size = ""
        bdinfo = meta['bdinfo']
        bd_sizes = [25, 50, 66, 100]
        for each in bd_sizes:
            if bdinfo['size'] < each:
                bd_size = each
                break
        if meta['uhd'] == "UHD" and bd_size != 25:
            bd_size = f"UHD{bd_size}"
        else:
            bd_size = f"BD{bd_size}"
        return bd_size