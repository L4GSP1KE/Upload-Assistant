import requests
import asyncio
import re
from termcolor import cprint
import distutils.util
import os
import time
import traceback
from src.trackers.COMMON import COMMON
from src.bbcode import BBCODE

from pprint import pprint

class PTP():

    def __init__(self, config):
        self.config = config
        self.tracker = 'PTP'
        self.api_user = config['TRACKERS']['PTP'].get('ApiUser', '').strip()
        self.api_key = config['TRACKERS']['PTP'].get('ApiKey', '').strip()
    
    def get_ptp_id_imdb(self, search_term, search_file_folder):
        imdb_id = ptp_torrent_id = None
        filename = str(os.path.basename(search_term))
        params = {
            'filelist' : filename
        }
        headers = {
            'ApiUser' : self.api_user,
            'ApiKey' : self.api_key
        }
        url = 'https://passthepopcorn.me/torrents.php'
        response = requests.get(url, params=params, headers=headers)
        try:
            if response.status_code == 200:
                response = response.json()
                if int(response['TotalResults']) >= 1:
                    for movie in response['Movies']:
                        if len(movie['Torrents']) >= 1:
                            for torrent in movie['Torrents']:
                                if search_file_folder == 'file':
                                    for file in torrent['FileList']:
                                        if file['Path'] == filename:
                                            imdb_id = movie['ImdbId']
                                            ptp_torrent_id = torrent['Id']
                                            dummy, ptp_torrent_hash = self.get_imdb_from_torrent_id(ptp_torrent_id)
                                            cprint(f'Matched release with PTP ID: {ptp_torrent_id}', 'grey', 'on_green')
                                            return imdb_id, ptp_torrent_id, ptp_torrent_hash
                                if search_file_folder == 'folder':
                                    if str(torrent['FilePath']) == filename:
                                        imdb_id = movie['ImdbId']
                                        ptp_torrent_id = torrent['Id']
                                        dummy, ptp_torrent_hash = self.get_imdb_from_torrent_id(ptp_torrent_id)
                                        cprint(f'Matched release with PTP ID: {ptp_torrent_id}', 'grey', 'on_green')
                                        return imdb_id, ptp_torrent_id, ptp_torrent_hash
                else:
                    return None, None, None
            elif int(response.status_code) in [400, 401, 403]:
                cprint(response.text, 'grey', 'on_red')
                return None, None, None
            elif int(response.status_code) == 503:
                cprint("PTP Unavailable (503)", 'grey', 'on_yellow')
                return None, None, None
            else:
                return None, None, None
        except Exception:
            # print(traceback.print_exc())
            return None, None, None
    
    def get_imdb_from_torrent_id(self, ptp_torrent_id):
        params = {
            'torrentid' : ptp_torrent_id
        }
        headers = {
            'ApiUser' : self.api_user,
            'ApiKey' : self.api_key
        }
        url = 'https://passthepopcorn.me/torrents.php'
        response = requests.get(url, params=params, headers=headers)
        try:
            if response.status_code == 200:
                response = response.json()
                imdb_id = response['ImdbId']
                for torrent in response['Torrents']:
                    if torrent.get('Id', 0) == str(ptp_torrent_id):
                        ptp_infohash = torrent.get('InfoHash', None)
                return imdb_id, ptp_infohash
            elif int(response.status_code) in [400, 401, 403]:
                cprint(response.text, 'grey', 'on_red')
                return None, None
            elif int(response.status_code) == 503:
                cprint("PTP Unavailable (503)", 'grey', 'on_yellow')
                return None, None
            else:
                return None, None
        except Exception:
            # print(traceback.print_exc())
            return None, None
    
    def get_ptp_description(self, ptp_torrent_id, is_disc):
        params = {
            'id' : ptp_torrent_id,
            'action' : 'get_description'
        }
        headers = {
            'ApiUser' : self.api_user,
            'ApiKey' : self.api_key
        }
        url = 'https://passthepopcorn.me/torrents.php'
        response = requests.get(url, params=params, headers=headers)
        ptp_desc = response.text
        bbcode = BBCODE()
        desc = bbcode.clean_ptp_description(ptp_desc, is_disc)
        return desc
    
    
                