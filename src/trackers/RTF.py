# -*- coding: utf-8 -*-
# import discord
import asyncio
import requests
import distutils.util
import base64
import os

from src.trackers.COMMON import COMMON
from src.console import console

class RTF():
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
    def __init__(self, config):
        self.config = config
        self.tracker = 'RTF'
        self.source_flag = 'sunshine'
        self.upload_url = 'https://retroflix.club/api/upload'
        self.search_url = 'https://retroflix.club/api/torrents/filter'
        self.forum_link = 'https://reelflix.xyz/pages/1'
        pass

    async def upload(self, meta):
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        await common.unit3d_edit_desc(meta, self.tracker, self.forum_link)
        # cat_id = await self.get_cat_id(meta['category'])
        # type_id = await self.get_type_id(meta['type'])
        # resolution_id = await self.get_res_id(meta['resolution'])
        stt_name = await self.edit_name(meta)
        if meta['anon'] == 0 and bool(distutils.util.strtobool(str(self.config['TRACKERS'][self.tracker].get('anon', "False")))) == False:
            anon = 0
        else:
            anon = 1
        if meta['bdinfo'] != None:
            mi_dump = None
            bd_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8').read()
        else:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt", 'r', encoding='utf-8').read()
            bd_dump = None
        desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'r').read()
        open_torrent = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]{meta['clean_name']}.torrent", 'rb')
        files = {'torrent': open_torrent}
        file = f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]{meta['clean_name']}.torrent"

#         <option value="39">VHS</option>
# <option value="4">DVDRIP</option>
# <option value="38">H.265/x265</option>
# <option value="3">720p</option>
# <option value="2">1080i</option>
# <option value="1">1080p</option>
# <option value="12">4K</option>
# <option value="18">DVD/NTSC</option>
# <option value="19">DVD/PAL</option>
# <option value="28">TVRIP</option>
# <option value="29">WEB-DL</option>
# <option value="30">WEBRIP</option>
# <option value="31">BLU-RAY</option>
# <option value="32">BDRIP</option>
# <option value="33">BRRIP</option>
# <option value="35">PDTV</option>
# <option value="34">HDRIP</option>
# <option value="36">HDTV/720p</option>
# <option value="37">HDTV/1080p</option>

        screenshots = []
        for image in meta['image_list']:
            if image['raw_url'] != None:
                screenshots.append(image['raw_url'])

        json_data = {
            'name' : stt_name,
            'description' : meta['overview'] + "\n\n" + desc,
            'mediainfo': f"{mi_dump}" if bd_dump == None else f"{bd_dump}",
            "nfo": "",
            "url": "https://www.imdb.com/title/" + (meta['imdb_id'] if str(meta['imdb_id']).startswith("tt") else "tt" + meta['imdb_id']) + "/",
            "descr": "short_desc",
            "poster": meta["poster"] if meta["poster"] != None else "",
            "type": "401" if meta['category'] == 'MOVIE'else "402",
            "screenshots": screenshots,
            'isAnonymous': self.config['TRACKERS'][self.tracker]["anon"],
        }

        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]{meta['clean_name']}.torrent", 'rb') as binary_file:
            binary_file_data = binary_file.read()
            base64_encoded_data = base64.b64encode(binary_file_data)
            base64_message = base64_encoded_data.decode('utf-8')
            json_data['file'] = base64_message

        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': self.config['TRACKERS'][self.tracker]['api_key'].strip(),
        }

        if meta['debug'] == False:
            response = requests.post(url=self.upload_url, json=json_data, headers=headers)
            try:
                console.print(response.json())
            except:
                console.print("It may have uploaded, go check")
                return
        else:
            console.print(f"[cyan]Request Data:")
            console.print(json_data)
        open_torrent.close()



    async def edit_name(self, meta):
        stt_name = meta['name']
        return stt_name

    async def get_cat_id(self, category_name):
        category_id = {
            'MOVIE': '1',
            }.get(category_name, '0')
        return category_id

    async def get_type_id(self, type):
        type_id = {
            'DISC': '43',
            'REMUX': '40',
            'WEBDL': '42',
            'WEBRIP': '45',
            #'FANRES': '6',
            'ENCODE': '41',
            'HDTV': '35',
            }.get(type, '0')
        return type_id

    async def get_res_id(self, resolution):
        resolution_id = {
            # '8640p':'10',
            '4320p': '1',
            '2160p': '2',
            # '1440p' : '3',
            '1080p': '3',
            '1080i': '4',
             '720p': '5',
             '576p': '6',
             '576i': '7',
             '480p': '8',
             '480i': '9'
            }.get(resolution, '10')
        return resolution_id


    async def search_existing(self, meta):
        dupes = []
        console.print("[yellow]Searching for existing torrents on site...")
        params = {
            'api_token' : self.config['TRACKERS'][self.tracker]['api_key'].strip(),
            'tmdbId' : meta['tmdb'],
            'categories[]' : await self.get_cat_id(meta['category']),
            'types[]' : await self.get_type_id(meta['type']),
            'resolutions[]' : await self.get_res_id(meta['resolution']),
            'name' : ""
        }
        if meta['category'] == 'TV':
            console.print('[bold red]Unable to search site for TV as this site only ALLOWS Movies')
        #     params['name'] = f"{meta.get('season', '')}{meta.get('episode', '')}"
        if meta.get('edition', "") != "":
            params['name'] = params['name'] + meta['edition']
        try:
            response = requests.get(url=self.search_url, params=params)
            response = response.json()
            for each in response['data']:
                result = [each][0]['attributes']['name']
                # difference = SequenceMatcher(None, meta['clean_name'], result).ratio()
                # if difference >= 0.05:
                dupes.append(result)
        except:
            console.print('[bold red]Unable to search for existing torrents on site. Either the site is down or your API key is incorrect')
            await asyncio.sleep(5)

        return dupes