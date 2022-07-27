import pickle
from bs4 import BeautifulSoup
import requests
import asyncio
import re
import os
from pathlib import Path
import traceback
import json
import distutils
import cli_ui
from unidecode import unidecode
from urllib.parse import urlparse, quote
from src.trackers.COMMON import COMMON
from src.bbcode import BBCODE
from src.exceptions import *
from src.console import console


class TTG():

    def __init__(self, config):
        self.config = config
        self.tracker = 'TTG'
        self.source_flag = 'TTG'
        self.username = config['TRACKERS']['TTG'].get('username', '').strip()
        self.password = config['TRACKERS']['TTG'].get('passkey', '').strip()
        self.passid = str(config['TRACKERS']['TTG'].get('login_question', '')).strip()
        self.passan = config['TRACKERS']['TTG'].get('login_answer', '').strip()
        self.uid = config['TRACKERS']['TTG'].get('user_id', '')
        self.signature = None
    


    async def edit_name(self, meta):
        ttg_name = meta['name']

        remove_list = ['Dubbed', 'Dual-Audio']
        for each in remove_list:
            ttg_name = ttg_name.replace(each, '')

        return ttg_name

    async def get_type_id(self, meta):
        lang = meta.get('original_language', 'UNKNOWN').upper()
        if meta['category'] == "MOVIE":
            # 51 = DVDRip
            if meta['resolution'].startswith("720"):
                type_id = 52 # 720p
            if meta['resolution'].startswith("1080"):
                type_id = 53 # 1080p/i
            if meta['is_disc'] == "BDMV":
                type_id = 54 # Blu-ray disc
        
        elif meta['category'] == "TV":
            if meta.get('tv_pack', 0) != 1:
                # TV Singles
                if meta['resolution'].startswith("720"):
                    type_id = 69 # 720p TV EU/US
                    if lang in ('ZH', 'CN', 'CMN'):
                        type_id = 76 # Chinese
                if meta['resolution'].startswith("1080"):
                    type_id = 70 # 1080 TV EU/US
                    if lang in ('ZH', 'CN', 'CMN'):
                        type_id = 75 # Chinese
                if lang in ('KR', 'KO'):
                    type_id = 75 # Korean
                if lang in ('JA', 'JP'):
                    type_id = 73 # Japanese
            else:
                # TV Packs
                type_id = 87 # EN/US
                if lang in ('KR', 'KO'):
                    type_id = 99 # Korean
                if lang in ('JA', 'JP'):
                    type_id = 88 # Japanese
                if lang in ('ZH', 'CN', 'CMN'):
                    type_id = 90 # Chinese
            
        
        if "documentary" in meta.get("genres", "").lower().replace(' ', '').replace('-', '') or 'documentary' in meta.get("keywords", "").lower().replace(' ', '').replace('-', ''):
            if meta['resolution'].startswith("720"):
                type_id = 62 # 720p
            if meta['resolution'].startswith("1080"):
                type_id = 63 # 1080
            if meta.get('is_disc', '') == 'BDMV':
                type_id = 64 # BDMV
        
        if "animation" in meta.get("genres", "").lower().replace(' ', '').replace('-', '') or 'animation' in meta.get("keywords", "").lower().replace(' ', '').replace('-', ''):
            if meta.get('sd', 1) == 0:
                type_id = 58

        if meta['resolution'] in ("2160p"):
            type_id = 108
            if meta.get('is_disc', '') == 'BDMV':
                type_id = 109

        # I guess complete packs?:
            # 103 = TV Shows KR
            # 101 = TV Shows JP
            # 60 = TV Shows
        return type_id

    async def get_anon(self, anon):
        if anon == 0 and bool(distutils.util.strtobool(self.config['TRACKERS'][self.tracker].get('anon', "False"))) == False:
            anon = 'no'
        else:
            anon = 'yes'
        return anon

    ###############################################################
    ######   STOP HERE UNLESS EXTRA MODIFICATION IS NEEDED   ######
    ###############################################################

    async def upload(self, meta):
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        await self.edit_desc(meta)
        ttg_name = await self.edit_name(meta)

        # FORM
            # type = category dropdown
            # name = name
            # descr = description
            # anonymity = "yes" / "no"
            # nodistr = "yes" / "no" (exclusive?) not required
            # imdb_c = tt123456
            #
        # POST > upload/upload

        ttg_desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'r').read()
        torrent_path = f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]{meta['clean_name']}.torrent"
        with open(torrent_path, 'rb') as torrentFile:
            if len(meta['filelist']) == 1:
                torrentFileName = unidecode(os.path.basename(meta['video']).replace(' ', '.'))
            else:
                torrentFileName = unidecode(os.path.basename(meta['path']).replace(' ', '.'))
            files = {
                'file' : (f"{torrentFileName}.torrent", torrentFile, "application/x-bittorent")
            }
            data = {
                'MAX_FILE_SIZE' : '4000000',
                'team' : '',
                'hr' : 'no',
                'name' : ttg_name,
                'type' : await self.get_type_id(meta),
                'descr' : ttg_desc.rstrip(),
                'imdb_c' : f"tt{meta.get('imdb_id', '').replace('tt', '')}",

                'anonymity' : await self.get_anon(meta['anon']),
                'nodistr' : 'no',
                
            }

            # Submit
            if meta['debug']:
                console.print(url)
                console.print(data)
            else:
                url = "https://totheglory.im/takeupload.php"
                with requests.Session() as session:
                    cookiefile = os.path.abspath(f"{meta['base_dir']}/data/cookies/TTG.pkl")
                    with open(cookiefile, 'rb') as cf:
                        session.cookies.update(pickle.load(cf))
                    up = session.post(url=url, data=data, files=files)
                    torrentFile.close()

                    
                    if up.url.startswith("https://totheglory.im/details.php?id="):
                        console.print(f"[green]Uploaded to: [yellow]{up.url}[/yellow][/green]")
                    else:
                        console.print(data)
                        console.print("\n\n")
                        console.print(up.text)
                        raise UploadException(f"Upload to TTG Failed: result URL {up.url} ({up.status_code}) was not expected", 'red')
        return


    async def search_existing(self, meta):
        dupes = []
        with requests.Session() as session:
            cookiefile = os.path.abspath(f"{meta['base_dir']}/data/cookies/TTG.pkl")
            with open(cookiefile, 'rb') as cf:
                session.cookies.update(pickle.load(cf))
            
            if int(meta['imdb_id'].replace('tt', '')) != 0:
                imdb = f"imdb{meta['imdb_id'].replace('tt', '')}"
            else:
                imdb = ""
            if meta.get('is_disc', '') == "BDMV":
                res_type = f"{meta['resolution']} Blu-ray"
            elif meta.get('is_disc', '') == "DVD":
                res_type = "DVD"
            else:
                res_type = meta['resolution']
            search_url = f"https://totheglory.im/browse.php?search_field= {imdb} {res_type}"
            r = session.get(search_url)
            soup = BeautifulSoup(r.text, 'html.parser')
            find = soup.find_all('a', href=True)
            for each in find:
                if each['href'].startswith('/t/'):
                    release = re.search(r"(<b>)(<font.*>)?(.*)<br", str(each))
                    if release:
                        dupes.append(release.group(3))

        return dupes

    


    async def validate_credentials(self, meta):
        cookiefile = os.path.abspath(f"{meta['base_dir']}/data/cookies/TTG.pkl")
        if not os.path.exists(cookiefile):
            await self.login(cookiefile)
        vcookie = await self.validate_cookies(meta, cookiefile)
        if vcookie != True:
            console.print('[red]Failed to validate cookies. Please confirm that the site is up and your passkey is valid.')
            recreate = cli_ui.ask_yes_no("Log in again and create new session?")
            if recreate == True:
                os.remove(cookiefile)
                await self.login(cookiefile)
                vcookie = await self.validate_cookies(meta, cookiefile)
                return vcookie
            else:
                return False
        return True
    
    async def validate_cookies(self, meta, cookiefile):
        url = "https://totheglory.im"
        if os.path.exists(cookiefile):
            with requests.Session() as session:
                with open(cookiefile, 'rb') as cf:
                    session.cookies.update(pickle.load(cf))
                resp = session.get(url=url)
                if meta['debug']:
                    console.print('[cyan]Cookies:')
                    console.print(session.cookies.get_dict())
                    console.print("\n\n\n\n\n\n")
                    console.print(resp.text)
                if resp.text.find("""<a href="/logout.php">Logout</a>""") != -1:
                    return True
                else:
                    return False
        else:
            return False

    async def login(self, cookiefile):
        url = "https://totheglory.im/takelogin.php"
        data={
            'username': self.username,
            'password': self.password,
            'passid': self.passid,
            'passan': self.passan
        }
        with requests.Session() as session:
            response = session.post(url, data=data)
            if response.url.endswith('2fa.php'):
                soup = BeautifulSoup(response.text, 'html.parser')
                auth_token = soup.find('input', {'name' : 'authenticity_token'}).get('value')
                two_factor_data = {
                    'otp' : console.input('[yellow]TTG 2FA Code: '),
                    'authenticity_token' : auth_token,
                    'uid' : self.uid
                }
                two_factor_url = "https://totheglory.im/take2fa.php"
                response = session.post(two_factor_url, data=two_factor_data)
            if response.url.endswith('my.php'):
                console.print('[green]Successfully logged into TTG')
                with open(cookiefile, 'wb') as cf:
                    pickle.dump(session.cookies, cf)
            else:
                console.print('[bold red blink]Something went wrong')
                await asyncio.sleep(1)
                console.print(response.text)
        return



    async def edit_desc(self, meta):
        ###
        #"{% if guess.streaming_service == 'Amazon Prime' %}
        #   {{ptgen | replace('[/img]', '[/img]\n\n
        #   [b][color=#ff00ff][size=3]亚马逊(Amazon)的无损REMUX片源，没有转码\nThis release is sourced from Amazon and is not transcoded, just remuxed from the direct Amazon stream[/size][/color][/b]\n\n')}}
        # {% elif guess.streaming_service == 'Netflix'%}
        #   {{ptgen | replace('[/img]', '[/img]\n\n
        #   [center][b][color=#ff00ff][size=3]﻿网飞(Netfilx)的无损REMUX片源，没有转码\nThis release is sourced from Netflix and is not transcoded, just remuxed from the direct Netflix stream.[/size][/color][/b][/center]\n\n')}}
        # {% else %}
        #   {{ptgen}}
        # {% endif %}
        
        # [b][i][color=#3c78d8]This torrent has been auto-uploaded by JinBot, please report me if you encounter any issues.[/color][/i][/b]"

        base = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'r').read()
        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'w') as descfile:
            from src.bbcode import BBCODE

            if int(meta.get('imdb_id', '0').replace('tt', '')) != 0:
                await self.ptgen(meta)

            # Add This line for all web-dls
            if meta['type'] == 'WEBDL' and meta.get('service_longname', '') != '' and meta.get('description', None) == None:
                descfile.write(f"[center][b][color=#ff00ff][size=3]{meta['service_longname']}的无损REMUX片源，没有转码/This release is sourced from {meta['service_longname']}[/size][/color][/b][/center]")
            bbcode = BBCODE()
            if meta.get('discs', []) != []:
                discs = meta['discs']
                for each in discs:
                    if each['type'] == "BDMV":
                        descfile.write(f"[quote={each.get('name', 'BDINFO')}]{each['summary']}[/quote]\n")
                        descfile.write("\n")
                        pass
                    if each['type'] == "DVD":
                        descfile.write(f"{each['name']}:\n")
                        descfile.write(f"[quote={os.path.basename(each['vob'])}][{each['vob_mi']}[/quote] [quote={os.path.basename(each['ifo'])}][{each['ifo_mi']}[/quote]\n")
                        descfile.write("\n")
            else:
                mi = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO_CLEANPATH.txt", 'r', encoding='utf-8').read()
                descfile.write(f"[quote=MediaInfo]{mi}[/quote]")
                descfile.write("\n")
            desc = base
            desc = bbcode.convert_code_to_quote(desc)
            desc = bbcode.convert_spoiler_to_hide(desc)
            desc = bbcode.convert_comparison_to_centered(desc, 1000)
            desc = desc.replace('[img]', '[img=350x350]')
            desc = re.sub("(\[img=\d+)]", "[img=350x350]", desc, flags=re.IGNORECASE)
            descfile.write(desc)
            images = meta['image_list']
            if len(images) > 0: 
                descfile.write("[center]")
                for each in range(len(images)):
                    web_url = images[each]['web_url']
                    img_url = images[each]['img_url']
                    descfile.write(f"[url={web_url}][img=350x350]{img_url}[/img][/url]")
                descfile.write("[/center]")
            if self.signature != None:
                descfile.write("\n\n")
                descfile.write(self.signature)
            descfile.close()

    
    async def ptgen(self, meta):
        ptgen = ""
        url = "https://api.iyuu.cn/App.Movie.Ptgen"
        params = {
            'site' : 'douban',
            'url' : f"tt{meta['imdb_id']}"
        }
        try:
            ptgen = requests.get(url, params=params)
            ptgen = ptgen.json()
            ptgen = ptgen['format']
            if "[/img]" in ptgen:
                ptgen = ptgen.split("[/img]")[1]
            ptgen = f"[img]{meta.get('imdb_info', {}).get('cover', meta.get('cover', ''))}[/img]{ptgen}"
        except:
            console.print("[bold red blink]There was an error getting the ptgen")
            console.print(ptgen)
        return ptgen