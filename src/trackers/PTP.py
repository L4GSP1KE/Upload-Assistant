import cli_ui
import requests
import asyncio
import re
from termcolor import cprint
import distutils.util
import os
from pathlib import Path
import time
import traceback
import json
import glob
import multiprocessing
import platform
import pickle
from pymediainfo import MediaInfo


from src.trackers.COMMON import COMMON
from src.bbcode import BBCODE
from src.exceptions import *


from pprint import pprint

class PTP():

    def __init__(self, config):
        self.config = config
        self.tracker = 'PTP'
        self.source_flag = 'PTP'
        self.api_user = config['TRACKERS']['PTP'].get('ApiUser', '').strip()
        self.api_key = config['TRACKERS']['PTP'].get('ApiKey', '').strip()
        self.announce_url = config['TRACKERS']['PTP'].get('announce_url', '').strip() 
        self.username = config['TRACKERS']['PTP'].get('username', '').strip() 
        self.password = config['TRACKERS']['PTP'].get('password', '').strip() 
        self.user_agent = f'Upload Assistant/2.1 ({platform.system()} {platform.release()})'
    
    async def get_ptp_id_imdb(self, search_term, search_file_folder):
        imdb_id = ptp_torrent_id = None
        filename = str(os.path.basename(search_term))
        params = {
            'filelist' : filename
        }
        headers = {
            'ApiUser' : self.api_user,
            'ApiKey' : self.api_key,
            'User-Agent' : self.user_agent
        }
        url = 'https://passthepopcorn.me/torrents.php'
        response = requests.get(url, params=params, headers=headers)
        await asyncio.sleep(1)
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
                                            dummy, ptp_torrent_hash = await self.get_imdb_from_torrent_id(ptp_torrent_id)
                                            cprint(f'Matched release with PTP ID: {ptp_torrent_id}', 'grey', 'on_green')
                                            return imdb_id, ptp_torrent_id, ptp_torrent_hash
                                if search_file_folder == 'folder':
                                    if str(torrent['FilePath']) == filename:
                                        imdb_id = movie['ImdbId']
                                        ptp_torrent_id = torrent['Id']
                                        dummy, ptp_torrent_hash = await self.get_imdb_from_torrent_id(ptp_torrent_id)
                                        cprint(f'Matched release with PTP ID: {ptp_torrent_id}', 'grey', 'on_green')
                                        return imdb_id, ptp_torrent_id, ptp_torrent_hash
                else:
                    return None, None, None
            elif int(response.status_code) in [400, 401, 403]:
                cprint(f"PTP: {response.text}", 'grey', 'on_red')
                return None, None, None
            elif int(response.status_code) == 503:
                cprint("PTP Unavailable (503)", 'grey', 'on_yellow')
                return None, None, None
            else:
                return None, None, None
        except Exception:
            # print(traceback.print_exc())
            pass
        return None, None, None
    
    async def get_imdb_from_torrent_id(self, ptp_torrent_id):
        params = {
            'torrentid' : ptp_torrent_id
        }
        headers = {
            'ApiUser' : self.api_user,
            'ApiKey' : self.api_key,
            'User-Agent' : self.user_agent
        }
        url = 'https://passthepopcorn.me/torrents.php'
        response = requests.get(url, params=params, headers=headers)
        await asyncio.sleep(1)
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
    
    async def get_ptp_description(self, ptp_torrent_id, is_disc):
        params = {
            'id' : ptp_torrent_id,
            'action' : 'get_description'
        }
        headers = {
            'ApiUser' : self.api_user,
            'ApiKey' : self.api_key,
            'User-Agent' : self.user_agent
        }
        url = 'https://passthepopcorn.me/torrents.php'
        response = requests.get(url, params=params, headers=headers)
        await asyncio.sleep(1)
        ptp_desc = response.text
        bbcode = BBCODE()
        desc = bbcode.clean_ptp_description(ptp_desc, is_disc)
        cprint(f"Successfully grabbed description from PTP", 'grey', 'on_green')
        return desc
    


    async def get_group_by_imdb(self, imdb):
        params = {
            'imdb' : imdb,
        }
        headers = {
            'ApiUser' : self.api_user,
            'ApiKey' : self.api_key,
            'User-Agent' : self.user_agent
        }
        url = 'https://passthepopcorn.me/torrents.php'
        response = requests.get(url=url, headers=headers, params=params)
        await asyncio.sleep(1)
        try:
            response = response.json()
            if response.get("Page") == "Browse": # No Releases on Site with ID
                return None
            elif response.get('Page') == "Details": # Group Found
                groupID = response.get('GroupId')
                cprint(f"Matched IMDb: tt{imdb} to Group ID: {groupID}", 'grey', 'on_green')
                cprint(f"Title: {response.get('Name')} ({response.get('Year')})", 'grey', 'on_green')
                return groupID
        except Exception:
            cprint("An error has occured trying to find a group ID", 'grey', 'on_red')
            return None


    async def get_torrent_info(self, imdb):
        params = {
            'imdb' : imdb,
            'action' : 'torrent_info',
            'fast' : 1
        }
        headers = {
            'ApiUser' : self.api_user,
            'ApiKey' : self.api_key,
            'User-Agent' : self.user_agent
        }
        url = "https://passthepopcorn.me/ajax.php"
        response = requests.get(url=url, params=params, headers=headers)
        await asyncio.sleep(1)
        tinfo = {}
        try:
            response = response.json()
            # title, plot, art, year, tags, Countries, Languages
            for key, value in response[0].items():
                if value not in (None, ""):
                    tinfo[key] = value
        except Exception:
            pass
        return tinfo

    async def get_torrent_info_tmdb(self, meta):
        tinfo = {
            "title" : meta.get("title", ""),
            "year" : meta.get("year", ""),
            "album_desc" : meta.get("overview", ""),
        }
        tags = []
        ptp_tags = [
            "action", "adventure", "animation", "arthouse", "asian", "biography", "camp", "comedy",
            "crime", "cult", "documentary", "drama", "experimental", "exploitation", "family", "fantasy", "film.noir",
            "history", "horror", "martial.arts", "musical", "mystery", "performance", "philosophy", "politics", "romance",
            "sci.fi", "short", "silent", "sport", "thriller", "video.art", "war", "western"
        ]
        for each in ptp_tags:
            if each in meta.get("genres", "").lower().replace(' ', '').replace('-', '') or each in meta.get("keywords", "").lower().replace(' ', '').replace('-', ''):
                tags.append(each)
        tinfo['tags'] = ", ".join(tags)
        return tinfo

    async def search_existing(self, groupID, meta):
        # Map resolutions to SD / HD / UHD
        quality = None
        if meta.get('sd', 0) == 1: # 1 is SD
            quality = "Standard Definition"
        elif meta['resolution'] in ["1440p", "1080p", "1080i", "720p"]:
            quality = "High Definition"
        elif meta['resolution'] in ["2160p", "4320p", "8640p"]:
            quality = "Ultra High Definition"
        

        params = {
            'id' : groupID,
        }
        headers = {
            'ApiUser' : self.api_user,
            'ApiKey' : self.api_key,
            'User-Agent' : self.user_agent
        }
        url = 'https://passthepopcorn.me/torrents.php'
        response = requests.get(url=url, headers=headers, params=params)
        await asyncio.sleep(1)
        existing = []
        try:
            response = response.json()
            torrents = response.get('Torrents', [])
            if len(torrents) != 0:
                for torrent in torrents:
                    if torrent.get('Quality') == quality and quality != None:
                        existing.append(torrent.get('ReleaseName', "RELEASE NAME NOT FOUND"))
        except Exception:
            cprint("An error has occured trying to find existing releases", 'grey', 'on_red')
        return existing


    async def ptpimg_url_rehost(self, image_url):
        payload = {
            'format' : 'json',
            'api_key' : self.config["DEFAULT"]["ptpimg_api"],
            'link-upload' : image_url
        }
        headers = { 'referer': 'https://ptpimg.me/index.php'}
        url = "https://ptpimg.me/upload.php"

        response = requests.post("https://ptpimg.me/upload.php", headers=headers, data=payload)
        try:
            response = response.json()
            ptpimg_code = response[0]['code']
            ptpimg_ext = response[0]['ext']
            img_url = f"https://ptpimg.me/{ptpimg_code}.{ptpimg_ext}"
        except:
            print("PTPIMG image rehost failed")
            img_url = image_url
            # img_url = ptpimg_upload(image_url, ptpimg_api)
        return img_url


    def get_type(self, imdb_info, meta):
        ptpType = None
        if imdb_info['type'] is not None:
            imdbType = imdb_info.get('type', 'movie').lower()
            if imdbType in ("movie", "tv movie"):
                if int(imdb_info.get('runtime', '60')) >= 45:
                    ptpType = "Feature Film"
                else:
                    ptpType = "Short Film"
            if imdbType == "short":
                ptpType = "Short Film"
            elif imdbType == "tv mini series":
                ptpType = "Miniseries"
            elif imdbType == "comedy":
                ptpType = "Stand-up Comedy"
            elif imdbType == "concert":
                ptpType = "Concert"
        else:
            keywords = meta.get("keywords", "").lower()
            tmdb_type = meta.get("tmdb_type", "movie").lower()
            if tmdb_type == "movie":
                if int(meta.get('runtime', 60)) >= 45:
                    ptpType = "Feature Film"
                else:
                    ptpType = "Short Film"
            if tmdb_type == "miniseries" or "miniseries" in keywords:
                ptpType = "Miniseries"
            if "short" in keywords or "short film" in keywords:
                ptpType = "Short Film"
            elif "stand-up comedy" in keywords:
                ptpType = "Stand-up Comedy"
            elif "concert" in keywords:
                ptpType = "Concert"
        if ptpType == None:
            if meta.get('mode', 'discord') == 'cli':
                ptpTypeList = ["Feature Film", "Short Film", "Miniseries", "Stand-up Comedy", "Concert", "Movie Collection"]
                ptpType = cli_ui.ask_choice("Select the proper type", choices=ptpTypeList)
        return ptpType

    def get_codec(self, meta):
        if meta['is_disc'] == "BDMV":
            bdinfo = meta['bdinfo']
            bd_sizes = [25, 50, 66, 100]
            for each in bd_sizes:
                if bdinfo['size'] < each:
                    codec = f"BD{each}"
                    break
        elif meta['is_disc'] == "DVD":
            if "DVD5" in meta['dvd_size']:
                codec = "DVD5"
            elif "DVD9" in meta['dvd_size']:
                codec = "DVD9"
        else:
            codecmap = {
                "AVC" : "H.264",
                "H.264" : "H.264",
                "HEVC" : "H.265",
                "H.265" : "H.265",
            }
            searchcodec = meta.get('video_codec', meta.get('video_encode'))
            codec = codecmap.get(searchcodec)
            if meta.get('has_encode_settings') == True:
                codec = codec.replace("H.", "x")
        return codec

    def get_resolution(self, meta):
        other_res = None
        res = meta.get('resolution', "OTHER")
        if (res == "OTHER" and meta['is_disc'] != "BDMV") or (meta['sd'] == 1 and meta['type'] == "WEBDL"):
            video_mi = meta['mediainfo']['media']['track'][1]
            other_res = f"{video_mi['Width']}x{video_mi['Height']}"
            res = "Other"
        if meta["is_disc"] == "DVD":
            res = meta["source"].replace(" DVD", "")
        return res, other_res

    def get_container(self, meta):
        container = None
        if meta["is_disc"] == "BDMV":
            container = "m2ts"
        elif meta['is_disc'] == "DVD":
            container = "VOB IFO"
        else:
            ext = os.path.splitext(meta['filelist'][0])[1]
            containermap = {
                '.mkv' : "MKV",
                '.mp4' : 'MP4'
            }
            container = containermap.get(ext, 'Other')
        return container


    def get_source(self, source):
        sources = {
            "Blu-ray" : "Blu-ray",
            "BluRay" : "Blu-ray",
            "HD DVD" : "HD-DVD",
            "HDDVD" : "HD-DVD",
            "Web" : "WEB",
            "HDTV" : "HDTV",
            "NTSC" : "DVD",
            "PAL" : "DVD"
        }
        source_id = sources.get(source, "OtherR")
        return source_id


    def get_subtitles(self, meta):
        sub_lang_map = {
            ("Arabic", "ara", "ar") : 22,
            ("Brazilian Portuguese", "Brazilian", "Portuguese-BR", 'pt-br') : 49,
            ("Bulgarian", "bul", "bg") : 29,
            ("Chinese", "chi", "zh", "Chinese (Simplified)", "Chinese (Traditional)") : 14,
            ("Croatian", "hrv", "hr", "scr") : 23,
            ("Czech", "cze", "cz", "cs") : 30,
            ("Danish", "dan", "da") : 10,
            ("Dutch", "dut", "nl") : 9,
            ("English", "eng", "en", "English (CC)", "English - SDH") : 3,
            ("English - Forced", "English (Forced)", "en (Forced)") : 50,
            ("English Intertitles", "English (Intertitles)", "English - Intertitles", "en (Intertitles)") : 51,
            ("Estonian", "est", "et") : 38,
            ("Finnish", "fin", "fi") : 15,
            ("French", "fre", "fr") : 5,
            ("German", "ger", "de") : 6,
            ("Greek", "gre", "el") : 26,
            ("Hebrew", "heb", "he") : 40,
            ("Hindi" "hin", "hi") : 41,
            ("Hungarian", "hun", "hu") : 24,
            ("Icelandic", "ice", "is") : 28,
            ("Indonesian", "ind", "id") : 47,
            ("Italian", "ita", "it") : 16,
            ("Japanese", "jpn", "ja") : 8,
            ("Korean", "kor", "ko") : 19,
            ("Latvian", "lav", "lv") : 37,
            ("Lithuanian", "lit", "lt") : 39,
            ("Norwegian", "nor", "no") : 12,
            ("Persian", "fa", "far") : 52,
            ("Polish", "pol", "pl") : 17,
            ("Portuguese", "por", "pt") : 21,
            ("Romanian", "rum", "ro") : 13,
            ("Russian", "rus", "ru") : 7,
            ("Serbian", "srp", "sr", "scc") : 31,
            ("Slovak", "slo", "sk") : 42,
            ("Slovenian", "slv", "sl") : 43,
            ("Spanish", "spa", "es") : 4,
            ("Swedish", "swe", "sv") : 11,
            ("Thai", "tha", "th") : 20,
            ("Turkish", "tur", "tr") : 18,
            ("Ukrainian", "ukr", "uk") : 34,
            ("Vietnamese", "vie", "vi") : 25,
        }

        sub_langs = []
        if meta.get('is_disc', '') != 'BDMV':
            mi = meta['mediainfo']
            for track in mi['media']['track']:
                if track['@type'] == "Text":
                    language = track.get('Language')
                    if language == "en":
                        if track.get('Forced', "") == "Yes":
                            language = "en (Forced)"
                        if "intertitles" in track.get('Title', "").lower():
                            language = "en (Intertitles)"
                    for lang, subID in sub_lang_map.items():
                        if language in lang and subID not in sub_langs:
                            sub_langs.append(subID)
        else:
            for language in meta['bdinfo']['subtitles']:
                for lang, subID in sub_lang_map.items():
                    if language in lang and subID not in sub_langs:
                        sub_langs.append(subID)
        
        if sub_langs == []:
            sub_langs = [44] # No Subtitle
        return sub_langs


    def get_remaster_title(self, meta):
        remaster_title = []
        # Collections
        # Masters of Cinema, The Criterion Collection, Warner Archive Collection
        if meta.get('distributor') in ('WARNER ARCHIVE', 'WARNER ARCHIVE COLLECTION', 'WAC'):
            remaster_title.append('Warner Archive Collection')
        elif meta.get('distributor') in ('CRITERION', 'CRITERION COLLECTION', 'CC'):
            remaster_title.append('The Criterion Collection')
        elif meta.get('distributor') in ('MASTERS OF CINEMA', 'MOC'):
            remaster_title.append('Masters of Cinema')
        
        # Editions
        # Director's Cut, Extended Edition, Rifftrax, Theatrical Cut, Uncut, Unrated
        if "director's cut" in meta.get('edition', '').lower():
            remaster_title.append("Director's Cut")
        elif "extended" in meta.get('edition', '').lower():
            remaster_title.append("Extended Edition")
        elif "theatrical" in meta.get('edition', '').lower():
            remaster_title.append("Theatrical Cut")
        elif "rifftrax" in meta.get('edition', '').lower():
            remaster_title.append("Theatrical Cut")
        elif "uncut" in meta.get('edition', '').lower():
            remaster_title.append("Uncut")
        elif "unrated" in meta.get('edition', '').lower():
            remaster_title.append("Unrated")
        else:
            if meta.get('edition') not in ('', None):
                remaster_title.append(meta['edition'])

        # Features
        # 2-Disc Set, 2in1, 2D/3D Edition, 3D Anaglyph, 3D Full SBS, 3D Half OU, 3D Half SBS,
        # 4K Restoration, 4K Remaster, 
        # Extras, Remux,
        if meta.get('type') == "REMUX":
            remaster_title.append("Remux")

        # DTS:X, Dolby Atmos, Dual Audio, English Dub, With Commentary,
        if "DTS:X" in meta['audio']:
            remaster_title.append('DTS:X')
        if "Atmos" in meta['audio']:
            remaster_title.append('Dolby Atmos')
        if "Dual" in meta['audio']:
            remaster_title.append('Dual Audio')
        if "Dubbed" in meta['audio']:
            remaster_title.append('English Dub')
        if meta.get('has_commentary', False) == True:
            remaster_title.append('With Commentary')


        # HDR10, HDR10+, Dolby Vision, 10-bit, 
        # if "Hi10P" in meta.get('video_encode', ''):
        #     remaster_title.append('10-bit')
        if meta.get('hdr', '').strip() == '' and meta.get('bit_depth') == '10':
            remaster_title.append('10-bit')
        if "HDR" in meta.get('hdr', ''):
            if "HDR10+" in meta['hdr']:
                remaster_title.append('HDR10+')
            else:
                remaster_title.append('HDR10')
        if "DV" in meta.get('hdr', ''):
            remaster_title.append('Dolby Vision')
        if "HLG" in meta.get('hdr', ''):
            remaster_title.append('HLG')

        if remaster_title != []:
            output = " / ".join(remaster_title)
        else:
            output = ""
        return output

    def convert_bbcode(self, desc):
        desc = desc.replace("[spoiler", "[hide").replace("[/spoiler]", "[/hide]")
        desc = desc.replace("[center]", "[align=center]").replace("[/center]", "[/align]")
        desc = desc.replace("[left]", "[align=left]").replace("[/left]", "[/align]")
        desc = desc.replace("[right]", "[align=right]").replace("[/right]", "[/align]")
        desc = desc.replace("[code]", "[quote]").replace("[/code]", "[/quote]")
        return desc

    async def edit_desc(self, meta):
        from src.prep import Prep
        prep = Prep(path=meta['path'], screens=meta['screens'], img_host=meta['imghost'], config=self.config)
        base = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'r').read()
        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'w') as desc:
            images = meta['image_list']
            discs = meta.get('discs', [])
            # For Discs
            if len(discs) >= 1:
                for i in range(len(discs)):
                    each = discs[i]
                    if each['type'] == "BDMV":
                        desc.write(f"[mediainfo]{each['summary']}[/mediainfo]\n")
                        desc.write("\n")
                        if i == 0:
                            base2ptp = self.convert_bbcode(base)
                            desc.write(base2ptp)
                            mi_dump = each['summary']
                        else:
                            mi_dump = each['summary']
                            if meta.get('vapoursynth', False) == True:
                                use_vs = True
                            else:
                                use_vs = False
                            ds = multiprocessing.Process(target=prep.disc_screenshots, args=(f"FILE_{i}", each['bdinfo'], meta['uuid'], meta['base_dir'], use_vs, [], meta.get('ffdebug', False), 2))
                            ds.start()
                            while ds.is_alive() == True:
                                await asyncio.sleep(1)
                            new_screens = glob.glob1(f"{meta['base_dir']}/tmp/{meta['uuid']}",f"FILE_{i}-*.png")
                            images, dummy = prep.upload_screens(meta, 2, 1, 0, 2, new_screens, {})   

                    if each['type'] == "DVD":
                        desc.write(f"[b][size=3]{each['name']}:[/size][/b]\n")
                        desc.write(f"[mediainfo]{each['ifo_mi_full']}[/mediainfo]\n")
                        desc.write(f"[mediainfo]{each['vob_mi_full']}[/mediainfo]\n")
                        desc.write("\n")
                        if i == 0:
                            base2ptp = self.convert_bbcode(base)
                            desc.write(base2ptp)
                        else:
                            ds = multiprocessing.Process(target=prep.dvd_screenshots, args=(meta, i, 2))
                            ds.start()
                            while ds.is_alive() == True:
                                await asyncio.sleep(1)
                            new_screens = glob.glob1(f"{meta['base_dir']}/tmp/{meta['uuid']}",f"{meta['base_dir']}/tmp/{meta['uuid']}/{meta['discs'][i]['name']}-*.png")
                            images, dummy = prep.upload_screens(meta, 2, 1, 0, 2, new_screens, {})  
                        
                    if len(images) > 0: 
                        for each in range(len(images)):
                            raw_url = images[each]['raw_url']
                            desc.write(f"[img]{raw_url}[/img]")
                    desc.write("\n")
            # For non-discs
            elif len(meta.get('filelist', [])) >= 1:
                for i in range(len(meta['filelist'])):
                    file = meta['filelist'][i]
                    if i == 0:
                        mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt", 'r', encoding='utf-8').read()
                    else:
                        # Export Mediainfo
                        mi_dump = MediaInfo.parse(file, output="STRING", full=False, mediainfo_options={'inform_version' : '1'})
                        # mi_dump = mi_dump.replace(file, os.path.basename(file))
                        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/TEMP_PTP_MEDIAINFO.txt", "w", newline="", encoding="utf-8") as f:
                            f.write(mi_dump)
                        mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/TEMP_PTP_MEDIAINFO.txt", "r", encoding="utf-8").read()
                        # Generate and upload screens for other files
                        s = multiprocessing.Process(target=prep.screenshots, args=(file, f"FILE_{i}", meta['uuid'], meta['base_dir'], meta, 2))
                        s.start()
                        while s.is_alive() == True:
                            await asyncio.sleep(3)
                        new_screens = glob.glob1(f"{meta['base_dir']}/tmp/{meta['uuid']}",f"FILE_{i}-*.png")
                        images, dummy = prep.upload_screens(meta, 2, 1, 0, 2, new_screens, {})

                    desc.write(f"[mediainfo]{mi_dump}[/mediainfo]\n")
                    if i == 0:
                        base2ptp = self.convert_bbcode(base)
                        desc.write(base2ptp)    
                    if len(images) > 0: 
                        for each in range(len(images)):
                            raw_url = images[each]['raw_url']
                            desc.write(f"[img]{raw_url}[/img]")
                    desc.write("\n")

        

    async def get_AntiCsrfToken(self, meta):
        if not os.path.exists(f"{meta['base_dir']}/data/cookies"):
            Path(f"{meta['base_dir']}/data/cookies").mkdir(parents=True, exist_ok=True)
        cookiefile = f"{meta['base_dir']}/data/cookies/PTP.pickle"
        with requests.Session() as session:
            loggedIn = False
            if os.path.exists(cookiefile):
                with open(cookiefile, 'rb') as cf:
                    session.cookies.update(pickle.load(cf))
                uploadresponse = session.get("https://passthepopcorn.me/upload.php")
                loggedIn = await self.validate_login(uploadresponse)
            else:
                cprint("PTP Cookies not found. Creating new session.", 'grey', 'on_yellow')
            if loggedIn == True:
                AntiCsrfToken = re.search(r'data-AntiCsrfToken="(.*)"', uploadresponse.text).group(1)
            else:
                passKey = re.match(r"https?://please\.passthepopcorn\.me:?\d*/(.+)/announce",self.announce_url).group(1)
                data = {
                    "username": self.username,
                    "password": self.password,
                    "passkey": passKey,
                    "keeplogged": "1",
                }
                headers = {"User-Agent" : self.user_agent}
                loginresponse = session.post("https://passthepopcorn.me/ajax.php?action=login", data=data, headers=headers)
                await asyncio.sleep(2)
                try:
                    resp = loginresponse.json()
                    if resp['Result'] == "TfaRequired":
                        data['TfaType'] = "normal"
                        data['TfaCode'] = cli_ui.ask_string("2FA Required: Please enter 2FA code")
                        loginresponse = session.post("https://passthepopcorn.me/ajax.php?action=login", data=data, headers=headers)
                        await asyncio.sleep(2)
                        resp = loginresponse.json()
                    try:
                        if resp["Result"] != "Ok":
                            raise LoginException("Failed to login to PTP. Probably due to the bad user name, password, announce url, or 2FA code.")
                        AntiCsrfToken = resp["AntiCsrfToken"]
                        with open(cookiefile, 'wb') as cf:
                            pickle.dump(session.cookies, cf)
                    except Exception:
                        raise LoginException(f"Got exception while loading JSON login response from PTP. Response: {resp.text}")
                except Exception:
                    raise LoginException(f"Got exception while loading JSON login response from PTP. Response: {loginresponse.text}")
        return AntiCsrfToken

    async def validate_login(self, response):
        loggedIn = False
        if response.text.find("""<a href="login.php?act=recover">""") != -1:
            raise LoginException("Looks like you are not logged in to PTP. Probably due to the bad user name or password.")
        elif "Your popcorn quota has been reached, come back later!" in response.text:
            raise LoginException("Your PTP request/popcorn quota has been reached, try again later")
        else:
            loggedIn = True
        return loggedIn

    async def fill_upload_form(self, groupID, meta):
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        resolution, other_resolution = self.get_resolution(meta)
        await self.edit_desc(meta)
        desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", "r").read()
        data = {
            "submit": "true",
            "remaster_year": "",
            "remaster_title": self.get_remaster_title(meta), #Eg.: Hardcoded English
            "type": self.get_type(meta['imdb_info'], meta),
            "codec": "Other", # Sending the codec as custom.
            "other_codec": self.get_codec(meta),
            "container": "Other",
            "other_container": self.get_container(meta),
            "resolution": resolution,
            "source": "Other", # Sending the source as custom.
            "other_source": self.get_source(meta['source']),
            "release_desc": desc,
            "nfo_text": "",
            "subtitles[]" : self.get_subtitles(meta),
            "AntiCsrfToken" : await self.get_AntiCsrfToken(meta)
            }
        if data["remaster_year"] != "" or data["remaster_title"] != "":
            data["remaster"] = "on"
        if resolution == "Other":
            data["other_resolution"] = other_resolution
        if meta.get('personalrelease', False) == True:
            data["internalrip"] = "on"
        # IF SPECIAL (idk how to check for this automatically)
            # data["special"] = "on"
        if int(str(meta.get("imdb_id", "0")).replace('tt', '')) == 0:
            data["imdb"] = "0"
        else:
            data["imdb"] = meta["imdb_id"]


        if groupID == None: # If need to make new group
            url = "https://passthepopcorn.me/upload.php"
            if data["imdb"] == "0":
                tinfo = await self.get_torrent_info_tmdb(meta)
            else:
                tinfo = await self.get_torrent_info(meta.get("imdb_id", "0"))
            cover = meta["imdb_info"].get("cover")
            if cover == None:
                cover = meta.get('poster')
            if cover != None and "ptpimg" not in cover:
                ptpimg_cover = await self.ptpimg_url_rehost(cover)
            new_data = {
                "title": tinfo.get("title", meta["imdb_info"].get("title", meta["title"])),
                "year": tinfo.get("year", meta["imdb_info"].get("year", meta["year"])),
                "image": ptpimg_cover,
                "tags": tinfo.get("tags", ""),
                "album_desc": tinfo.get("plot", meta.get("overview", "")),
                "trailer": meta.get("youtube", ""),
            }
            while new_data["tags"] == "":
                 if meta.get('mode', 'discord') == 'cli':
                    cprint('Unable to match any tags', 'grey', 'on_yellow')
                    print("Valid tags can be found on the PTP upload form")
                    new_data["tags"] = cli_ui.ask_string("Please enter at least one tag. Comma seperated (action, animation, short):")
            data.update(new_data)
            if meta["imdb_info"].get("directors", None) != None:
                data["artist[]"] = tuple(meta['imdb_info'].get('directors'))
                data["importance[]"] = "1"
        else: # Upload on existing group
            url = f"https://passthepopcorn.me/upload.php?groupid={groupID}"
            data["groupid"] = groupID

        return url, data

    async def upload(self, meta, url, data):
        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]{meta['clean_name']}.torrent", 'rb') as torrentFile:
            files = {
                "file_input" : ("placeholder.torrent", torrentFile, "application/x-bittorent")
            }
            headers = {
                # 'ApiUser' : self.api_user,
                # 'ApiKey' : self.api_key,
                 "User-Agent": self.user_agent
            }
            if meta['debug']:
                pprint(url)
                pprint(data)
            else:
                with requests.Session() as session:
                    cookiefile = f"{meta['base_dir']}/data/cookies/PTP.pickle"
                    with open(cookiefile, 'rb') as cf:
                        session.cookies.update(pickle.load(cf))
                    response = session.post(url=url, data=data, headers=headers, files=files)
                cprint(response.url, 'cyan')
                responsetext = response.text
                # If the repsonse contains our announce url then we are on the upload page and the upload wasn't successful.
                if responsetext.find(self.announce_url) != -1:
                    # Get the error message.
                    # <div class="alert alert--error text--center">No torrent file uploaded, or file is empty.</div>
                    errorMessage = ""
                    match = re.search(r"""<div class="alert alert--error.*?>(.+?)</div>""", responsetext)
                    if match is not None:
                        errorMessage = match.group(1)

                    raise UploadException(f"Upload to PTP failed: {errorMessage} ({response.status_code}). (We are still on the upload page.)")

                
                # URL format in case of successful upload: https://passthepopcorn.me/torrents.php?id=9329&torrentid=91868
                match = re.match(r".*?passthepopcorn\.me/torrents\.php\?id=(\d+)&torrentid=(\d+)", response.url)
                if match is None:
                    pprint(url)
                    pprint(data)
                    raise UploadException(f"Upload to PTP failed: result URL {response.url} ({response.status_code}) is not the expected one.")

        
