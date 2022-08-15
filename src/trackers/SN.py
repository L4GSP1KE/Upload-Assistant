# -*- coding: utf-8 -*-
import requests
import asyncio
import traceback

from src.trackers.COMMON import COMMON
from src.console import console


class SN():
    """
    Edit for Tracker:
        Edit BASE.torrent with announce and source
        Check for duplicates
        Set type/category IDs
        Upload
    """

    def __init__(self, config):
        self.config = config
        self.tracker = 'SN'
        self.source_flag = 'Swarmazon'
        self.upload_url = 'https://swarmazon.club/api/upload.php'
        self.forum_link = 'https://swarmazon.club/php/forum.php?forum_page=2-swarmazon-rules'
        self.search_url = 'https://swarmazon.club/api/search.php'
        pass

    async def get_type_id(self, type):
        type_id = {
            'BluRay': '3',
            'Web': '1',
            # boxset is 4
            #'NA': '4',
            'DVD': '2'
        }.get(type, '0')
        return type_id

    async def upload(self, meta):
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        #await common.unit3d_edit_desc(meta, self.tracker, self.forum_link)
        await self.edit_desc(meta)
        cat_id = ""
        sub_cat_id = ""
        #cat_id = await self.get_cat_id(meta)
        if meta['category'] == 'MOVIE':
            cat_id = 1
            # sub cat is source so using source to get
            sub_cat_id = await self.get_type_id(meta['source'])
        elif meta['category'] == 'TV':
            cat_id = 2
            if meta['tv_pack']:
                sub_cat_id = 6
            else:
                sub_cat_id = 5
            # todo need to do a check for docs and add as subcat


        if meta['bdinfo'] != None:
            mi_dump = None
            bd_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8').read()
        else:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt", 'r', encoding='utf-8').read()
            bd_dump = None
        desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'r').read()

        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]{meta['clean_name']}.torrent", 'rb') as f:
            tfile = f.read()
            f.close()

        # uploading torrent file.
        files = {
            'torrent': (f"{meta['name']}.torrent", tfile)
        }

        # adding bd_dump to description if it exits and adding empty string to mediainfo
        if bd_dump:
            desc += "\n\n" + bd_dump
            mi_dump = ""

        data = {
            'api_key': self.config['TRACKERS'][self.tracker]['api_key'].strip(),
            'name': meta['name'],
            'category_id': cat_id,
            'type_id': sub_cat_id,
            'media_ref': f"tt{meta['imdb_id']}",
            'description': desc,
            'media_info': mi_dump

        }

        if meta['debug'] == False:
            response = requests.request("POST", url=self.upload_url, data=data, files=files)

            try:
                if response.json().get('success'):
                    console.print(response.json())
                else:
                    console.print("[red]Did not upload successfully")
                    console.print(response.json())
            except:
                console.print("[red]Error! It may have uploaded, go check")
                console.print(data)
                console.print_exception()
                return
        else:
            console.print(f"[cyan]Request Data:")
            console.print(data)


    async def edit_desc(self, meta):
        base = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'r').read()
        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'w') as desc:
            desc.write(base)
            images = meta['image_list']
            if len(images) > 0:
                desc.write("[center]")
                for each in range(len(images)):
                    web_url = images[each]['web_url']
                    img_url = images[each]['img_url']
                    desc.write(f"[url={web_url}][img]{img_url}[/img][/url]")
                desc.write("[/center]")
            desc.write(f"\n[center][url={self.forum_link}]Simplicity, Socializing and Sharing![/url][/center]")
            desc.close()
        return


    async def search_existing(self, meta):
        dupes = []
        console.print("[yellow]Searching for existing torrents on site...")

        params = {
            'api_key' : self.config['TRACKERS'][self.tracker]['api_key'].strip()
        }

        # using title if IMDB id does not exist to search
        if meta['imdb_id'] == 0:
            if meta['category'] == 'TV':
                params['filter'] = meta['title'] + f"{meta.get('season', '')}{meta.get('episode', '')}" + " " + meta['resolution']
            else:
                params['filter'] = meta['title']
        else:
            #using IMDB_id to search if it exists.
            if meta['category'] == 'TV':
                params['media_ref'] = f"tt{meta['imdb_id']}"
                params['filter'] = f"{meta.get('season', '')}{meta.get('episode', '')}" + " " + meta['resolution']
            else:
                params['media_ref'] = f"tt{meta['imdb_id']}"
                params['filter'] = meta['resolution']

        try:
            response = requests.get(url=self.search_url, params=params)
            response = response.json()
            for i in response['data']:
                result = i['name']
                dupes.append(result)
        except:
            console.print('[red]Unable to search for existing torrents on site. Either the site is down or your API key is incorrect')
            await asyncio.sleep(5)

        return dupes
