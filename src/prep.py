# -*- coding: utf-8 -*-
from math import exp
import nest_asyncio
import imdb
from src.discparse import DiscParse
import multiprocessing
import os
from os.path import basename
import re
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
import pyimgbox
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
from imdb import IMDb
import traceback
from subprocess import Popen
import cli_ui
from pprint import pprint
import itertools






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
        self.img_host = img_host.lower()
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

        meta['is_disc'], videoloc, bdinfo, meta['discs'] = await self.get_disc(meta)
        
        # If BD:
        if meta['is_disc'] == "BDMV":
            video, meta['scene'] = self.is_scene(self.path)
            meta['filelist'] = []

            try:
                guess_name = bdinfo['title'].replace('-','')
                filename = guessit(re.sub("[^0-9a-zA-Z]+", " ", guess_name))['title']
                try:
                    meta['search_year'] = guessit(bdinfo['title'])['year']
                except:
                    meta['search_year'] = ""
            except:
                guess_name = bdinfo['label'].replace('-','')
                filename = guessit(re.sub("[^0-9a-zA-Z]+", " ", guess_name))['title']
                try:
                    meta['search_year'] = guessit(bdinfo['label'])['year']
                except:
                    meta['search_year'] = ""
            
            # await self.disc_screenshots(video, filename, bdinfo, folder_id, base_dir)
            if meta.get('edit', False) == False:
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
        #IF DVD
        elif meta['is_disc'] == "DVD":
            video, meta['scene'] = self.is_scene(self.path)
            meta['filelist'] = []
            guess_name = meta['discs'][0]['path'].replace('-','')
            # filename = guessit(re.sub("[^0-9a-zA-Z]+", " ", guess_name))['title']
            filename = guessit(guess_name)['title']
            try:
                meta['search_year'] = guessit(meta['discs'][0]['path'])['year']
            except:
                meta['search_year'] = ""
            if meta.get('edit', False) == False:
                mi = self.exportInfo(f"{meta['discs'][0]['path']}/VTS_{meta['discs'][0]['main_set'][0][:2]}_1.VOB", False, meta['uuid'], meta['base_dir'], export_text=False)
            #screenshots
            if meta.get('edit', False) == False:
                ds = multiprocessing.Process(target=self.dvd_screenshots, args=(meta, meta['discs']))
                ds.start()
                while ds.is_alive() == True:
                    await asyncio.sleep(3)
            #NTSC/PAL
            meta['dvd_size'] = await self.get_dvd_size(meta['discs'])
        #If NOT BD/VD
        else:
            videopath, meta['filelist'] = self.get_video(videoloc) 

            video, meta['scene'] = self.is_scene(videopath)
            guess_name = ntpath.basename(video).replace('-','')
            filename = guessit(re.sub("[^0-9a-zA-Z]+", " ", guess_name))["title"]

            try:
                meta['search_year'] = guessit(video)['year']
            except:
                meta['search_year'] = ""
            
            if meta.get('edit', False) == False:
                mi = self.exportInfo(videopath, meta['isdir'], folder_id, base_dir, export_text=True)
                meta['mediainfo'] = mi
            else:
                mi = meta['mediainfo']

            if meta.get('resolution', None) == None:
                meta['resolution'] = self.get_resolution(guessit(video), folder_id, base_dir)
            # if meta.get('sd', None) == None:
            meta['sd'] = self.is_sd(meta['resolution'])

            # await self.screenshots(videopath, filename, folder_id, base_dir)
            if meta.get('edit', False) == False:
                s = multiprocessing.Process(target=self.screenshots, args=(videopath, filename, folder_id, base_dir))
                s.start()
                while s.is_alive() == True:
                    await asyncio.sleep(3)
        
        

        meta['bdinfo'] = bdinfo
        
        
        if meta.get('type', None) == None:
            meta['type'] = self.get_type(video, meta['scene'], meta['is_disc'])
        if meta.get('category', None) == None:
            meta['category'] = self.get_cat(video)
        else:
            meta['category'] = meta['category'].upper()

               
        if meta.get('tmdb', None) == None and meta.get('imdb', None) == None:
            meta = await self.get_tmdb_id(filename, meta['search_year'], meta, meta['category'])
        elif meta.get('imdb', None) != None:
            meta = await self.get_tmdb_from_imdb(meta, filename)
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
        meta['source'], meta['type'] = self.get_source(meta['type'], video, meta['path'], mi)
        if meta.get('service', None) == None:
            meta['service'] = self.get_service(video)
        meta['uhd'] = self.get_uhd(meta['type'], guessit(self.path), meta['resolution'], self.path)
        meta['hdr'] = self.get_hdr(mi, bdinfo)
        if meta.get('is_disc', None) == "BDMV": #Blu-ray Specific
            meta['region'] = self.get_region(self.path, region=None)
            meta['video_codec'] = self.get_video_codec(bdinfo)
        else:
            meta['video_codec'] = mi['media']['track'][1]['Format']
            meta['video_encode'] = self.get_video_encode(mi, meta['type'], bdinfo)
        if meta.get('edition', None) == None:
            meta['edition'], meta['repack'] = self.get_edition(guessit(self.path), video, bdinfo)

        
        
        
        #WORK ON THIS
        meta.get('stream', False)
        meta['stream'] = self.stream_optimized(meta['stream'])
        meta.get('anon', False)
        meta['anon'] = self.is_anon(meta['anon'])
            
        
        
        meta = await self.gen_desc(meta)
        # pprint(meta)
        return meta




    """
    Determine if disc and if so, get bdinfo
    """
    async def get_disc(self, meta):
        is_disc = None
        videoloc = meta['path']
        bdinfo = None
        bd_summary = None
        discs = []
        parse = DiscParse()
        for path, directories, files in os.walk(meta['path']):
            for each in directories:
                if each.upper() == "BDMV": #BDMVs
                    is_disc = "BDMV"
                    disc = {
                        'path' : f"{path}/{each}",
                        'name' : os.path.basename(path),
                        'type' : 'BDMV',
                        'summary' : "",
                        'bdinfo' : ""
                    }
                    discs.append(disc)
                elif each == "VIDEO_TS": #DVDs
                    is_disc = "DVD"
                    disc = {
                        'path' : f"{path}/{each}",
                        'name' : os.path.basename(path),
                        'type' : 'DVD',
                        'vob_mi' : '',
                        'ifo_mi' : '',
                        'main_set' : [],
                        'size' : ""
                    }
                    discs.append(disc)
        if is_disc == "BDMV":
            discs, bdinfo = await parse.get_bdinfo(discs, meta['uuid'], meta['base_dir'])
        elif is_disc == "DVD":
            discs = await parse.get_dvdinfo(discs)
            export = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt", 'w', newline="", encoding='utf-8')
            export.write(discs[0]['ifo_mi'])
            export.close()
        return is_disc, videoloc, bdinfo, discs


   

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
    def exportInfo(self, video, isdir, folder_id, base_dir, export_text):
        cprint("Exporting MediaInfo...", "grey", "on_yellow")
        if export_text:
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
        
        return mi




    """
    Get Resolution
    """

    def get_resolution(self, guess, folder_id, base_dir):
        with open(f'{base_dir}/tmp/{folder_id}/MediaInfo.json', 'r', encoding='utf-8') as f:
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

    def mi_resolution(self, res, guess):
        res_map = {
            "3840x2160p" : "2160p", "2160p" : "2160p",
            "1920x1080p" : "1080p", "1080p" : "1080p",
            "1920x1080i" : "1080i", "1080i" : "1080i", 
            "1280x720p" : "720p", "720p" : "720p",
            "720x576p" : "576p", "576p" : "576p",
            "720x576i" : "576i", "576i" : "576i",
            "720x480p" :  "480p", "480p" : "480p",
            "720x480i" : "480i", "480i" : "480i",
            "15360x8640p" : "8640p", "8640p" : "8640p",
            "7680x4320p" : "4320p", "4320p" : "4320p",
            "OTHER" : "OTHER"}
        resolution = res_map.get(res, None)
        if resolution == None:     
            resolution = guess['screen_size']
            resolution = self.mi_resolution(resolution, guess)
        
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
        #Get longest m2ts
        length = 0 
        for each in bdinfo['files']:
            int_length = sum(int(float(x)) * 60 ** i for i, x in enumerate(reversed(each['length'].split(':'))))
            if int_length > length:
                length = int_length
                for root, dirs, files in os.walk(bdinfo['path']):
                    for name in files:
                        if name.lower() == each['file'].lower():
                            file = f"{root}/{name}"
                            
        
        # length = sum(int(x) * 60 ** i for i, x in enumerate(reversed(length.split(':'))))
        # for i in range(screens):
        # pprint(bdinfo)
        if "VC-1" in bdinfo['video'][0]['codec']:
            keyframe = 'nokey'
            # print("VC-1")
        else:
            keyframe = 'none'
            
        i = 0
        while i != self.screens:
            image = f"{base_dir}/tmp/{folder_id}/{filename}-{i}.png"
            (
                ffmpeg
                .input(file, ss=random.randint(round(length/5) , round(length - length/5)), skip_frame=keyframe)
                .output(image, vframes=1)
                .overwrite_output()
                .global_args('-loglevel', 'quiet')
                .run(quiet=True)
            )
            # print(os.path.getsize(image))
            # print(f'{i+1}/{self.screens}')
            cli_ui.info_count(i, self.screens, "Screens Saved")
            if os.path.getsize(Path(image)) <= 31000000 and self.img_host == "imgbb":
                i += 1
            elif os.path.getsize(Path(image)) <= 20000000 and self.img_host == "pstorage.space":
                i += 1
            elif os.path.getsize(Path(image)) <= 10000000 and self.img_host == "imgbox":
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
                
        
    def dvd_screenshots(self, meta, discs):
        cprint("Saving Screens...", "grey", "on_yellow")
        ifo_mi = MediaInfo.parse(f"{meta['discs'][0]['path']}/VTS_{meta['discs'][0]['main_set'][0][:2]}_0.IFO")
        sar = 1
        for track in ifo_mi.tracks:
            if track.track_type == "Video":
                length = float(track.duration)
                par = float(track.pixel_aspect_ratio)
                dar = float(track.display_aspect_ratio)
                width = float(track.width)
                height = float(track.height)
        if par < 1:
            # multiply that dar by the height and then do a simple width / height
            new_height = dar * height
            sar = width / new_height

        if sar > 1:
            w_sar = 1
            h_sar = sar
        else:
            w_sar = sar
            h_sar = 1
        
        length = round(float(length))
        if len(meta['discs'][0]['main_set']) >= 3:
            main_set = meta['discs'][0]['main_set'][1:-1]
        n = 0        
        i = 0

        while i != self.screens:
            if n >= self.screens:
                n -= self.screens
            image = f"{meta['base_dir']}/tmp/{meta['uuid']}/{meta['discs'][0]['name']}-{i}.png"
            (
                ffmpeg
                .input(f"{meta['discs'][0]['path']}/VTS_{main_set[n]}", ss=random.randint(round(length/5) , round(length - length/5)))
                .filter('scale', int(width * w_sar), int(height * h_sar))
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
            elif os.path.getsize(Path(image)) <= 10000000 and self.img_host == "imgbox":
                i += 1
            elif os.path.getsize(Path(image)) <= 10000:
                cprint("Image is incredibly small (and is most likely to be a single color), retaking", 'grey', 'on_yellow')
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
        with open(f"{base_dir}/tmp/{folder_id}/MediaInfo.json", encoding='utf-8') as f:
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
                elif os.path.getsize(Path(image)) <= 10000000 and self.img_host == "imgbox":
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
        # elif scene == True:
            # type = "ENCODE"
        elif "hdtv" in filename:
            type = "HDTV"
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

    async def get_tmdb_from_imdb(self, meta, filename):
        imdb_id = meta['imdb']
        if str(imdb_id)[:2].lower() != "tt":
            imdb_id = f"tt{imdb_id}"
        find = tmdb.Find(id=imdb_id)
        info = find.info(external_source="imdb_id")
        if len(info['movie_results']) >= 1:
            meta['category'] = "MOVIE"
            meta['tmdb'] = meta['tmdb_manual'] = info['movie_results'][0]['id']
        elif len(info['tv_results']) >= 1:
            meta['category'] = "TV"
            meta['tmdb'] = meta['tmdb_manual'] = info['tv_results'][0]['id']
        else:
            cprint("TMDb was unable to find anything with that IMDb, searching TMDb normally", 'grey', 'on_yellow')
            meta = await self.get_tmdb_id(filename, meta['search_year'], meta, meta['category'])
        await asyncio.sleep(3)
        return meta

    async def get_tmdb_id(self, filename, search_year, meta, category, attempted=0):
        search = tmdb.Search()
        try:
            if category == "MOVIE":
                search.movie(query=filename, year=search_year)
            elif category == "TV":
                search.tv(query=filename, first_air_date_year=search_year)
            meta['tmdb'] = search.results[0]['id']
            meta['category'] = category
        except IndexError:
            try:
                if category == "MOVIE":
                    search.movie(query=filename)
                elif category == "TV":
                    search.tv(query=filename)
                meta['tmdb'] = search.results[0]['id']
                meta['category'] = category
            except IndexError:
                if category == "MOVIE":
                    category = "TV"
                else:
                    category = "MOVIE"
                if attempted <= 1:
                    attempted += 1
                    await self.get_tmdb_id(filename, search_year, meta, category, attempted)
                else:
                    cprint('Unable to find TMDb match, please retry and pass one as an argument', 'grey', 'on_red')
                    exit()
        return meta
    
    async def tmdb_other_meta(self, meta):
        if meta['tmdb'] == "0":
            try:
                title = guessit(meta['path'])['title'].lower()
                title = title.split('aka')[0]
                meta = await self.get_tmdb_id(guessit(title)['title'], meta['search_year'], meta)
                if meta['tmdb'] == "0":
                    meta = await self.get_tmdb_id(title, "", meta, meta['category'])
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
            if meta['imdb_id'] == "":
                meta['imdb_id'] = '0'
            meta['tvdb_id'] = external.get('tvdb_id', '0')
            if meta['tvdb_id'] == "":
                meta['tvdb_id'] = '0'
            
            # meta['aka'] = f" AKA {response['original_title']}"
            meta['aka'] = await self.get_imdb_aka(meta['imdb_id'])
            meta['keywords'] = self.get_keywords(movie)
            if meta.get('anime', False) == False:
                meta['mal_id'], meta['aka'], meta['anime'] = self.get_anime(response, meta)
            meta['poster'] = response.get('poster_path', "")
            meta['overview'] = response['overview']
        elif meta['category'] == "TV":
            tv = tmdb.TV(meta['tmdb'])
            response = tv.info()
            meta['title'] = response['name']
            meta['year'] = datetime.strptime(response['first_air_date'],'%Y-%m-%d').year
            
            external = tv.external_ids()
            meta['imdb_id'] = external.get('imdb_id', "0")
            if meta['imdb_id'] == "":
                meta['imdb_id'] = '0'
            meta['tvdb_id'] = external.get('tvdb_id', '0')
            if meta['tvdb_id'] == "":
                meta['tvdb_id'] = '0'

            
            # meta['aka'] = f" AKA {response['original_name']}"
            meta['aka'] = await self.get_imdb_aka(meta['imdb_id'])
            meta['keywords'] = self.get_keywords(tv)
            meta['mal_id'], meta['aka'], meta['anime'] = self.get_anime(response, meta)
            meta['poster'] = response.get('poster_path', '')
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
        tmdb_name = tmdb_name.replace('-', "")
        tmdb_name = ' '.join(tmdb_name.split())
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
            elif channel_layout == "":
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


    def get_source(self, type, video, path, mi):
        try:
            try:
                source = guessit(video)['source']
            except:
                try:
                    source = guessit(path['source'])
                except:
                    source = "BluRay"
            
            if source in ("Blu-ray", "Ultra HD Blu-ray", "BluRay", "BR"):
                if type == "DISC":
                    source = "Blu-ray"
                elif type in ('ENCODE', 'REMUX'):
                    source = "BluRay"
            elif source in ("DVD", "dvd"):
                try:
                   system = mi['media']['track'][1]['Standard']
                except:
                    try:
                        other = guessit(video)['other']
                        if "PAL" in other:
                            system = "PAL"
                        elif "NTSC" in other:
                            system = "NTSC"
                    except:
                        system = ""
                        # system = click.prompt("Encoding system not found", type=click.Choice(["PAL", "NTSC"], case_sensitive=False))
                    source = system
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
        dv = ""
        if bdinfo != None: #Disks
            hdr_mi = bdinfo['video'][0]['hdr_dv']
            if "HDR10+" in hdr_mi:
                hdr = "HDR10+"
            elif hdr == "HDR10":
                hdr = "HDR"
            try:
                if bdinfo['video'][1]['hdr_dv'] == "Dolby Vision":
                    dv = "DV"
            except:
                pass
        else: 
            try:
                hdr_mi = mi['media']['track'][1]['colour_primaries']
                if hdr_mi in ("BT.2020", "REC.2020"):
                    hdr = "HDR"
                    try:
                        if "HDR10+" in mi['media']['track'][1]['HDR_Format_String']:
                            hdr = "HDR10+"
                    except:
                        hdr = "PQ10"
                    try:
                        if "HLG" in mi['media']['track'][1]['transfer_characteristics_Original']:
                            hdr = "HLG"
                    except:
                        pass
            except:
                pass

            try:
                # print(mi['media']['track'][1]['HDR_Format'])
                if "Dolby Vision" in mi['media']['track'][1]['HDR_Format']:
                    dv = "DV"
            except:
                pass

        hdr = f"{dv} {hdr}"
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
        repack = ""
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
            edition = ""
            repack = "REPACK"
        if "PROPER" in video:
            edition = ""
            repack = "PROPER"
        
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
        return edition, repack





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
            exclude = ["*.*", "sample.mkv"] 
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
    def upload_screens(self, meta, screens, img_host_num, i, return_dict):
        cprint('Uploading Screens', 'grey', 'on_yellow')
        os.chdir(f"{meta['base_dir']}/tmp/{meta['uuid']}")
        img_host = self.config['DEFAULT'][f'img_host_{img_host_num}']
        if img_host != self.img_host:
            img_host = self.img_host
            i -= 1
           
        # description = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'a', newline="")
        # description.write('[center]')
        image_list = []
        image_glob = glob.glob("*.png")
        if img_host == 'imgbox':
            nest_asyncio.apply()
            image_list = asyncio.run(self.imgbox_upload(f"{meta['base_dir']}/tmp/{meta['uuid']}", image_glob))               
        else:
            for image in image_glob:        
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
                        cprint("imgbb failed, trying next image host", 'yellow')
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
                        cprint("freeimage.host failed, trying next image host", 'yellow')
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
                        cprint("pstorage.space failed, trying next image host", 'yellow')
                        self.upload_screens(meta, screens - i, img_host_num + 1, i)
                elif img_host == "ptpimg":
                    payload = {
                        'format' : 'json',
                        'api_key' : self.config['DEFAULT']['ptpimg_api'] # API key is obtained from inspecting element on the upload page. 
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
                        cprint("ptpimg failed, trying next image host", 'yellow')
                        self.upload_screens(meta, screens - i, img_host_num + 1, i)
                else:
                    cprint("Please choose a supported image host in your config", 'grey', 'on_red')
                    exit()


        
            
            # description.write(f"[url={web_url}][img=350]{img_url}[/img][/url]")
            # if i % 3 == 0:
            #     description.write("\n")
                image_dict = {}
                image_dict['web_url'] = web_url
                image_dict['img_url'] = img_url
                image_list.append(image_dict)
                cli_ui.info_count(i-1, screens, "Uploaded")
                i += 1
                time.sleep(0.5)
        # description.write("[/center]")
        # description.write("\n")
            
        # description.close()
        return_dict['image_list'] = image_list
        return image_list


    async def imgbox_upload(self, chdir, image_glob):
        os.chdir(chdir)
        image_list = []
        image_glob = glob.glob("*.png")
        async with pyimgbox.Gallery() as gallery:
            async for submission in gallery.add(image_glob):
                image_dict = {}
                image_dict['web_url'] = submission['web_url']
                image_dict['img_url'] = submission['image_url']
                image_list.append(image_dict)
        return image_list






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
        repack = meta.get('repack', "")
        three_d = meta.get('3D', "")
        tag = meta.get('tag', "")
        source = meta.get('source', "")
        uhd = meta.get('uhd', "")
        hdr = meta.get('hdr', "")
        if meta.get('is_disc', "") == "BDMV": #Disk
            video_codec = meta.get('video_codec', "")
            region = meta.get('region', "")
        elif meta.get('is_disc', "") == "DVD":
            region = meta.get('region', "")
            dvd_size = meta.get('dvd_size', "")
        else:
            video_codec = meta.get('video_codec', "")
            video_encode = meta.get('video_encode', "")
        edition = meta.get('edition', "")

        if meta['debug']:
            cprint("get_name meta:", 'cyan')
            pprint(meta)

        #YAY NAMING FUN
        if meta['category'] == "MOVIE": #MOVIE SPECIFIC
            if type == "DISC": #Disk
                if meta['is_disc'] == 'BDMV':
                    name = f"{title} {alt_title} {year} {three_d} {edition} {repack} {resolution} {region} {uhd} {source} {hdr} {video_codec} {audio}"
                    potential_missing = ['edition', 'region']
                elif meta['is_disc'] == 'DVD':
                    name = f"{title} {alt_title} {year} {edition} {repack} {source} {dvd_size} {audio}"
                    potential_missing = ['edition']
            elif type == "REMUX" and source == "BluRay": #BluRay Remux
                name = f"{title} {alt_title} {year} {three_d} {edition} {repack} {resolution} {uhd} {source} REMUX {hdr} {video_codec} {audio}" 
                potential_missing = ['edition', 'description']
            elif type == "REMUX" and source in ("PAL DVD", "NTSC DVD"): #DVD Remux
                name = f"{title} {alt_title} {year} {edition} {repack} {source} REMUX  {audio}" 
                potential_missing = ['edition', 'description']
            elif type == "ENCODE": #Encode
                name = f"{title} {alt_title} {year} {edition} {repack} {resolution} {uhd} {source} {audio} {hdr} {video_encode}"  
                potential_missing = ['edition', 'description']
            elif type == "WEBDL": #WEB-DL
                name = f"{title} {alt_title} {year} {edition} {repack} {resolution} {uhd} {service} WEB-DL {audio} {hdr} {video_encode}"
                potential_missing = ['edition', 'service']
            elif type == "WEBRIP": #WEBRip
                name = f"{title} {alt_title} {year} {edition} {repack} {resolution} {uhd} {service} WEBRip {audio} {hdr} {video_encode}"
                potential_missing = ['edition', 'service']
            elif type == "HDTV": #HDTV
                name = f"{title} {alt_title} {year} {edition} {repack} {resolution} HDTV {audio} {video_encode}"
                potential_missing = []
        elif meta['category'] == "TV": #TV SPECIFIC
            if type == "DISC": #Disk
                if meta['is_disc'] == 'BDMV':
                    name = f"{title} {meta['search_year']} {alt_title} {season}{episode} {three_d} {edition} {repack} {resolution} {region} {uhd} {source} {hdr} {video_codec} {audio}"
                    potential_missing = ['edition', 'region']
                if meta['is_disc'] == 'DVD':
                    name = f"{title} {alt_title} {season}{episode}{three_d} {edition} {repack} {source} {dvd_size} {audio}"
                    potential_missing = ['edition']
            elif type == "REMUX" and source == "BluRay": #BluRay Remux
                name = f"{title} {meta['search_year']} {alt_title} {season}{episode} {three_d} {edition} {repack} {resolution} {uhd} {source} REMUX {hdr} {video_codec} {audio}" #SOURCE
                potential_missing = ['edition', 'description']
            elif type == "REMUX" and source in ("PAL DVD", "NTSC DVD"): #DVD Remux
                name = f"{title} {meta['search_year']} {alt_title} {season}{episode} {edition} {repack} {source} REMUX {audio}" #SOURCE
                potential_missing = ['edition', 'description']
            elif type == "ENCODE": #Encode
                name = f"{title} {meta['search_year']} {alt_title} {season}{episode} {edition} {repack} {resolution} {uhd} {source} {audio} {hdr} {video_encode}" #SOURCE
                potential_missing = ['edition', 'description']
            elif type == "WEBDL": #WEB-DL
                name = f"{title} {meta['search_year']} {alt_title} {season}{episode} {edition} {repack} {resolution} {uhd} {service} WEB-DL {audio} {hdr} {video_encode}"
                potential_missing = ['edition', 'service']
            elif type == "WEBRIP": #WEBRip
                name = f"{title} {meta['search_year']} {alt_title} {season}{episode} {edition} {repack} {resolution} {uhd} {service} WEBRip {audio} {hdr} {video_encode}"
                potential_missing = ['edition', 'service']
            elif type == "HDTV": #HDTV
                name = f"{title} {meta['search_year']} {alt_title} {season}{episode} {edition} {repack} {resolution} HDTV {audio} {video_encode}"
                potential_missing = []


    
        name = ' '.join(name.split())
        name_notag = name
        name = name_notag + tag
        clean_name = self.clean_filename(name)
        return name_notag, name, clean_name, potential_missing




    async def get_season_episode(self, video, meta):
        if meta['category'] == 'TV':
            filelist = meta['filelist']
            meta['tv_pack'] = 0
            if meta['anime'] == False:
                try:
                    try:
                        guess_year = guessit(video)['year']
                    except:
                        guess_year = ""
                    if guessit(video)["season"] == guess_year:
                        if f"s{guessit(video)['season']}" in video.lower():
                            season = "S" + str(guessit(video)["season"]).zfill(2)
                        else:
                            season = "S01"
                    else:
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
                        meta['tv_pack'] = 1
                except:
                    # print(traceback.format_exc())
                    episode = ""
                    meta['tv_pack'] = 1
            else:
                parsed = anitopy.parse(Path(video).name)
                romaji, mal_id, eng_title, seasonYear = self.get_romaji(guessit(parsed['anime_title'])['title'])
                if meta.get('tmdb_manual', None) == None:
                    year = parsed.get('anime_year', str(seasonYear))
                    meta = await self.get_tmdb_id(guessit(parsed['anime_title'])['title'], year, meta, meta['category'])
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
                        meta['tv_pack'] = 1
                except:
                    episode = ""
                    meta['tv_pack'] = 1
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
            if meta.get('manual_season', None) == None:
                meta['season'] = season
            else:
                meta['season'] = f"S{meta['manual_season'].zfill(2)}"
            if meta.get('manual_episode', None) == None:
                meta['episode'] = episode
            else:
                meta['episode'] = f"E{meta['manual_episode'].zfill(2)}"
            
            if " COMPLETE " in Path(video).name.replace('.', ' '):
                meta['season'] = "COMPLETE"
        return meta


    def get_service(self, video):
        service = guessit(video).get('streaming_service', "")
        services = {
            '9NOW': '9NOW', '9Now': '9NOW', 'AE': 'AE', 'A&E': 'AE', 'AJAZ': 'AJAZ', 'Al Jazeera English': 'AJAZ', 
            'ALL4': 'ALL4', 'Channel 4': 'ALL4', 'AMBC': 'AMBC', 'ABC': 'AMBC', 'AMC': 'AMC', 'AMZN': 'AMZN', 
            'Amazon Prime': 'AMZN', 'ANLB': 'ANLB', 'AnimeLab': 'ANLB', 'ANPL': 'ANPL', 'Animal Planet': 'ANPL', 
            'AOL': 'AOL', 'ARD': 'ARD', 'AS': 'AS', 'Adult Swim': 'AS', 'ATK': 'ATK', "America's Test Kitchen": 'ATK', 
            'ATVP': 'ATVP', 'AppleTV': 'ATVP', 'AUBC': 'AUBC', 'ABC Australia': 'AUBC', 'BCORE': 'BCORE', 'BKPL': 'BKPL', 
            'Blackpills': 'BKPL', 'BluTV': 'BLU', 'Binge': 'BNGE', 'BOOM': 'BOOM', 'Boomerang': 'BOOM', 'BRAV': 'BRAV', 
            'BravoTV': 'BRAV', 'CBC': 'CBC', 'CBS': 'CBS', 'CC': 'CC', 'Comedy Central': 'CC', 'CCGC': 'CCGC', 
            'Comedians in Cars Getting Coffee': 'CCGC', 'CHGD': 'CHGD', 'CHRGD': 'CHGD', 'CMAX': 'CMAX', 'Cinemax': 'CMAX', 
            'CMOR': 'CMOR', 'CMT': 'CMT', 'Country Music Television': 'CMT', 'CN': 'CN', 'Cartoon Network': 'CN', 'CNBC': 'CNBC', 
            'CNLP': 'CNLP', 'Canal+': 'CNLP', 'COOK': 'COOK', 'CORE': 'CORE', 'CR': 'CR', 'Crunchy Roll': 'CR', 'Crave': 'CRAV', 
            'CRIT': 'CRIT', 'CRKL': 'CRKL', 'Crackle': 'CRKL', 'CSPN': 'CSPN', 'CSpan': 'CSPN', 'CTV': 'CTV', 'CUR': 'CUR', 
            'CuriosityStream': 'CUR', 'CW': 'CW', 'The CW': 'CW', 'CWS': 'CWS', 'CWSeed': 'CWS', 'DAZN': 'DAZN', 'DCU': 'DCU', 
            'DC Universe': 'DCU', 'DDY': 'DDY', 'Digiturk Diledigin Yerde': 'DDY', 'DEST': 'DEST', 'DramaFever': 'DF', 'DHF': 'DHF', 
            'Deadhouse Films': 'DHF', 'DISC': 'DISC', 'Discovery': 'DISC', 'DIY': 'DIY', 'DIY Network': 'DIY', 'DOCC': 'DOCC', 
            'Doc Club': 'DOCC', 'DPLY': 'DPLY', 'DPlay': 'DPLY', 'DRPO': 'DRPO', 'Discovery Plus': 'DSCP', 'DSKI': 'DSKI', 
            'Daisuki': 'DSKI', 'DSNP': 'DSNP', 'Disney+': 'DSNP', 'DSNY': 'DSNY', 'Disney': 'DSNY', 'DTV': 'DTV', 
            'EPIX': 'EPIX', 'ePix': 'EPIX', 'ESPN': 'ESPN', 'ESQ': 'ESQ', 'Esquire': 'ESQ', 'ETTV': 'ETTV', 'El Trece': 'ETTV', 
            'ETV': 'ETV', 'E!': 'ETV', 'FAM': 'FAM', 'Family': 'FAM', 'Fandor': 'FANDOR', 'Facebook Watch': 'FBWatch', 'FJR': 'FJR', 
            'Family Jr': 'FJR', 'FOOD': 'FOOD', 'Food Network': 'FOOD', 'FOX': 'FOX', 'Fox': 'FOX', 'Fox Premium': 'FOXP', 
            'UFC Fight Pass': 'FP', 'FPT': 'FPT', 'FREE': 'FREE', 'Freeform': 'FREE', 'FTV': 'FTV', 'FUNI': 'FUNI', 
            'Foxtel': 'FXTL', 'FYI': 'FYI', 'FYI Network': 'FYI', 'GC': 'GC', 'NHL GameCenter': 'GC', 'GLBL': 'GLBL', 
            'Global': 'GLBL', 'GLOB': 'GLOB', 'GloboSat Play': 'GLOB', 'GO90': 'GO90', 'GagaOOLala': 'Gaga', 'HBO': 'HBO', 
            'HBO Go': 'HBO', 'HGTV': 'HGTV', 'HIDI': 'HIDI', 'HIST': 'HIST', 'History': 'HIST', 'HLMK': 'HLMK', 'Hallmark': 'HLMK', 
            'HMAX': 'HMAX', 'HBO Max': 'HMAX', 'HS': 'HS', 'HULU': 'HULU', 'Hulu': 'HULU', 'hoichoi': 'HoiChoi', 'ID': 'ID', 
            'Investigation Discovery': 'ID', 'IFC': 'IFC', 'iflix': 'IFX', 'National Audiovisual Institute': 'INA', 'ITV': 'ITV', 
            'KAYO': 'KAYO', 'KNOW': 'KNOW', 'Knowledge Network': 'KNOW', 'KNPY': 'KNPY', 'LIFE': 'LIFE', 'Lifetime': 'LIFE', 'LN': 'LN', 
            'MBC': 'MBC', 'MNBC': 'MNBC', 'MSNBC': 'MNBC', 'MTOD': 'MTOD', 'Motor Trend OnDemand': 'MTOD', 'MTV': 'MTV', 'MUBI': 'MUBI', 
            'NATG': 'NATG', 'National Geographic': 'NATG', 'NBA': 'NBA', 'NBA TV': 'NBA', 'NBC': 'NBC', 'NF': 'NF', 'Netflix': 'NF', 
            'National Film Board': 'NFB', 'NFL': 'NFL', 'NFLN': 'NFLN', 'NFL Now': 'NFLN', 'NICK': 'NICK', 'Nickelodeon': 'NICK', 'NRK': 'NRK', 
            'Norsk Rikskringkasting': 'NRK', 'OnDemandKorea': 'ODK', 'Opto': 'OPTO', 'Oprah Winfrey Network': 'OWN', 'PA': 'PA', 'PBS': 'PBS', 
            'PBSK': 'PBSK', 'PBS Kids': 'PBSK', 'PCOK': 'PCOK', 'Peacock': 'PCOK', 'PLAY': 'PLAY', 'PLUZ': 'PLUZ', 'Pluzz': 'PLUZ', 'PMNP': 'PMNP', 
            'PMNT': 'PMNT', 'POGO': 'POGO', 'PokerGO': 'POGO', 'PSN': 'PSN', 'Playstation Network': 'PSN', 'PUHU': 'PUHU', 'QIBI': 'QIBI', 
            'RED': 'RED', 'YouTube Red': 'RED', 'RKTN': 'RKTN', 'Rakuten TV': 'RKTN', 'The Roku Channel': 'ROKU', 'RSTR': 'RSTR', 'RTE': 'RTE', 
            'RTE One': 'RTE', 'RUUTU': 'RUUTU', 'SBS': 'SBS', 'Science Channel': 'SCI', 'SESO': 'SESO', 'SeeSo': 'SESO', 'SHMI': 'SHMI', 'Shomi': 'SHMI', 
            'SHO': 'SHO', 'Showtime': 'SHO', 'SNET': 'SNET', 'Sportsnet': 'SNET', 'Sony': 'SONY', 'SPIK': 'SPIK', 'Spike': 'SPIK', 'Spike TV': 'SPKE', 
            'SPRT': 'SPRT', 'Sprout': 'SPRT', 'STAN': 'STAN', 'Stan': 'STAN', 'STARZ': 'STARZ', 'STZ': 'STZ', 'Starz': 'STZ', 'SVT': 'SVT', 
            'Sveriges Television': 'SVT', 'SWER': 'SWER', 'SwearNet': 'SWER', 'SYFY': 'SYFY', 'Syfy': 'SYFY', 'TBS': 'TBS', 'TEN': 'TEN', 
            'TFOU': 'TFOU', 'TFou': 'TFOU', 'TIMV': 'TIMV', 'TLC': 'TLC', 'TOU': 'TOU', 'TRVL': 'TRVL', 'TUBI': 'TUBI', 'TubiTV': 'TUBI', 
            'TV3': 'TV3', 'TV3 Ireland': 'TV3', 'TV4': 'TV4', 'TV4 Sweeden': 'TV4', 'TVING': 'TVING', 'TVL': 'TVL', 'TV Land': 'TVL', 
            'TVNZ': 'TVNZ', 'UFC': 'UFC', 'UKTV': 'UKTV', 'UNIV': 'UNIV', 'Univision': 'UNIV', 'USAN': 'USAN', 'USA Network': 'USAN', 
            'VH1': 'VH1', 'VIAP': 'VIAP', 'VICE': 'VICE', 'Viceland': 'VICE', 'Viki': 'VIKI', 'VIMEO': 'VIMEO', 'VLCT': 'VLCT', 
            'Velocity': 'VLCT', 'VMEO': 'VMEO', 'Vimeo': 'VMEO', 'VRV': 'VRV', 'VUDU': 'VUDU', 'WME': 'WME', 'WatchMe': 'WME', 'WNET': 'WNET', 
            'W Network': 'WNET', 'WWEN': 'WWEN', 'WWE Network': 'WWEN', 'XBOX': 'XBOX', 'Xbox Video': 'XBOX', 'YHOO': 'YHOO', 'Yahoo': 'YHOO', 
            'YT': 'YT', 'ZDF': 'ZDF', 'iP': 'iP', 'BBC iPlayer': 'iP', 'iQIYI': 'iQIYI', 'iT': 'iT', 'iTunes': 'iT'
            }
        
        video_name = video.replace('.', ' ')
        for key, value in services.items():
            if (' ' + value + ' ') in (' ' + video_name + ' '):
                service = value
            elif key == service:
                service = value
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

    
    async def gen_desc(self, meta):
        desclink = meta.get('desclink', None)
        descfile = meta.get('descfile', None)
        description = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'w', newline="")
        description.seek(0)
        if meta.get('discs', []) != []:
            discs = meta['discs']
            if discs[0]['type'] == "DVD":
                description.write(f"[spoiler=VOB MediaInfo][code]{discs[0]['vob_mi']}[/code][/spoiler]")
            if len(discs) >= 2:
                for each in discs[1:]:
                    if each['type'] == "BDMV":
                        description.write(f"[spoiler={each.get('name', 'BDINFO')}][code]{each['summary']}[/code][/spoiler]")
                        description.write("\n")
                    if each['type'] == "DVD":
                        description.write(f"{each['name']}:\n")
                        description.write(f"[spoiler={os.path.basename(each['vob'])}][code][{each['vob_mi']}[/code][/spoiler] [spoiler={os.path.basename(each['ifo'])}][code][{each['ifo_mi']}[/code][/spoiler]")
                        description.write("\n")
        if meta['nfo'] != False:
            description.write("[code]")
            nfo = glob.glob("*.nfo")[0]
            description.write(open(nfo, 'r').read())
            description.write("[/code]")
            description.write("\n")
        if desclink != None:
            parsed = urllib.parse.urlparse(desclink)
            raw = parsed._replace(path=f"/raw{parsed.path}")
            raw = urllib.parse.urlunparse(raw)
            description.write(requests.get(raw).text)
            description.write("\n")
        if descfile != None:
            if os.path.isfile(descfile) == True:
                text = open(descfile, 'r').read()
                description.write(text)
        if meta['desc'] != None:
            description.write(meta['desc'])
            description.write("\n")
            description.write("\n")
        return meta
        
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
        archive = f"{meta['base_dir']}/tmp/{meta['title']}-{meta['uuid']}"
        shutil.make_archive(archive, 'tar', f"{meta['base_dir']}/tmp/{meta['uuid']}")
        files = {
            "files[]" : (f"{meta['title']}.tar", open(f"{archive}.tar", 'rb'))}
        try:
            response = requests.post("https://uguu.se/upload.php", files=files).json()
            if meta['debug']:
                cprint(response, 'cyan')
            url = response['files'][0]['url']
            return url
        except:
            return False
        return 

    async def get_imdb_aka(self, imdb_id):
        if imdb_id == "0":
            return ""
        ia = IMDb()
        result = ia.get_movie(imdb_id.replace('tt', ''))
                
        aka = result.get('original title', result.get('localized title', ""))
        if aka != "":
            aka = f" AKA {aka}"
        return aka

    async def get_dvd_size(self, discs):
        sizes = []
        dvd_sizes = []
        for each in discs:
            sizes.append(each['size'])
        grouped_sizes = [list(i) for j, i in itertools.groupby(sorted(sizes))]
        for each in grouped_sizes:
            if len(each) > 1:
                dvd_sizes.append(f"{len(each)}x{each[0]}")
        dvd_sizes.sort()
        compact = " ".join(dvd_sizes)
        return compact
    

    