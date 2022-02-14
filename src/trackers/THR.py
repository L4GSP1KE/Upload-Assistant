# -*- coding: utf-8 -*-
import asyncio
from torf import Torrent
import requests
import json
import glob
from difflib import SequenceMatcher
from unidecode import unidecode
import base64
import os
from termcolor import cprint
from bs4 import BeautifulSoup

from pprint import pprint

# from pprint import pprint

class THR():
    """
    Edit for Tracker:
        Edit BASE.torrent with announce and source
        Check for duplicates
        Set type/category IDs
        Upload
    """
    def __init__(self, config):
        self.config = config
        self.username = config['TRACKERS']['THR'].get('username')
        self.password = config['TRACKERS']['THR'].get('password')
        pass
    
    async def upload(self, session, meta):
        await self.edit_torrent(meta)
        cat_id = await self.get_cat_id(meta)
        subs = self.get_subtitles(meta)
        pronfo = await self.edit_desc(meta)


        if meta.get('is_disc', '') == 'BDMV':
            mi_file = None
            # bd_file = f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8'
        else:
            mi_file = os.path.abspath(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt")
            with open(mi_file, 'r') as f:
                mi_file = f.read()
                f.close()
            # bd_file = None

        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[THR]DESCRIPTION.txt", 'r') as f:
            desc = f.read()
            f.close()
        
        torrent_path = os.path.abspath(f"{meta['base_dir']}/tmp/{meta['uuid']}/[THR]{meta['clean_name']}.torrent")
        with open(torrent_path, 'rb') as f:
            tfile = f.read()
            f.close()
        
        thr_name = unidecode(meta['name'].replace('DD+', 'DDP'))
        #Upload Form
        url = 'https://www.torrenthr.org/takeupload.php'
        files = {
            'tfile' : (f"{thr_name}.torrent", tfile)
        }
        payload = {
            'name' : thr_name,
            'descr' : desc,
            'type' : cat_id,
            'url' : f"https://www.imdb.com/title/tt{meta.get('imdb_id').replace('tt', '')}/",
            'tube' : meta.get('youtube', '')
        }
        headers = {
            'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
        }
        #If pronfo fails, put mediainfo into THR parser
        if pronfo == False and meta.get('is_disc', '') != 'BDMV':
            files['nfo'] = ("MEDIAINFO.txt", mi_file)
        if subs != []:
            payload['subs[]'] = tuple(subs)


        if meta['debug'] == False:
            response = session.post(url=url, files=files, data=payload, headers=headers)
            try:
                if response.url.endswith('uploaded=1'):
                    cprint(f'Successfully Uploaded at: {response.url}', 'grey', 'on_green')
                #Check if actually uploaded
            except:
                cprint("It may have uploaded, go check")
                # cprint(f"Request Data:", 'cyan')
                # pprint(data)
                return 
        else:
            cprint(f"Request Data:", 'cyan')
            pprint(payload)
        
    
    
    async def get_cat_id(self, meta):
        if meta['category'] == "MOVIE":
            if meta.get('is_disc') == "BMDV":
                cat = '40'
            elif meta.get('is_disc') == "DVD" or meta.get('is_disc') == "HDDVD":
                cat = '14'
            else:
                if meta.get('sd') == 1:
                    cat = '4'
                else:
                    cat = '17'
        elif meta['category'] == "TV":
            if meta.get('sd') == 1:
                cat = '7'
            else:
                cat = '34'
        elif meta.get('anime') != False:
            cat = '31'
        return cat

    def get_subtitles(self, meta):
        subs = []
        sub_langs = []
        if meta.get('is_disc', '') != 'BDMV':
            with open(f"{meta.get('base_dir')}/tmp/{meta.get('uuid')}/MediaInfo.json", 'r', encoding='utf-8') as f:
                mi = json.load(f)
            for track in mi['media']['track']:
                if track['@type'] == "Text":
                    if track.get('Language') in ['hr', 'en', 'bs', 'sr', 'sl']:
                        sub_langs.append(track.get('Language'))
        else:
            sub_langs = meta['bdinfo']['subtitles']
        if sub_langs != []:
            subs = []
            sub_lang_map = {
                'hr' : 1, 'en' : 2, 'bs' : 3, 'sr' : 4, 'sl' : 5,
                'Croatian' : 1, 'English' : 2, 'Bosnian' : 3, 'Serbian' : 4, 'Slovenian' : 5
            }
            for sub in sub_langs:
                subs.append(sub_lang_map.get(sub))
        return subs





    async def edit_torrent(self, meta):
        if os.path.exists(f"{meta['base_dir']}/tmp/{meta['uuid']}/BASE.torrent"):
            THR_torrent = Torrent.read(f"{meta['base_dir']}/tmp/{meta['uuid']}/BASE.torrent")
            THR_torrent.metainfo['announce'] = self.config['TRACKERS']['THR']['announce_url']
            THR_torrent.metainfo['info']['source'] = "[https://www.torrenthr.org] TorrentHR.org"
            Torrent.copy(THR_torrent).write(f"{meta['base_dir']}/tmp/{meta['uuid']}/[THR]{meta['clean_name']}.torrent", overwrite=True)
        return 
        
    async def edit_desc(self, meta):
        pronfo = False
        base = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'r').read()
        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[THR]DESCRIPTION.txt", 'w') as desc:
            desc.write(base)
            # REHOST IMAGES
            os.chdir(f"{meta['base_dir']}/tmp/{meta['uuid']}")
            image_glob = glob.glob("*.png")
            image_list = []
            for image in image_glob:
                url = "https://img2.torrenthr.org/api/1/upload"
                data = {
                    'key' : self.config['TRACKERS']['THR'].get('img_api'),
                    # 'source' : base64.b64encode(open(image, "rb").read()).decode('utf8')
                }
                files = {'source' : open(image, 'rb')}
                response = requests.post(url, data = data, files=files)
                try:
                    response = response.json()
                    # med_url = response['image']['medium']['url']
                    img_url = response['image']['url']
                    image_list.append(img_url)
                except:
                    cprint("Failed to upload image", 'yellow')
                    pprint(response.text)
                await asyncio.sleep(1)
            desc.write("[align=center]")
            if meta.get('is_disc', '') == 'BDMV':
                with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt") as bd_file:
                    desc.write(f"[nfo]{bd_file.read()}[/nfo]")
                    bd_file.close()
            else:
                # ProNFO
                pronfo_url = f"https://www.pronfo.com/api/v1/access/upload/{self.config['TRACKERS']['THR'].get('pronfo_api_key', '')}"
                data = {
                    'content' : open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt", 'r').read(),
                    'theme' : self.config['TRACKERS']['THR'].get('pronfo_theme', 'gray'),
                    'rapi' : self.config['TRACKERS']['THR'].get('pronfo_rapi_id')
                }
                response = requests.post(pronfo_url, data=data)
                try:
                    response = response.json()
                    if response.get('error', True) == False:
                        mi_img = response.get('url')
                        desc.write(f"\n[img]{mi_img}[/img]\n")
                        pronfo = True
                except:
                    cprint('Error parsing pronfo response, using THR parser instead', 'grey', 'on_red')
                    if meta['debug']:
                        cprint(response, 'grey', 'on_red')
                        pprint(response.text) 

            for each in image_list:
                desc.write(f"\n[img]{each}[/img]\n")
            desc.write("\n\n[size=2][url=https://www.torrenthr.org/forums.php?action=viewtopic&topicid=8977]Created by L4G's Upload Assistant[/url][/size][/align]")
            desc.close()
        return pronfo

   


    def search_existing(self, session, imdb_id):
        imdb_id = imdb_id.replace('tt', '')
        search_url = f"https://www.torrenthr.org/browse.php?search={imdb_id}&blah=2&incldead=1"
        search = session.get(search_url)
        soup = BeautifulSoup(search.text, 'html.parser')
        dupes = []
        for link in soup.find_all('a', href=True):
            if link['href'].startswith('details.php'):
                if link.get('onmousemove', False):
                    dupe = link['onmousemove'].split("','/images")
                    dupe = dupe[0].replace("return overlibImage('", "")
                    dupes.append(dupe)
        return dupes

    def login(self, session):
        url = 'https://www.torrenthr.org/takelogin.php'
        payload = {
            'username' : self.username,
            'password' : self.password,
            'ssl' : 'yes'
        }
        headers = {
            'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
        }
        resp = session.post(url, headers=headers, data=payload)
        if resp.url == "https://www.torrenthr.org/index.php":
            cprint('Successfully logged in', 'grey', 'on_green')
        return session