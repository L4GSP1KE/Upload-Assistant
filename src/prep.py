# -*- coding: utf-8 -*-

import multiprocessing
import os
from os.path import basename
import sys
import shortuuid
import asyncio
from guessit import guessit
import ntpath
from pathlib import Path
import urllib
import ffmpeg
import random
import json
import glob
import requests
from pymediainfo import MediaInfo
import tmdbsimple as tmdb
from datetime import datetime
from difflib import SequenceMatcher
from torf import Torrent
from termcolor import colored, cprint
# from pprint import pprint
import base64
import time
import anitopy
import shutil
import traceback
import logging
from subprocess import Popen
import cli_ui
from pprint import pprint






class Prep():
    """
    Prepare for upload:
        Mediainfo/BDInfo
        Screenshots
        Database Identifiers (TMDB/IMDB/MAL/etc)
        Create Name
    """
    def __init__(self, path, screens, img_host, config):
        self.path = path
        self.screens = screens
        self.config = config
        self.img_host = img_host
        tmdb.API_KEY = config['DEFAULT']['tmdb_api']


    async def gather_prep(self, meta):
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        meta['isdir'] = os.path.isdir(self.path)
        base_dir = meta['base_dir']

        folder_id = shortuuid.uuid()
        meta['uuid'] = folder_id 
        if not os.path.exists(f"{base_dir}/tmp/{folder_id}"):
            Path(f"{base_dir}/tmp/{folder_id}").mkdir(parents=True, exist_ok=True)

        if meta['debug']:
            cprint(f"ID: {meta['uuid']}", 'cyan')

        is_disc, videoloc, bdinfo, bd_summary = await self.get_disc(self.path, folder_id, base_dir)
        
        # If BD:
        if bdinfo != None:
            video, scene = self.is_scene(self.path)
            meta['filelist'] = []

            try:
                filename = guessit(bdinfo['label'])['title']
                try:
                    meta['search_year'] = guessit(bdinfo['label'])['year']
                except:
                    meta['search_year'] = ""
            except:
                filename = guessit(bdinfo['title'])['title']
                try:
                    meta['search_year'] = guessit(bdinfo['title'])['year']
                except:
                    meta['search_year'] = ""
            
            # await self.disc_screenshots(video, filename, bdinfo, folder_id, base_dir)
            ds = multiprocessing.Process(target=self.disc_screenshots, args=(video, filename, bdinfo, folder_id, base_dir))
            ds.start()
            while ds.is_alive() == True:
                await asyncio.sleep(3)

            if meta.get('resolution', None) == None:
                meta['resolution'] = self.mi_resolution(bdinfo['video'][0]['res'], guessit(video))
            # if meta.get('sd', None) == None:
            meta['sd'] = self.is_sd(meta['resolution'])

            mi = None
            mi_dump = None

        #If NOT BD
        else:
            videopath, meta['filelist'] = self.get_video(videoloc) 

            video, scene = self.is_scene(videopath)

            filename = guessit(ntpath.basename(video))["title"]

            try:
                meta['search_year'] = guessit(video)['year']
            except:
                meta['search_year'] = ""
            

            mi_dump, mi = self.exportInfo(videopath, filename, meta['isdir'], folder_id, base_dir)

            if meta.get('resolution', None) == None:
                meta['resolution'] = self.get_resolution(guessit(video), folder_id, base_dir)
            # if meta.get('sd', None) == None:
            meta['sd'] = self.is_sd(meta['resolution'])

            # await self.screenshots(videopath, filename, folder_id, base_dir)
            s = multiprocessing.Process(target=self.screenshots, args=(videopath, filename, folder_id, base_dir))
            s.start()
            while s.is_alive() == True:
                await asyncio.sleep(3)
        
        

        meta['bdinfo'] = bdinfo
        
        
        if meta.get('type', None) == None:
            meta['type'] = self.get_type(video, scene, is_disc)
        if meta.get('category', None) == None:
            meta['category'] = self.get_cat(video) 

        
        if meta.get('tmdb', None) == None:
            meta = await self.get_tmdb_id(filename, meta['search_year'], meta)
        else:
            meta['tmdb_manual'] = meta.get('tmdb', None)
        meta = await self.tmdb_other_meta(meta)

        if meta.get('tag', None) == None:
            meta['tag'] = self.get_tag(video, meta)
        meta = await self.get_season_episode(video, meta)
        meta = await self.tag_override(meta)

        meta['video'] = video
        meta['audio'] = self.get_audio_v2(mi, meta['anime'], bdinfo)
        meta['3D'] = self.is_3d(mi, bdinfo)
        meta['source'], meta['type'] = self.get_source(meta['type'], video)
        if meta.get('service', None) == None:
            meta['service'] = self.get_service(video)
        meta['uhd'] = self.get_uhd(meta['type'], guessit(self.path), meta['resolution'], self.path)
        meta['hdr'] = self.get_hdr(mi, bdinfo)
        if meta.get('type', None) == "DISC": #Disk
            meta['region'] = self.get_region(self.path, region=None)
            meta['video_codec'] = self.get_video_codec(bdinfo)
        else:
            meta['video_codec'] = mi['media']['track'][1]['Format']
            meta['video_encode'] = self.get_video_encode(mi, meta['type'], bdinfo)
        if meta.get('edition', None) == None:
            meta['edition'] = self.get_edition(guessit(self.path), video, bdinfo)

        
        
        
        #WORK ON THIS
        meta.get('stream', False)
        meta['stream'] = self.stream_optimized(meta['stream'])
        meta.get('anon', False)
        meta['anon'] = self.is_anon(meta['anon'])
            
        
        
        await self.gen_desc(meta, bd_summary)
        # pprint(meta)
        return meta
















    """
    Determine if disc and if so, get bdinfo
    """
    async def get_disc(self, base_path, folder_id, base_dir):
        is_disc = None
        videoloc = base_path
        bdinfo = None
        bd_summary = None
        for path, directories, files in os.walk(base_path):
            if "STREAM" in directories:
                is_disc = "BDMV"
                # videoloc = os.path.join(path, "STREAM", get_largest(os.path.join(path, "STREAM"))) 
                bd_summary, bdinfo = await self.get_bdinfo(base_path, folder_id, base_dir)
            elif "VIDEO_TS" in directories:
                is_disc = "DVD"
                videoloc = directories
                bd_summary, bdinfo = await self.get_bdinfo(base_path, folder_id, base_dir) #Probably doesnt work
            
        return is_disc, videoloc, bdinfo, bd_summary


    """
    Get and parse bdinfo
    """
    async def get_bdinfo(self, path, folder_id, base_dir):
        cprint("Getting BDInfo", 'grey', 'on_yellow')
        save_dir = f"{base_dir}/tmp/{folder_id}"
        if not os.path.exists(save_dir):
            os.mkdir(save_dir)
        bdinfo_text = None
        
        for file in os.listdir(save_dir):
            if file.startswith("BDINFO"):
                bdinfo_text = save_dir + "/" + file
        if bdinfo_text == None:
            if sys.platform.startswith('linux'):
                try:
                    # await asyncio.subprocess.Process(['mono', "bin/BDInfo/BDInfo.exe", "-w", path, save_dir])
                    proc = await asyncio.create_subprocess_exec('mono', "bin/BDInfo/BDInfo.exe", '-w', path, save_dir)
                    await proc.wait()
                except:
                    cprint('mono not found, please install mono', 'grey', 'on_red')
                    
            elif sys.platform.startswith('win32'):
                # await asyncio.subprocess.Process(["bin/BDInfo/BDInfo.exe", "-w", path, save_dir])
                proc = await asyncio.create_subprocess_exec("bin/BDInfo/BDInfo.exe", "-w", path, save_dir)
                await proc.wait()
                await asyncio.sleep(1)
        while True:
            try:
                for file in os.listdir(save_dir):
                    if file.startswith("BDINFO"):
                        bdinfo_text = save_dir + "/" + file
                with open(bdinfo_text, 'r') as f:
                    text = f.read()
                    result = text.split("QUICK SUMMARY:", 2)
                    result2 = result[1].rstrip("\n")
                    result = result2.split("********************", 1)
                    bd_summary = f"QUICK SUMMARY:{result[0]}".rstrip("\n")
                    f.close()
            except Exception:
                # print(e)
                await asyncio.sleep(5)
                continue
            break
        with open(f"{save_dir}/BDINFO.txt", 'w') as f:
            f.write(bd_summary)
            f.close()
        bdinfo = self.parse_bdinfo(bd_summary)
        # shutil.rmtree(f"{base_dir}/tmp")
        return bd_summary, bdinfo
            

    def parse_bdinfo(self, bdinfo_input):
        bdinfo = dict()
        bdinfo['video'] = list()
        bdinfo['audio'] = list()
        lines = bdinfo_input.splitlines()
        for l in lines:
            line = l.strip().lower()
            if line.startswith("*"):
                line = l.replace("*", "").strip().lower()
                # print(line)
            if line.startswith("playlist:"):
                playlist = l.split(':', 1)[1]
                bdinfo['playlist'] = playlist.split('.',1)[0].strip()
            if line.startswith("length:"):
                length = l.split(':', 1)[1]
                bdinfo['length'] = length.split('.',1)[0].strip()
            if line.startswith("video:"):
                split1 = l.split(':', 1)[1]
                split2 = split1.split('/', 12)
                while len(split2) != 9:
                    split2.append("")
                n=0
                if "Eye" in split2[2].strip():
                    n = 1
                    three_dim = split2[2].strip()
                else:
                    three_dim = ""
                try:
                    bit_depth = split2[n+6].strip()
                    hdr_dv = split2[n+7].strip()
                    color = split2[n+8].strip()
                except:
                    bit_depth = ""
                    hdr_dv = ""
                    color = ""
                bdinfo['video'].append({
                    'codec': split2[0].strip(), 
                    'bitrate': split2[1].strip(), 
                    'res': split2[n+2].strip(), 
                    'fps': split2[n+3].strip(), 
                    'aspect_ratio' : split2[n+4].strip(),
                    'profile': split2[n+5].strip(),
                    'bit_depth' : bit_depth,
                    'hdr_dv' : hdr_dv, 
                    'color' : color,
                    '3d' : three_dim,
                    })
            elif line.startswith("audio:"):
                if "(" in l:
                    l = l.split("(")[0]
                l = l.strip()
                split1 = l.split(':', 1)[1]
                split2 = split1.split('/')
                n = 0
                if "Atmos" in split2[2].strip():
                    n = 1
                    fuckatmos = split2[2].strip()
                else:
                    fuckatmos = ""
                bdinfo['audio'].append({
                    'language' : split2[0].strip(), 
                    'codec' : split2[1].strip(), 
                    'channels' : split2[n+2].strip(), 
                    'sample_rate' : split2[n+3].strip(), 
                    'bitrate' : split2[n+4].strip(), 
                    'bit_depth' : split2[n+5].strip(),
                    'atmos_why_you_be_like_this': fuckatmos,
                    })
            elif line.startswith("disc title:"):
                title = l.split(':', 1)[1]
                # print(f"TITLE: {title}")
                bdinfo['title'] = title
            elif line.startswith("disc label:"):
                label = l.split(':', 1)[1]
                bdinfo['label'] = label
        # pprint(bdinfo)
        return bdinfo



    """
    Get video files

    """
    def get_video(self, videoloc):
        filelist = []
        if os.path.isdir(videoloc):
            os.chdir(videoloc)
            filelist = glob.glob('*.mkv') + glob.glob('*.mp4') + glob.glob('*.m2ts')
            video = sorted(filelist)[0]        
        else:
            video= videoloc
            filelist.append(videoloc)
        return video, filelist






    """
    Get and parse mediainfo
    """
    def exportInfo(self, video, filename, isdir, folder_id, base_dir):
        cprint("Exporting MediaInfo...", "grey", "on_yellow")
        #MediaInfo to text
        if isdir == False:
            os.chdir(os.path.dirname(video))
        media_info = MediaInfo.parse(os.path.basename(video), output="STRING", full=False)
        export = open(f"{base_dir}/tmp/{folder_id}/MEDIAINFO.txt", 'w', newline="", encoding='utf-8')
        export.write(media_info)
        export.close()
        mi_dump = media_info

        #MediaInfo to JSON
        media_info = MediaInfo.parse(video, output="JSON")
        export = open(f"{base_dir}/tmp/{folder_id}/MediaInfo.json", 'w', encoding='utf-8')
        export.write(media_info)
        export.close()
        with open(f"{base_dir}/tmp/{folder_id}/MediaInfo.json", 'r', encoding='utf-8') as f:
            mi = json.load(f)
        cprint("MediaInfo Exported.", "grey", "on_green")
        
        return mi_dump, mi




    """
    Get Resolution
    """

    def get_resolution(self, guess, folder_id, base_dir):
        with open(f'{base_dir}/tmp/{folder_id}/MediaInfo.json', 'r') as f:
            mi = json.load(f)
            try:
                width = mi['media']['track'][1]['Width']
                height = mi['media']['track'][1]['Height']
            except:
                width = 0
                height = 0
            if mi['media']['track'][1]['FrameRate_Mode'] == "CFR":
                framerate = mi['media']['track'][1]['FrameRate']
            else:
                framerate = ""
            try:
                scan = mi['media']['track'][1]['ScanType']
            except:
                scan = "Progressive"
            if scan == "Progressive":
                scan = "p"
            elif  framerate == "25.000":
                scan = "p"
            else:
                scan = "i"
            width_list = [3840, 1920, 1280, 720, 15360, 7680, 0]
            height_list = [2160, 1080, 720, 576, 480, 8640, 4320, 0]
            width = self.closest(width_list, int(width))
            height = self.closest(height_list, int(height))
            res = f"{width}x{height}{scan}"
            resolution = self.mi_resolution(res, guess)

        return resolution

    def closest(self, lst, K):
        return lst[min(range(len(lst)), key = lambda i: abs(lst[i]-K))]

    def mi_resolution(self, resolution, guess):
        if resolution in ("2160p", "3840x2160p"):
            # resolution_id = 1
            resolution = "2160p"
        elif resolution in ("1080p", "1920x1080p"):
            # resolution_id = 2
            resolution = "1080p"
        elif resolution in ("1080i" ,  "1920x1080i"):
            # resolution_id = 3
            resolution = "1080i"
        elif resolution in ("720p" ,  "1280x720p"):
            # resolution_id = 5
            resolution = "720p"
        elif resolution in ("576p" ,  "720x576p"):
            # resolution_id = 6
            resolution = "576p"
        elif resolution in ("576i" ,  "720x576i"):
            # resolution_id = 7
            resolution = "576i"
        elif resolution in ("480p" ,  "720x480p"):
            # resolution_id = 8
            resolution = "480p"
        elif resolution in ("480i" ,  "720x480p"):
            # resolution_id = 9
            resolution = "480i"
        elif resolution in ("8640p" ,  "15360x8640p"):
            # resolution_id = 10
            resolution = "8640p"
        elif resolution in ("4320p" ,  "7680x4320p"):
            # resolution_id = 11
            resolution = "4320p"
        elif resolution == "OTHER":
            # resolution_id = 10
            resolution = "OTHER"
        else:
            # try: 
            resolution = guess['screen_size']
            resolution= self.mi_resolution(resolution, guess)
            # except:
            #     resolution = click.prompt('Unable to parse resolution. Please select one:', type=click.Choice(['2160p', '1080p', '1080i', '720p', '576p', '576i', '480p', '480i', '8640p', '4320p', 'OTHER'], case_sensitive=False))
            #     resolution, sd = mi_resolution(resolution, guess)
        #is sd
               
        return resolution

    def is_sd(self, resolution):
        if resolution in ("OTHER", "480i", "480p", "576i", "576p"):
            sd = 1
        else:
            sd = 0
        return sd

    """
    Is a scene release?
    """
    def is_scene(self, video):
        scene = False
        base = os.path.basename(video)
        base = os.path.splitext(base)[0]
        base = urllib.parse.quote(base)
        url = f"https://www.srrdb.com/api/search/r:{base}"
        try:
            response = requests.get(url)
            response = response.json()
            if response['resultsCount'] != "0":
                video = f"{response['results'][0]['release']}.mkv"
                scene = True
        except:
            video = video
            scene = False
        return video, scene








    """
    Generate Screenshots
    """

    def disc_screenshots(self, path, filename, bdinfo, folder_id, base_dir):
        cprint("Saving Screens...", "grey", "on_yellow")
        length = bdinfo['length']
        length = secs = sum(int(x) * 60 ** i for i, x in enumerate(reversed(length.split(':'))))
        # for i in range(screens):
        # pprint(bdinfo)
        if "VC-1" in bdinfo['video'][0]['codec']:
            is_vc1 = 'nokey'
            # print("VC-1")
        else:
            is_vc1 = 'none'
            
        i = 0
        while i != self.screens:
            image = f"{base_dir}/tmp/{folder_id}/{filename}-{i}.png"
            (
                ffmpeg
                .input(f"bluray:{path}", ss=random.randint(round(length/5) , round(length - length/5)), skip_frame=is_vc1)
                .output(image, vframes=1)
                .overwrite_output()
                .global_args('-loglevel', 'quiet', "-playlist", f"{bdinfo['playlist']}", )
                .run(quiet=True)
            )
            # print(os.path.getsize(image))
            # print(f'{i+1}/{self.screens}')
            cli_ui.info_count(i, self.screens, "Screens Saved")
            if os.path.getsize(Path(image)) <= 31000000 and self.img_host == "imgbb":
                i += 1
            elif os.path.getsize(Path(image)) <= 20000000 and self.img_host == "pstorage.space":
                i += 1
            elif os.path.getsize(Path(image)) <= 10000:
                cprint("Image is incredibly small, retaking", 'grey', 'on_yellow')
                time.sleep(1)
            elif self.img_host == "ptpimg":
                i += 1
            elif self.img_host == "freeimage.host":
                i += 1
            else:
                cprint("Image too large for your image host, retaking", 'grey', 'on_red')
                time.sleep(1)
                
        


    def screenshots(self, path, filename, folder_id, base_dir):
        cprint("Saving Screens...", "grey", "on_yellow")
        with open(f"{base_dir}/tmp/{folder_id}/MediaInfo.json") as f:
            mi = json.load(f)
            length = mi['media']['track'][1]['Duration']
            length = round(float(length))
            # for i in range(screens):
            i = 0
            while i != self.screens:
                image = f"{base_dir}/tmp/{folder_id}/{filename}-{i}.png"
                (
                    ffmpeg
                    .input(path, ss=random.randint(round(length/5) , round(length - length/5)))
                    .output(image, vframes=1)
                    .overwrite_output()
                    .global_args('-loglevel', 'quiet')
                    .run(quiet=True)
                )
                # print(os.path.getsize(image))
                # print(f'{i+1}/{self.screens}')
                cli_ui.info_count(i, self.screens, "Screens Saved")
                # print(Path(image))
                if os.path.getsize(Path(image)) <= 31000000 and self.img_host == "imgbb":
                    i += 1
                elif os.path.getsize(Path(image)) <= 20000000 and self.img_host == "pstorage.space":
                    i += 1
                elif os.path.getsize(Path(image)) <= 10000:
                    cprint("Image is incredibly small, retaking", 'grey', 'on_yellow')
                    time.sleep(1)
                elif self.img_host == "ptpimg":
                    i += 1
                elif self.img_host == "freeimage.host":
                    i += 1
                else:
                    cprint("Image too large for your image host, retaking", 'grey', 'on_red')
                    time.sleep(1)
                    



    """
    Get type and category
    """

    def get_type(self, video, scene, is_disc):
        filename = video.lower()
        if "remux" in filename:
            type = "REMUX"
        elif any(word in filename for word in [" web ", ".web.", "web-dl"]):
            type = "WEBDL"
        elif "webrip" in filename:
            type = "WEBRIP"
        elif scene == True:
            type = "ENCODE"
        elif is_disc != None:
            type = "DISC"
        else:
            type = "ENCODE"
        return type

    def get_cat(self, video):
        # if category is None:
        category = guessit(video)['type']
        if category.lower() == "movie":
            category = "MOVIE" #1
        elif category.lower() in ("tv", "episode"):
            category = "TV" #2
        else:
            category = "MOVIE"
        return category


    async def get_tmdb_id(self, filename, search_year, meta):
        search = tmdb.Search()
        try:
            if meta['category'] == "MOVIE":
                search.movie(query=filename, year=search_year)
            elif meta['category'] == "TV":
                search.tv(query=filename, first_air_date_year=search_year)
            meta['tmdb'] = search.results[0]['id']
        
        except:
            meta['tmdb'] = "0"
        return meta
    
    async def tmdb_other_meta(self, meta):
        if meta['tmdb'] == "0":
            try:
                title = guessit(meta['path'])['title'].lower()
                title = title.split('aka')[0]
                meta = await self.get_tmdb_id(title, meta['search_year'], meta)
                if meta['tmdb'] == "0":
                    meta = await self.get_tmdb_id(title, "", meta)
            except:
                cprint("Unable to find tmdb entry", 'grey', 'on_red')
                return meta
        if meta['category'] == "MOVIE":
            movie = tmdb.Movies(meta['tmdb'])
            response = movie.info()
            meta['title'] = response['title']
            meta['year'] = datetime.strptime(response['release_date'],'%Y-%m-%d').year
            
            external = movie.external_ids()
            meta['imdb_id'] = external.get('imdb_id', "0")
            meta['tvdb_id'] = external.get('tvdb_id', '0')
            
            meta['aka'] = f" AKA {response['original_title']}"
            meta['keywords'] = self.get_keywords(movie)
            if meta.get('anime', False) == False:
                meta['mal_id'], meta['aka'], meta['anime'] = self.get_anime(response, meta)
            meta['poster'] = response['poster_path']
            meta['overview'] = response['overview']
        elif meta['category'] == "TV":
            tv = tmdb.TV(meta['tmdb'])
            response = tv.info()
            meta['title'] = response['name']
            meta['year'] = datetime.strptime(response['first_air_date'],'%Y-%m-%d').year
            
            external = tv.external_ids()
            meta['imdb_id'] = external.get('imdb_id', "0")
            meta['tvdb_id'] = external.get('tvdb_id', '0')

            
            meta['aka'] = f" AKA {response['original_name']}"
            meta['keywords'] = self.get_keywords(tv)
            meta['mal_id'], meta['aka'], meta['anime'] = self.get_anime(response, meta)
            meta['poster'] = response['poster_path']
            meta['overview'] = response['overview']
        meta['poster'] = f"https://image.tmdb.org/t/p/original{meta['poster']}"

        difference = SequenceMatcher(None, meta['title'], meta['aka'][5:]).ratio()
        if difference >= 0.8:
            meta['aka'] = ""
            
        
        return meta



    def get_keywords(self, tmdb_info):
        if tmdb_info is not None:
            tmdb_keywords = tmdb_info.keywords()
            if tmdb_keywords.get('keywords') is not None:
                keywords=[f"{keyword['name'].replace(',',' ')}" for keyword in tmdb_keywords.get('keywords')]
            elif tmdb_keywords.get('results') is not None:
                keywords=[f"{keyword['name'].replace(',',' ')}" for keyword in tmdb_keywords.get('results')]
            return(', '.join(keywords))
        else:
            return ''

    def get_anime(self, response ,meta):
        tmdb_name = meta['title']
        if meta.get('aka', "") == "":
            alt_name = ""
        else:
            alt_name = meta['aka']
        anime = False
        animation = False
        for each in response['genres']:
            if each['id'] == 16:
                animation = True
        if response['original_language'] == 'ja' and animation == True:
            romaji, mal_id, eng_title, season_year = self.get_romaji(tmdb_name)
            alt_name = f" AKA {romaji}"
            
            anime = True
            # mal = AnimeSearch(romaji)
            # mal_id = mal.results[0].mal_id
        else:
            mal_id = 0
        return mal_id, alt_name, anime

    def get_romaji(self, tmdb_name):
        query = '''
            query ($search: String) { 
                Media (search: $search, type: ANIME) { 
                    id
                    idMal
                    title {
                        romaji
                        english
                        native
                    }
                    seasonYear
                }
            }
        '''

        # Define our query variables and values that will be used in the query request
        variables = {
            'search': tmdb_name
        }

        url = 'https://graphql.anilist.co'

        # Make the HTTP Api request
        response = requests.post(url, json={'query': query, 'variables': variables})
        json = response.json()
        romaji = json['data']['Media']['title']['romaji']
        mal_id = json['data']['Media']['idMal']
        eng_title = json['data']['Media']['title']['english']
        season_year = json['data']['Media']['seasonYear']
        return romaji, mal_id, eng_title, season_year








    """
    Mediainfo/Bdinfo > meta
    """
    def get_audio_v2(self, mi, anime, bdinfo):
        #Get formats
        if bdinfo != None: #Disks
            format = bdinfo['audio'][0]['codec']
            try:
                additional = bdinfo['audio'][0]['atmos_why_you_be_like_this']
            except:
                additional = ""
            #Channels
            chan = bdinfo['audio'][0]['channels']


        else: 
            format = mi['media']['track'][2]['Format']
            try:
                additional = mi['media']['track'][2]['Format_AdditionalFeatures']
                # format = f"{format} {additional}"
            except:
                additional = ""

            #Channels
            channels = mi['media']['track'][2]['Channels']
            try:
                channel_layout = mi['media']['track'][2]['ChannelLayout']
            except:
                try:
                    channel_layout = mi['media']['track'][2]['ChannelLayout_Original']
                except:
                    channel_layout = ""
            if "LFE" in channel_layout:
                chan = f"{int(channels) - 1}.1"
            else:
                chan = f"{channels}.0"
            
        
        extra = ""
        dual = ""
        
        #Convert commercial name to naming conventions
        audio = {
            "DTS": "DTS",
            "AAC": "AAC",
            "AAC LC": "AAC",
            "AC-3": "DD",
            "E-AC-3": "DD+",
            "MLP FBA": "TrueHD",
            "FLAC": "FLAC",
            "Opus": "OPUS",
            "Vorbis": "VORBIS",
            "PCM": "LPCM",
            #BDINFO AUDIOS
            "LPCM Audio" : "LPCM",
            "Dolby Digital Audio" : "DD",
            "Dolby Digital Plus Audio" : "DD+",
            # "Dolby TrueHD" : "TrueHD",
            "Dolby TrueHD Audio" : "TrueHD",
            "DTS Audio" : "DTS", 
            "DTS-HD Master Audio" : "DTS-HD MA",
            "DTS-HD High-Res Audio" : "DTS-HD HRA",
        }
        audio_extra = {
            "XLL": "-HD MA",
            "XLL X": ":X",
            "ES": "-ES",
        }
        format_extra = {
            "JOC": " Atmos",
            "16-ch": " Atmos",
            "Atmos Audio": " Atmos",
        }

        codec = audio.get(format, "") + audio_extra.get(additional, "")
        extra = format_extra.get(additional, "")
        
        if codec == "":
            codec = format


        if anime == True:
            eng, jap = False, False
            try:
                for t in mi['media']['track']:
                    if t['@type'] != "Audio":
                        pass
                    else: 
                        if t['Language'] == "en":
                            eng = True
                        if t['Language'] == "ja":
                            jap = True
                if eng and jap == True:
                    dual = "Dual-Audio"
            except:
                pass
        audio = f"{dual} {codec} {chan}{extra}"
        return audio


    def is_3d(self, mi, bdinfo):
        if bdinfo != None:
            if bdinfo['video'][0]['3d'] != "":
                return "3D"
            else:
                return ""
        else:
            return ""

    def get_tag(self, video, meta):
        try:
            tag = guessit(video)['release_group']
            tag = f"-{tag}"
        except:
            tag = ""
        if tag == "-":
            tag = ""
        if tag[1:].lower() in ["nogroup"]:
            tag = ""
        return tag


    def get_source(self, type, video):
        try:
            try:
                source = guessit(video)['source']
            except:
                source = ""
            
            if source in ("Blu-ray", "Ultra HD Blu-ray", "BluRay", "BR"):
                if type == "DISC":
                    source = "Blu-ray"
                elif type in ('ENCODE', 'REMUX'):
                    source = "BluRay"
            elif source in ("DVD", "dvd"):
                try:
                    other = guessit(video)['other']
                    if "PAL" in other:
                        system = "PAL"
                    elif "NTSC" in other:
                        system = "NTSC"
                except:
                    system = ""
                    # system = click.prompt("Encoding system not found", type=click.Choice(["PAL", "NTSC"], case_sensitive=False))
                source = system + " DVD"
            elif source in ("Web"):
                if type == "ENCODE":
                    type = "WEBRIP"
        except Exception:
            # print(traceback.format_exc())
            # prompt = click.prompt("Unable to find source, please choose one", type=click.Choice(["BR", "DVD"], case_sensitive=False), default="BR")
            # source = get_source(type_id, prompt, 2)
            source = "BluRay"

        return source, type

    def get_uhd(self, type, guess, resolution, path):
        try:
            source = guess['Source']
            other = guess['Other']
        except:
            source = ""
            other = ""
        uhd = ""
        if source == 'Blu-ray' and other == "Ultra HD" or source == "Ultra HD Blu-ray":
            uhd = "UHD"
        elif "UHD" in path:
            uhd = "UHD"
        elif type in ("DISC", "REMUX", "ENCODE", "WEBRIP"):
            uhd = ""
            
        if type in ("DISC", "REMUX", "ENCODE") and resolution == "2160p":
            uhd = "UHD"

        return uhd

    def get_hdr(self, mi, bdinfo):
        hdr = ""
        if bdinfo != None: #Disks
            hdr_mi = bdinfo['video'][0]['hdr_dv']
            if "HDR10+" in hdr_mi:
                hdr = "HDR10+"
            elif hdr == "HDR10":
                hdr = "HDR"
            try:
                if bdinfo['video'][1]['hdr_dv'] == "Dolby Vision":
                    hdr = hdr + " DV "
            except:
                pass
        else: 
            try:
                hdr_mi = mi['media']['track'][1]['colour_primaries']
                if hdr_mi in ("BT.2020", "REC.2020"):
                    hdr = "HDR"
                    try:
                        if "HDR10+" in mi['media']['track'][1]['HDR_Format_Compatibility']:
                            hdr = "HDR10+"
                    except:
                        pass
                    try:
                        if "HLG" in mi['media']['track'][1]['transfer_characteristics_Original']:
                            hdr = "HLG"
                    except:
                        pass
            except:
                pass

            else:
                try:
                    # print(mi['media']['track'][1]['HDR_Format'])
                    if "Dolby Vision" in mi['media']['track'][1]['HDR_Format']:
                        hdr = "DV"
                except:
                    pass
        return hdr

    def get_region(self, path, region):
        if region != None:
            region = region
        else: 
            regions = {
            "USA" : "USA",
            "FRE" : "FRE",
            "GBR" : "GBR",
            "GER" : "GER",
            "CZE" : "CZE",
            "EUR" : "EUR",
            "CAN" : "CAN",
            "TWN" : "TWN",
            "AUS" : "AUS",
            "BRA" : "BRA",
            "ITA" : "ITA",
            "ESP" : "ESP",
            "HKG" : "HKG",
            "JPN" : "JPN",
            "NOR" : "NOR",
            "FRA" : "FRA",
            }
            region = regions.get(region, "")
            # if region == "":
            #     region = click.prompt("Enter region, leave blank for unknown", default="")
            if region == None:
                region = ""
        return region

    
    def get_video_codec(self, bdinfo):
        codecs = {
            "MPEG-4 AVC Video" : "AVC",
            "MPEG-H HEVC Video" : "HEVC",
        }
        codec = codecs.get(bdinfo['video'][0]['codec'], "")
        return codec

    def get_video_encode(self, mi, type, bdinfo):
        video_encode = ""
        codec = ""
        try:
            format = mi['media']['track'][1]['Format']
            format_profile = mi['media']['track'][1]['Format_Profile']
        except:
            format = bdinfo['video'][0]['codec']
            format_profile = bdinfo['video'][0]['profile']
        if type in ("ENCODE", "WEBRIP"): #ENCODE or WEBRIP
            if format == 'AVC':
                codec = 'x264'
            elif format == 'HEVC':
                codec = 'x265'
        elif type == 'WEBDL': #WEB-DL
            if format == 'AVC':
                codec = 'H.264'
            elif format == 'HEVC':
                codec = 'H.265'
        elif format == "VP9":
            codec = "VP9"
        elif format == "VC-1":
            codec = "VC-1"
        if format_profile == 'High 10':
            profile = "Hi10P"
        else:
            profile = ""
        video_encode = f"{profile} {codec}"
        return video_encode


    def get_edition(self, guess, video, bdinfo):
        if bdinfo != None:
            try:
                edition = guessit(bdinfo['label'])['edition']
            except:
                edition = ""
        else:
            try:
                edition = guess['edition']
            except:
                edition = ""
        if "open matte" in video.replace('.', ' ').lower():
            edition = edition + "Open Matte"
        if "REPACK" in video:
            edition = edition + " REPACK "
        if "PROPER" in video:
            edition = edition + " PROPER "
        
        bad = ['internal', 'limited', 'retail']

        if edition.lower() in bad:
            edition = ""
        # try:
        #     other = guess['other']
        # except:
        #     other = ""
        # if " 3D " in other:
        #     edition = edition + " 3D "
        # if edition == None or edition == None:
        #     edition = ""
        return edition





    """
    Create Torrent
    """
    def create_torrent(self, meta, path):
        video = meta['video']
        if meta['isdir'] == True:
            os.chdir(path)
            globs = glob.glob("*.mkv") + glob.glob("*.mp4")
            if len(globs) == 1:
                path = video
        if meta['bdinfo'] != None:
            include, exclude = "", ""
        else:
            exclude = ["*.*"] 
            include = ["*.mkv", "*.mp4"]
        torrent = Torrent(path,
            # trackers = [announce],
            # source = "",
            private = True,
            exclude_globs = [exclude],
            include_globs = [include],
            created_by = "L4G's Upload Assistant")
        cprint("Creating .torrent", 'grey', 'on_yellow')
        torrent.piece_size_max = 16777216
        torrent.generate(callback=self.torf_cb, interval=5)
        torrent.write(f"{meta['base_dir']}/tmp/{meta['uuid']}/BASE.torrent", overwrite=True)
        torrent.verify_filesize(path)
        cprint(".torrent created", 'grey', 'on_green')
        return torrent

    
    def torf_cb(self, torrent, filepath, pieces_done, pieces_total):
        # print(f'{pieces_done/pieces_total*100:3.0f} % done')
        cli_ui.info_progress("Hashing...", pieces_done, pieces_total)







    """
    Upload Screenshots
    """
    def upload_screens(self, meta, screens, img_host_num, i):
        cprint('Uploading Screens', 'grey', 'on_yellow')
        os.chdir(f"{meta['base_dir']}/tmp/{meta['uuid']}")
        img_host = self.config['DEFAULT'][f'img_host_{img_host_num}']
        if img_host != self.img_host:
            img_host = self.img_host
            i -= 1
           
        description = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'a', newline="")
        description.write('[center]')
        for image in glob.glob("*.png"):
            tasks = []        
            if img_host == "imgbb":
                url = "https://api.imgbb.com/1/upload"
                data = {
                    'key': self.config['DEFAULT']['imgbb_api'],
                    'image': base64.b64encode(open(image, "rb").read()).decode('utf8')
                }
                response = requests.post(url, data = data).json()
                try:
                    img_url = response['data']['url']
                    web_url = response['data']['url_viewer']
                except:
                    self.upload_screens(meta, screens - i , img_host_num + 1, i)
            elif img_host == "freeimage.host":
                url = "https://freeimage.host/api/1/upload"
                data = {
                    'key': '6d207e02198a847aa98d0a2a901485a5',
                    'action' : 'upload',
                    'source' : base64.b64encode(open(image, "rb").read()).decode('utf8'),
                }
                headers = {'content-type' : 'image/png'}
                files= {open(image, 'rb')}
                response = requests.post(url, data = data).json()
                try:
                    img_url = response['image']['url']
                    web_url = response['image']['url_viewer']
                except:
                    self.upload_screens(meta, screens - i, img_host_num + 1, i)
            elif img_host == "pstorage.space":
                url = "https://pstorage.space/api/1/upload"
                data = {
                    'key' : self.config['DEFAULT']['pstorage_api'],
                    'source' : base64.b64encode(open(image, "rb").read()).decode('utf8'),
                    'filename' : image
                }
                response = requests.post(url, data = data).json()
                try:
                    img_url = response['url']
                    web_url = response['url_viewer']
                except:
                    self.upload_screens(meta, screens - i, img_host_num + 1, i)
            elif img_host == "ptpimg":
                # data = {
                #     'format': 'json',
                #     'api_key': self.config['DEFAULT']['ptpimg_api'],
                #     'file-upload' : open(image, 'rb')
                #     } # API key is obtained from inspecting element on the upload page. 
                payload = {
                    'format' : 'json',
                    'api_key' : self.config['DEFAULT']['ptpimg_api']
                }
                files = [('file-upload[0]', open(image, 'rb'))] 
                headers = { 'referer': 'https://ptpimg.me/index.php'} 
                url = "https://ptpimg.me/upload.php"

                # tasks.append(asyncio.ensure_future(self.upload_image(session, url, data, headers, files=None)))
                response = requests.post("https://ptpimg.me/upload.php", headers=headers, data=payload, files=files)
                try:
                    response = response.json()
                    ptpimg_code = response[0]['code'] 
                    ptpimg_ext = response[0]['ext'] 
                    img_url = f"https://ptpimg.me/{ptpimg_code}.{ptpimg_ext}" 
                    web_url = f"https://ptpimg.me/{ptpimg_code}.{ptpimg_ext}" 
                except:
                    # print(traceback.format_exc())
                    self.upload_screens(meta, screens - i, img_host_num + 1, i)
                    cprint("PTPimg down?", 'grey', 'on_red')
                    pass
            else:
                cprint("Please choose a supported image host in your config", 'grey', 'on_red')
                exit()


        
            
            # description.write(f"[url={web_url}][img]https://images.weserv.nl/?url={img_url}&w=350[/img][/url]")
            description.write(f"[url={web_url}][img=350]{img_url}[/img][/url]")
            if i % 3 == 0:
                description.write("\n")
            cli_ui.info_count(i-1, screens, "Uploaded")
            i += 1
            time.sleep(0.5)
        description.write("[/center]")
        description.write("\n")
            
        description.close()










    async def get_name(self, meta):
        type = meta.get('type', "")
        title = meta.get('title',"")
        alt_title = meta.get('aka', "")
        year = meta.get('year', "")
        resolution = meta.get('resolution', "")
        audio = meta.get('audio', "")
        service = meta.get('service', "")
        season = meta.get('season', "")
        episode = meta.get('episode', "")

        three_d = meta.get('3D', "")
        tag = meta.get('tag', "")
        source = meta.get('source', "")
        uhd = meta.get('uhd', "")
        hdr = meta.get('hdr', "")
        if type == "DISC": #Disk
            region = meta.get('region', "")
            video_codec = meta.get('video_codec', "")
        else:
            video_codec = meta.get('video_codec', "")
            video_encode = meta.get('video_encode', "")
        edition = meta.get('edition', "")


        #YAY NAMING FUN
        if meta['category'] == "MOVIE": #MOVIE SPECIFIC
            if type == "DISC": #Disk
                name = f"{title} {alt_title} {year} {three_d} {resolution} {edition} {region} {uhd} {source} {hdr} {video_codec} {audio}"
                convention = "Name Year Resolution Region Source Video-codec Audio-Tag"
            elif type == "REMUX" and source == "BluRay": #BluRay Remux
                name = f"{title} {alt_title} {year} {three_d} {resolution} {edition} {uhd} {source} REMUX {hdr} {video_codec} {audio}" 
                convention = "Name Year Resolution Source Video-codec Audio-Tag"
            elif type == "REMUX" and source in ("PAL DVD", "NTSC DVD"): #DVD Remux
                name = f"{title} {alt_title} {year} {source} REMUX  {audio}" 
                convention = "Name Year Encoding_system Format Source Audio-Tag"
            elif type == "ENCODE": #Encode
                name = f"{title} {alt_title} {year} {resolution} {edition} {uhd} {source} {audio} {hdr} {video_encode}"  
                convention = "Name Year Resolution Source Audio Video-Tag"
            elif type == "WEBDL": #WEB-DL
                name = f"{title} {alt_title} {year} {resolution} {edition} {uhd} {service} WEB-DL {audio} {hdr} {video_encode}"
                convention = "Name Year Resolution Source Rip-type Audio Video-codec-Tag"
            elif type == "WEBRIP": #WEBRip
                name = f"{title} {alt_title} {year} {resolution} {edition} {uhd} {service} WEBRip {audio} {hdr} {video_encode}"
                convention = "Name Year Resolution Source Rip-type Audio Video-codec-Tag"
            elif type == "HDTV": #HDTV
                name = f"{title} {alt_title} {year} {resolution} {edition} HDTV {audio} {video_encode}"
                convention = "Name Year Resolution Source Audio Video-Tag"
        elif meta['category'] == "TV": #TV SPECIFIC
            if type == "DISC": #Disk
                name = f"{title} {alt_title} {season}{episode} {three_d} {resolution} {edition} {region} {uhd} {source} {hdr} {video_codec} {audio}"
                convention = "Name Year Resolution Region Source Video-codec Audio-Tag"
            elif type == "REMUX" and source == "BluRay": #BluRay Remux
                name = f"{title} {alt_title} {season}{episode} {three_d} {resolution} {edition} {uhd} {source} REMUX {hdr} {video_codec} {audio}" #SOURCE
                convention = "Name Year Resolution Source Video-codec Audio-Tag"
            elif type == "REMUX" and source in ("PAL DVD", "NTSC DVD"): #DVD Remux
                name = f"{title} {alt_title} {season}{episode} {source} REMUX {audio}" #SOURCE
                convention = "Name Year Encoding_system Format Source Audio-Tag"
            elif type == "ENCODE": #Encode
                name = f"{title} {alt_title} {season}{episode} {resolution} {edition} {uhd} {source} {audio} {hdr} {video_encode}" #SOURCE
                convention = "Name Year Resolution Source Audio Video-Tag"
            elif type == "WEBDL": #WEB-DL
                name = f"{title} {alt_title} {season}{episode} {resolution} {edition} {uhd} {service} WEB-DL {audio} {hdr} {video_encode}"
                convention = "Name Year Resolution Source Rip-type Audio Video-Tag"
            elif type == "WEBRIP": #WEBRip
                name = f"{title} {alt_title} {season}{episode} {resolution} {edition} {uhd} {service} WEBRip {audio} {hdr} {video_encode}"
                convention = "Name Year Resolution Source Rip-type Audio Video-Tag"
            elif type == "HDTV": #HDTV
                name = f"{title} {alt_title} {season}{episode} {resolution} {edition} HDTV {audio} {video_encode}"
                convention = "Name Year Resolution Source Audio Video-Tag"


    
        name = ' '.join(name.split())
        name_notag = name
        name = name_notag + tag
        clean_name = self.clean_filename(name)
        return name_notag, name, clean_name




    async def get_season_episode(self, video, meta):
        filelist = meta['filelist']
        if meta['anime'] == False:
            try:
                season = "S" + str(guessit(video)["season"]).zfill(2)
            except:
                try:
                    season = guessit(video)['date']
                except:
                    season = "S01"
            try:
                episodes = ""
                if len(filelist) == 1:
                    episodes = guessit(video)['episode']
                    if type(episodes) == list:
                        episode = ""
                        for item in guessit(video)["episode"]:
                            ep = (str(item).zfill(2))
                            episode += f"E{ep}"
                    else:
                        episode = "E" + str(episodes).zfill(2)
                else:
                    episode = ""
            except:
                # print(traceback.format_exc())
                episode = ""
        else:
            parsed = anitopy.parse(Path(video).name)
            romaji, mal_id, eng_title, seasonYear = self.get_romaji(guessit(parsed['anime_title'])['title'])
            if meta.get('tmdb_manual', None) == None:
                year = parsed.get('anime_year', str(seasonYear))
                meta = await self.get_tmdb_id(guessit(parsed['anime_title'])['title'], year, meta)
            meta = await self.tmdb_other_meta(meta)
            tag = parsed.get('release_group', "")
            if tag != "":
                meta['tag'] = f"-{tag}"
            try:
                if len(filelist) == 1:
                    episodes = parsed['episode_number']
                    if type(episodes) == list:
                        episode = ""
                        for item in episodes:
                            ep = (str(item).zfill(2))
                            episode += f"E{ep}"
                    else:
                        episode = f"E{episodes.zfill(2)}"
                else:
                    episode = ""
            except:
                episode = ""
            try:
                season = parsed['anime_season']
                season = f"S{season.zfill(2)}"
            except:
                try:
                    data = {
                        'id' : str(meta['tvdb_id']),
                        'origin' : 'tvdb',
                        'absolute' : str(parsed['episode_number']),
                        'destination' : 'anidb'
                    }
                    url = "http://thexem.de/map/single"
                    response = requests.post(url, data=data).json()
                    season = f"S{str(response['data']['anidb']['season']).zfill(2)}"
                    if len(filelist) == 1:
                        episode = f"E{str(response['data']['anidb']['episode']).zfill(2)}"
                except:
                    # print(f"{meta['title']} does not exist on thexem")
                    season = "S01"
            try:
                version = parsed['release_version']
                version = f"v{version}"
            except:
                version = ""
            episode = episode + version

        meta['season'] = season
        meta['episode'] = episode
        return meta


    def get_service(self, video):
        try:
            service = guessit(video)['streaming_service']
            if service == 'Amazon Prime':
                service = "AMZN"
            elif service == 'Netflix':
                service = "NF"
            elif service == 'Hulu':
                service = "HULU"
            elif service == "HBO Max":
                service = "HMAX"
        except:
            if "HMAX" in video:
                service = "HMAX"
            elif "DSNP" in video:
                service = "DSNP"
            elif "ATVP" in video:
                service = "ATVP"
            elif "ALL4" in video:
                service = "ALL4"
            else:
                service = ""
        return service



    def stream_optimized(self, stream_opt):
        if stream_opt == True:
            stream = 1
        else:
            stream = 0
        return stream

    def is_anon(self, anon_in):
        anon = self.config['DEFAULT']['anon']
        if anon.lower() == "true":
            anon_in = True
        if anon_in == True:
            anon_out = 1
        else:
            anon_out = 0
        return anon_out

    async def upload_image(self, session, url, data, headers, files):
        if headers == None and files == None:
            async with session.post(url=url, data=data) as resp:
                response = await resp.json()
                return response
        elif headers == None and files != None:
            async with session.post(url=url, data=data, files=files) as resp:
                response = await resp.json()
                return response
        elif headers != None and files == None:
            async with session.post(url=url, data=data, headers=headers) as resp:
                response = await resp.json()
                return response
        else:
            async with session.post(url=url, data=data, headers=headers, files=files) as resp:
                response = await resp.json()
                return response
            
    
    def clean_filename(self, name):
        invalid = '<>:"/\|?*'
        for char in invalid:
            name = name.replace(char, '-')
        return name

    
    async def gen_desc(self, meta, bd_summary):
        description = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'w', newline="")
        description.seek(0)
        if bd_summary != None:
            description.write("[code]")
            description.write(bd_summary)
            description.write("[/code]")
            description.write("\n")
        if meta['nfo'] != False:
            description.write("[code]")
            nfo = glob.glob("*.nfo")[0]
            description.write(open(nfo, 'r').read())
            description.write("[/code]")
            description.write("\n")
        # if desclink != None:
        #     parsed = urllib.parse.urlparse(desclink)
        #     raw = parsed._replace(path=f"/raw{parsed.path}")
        #     raw = urllib.parse.urlunparse(raw)
        #     description.write(requests.get(raw).text)
        #     description.write("\n")
        # if descfile != None:
        #     if os.path.isfile(descfile) == True:
        #         text = open(descfile, 'r').read()
        #         description.write(text)
        if meta['desc'] != None:
            description.write(meta['desc'])
            description.write("\n")
            description.write("\n")

    async def tag_override(self, meta):
        with open(f"{meta['base_dir']}/data/tags.json", 'r', encoding="utf-8") as f:
            tags = json.load(f)
            f.close()
        
        for tag in tags:
            value = tags.get(tag)
            if meta['tag'][1:] == tag:
                for key in value:
                    if key == 'type':
                        if meta[key] == "ENCODE":
                            meta[key] = value.get(key)
                        else:
                            pass
                    else:
                        meta[key] = value.get(key)
                # print(f"Tag: {meta['tag']} | Key: {key} | Value: {meta[key]}")
        return meta
    

    async def package(self, meta):
        archive = f"{meta['base_dir']}/tmp/{meta['title']}"
        shutil.make_archive(archive, 'tar', f"{meta['base_dir']}/tmp/{meta['uuid']}")
        files = {
            "files[]" : (f"{meta['title']}.tar", open(f"{archive}.tar", 'rb'))}
        try:
            response = requests.post("https://uguu.se/upload.php", files=files).json()
            print(response)
            url = response['files'][0]['url']
            return url
        except:
            return False
        return 