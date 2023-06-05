import requests
import asyncio
import re
import os
from pathlib import Path
import distutils.util
import json
import glob
import pickle
from unidecode import unidecode
from urllib.parse import urlparse, quote
import cli_ui
from bs4 import BeautifulSoup

from src.trackers.COMMON import COMMON
from src.exceptions import *
from src.console import console

class FL():

    def __init__(self, config):
        self.config = config
        self.tracker = 'FL'
        self.source_flag = 'FL'
        self.username = config['TRACKERS'][self.tracker].get('username', '').strip()
        self.password = config['TRACKERS'][self.tracker].get('password', '').strip()
        self.fltools = config['TRACKERS'][self.tracker].get('fltools', {})
        self.uploader_name = config['TRACKERS'][self.tracker].get('uploader_name')
        self.signature = None
        self.banned_groups = [""]
    

    async def get_category_id(self, meta):
        has_ro_audio, has_ro_sub = await self.get_ro_tracks(meta)
        # 25 = 3D Movie
        if meta['category'] == 'MOVIE':
            # 4 = Movie HD
            cat_id = 4
            if meta['is_disc'] == "BDMV" or meta['type'] == "REMUX":
                # 20 = BluRay
                cat_id = 20
                if meta['resolution'] == '2160p':
                    # 26 = 4k Movie - BluRay
                    cat_id = 26
            elif meta['resolution'] == '2160p':
                # 6 = 4k Movie
                cat_id = 6
            elif meta.get('sd', 0) == 1:
                # 1 = Movie SD
                cat_id = 1
            if has_ro_sub and meta.get('sd', 0) == 0 and meta['resolution'] != '2160p':
                # 19 = Movie + RO
                cat_id = 19
        
        if meta['category'] == 'TV':
            # 21 = TV HD
            cat_id = 21
            if meta['resolution'] == '2160p':
                # 27 = TV 4k
                cat_id = 27
            elif meta.get('sd', 0) == 1:
                # 23 = TV SD
                cat_id = 23
            
        if meta['is_disc'] == "DVD":
            # 2 = DVD
            cat_id = 2
            if has_ro_sub:
                # 3 = DVD + RO 
                cat_id = 3

        if meta.get('anime', False) == True:
            # 24 = Anime
            cat_id = 24
        return cat_id

    async def edit_name(self, meta):
        fl_name = meta['name']
        if 'DV' in meta.get('hdr', ''):
            fl_name = fl_name.replace(' DV ', ' DoVi ')
        if meta.get('type') in ('WEBDL', 'WEBRIP', 'ENCODE'):
            fl_name = fl_name.replace(meta['audio'], meta['audio'].replace(' ', '', 1))
        fl_name = fl_name.replace(meta.get('aka', ''), '')
        if meta.get('imdb_info'):
            fl_name = fl_name.replace(meta['title'], meta['imdb_info']['aka'])
            if meta['year'] != meta.get('imdb_info', {}).get('year', meta['year']) and str(meta['year']).strip() != '':
                fl_name = fl_name.replace(str(meta['year']), str(meta['imdb_info']['year']))
        if meta['category'] == "TV" and meta.get('tv_pack', 0) == 0 and meta.get('episode_title_storage', '').strip() != '':
            fl_name = fl_name.replace(meta['episode'], f"{meta['episode']} {meta['episode_title_storage']}")
        if 'DD+' in meta.get('audio', '') and 'DDP' in meta['uuid']:
            fl_name = fl_name.replace('DD+', 'DDP')
        if 'Atmos' in meta.get('audio', '') and 'Atmos' not in meta['uuid']:
            fl_name = fl_name.replace('Atmos', '')

        fl_name = fl_name.replace('BluRay REMUX', 'Remux').replace('BluRay Remux', 'Remux').replace('Bluray Remux', 'Remux')
        fl_name = fl_name.replace('PQ10', 'HDR').replace('HDR10+', 'HDR')
        fl_name = fl_name.replace('DoVi HDR HEVC', 'HEVC DoVi HDR').replace('HDR HEVC', 'HEVC HDR').replace('DoVi HEVC', 'HEVC DoVi')
        fl_name = fl_name.replace('DTS7.1', 'DTS').replace('DTS5.1', 'DTS').replace('DTS2.0', 'DTS').replace('DTS1.0', 'DTS')
        fl_name = fl_name.replace('Dubbed', '').replace('Dual-Audio', '')
        fl_name = ' '.join(fl_name.split())
        fl_name = re.sub("[^0-9a-zA-ZÀ-ÿ. &+'\-\[\]]+", "", fl_name)
        fl_name = fl_name.replace(' ', '.').replace('..', '.')
        return fl_name 

    
    ###############################################################
    ######   STOP HERE UNLESS EXTRA MODIFICATION IS NEEDED   ######
    ###############################################################

    async def upload(self, meta):
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        await self.edit_desc(meta)
        fl_name = await self.edit_name(meta)
        cat_id = await self.get_category_id(meta)
        has_ro_audio, has_ro_sub = await self.get_ro_tracks(meta)
        
        # Confirm the correct naming order for FL
        cli_ui.info(f"Filelist name: {fl_name}")
        if meta.get('unattended', False) == False:
            fl_confirm = cli_ui.ask_yes_no("Correct?", default=False)
            if fl_confirm != True:
                fl_name_manually = cli_ui.ask_string("Please enter a proper name", default="")
                if fl_name_manually == "":
                    console.print('No proper name given')
                    console.print("Aborting...")
                    return
                else:
                    fl_name = fl_name_manually

        # Torrent File Naming
        # Note: Don't Edit .torrent filename after creation, SubsPlease anime releases (because of their weird naming) are an exception
        if meta.get('anime', True) == True and meta.get('tag', '') == '-SubsPlease':
            torrentFileName = fl_name
        else:
            if meta.get('isdir', False) == False:
                torrentFileName = meta.get('uuid')
                torrentFileName = os.path.splitext(torrentFileName)[0]
            else:
                torrentFileName = meta.get('uuid')

        # Download new .torrent from site
        fl_desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'r', newline='').read()
        torrent_path = f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]{meta['clean_name']}.torrent"
        if meta['bdinfo'] != None:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8').read()
        else:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO_CLEANPATH.txt", 'r', encoding='utf-8').read()
        with open(torrent_path, 'rb') as torrentFile:
            torrentFileName = unidecode(torrentFileName)
            files = {
                'file' : (f"{torrentFileName}.torrent", torrentFile, "application/x-bittorent")
            }
            data = {
                'name' : fl_name,
                'type' : cat_id,
                'descr' : fl_desc.strip(),
                'nfo' : mi_dump
            }

            if int(meta.get('imdb_id', '').replace('tt', '')) != 0:
                data['imdbid'] = meta.get('imdb_id', '').replace('tt', '')
                data['description'] = meta['imdb_info'].get('genres', '')
            if self.uploader_name not in ("", None) and bool(distutils.util.strtobool(str(self.config['TRACKERS'][self.tracker].get('anon', "False")))) == False:
                data['epenis'] = self.uploader_name
            if has_ro_audio:
                data['materialro'] = 'on'
            if meta['is_disc'] == "BDMV" or meta['type'] == "REMUX":
                data['freeleech'] = 'on'
            if int(meta.get('tv_pack', '0')) != 0:
                data['freeleech'] = 'on'
            if int(meta.get('freeleech', '0')) != 0:
                data['freeleech'] = 'on'

            url = "https://filelist.io/takeupload.php"
            # Submit
            if meta['debug']:
                console.print(url)
                console.print(data)
            else:
                with requests.Session() as session:
                    cookiefile = os.path.abspath(f"{meta['base_dir']}/data/cookies/FL.pkl")
                    with open(cookiefile, 'rb') as cf:
                        session.cookies.update(pickle.load(cf))
                    up = session.post(url=url, data=data, files=files)
                    torrentFile.close()
                    
                    # Match url to verify successful upload
                    match = re.match(r".*?filelist\.io/details\.php\?id=(\d+)&uploaded=(\d+)", up.url)
                    if match:
                        id = re.search(r"(id=)(\d+)", urlparse(up.url).query).group(2)
                        await self.download_new_torrent(session, id, torrent_path)
                    else:
                        console.print(data)
                        console.print("\n\n")
                        console.print(up.text)
                        raise UploadException(f"Upload to FL Failed: result URL {up.url} ({up.status_code}) was not expected", 'red')
        return


    async def search_existing(self, meta):
        dupes = []
        with requests.Session() as session:
            cookiefile = os.path.abspath(f"{meta['base_dir']}/data/cookies/FL.pkl")
            with open(cookiefile, 'rb') as cf:
                session.cookies.update(pickle.load(cf))
            
            search_url = f"https://filelist.io/browse.php"
            if int(meta['imdb_id'].replace('tt', '')) != 0:
                params = {
                    'search' : meta['imdb_id'],
                    'cat' : await self.get_category_id(meta),
                    'searchin' : '3'
                }
            else:
                params = {
                    'search' : meta['title'],
                    'cat' : await self.get_category_id(meta),
                    'searchin' : '0'
                }
            
            r = session.get(search_url, params=params)
            await asyncio.sleep(0.5)
            soup = BeautifulSoup(r.text, 'html.parser')
            find = soup.find_all('a', href=True)
            for each in find:
                if each['href'].startswith('details.php?id=') and "&" not in each['href']:
                    dupes.append(each['title'])

        return dupes

    


    async def validate_credentials(self, meta):
        cookiefile = os.path.abspath(f"{meta['base_dir']}/data/cookies/FL.pkl")
        if not os.path.exists(cookiefile):
            await self.login(cookiefile)
        vcookie = await self.validate_cookies(meta, cookiefile)
        if vcookie != True:
            console.print('[red]Failed to validate cookies. Please confirm that the site is up and your passkey is valid.')
            recreate = cli_ui.ask_yes_no("Log in again and create new session?")
            if recreate == True:
                if os.path.exists(cookiefile):
                    os.remove(cookiefile)
                await self.login(cookiefile)
                vcookie = await self.validate_cookies(meta, cookiefile)
                return vcookie
            else:
                return False
        return True
    
    
    async def validate_cookies(self, meta, cookiefile):
        url = "https://filelist.io/index.php"
        if os.path.exists(cookiefile):
            with requests.Session() as session:
                with open(cookiefile, 'rb') as cf:
                    session.cookies.update(pickle.load(cf))
                resp = session.get(url=url)
                if meta['debug']:
                    console.print('[cyan]Cookies:')
                    console.print(session.cookies.get_dict())
                    console.print(resp.url)
                if resp.text.find("Logout") != -1:
                    return True
                else:
                    return False
        else:
            return False
    
    async def login(self, cookiefile):
        with requests.Session() as session:
            r = session.get("https://filelist.io/login.php")
            await asyncio.sleep(0.5)
            soup = BeautifulSoup(r.text, 'html.parser')
            validator = soup.find('input', {'name' : 'validator'}).get('value')
            data = {
                'validator' : validator,
                'username' : self.username,
                'password' : self.password,
                'unlock' : '1',
            }
            response = session.post('https://filelist.io/takelogin.php', data=data)
            await asyncio.sleep(0.5)
            index = 'https://filelist.io/index.php'
            response = session.get(index)
            if response.text.find("Logout") != -1:
                console.print('[green]Successfully logged into FL')
                with open(cookiefile, 'wb') as cf:
                    pickle.dump(session.cookies, cf)
            else:
                console.print('[bold red]Something went wrong while trying to log into FL')
                await asyncio.sleep(1)
                console.print(response.url)
        return

    async def download_new_torrent(self, session, id, torrent_path):
        download_url = f"https://filelist.io/download.php?id={id}"
        r = session.get(url=download_url)
        if r.status_code == 200:
            with open(torrent_path, "wb") as tor:
                tor.write(r.content)
        else:
            console.print("[red]There was an issue downloading the new .torrent from FL")
            console.print(r.text)
        return



    async def edit_desc(self, meta):
        base = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'r').read()
        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'w', newline='') as descfile:
            from src.bbcode import BBCODE
            bbcode = BBCODE()
            
            desc = base
            desc = bbcode.remove_spoiler(desc)
            desc = bbcode.convert_code_to_quote(desc)
            desc = bbcode.convert_comparison_to_centered(desc, 900)
            desc = desc.replace('[img]', '[img]').replace('[/img]', '[/img]')
            desc = re.sub("(\[img=\d+)]", "[img]", desc, flags=re.IGNORECASE)
            if meta['is_disc'] != 'BDMV':
                url = "https://up.img4k.net/api/description"
                data = {
                    'mediainfo' : open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO_CLEANPATH.txt", 'r').read(),
                }
                if int(meta['imdb_id'].replace('tt', '')) != 0:
                    data['imdbURL'] = f"tt{meta['imdb_id']}"
                screen_glob = glob.glob1(f"{meta['base_dir']}/tmp/{meta['uuid']}", f"{meta['filename']}-*.png")
                files = []
                for screen in screen_glob:
                    files.append(('images', (os.path.basename(screen), open(f"{meta['base_dir']}/tmp/{meta['uuid']}/{screen}", 'rb'), 'image/png')))
                response = requests.post(url, data=data, files=files, auth=(self.fltools['user'], self.fltools['pass']))
                final_desc = response.text.replace('\r\n', '\n')
            else:
                # BD Description Generator
                final_desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_EXT.txt", 'r', encoding='utf-8').read()
                if final_desc.strip() != "": # Use BD_SUMMARY_EXT and bbcode format it
                    final_desc = final_desc.replace('[/pre][/quote]', f'[/pre][/quote]\n\n{desc}\n', 1)
                    final_desc = final_desc.replace('DISC INFO:', '[pre][quote=BD_Info][b][color=#FF0000]DISC INFO:[/color][/b]').replace('PLAYLIST REPORT:', '[b][color=#FF0000]PLAYLIST REPORT:[/color][/b]').replace('VIDEO:', '[b][color=#FF0000]VIDEO:[/color][/b]').replace('AUDIO:', '[b][color=#FF0000]AUDIO:[/color][/b]').replace('SUBTITLES:', '[b][color=#FF0000]SUBTITLES:[/color][/b]')
                    final_desc += "[/pre][/quote]\n" # Closed bbcode tags
                    # Upload screens and append to the end of the description
                    url = "https://up.img4k.net/api/description"
                    screen_glob = glob.glob1(f"{meta['base_dir']}/tmp/{meta['uuid']}", f"{meta['filename']}-*.png")
                    files = []
                    for screen in screen_glob:
                        files.append(('images', (os.path.basename(screen), open(f"{meta['base_dir']}/tmp/{meta['uuid']}/{screen}", 'rb'), 'image/png')))
                    response = requests.post(url, files=files, auth=(self.fltools['user'], self.fltools['pass']))
                    final_desc += response.text.replace('\r\n', '\n')
            descfile.write(final_desc)

            if self.signature != None:
                descfile.write(self.signature)
            descfile.close()

    
    async def get_ro_tracks(self, meta):
        has_ro_audio = has_ro_sub = False
        if meta.get('is_disc', '') != 'BDMV':
            mi = meta['mediainfo']
            for track in mi['media']['track']:
                if track['@type'] == "Text":
                    if track.get('Language') == "ro":
                        has_ro_sub = True
                if track['@type'] == "Audio":
                    if track.get('Audio') == 'ro':
                        has_ro_audio = True
        else:
            if "Romanian" in meta['bdinfo']['subtitles']:
                has_ro_sub = True
            for audio_track in meta['bdinfo']['audio']:
                if audio_track['language'] == 'Romanian':
                    has_ro_audio = True
                    break
        return has_ro_audio, has_ro_sub
