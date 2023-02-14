# -*- coding: utf-8 -*-
# import discord
import requests
import platform

from src.trackers.COMMON import COMMON
from src.console import console


class TL():
    CATEGORIES = {
        'Movie4K': 47,
        'MovieBluray': 13,
        'MovieBlurayRip': 14,
        'MovieCam': 8,
        'MovieTS': 9,
        'MovieDocumentary': 29,
        'MovieDvd': 12,
        'MovieDvdRip': 11,
        'MovieForeign': 36,
        'MovieHdRip': 43,
        'MovieWebrip': 37,
        'TvBoxsets': 27,
        'TvEpisodes': 26,
        'TvEpisodesHd': 32,
        'TvForeign': 44
    }

    def __init__(self, config):
        self.config = config
        self.tracker = 'TL'
        self.source_flag = 'TorrentLeech.org'
        self.upload_url = 'https://www.torrentleech.org/torrents/upload/apiupload'
        self.signature = None
        self.banned_groups = [""]
        
        self.announce_key = self.config['TRACKERS'][self.tracker]['announce_key']
        self.config['TRACKERS'][self.tracker]['announce_url'] = f"https://tracker.torrentleech.org/a/{self.announce_key}/announce"
        pass
    
    async def get_cat_id(self, common, meta):
        if meta['category'] == 'MOVIE':
            if meta['original_language'] != 'en':
                return self.CATEGORIES['MovieForeign']
            elif 'Documentary' in meta['genres']:
                return self.CATEGORIES['MovieDocumentary']
            elif meta['uhd']:
                return self.CATEGORIES['Movie4K']
            elif meta['is_disc'] in ('BDMV', 'HDDVD') or (meta['type'] == 'REMUX' and meta['source'] in ('BluRay', 'HDDVD')):
                return self.CATEGORIES['MovieBluray']
            elif meta['type'] == 'ENCODE' and meta['source'] in ('BluRay', 'HDDVD'):
                return self.CATEGORIES['MovieBlurayRip']
            elif meta['is_disc'] == 'DVD' or (meta['type'] == 'REMUX' and 'DVD' in meta['source']):
                return self.CATEGORIES['MovieDvd']
            elif meta['type'] == 'ENCODE' and 'DVD' in meta['source']:
                return self.CATEGORIES['MovieDvdRip']
            elif 'WEB' in meta['type']:
                return self.CATEGORIES['MovieWebrip']
        elif meta['category'] == 'TV':
            if meta['original_language'] != 'en': 
                return self.CATEGORIES['TvForeign']
            elif await common.is_season_pack(meta):
                return self.CATEGORIES['TvBoxsets']
            elif meta['sd']:
                return self.CATEGORIES['TvEpisodes']
            else:
                return self.CATEGORIES['TvEpisodesHd']

        raise NotImplementedError('Failed to determine TL category!')

    async def upload(self, meta):
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        cat_id = await self.get_cat_id(common, meta)
        await common.unit3d_edit_desc(meta, self.tracker, self.signature)

        if meta['bdinfo'] != None:
            mi_dump = None
            bd_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8').read()
        else:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt", 'r', encoding='utf-8').read()
            bd_dump = None
        desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'r').read()
        open_torrent = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]{meta['clean_name']}.torrent", 'rb')
        files = {'torrent': (meta['name'] + '.torrent', open_torrent)}
        data = {
            'description' : desc + '\n\n' + (bd_dump if meta['bdinfo'] != None else mi_dump),
            'announcekey' : self.announce_key,
            'category' : cat_id
        }
        headers = {
            'User-Agent': f'Upload Assistant/2.1 ({platform.system()} {platform.release()})'
        }
        
        if meta['debug'] == False:
            response = requests.post(url=self.upload_url, files=files, data=data, headers=headers)
            if not response.text.isnumeric():
                console.print(f'[red]{response.text}')
        else:
            console.print(f"[cyan]Request Data:")
            console.print(data)
        open_torrent.close()
