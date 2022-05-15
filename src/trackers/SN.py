# -*- coding: utf-8 -*-
import requests
from termcolor import cprint
from pprint import pprint
import traceback

from src.trackers.COMMON import COMMON


# from pprint import pprint

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
        self.upload_url = 'https://swarmazon.club/en/upload/upload.php'
        self.forum_link = 'https://swarmazon.club/php/forum.php?forum_page=2-swarmazon-rules'
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

        # need to pass the name of the file along with the torrent
        files = {
            'fileToUpload': (f"{meta['name']}.torrent", tfile)
        }

        # adding bd_dump to description if it exits and adding empty string to mediainfo
        if bd_dump:
            desc += "\n\n" + bd_dump
            mi_dump = ""

        data = {
            'name': meta['name'],
            'categoryId': cat_id,
            'typeid': sub_cat_id,
            'media_ref': f"https://www.imdb.com/title/tt{meta['imdb_id']}",
            'description': desc,
            'mediainfo': mi_dump
        }

        cookie = {'PHPSESSID': self.config['TRACKERS'][self.tracker].get('PHPSESSID'), 'swarmazon_remember': self.config['TRACKERS'][self.tracker].get('swarmazon_remember')}

        if meta['debug'] == False:
            response = requests.request("POST", url=self.upload_url, data=data, files=files, cookies=cookie)
            try:
                if str(response.url).__contains__("view"):
                    cprint(response.url)
                else:
                    cprint("No DL link in response, unable to download torrent. It maybe a duplicate, go check", 'grey', 'on_red')
                    pprint(data)
            except:
                cprint("It may have uploaded, go check", 'grey', 'on_red')
                pprint(data)
                print(traceback.print_exc())
                return
        else:
            cprint(f"Request Data:", 'cyan')
            pprint(data)


    async def edit_desc(self, meta):
        base = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'r').read()
        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'w') as desc:
            desc.write(base)
            desc.write(f"[center]")
            images = meta['image_list']
            if len(images) > 0:
                for each in range(len(images)):
                    web_url = images[each]['web_url']
                    img_url = images[each]['img_url']
                    desc.write(f"[url={web_url}][img=720]{img_url}[/img][/url]")
            desc.write(f"\n[url={self.forum_link}]Simplicity, Socializing and Sharing![/url][/center]")
            desc.close()
        return

