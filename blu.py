import os
import sys
import configparser
from pathlib import Path
from datetime import datetime
from click.termui import edit
from pymediainfo import MediaInfo
import click
from termcolor import colored, cprint
import ffmpeg
import json
import ntpath
import random
import glob
import re
import time
import requests
import base64
import tmdbsimple as tmdb
from guessit import guessit
from torf import Torrent
from difflib import SequenceMatcher
import shutil
# import pyimgbox
from mal import AnimeSearch
import xmlrpc.client
import urllib
import qbittorrentapi
from subprocess import Popen, PIPE, STDOUT, run, DEVNULL
import keyboard
import bencode
from pyrobase.parts import Bunch
import errno
import hashlib
from deluge_client import DelugeRPCClient, LocalDelugeRPCClient
import traceback
from pprint import pprint
# from PIL import Image

base_dir = os.path.abspath(os.path.dirname(__file__))
os.chdir(base_dir)

config = configparser.ConfigParser()
config.read('config.ini')
tmdb.API_KEY = config['DEFAULT']['tmdb_api']
announce = config['DEFAULT']['announce_url']
blu_api = config['DEFAULT']['blu_api']
rtorrent_url = config['DEFAULT']['rtorrent_url']
remote_path = config['DEFAULT']['remote_path']
local_path = config['DEFAULT']['local_path']
torrent_client = config['DEFAULT']['torrent_client']
img_host = config['DEFAULT']['img_host']
img_api = config['DEFAULT']['img_api']





#TODO

#FAST RESUME < qbit only
#FANRES/TRAILER SUPPORT <- probably not
#DISK SUPPORT <- done. probably
#tmdb/imdb id input argument
#mkv 3d
#Audio formats I may have missed
#Description feature is pretty meh
#Replace cprint with something more windows friendly
#Make less sloppy
#detect stream optimized



#Do the thingy
@click.command()
@click.argument('path',type=click.Path('r'))
@click.option('--screens', '-s', help="Number of screenshots", default=6)
@click.option('--category', '-c', type=click.Choice(['MOVIE', 'TV'], case_sensitive=False), help="Category")
@click.option('--debug', is_flag=True, help="Used for testing features")
@click.option('--type', '-t', type=click.Choice(['DISK', 'REMUX', 'ENCODE', 'WEBDL', 'WEBRIP', 'HDTV'], case_sensitive=False), help="Type")
@click.option('--res', '-r',type=click.Choice(['2160p', '1080p', '1080i', '720p', '576p', '576i', '480p', '480i', '8640p', '4320p', 'OTHER'], case_sensitive=False), help="Resolution")
@click.option('--tag', '-g', help="Group tag")
@click.option('--desc', '-d', help="Custom description (String)")
@click.option('--descfile', '-df', help="Custom description (Path to File)", type=click.Path('rb'))
@click.option('--desclink', '-hb', help="Custom description (Link to hastebin)")
@click.option('--bdinfo', '-bdinfo', help="Choose to paste BDInfo instead of scan", is_flag=True)
@click.option('--nfo', '-nfo', help="Use nfo from directory as description", is_flag=True)
@click.option('--keywords', '-k', help='Add keywords e.g. "keyword, keyword2, etc"')
@click.option('--anon', '-a', help="Anonymous upload", is_flag=True)
@click.option('--stream', '-st', help="Stream Optimized Upload", is_flag=True)
@click.option('--region', '-r', help="Disk Region")
@click.option('--dupe', '-st', help="Ths release is a duplicate", is_flag=True)
def doTheThing(path, screens, category, debug, type, res, tag, desc, descfile, desclink, bdinfo, nfo, keywords, anon, stream, region, dupe):
    path = os.path.abspath(path)
    if descfile != None:
        descfile = os.path.abspath(descfile)
    isdir = os.path.isdir(path)
    is_disk, videoloc, bdinfo, bd_summary = get_disk(path, bdinfo)
  

    if bdinfo != "":
        video, scene = is_scene(path)
        filelist = []
        try:
            filename = guessit(bdinfo['label'])['title']
            try:
                search_year = guessit(bdinfo['label'])['year']
            except:
                search_year = ""
        except:
            filename = guessit(bdinfo['title'])['title']
            try:
                search_year = guessit(bdinfo['title'])['year']
            except:
                search_year = ""
        Path(f"{base_dir}/{filename}").mkdir(parents=True, exist_ok=True)
    else:
        videopath, filelist = get_video(videoloc) 
        video, scene = is_scene(videopath)
        filename = guessit(ntpath.basename(video))["title"]
        Path(f"{base_dir}/{filename}").mkdir(parents=True, exist_ok=True)
        try:
            search_year = guessit(video)['year']
        except:
            search_year = ""
        
    guess = guessit(path)

    #Get year (if exists)
    # print(search_year)

    #Get type
    if type == None:
        type = get_type(video, scene, is_disk)

    #Guess Category ID
    cat_id = get_cat(category, video)

    #Guess Type ID
    type_id = get_type_id(type)

    gen_desc(filename, desc, descfile, desclink, bd_summary, path, nfo)

    if is_disk == "":
        #Export Mediainfo
        mi_dump, mi = exportInfo(videopath, filename, isdir)

        #Get resolution
        resolution_id, resolution_name, sd = get_resolution(filename, guess)
        
        #Generate Screenshots
        screenshots(videopath, filename, screens, debug)
    else:
        #Get resolution
        disk_screenshots(video, filename, screens, debug, bdinfo)
        resolution_id, resolution_name, sd = mi_resolution(bdinfo['video'][0]['res'], guess)
        mi = ""
        mi_dump = None

    #Get ids/name
    tmdb_id, tmdb_name, tmdb_year, cat_id, alt_name, imdb_id, anime, mal_id, keywords = get_tmdb(filename, cat_id, keywords, search_year)

    #Create description
    
    #Generate name
    name = get_name(path, video, tmdb_name, alt_name, guess, resolution_name, cat_id, type_id, tmdb_year, filename, tag, anime, region, bdinfo, mi, filelist)

    #Search for existing release
    name = search_existing(name, dupe)
    
    #Create torrent
    torrent_path, torrent = create_torrent(name, path, filename, video, isdir, is_disk)

    #Add to client
    
    if torrent_client == "rtorrent":
        rtorrent(path, torrent_path, torrent, is_disk)
    elif torrent_client == "qbit":
        # if is_disk != "":
        #     path = os.path.dirname(path)
        qbittorrent(path, torrent)
    elif torrent_client == "deluge":
        if is_disk != "":
            path = os.path.dirname(path)
        deluge(path, torrent_path, torrent)


    anon = is_anon(anon)
    stream_opt = stream_optimized(stream)
    

    data = {
        'name' : name,
        'description' : desc,
        'mediainfo' : mi_dump,
        'category_id' : cat_id,
        'type_id' : type_id,
        'resolution_id' : resolution_id,
        'tmdb' : tmdb_id,
        'imdb' : imdb_id,
        'tvdb' : 0,
        'mal' : mal_id,
        'igdb' : 0,
        'anonymous' : anon,
        'stream' : stream_opt,
        'sd' : sd,
        # 'internal' : 0,
        # 'featured' : 0,
        # 'free' : 0,
        # 'double_up' : 0,
        # 'sticky' : 0,
    }
    # pprint(data)
    # print(torrent_path)
    #Upload to BLU
    if click.confirm("Upload to BLU", default=False):
        if is_disk != "":
            mi_dump = None
        desc = open(f"{base_dir}/{filename}/DESCRIPTION.txt", 'r').read()
        files = {'torrent': open(torrent_path, 'rb')}
        data = {
            'name' : name,
            'description' : desc,
            'mediainfo' : mi_dump,
            'category_id' : cat_id,
            'type_id' : type_id,
            'resolution_id' : resolution_id,
            'tmdb' : tmdb_id,
            'imdb' : imdb_id,
            'tvdb' : 0,
            'mal' : mal_id,
            'igdb' : 0,
            'anonymous' : anon,
            'stream' : stream_opt,
            'sd' : sd,
            'keywords' : keywords,
            # 'internal' : 0,
            # 'featured' : 0,
            # 'free' : 0,
            # 'double_up' : 0,
            # 'sticky' : 0,
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:53.0) Gecko/20100101 Firefox/53.0'
        }
        url = f"https://blutopia.xyz/api/torrents/upload?api_token={blu_api}"
        response = requests.post(url=url, files=files, data=data, headers=headers)
        try:
            print(response.json())
        except:
            print("It may have uploaded, go check")
    
    if click.confirm("Clean up?", default=True):
        shutil.rmtree(f"{base_dir}/{filename}")
    


#Get first video
def get_video(videoloc):
    filelist = []
    if os.path.isdir(videoloc):
        os.chdir(videoloc)
        filelist = glob.glob('*.mkv') + glob.glob('*.mp4') + glob.glob('*.m2ts')
        video = sorted(filelist)[0]        
    else:
        video= videoloc
        filelist.append(videoloc)
    return video, filelist

#Check if scene
def is_scene(video):
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
#Get type
def get_type(video, scene, is_disk):
    filename = video.lower()
    if "remux" in filename:
        type = "REMUX"
    elif any(word in filename for word in [" web ", ".web.", "web-dl"]):
        type = "WEBDL"
    elif "webrip" in filename:
        type = "WEBRIP"
    elif scene == True:
        type = "ENCODE"
    elif is_disk != "":
        type = "DISK"
    else:
        print("Unable to determine type, please input or use -t next time")
        type = click.prompt("Please enter type", type=click.Choice(['DISK', 'REMUX', 'ENCODE', 'WEBDL', 'WEBRIP', 'HDTV'], case_sensitive=False), default='ENCODE')
    return type

#Export MediaINfo
def exportInfo(video, filename, isdir):
    cprint("Exporting MediaInfo...", "grey", "on_yellow")
    #MediaInfo to text
    if isdir == False:
        os.chdir(os.path.dirname(video))
    media_info = MediaInfo.parse(os.path.basename(video), output="STRING", full=False)
    export = open(f"{base_dir}/{filename}/MEDIAINFO-{filename}.txt", 'w', newline="", encoding='utf-8')
    export.write(media_info)
    export.close()
    mi_dump = media_info

    #MediaInfo to JSON
    media_info = MediaInfo.parse(video, output="JSON")
    export = open(f"{base_dir}/{filename}/MediaInfo.json", 'w', encoding='utf-8')
    export.write(media_info)
    export.close()
    with open(f'{base_dir}/{filename}/MediaInfo.json', 'r', encoding='utf-8') as f:
        mi = json.load(f)
    cprint("MediaInfo Exported.", "grey", "on_green")
    
    return mi_dump, mi

#Generate Screenshots
def screenshots(path, filename, screens, debug):
    cprint("Saving Screens...", "grey", "on_yellow")
    with open(f"{base_dir}/{filename}/MediaInfo.json") as f:
        mi = json.load(f)
        length = mi['media']['track'][1]['Duration']
        length = round(float(length))
        # for i in range(screens):
        i = 0
        while i != screens:
            image = f"{base_dir}/{filename}/{filename}-{i}.png"
            (
                ffmpeg
                .input(path, ss=random.randint(round(length/5) , round(length - length/5)))
                .output(image, vframes=1)
                .overwrite_output()
                .global_args('-loglevel', 'quiet')
                .run(quiet=True)
            )
            # print(os.path.getsize(image))
            print(f'{i+1}/{screens}')
            print(Path(image))
            if os.path.getsize(Path(image)) <= 31000000 and img_host == "imgbb":
                i += 1
            elif os.path.getsize(Path(image)) <= 20000000 and img_host == "pstorage.space":
                i += 1
            elif os.path.getsize(Path(image)) <= 10000:
                cprint("Image is incredibly small, retaking", 'grey', 'on_yellow')
                time.sleep(1)
            elif img_host == "ptpimg":
                i += 1
            elif img_host == "freeimage.host":
                i += 1
            else:
                cprint("Image too large for your image host, retaking", 'grey', 'on_red')
                time.sleep(1)
                
    cprint("Screens saved.", "grey", "on_green")
    #Upload Screenshots
    if debug == True:
        if click.confirm("Upload Screens?", default=True):
            upload_screens(filename, screens)
    else:
        upload_screens(filename, screens)

def disk_screenshots(path, filename, screens, debug, bdinfo):
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
    while i != screens:
        image = f"{base_dir}/{filename}/{filename}-{i}.png"
        (
            ffmpeg
            .input(f"bluray:{path}", ss=random.randint(round(length/5) , round(length - length/5)), skip_frame=is_vc1)
            .output(image, vframes=1)
            .overwrite_output()
            .global_args('-loglevel', 'quiet', "-playlist", f"{bdinfo['playlist']}", )
            .run(quiet=True)
        )
        # print(os.path.getsize(image))
        print(f'{i+1}/{screens}')
        if os.path.getsize(Path(image)) <= 31000000 and img_host == "imgbb":
            i += 1
        elif img_host != "imgbb":
            i += 1
        else:
            cprint("Image too large for imgbb, retaking", 'grey', 'on_red')
            time.sleep(1)
            
    cprint("Screens saved.", "grey", "on_green")
    #Upload Screenshots
    if debug == True:
        if click.confirm("Upload Screens?", default=True):
            upload_screens(filename, screens)
    else:
        upload_screens(filename, screens)


#Upload images & write description
def upload_screens(filename, screens):
    cprint('Uploading Screens', 'grey', 'on_yellow')
    os.chdir(f"{base_dir}/{filename}")
    i=1
    description = open(f"{base_dir}/{filename}/DESCRIPTION.txt", 'a', newline="")
    
        
    for image in glob.glob("*.png"):        
        data = {
            'key': img_api,
            'image': base64.b64encode(open(image, "rb").read())
        }
        if img_host == "imgbb":
            url = "https://api.imgbb.com/1/upload"
            response = requests.post(url, data = data).json()
            try:
                img_url = response['data']['url']
                web_url = response['data']['url_viewer']
            except:
                pprint(response)
        elif img_host == "freeimage.host":
            url = "https://freeimage.host/api/1/upload"
            response = requests.post(url, data = data).json()
            try:
                img_url = response['image']['url']
                web_url = response['image']['url_viewer']
            except:
                pprint(response)
        elif img_host == "pstorage.space":
            url = "https://pstorage.space/api/1/upload"
            data = {
                'key' : img_api,
                'source' : base64.b64encode(open(image, "rb").read()),
                'filename' : image
            }
            response = requests.post(url, data = data).json()
            try:
                img_url = response['url']
                web_url = response['url_viewer']
            except:
                pprint(response)
        elif img_host == "ptpimg":
            try:
                payload = {'format': 'json', 'api_key': img_api} # API key is obtained from inspecting element on the upload page. 
                # payload = {'api_key': img_api} # API key is obtained from inspecting element on the upload page. 
                files = [('file-upload[0]', open(image, 'rb'))] 
                headers = { 'referer': 'https://ptpimg.me/index.php'} 
                # ptpimg_response = requests.post("https://ptpimg.me/upload.php", headers=headers, data=payload, files=files) 
                ptpimg_response = requests.request("POST", "https://ptpimg.me/upload.php", headers=headers, data=payload, files=files) 
                # Then that returns either some error or a json response. 
                ptpimg_response = ptpimg_response.json()
                # pprint(ptpimg_response)
                ptpimg_code = ptpimg_response[0]['code'] 
                ptpimg_ext = ptpimg_response[0]['ext'] 
                img_url = f"https://ptpimg.me/{ptpimg_code}.{ptpimg_ext}" 
                web_url = f"https://ptpimg.me/{ptpimg_code}.{ptpimg_ext}" 
            except:
                # print(traceback.format_exc())
                cprint("PTPimg down?", 'grey', 'on_red')
                pass
        # elif img_host == "gifyu":
        #     url = "https://gifyu.com/api/1/upload/"
        #     data = {
        #         'key' : "9aa9c4dedd20aeb9a63e41676e061820",
        #         'image': base64.b64encode(open(image, "rb").read())
        #     }
        #     response = requests.post(url, data = data).json()
        #     pprint(response)
        else:
            cprint("Please choose a supported image host in your config", 'grey', 'on_red')
            exit()
        description.write(f"[url={web_url}][img=400]{img_url}[/img][/url]")
        if i % 3 == 0:
            description.write("\n")
        print(f"{i}/{screens}")
        i += 1
        time.sleep(1)
    description.write("\n")
    description.write("\n[center][url=https://blutopia.xyz/forums/topics/3087]Created by L4G's Upload Assistant[/url][/center]")
    description.close()

#Get Category ID
def get_cat(category, video):
    if category is None:
        cat_guess = guessit(video)['type']
        category = get_cat(cat_guess, video)
    elif category.lower() == "movie":
        category = 1
    elif category.lower() in ("tv", "episode"):
        category = 2
    else:
        category = click.prompt("Unable to guess category. Please select one:", type=click.Choice(['MOVIE', "TV"], case_sensitive=False))
        get_cat(category, video)
    return category

#Get Type ID
def get_type_id(type):
    type = type.upper()
    if type == "DISK":
        type_id = 1
    elif type == "REMUX":
        type_id = 3
    elif type == "ENCODE":
        type_id = 12
    elif type == "WEBDL":
        type_id = 4
    elif type == "WEBRIP":
        type_id = 5
    elif type == "HDTV":
        type_id = 6
    return type_id

#Resolution
def mi_resolution(resolution, guess):
    if resolution in ("2160p", "3840x2160p"):
        resolution_id = 1
        resolution_name = "2160p"
    elif resolution in ("1080p", "1920x1080p"):
        resolution_id = 2
        resolution_name = "1080p"
    elif resolution in ("1080i" ,  "1920x1080i"):
        resolution_id = 3
        resolution_name = "1080i"
    elif resolution in ("720p" ,  "1280x720p"):
        resolution_id = 5
        resolution_name = "720p"
    elif resolution in ("576p" ,  "720x576p"):
        resolution_id = 6
        resolution_name = "576p"
    elif resolution in ("576i" ,  "720x576i"):
        resolution_id = 7
        resolution_name = "576i"
    elif resolution in ("480p" ,  "720x480p"):
        resolution_id = 8
        resolution_name = "480p"
    elif resolution in ("480i" ,  "720x480p"):
        resolution_id = 9
        resolution_name = "480i"
    elif resolution in ("8640p" ,  "15360x8640p"):
        resolution_id = 10
        resolution_name = "8640p"
    elif resolution in ("4320p" ,  "7680x4320p"):
        resolution_id = 11
        resolution_name = "4320p"
    elif resolution == "OTHER":
        resolution_id = 10
    else:
        try: 
            resolution = guess['screen_size']
            resolution_id, resolution_name, sd = mi_resolution(resolution, guess)
        except:
            resolution = click.prompt('Unable to parse resolution. Please select one:', type=click.Choice(['2160p', '1080p', '1080i', '720p', '576p', '576i', '480p', '480i', '8640p', '4320p', 'OTHER'], case_sensitive=False))
            resolution_id, resolution_name, sd = mi_resolution(resolution, guess)
    #is sd
    if resolution_id in (10, 9, 8, 7):
        sd = 1
    else:
        sd = 0
    
    return resolution_id, resolution_name, sd
#Resolution
def get_resolution(filename, guess):
    with open(f'{base_dir}/{filename}/MediaInfo.json', 'r') as f:
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
        width = closest(width_list, int(width))
        height = closest(height_list, int(height))
        res = f"{width}x{height}{scan}"
        resolution_id = mi_resolution(res, guess)

    return resolution_id

def closest(lst, K):
    return lst[min(range(len(lst)), key = lambda i: abs(lst[i]-K))]
#Get TMDB Name/ID/year
def get_tmdb(filename, category, keywords, search_year):
    i = 0
    search = tmdb.Search()
    while True:
        try:
            if category == 1: #MOVIE
                search.movie(query=filename, year=search_year)
                tmdb_name = search.results[i]['title']
                release_date = search.results[i]['release_date']
                dt = datetime.strptime(release_date, '%Y-%m-%d')
                tmdb_year = dt.year
                tmdb_id = search.results[i]['id']
                try:
                    imdb_id = tmdb.Movies(tmdb_id).external_ids()['imdb_id']
                except:
                    imdb_id = 0
                if 'original_title' in search.results[i]:
                    alt_name = f" AKA {search.results[i]['original_title']}"
                tmdb_keywords = get_keywords(tmdb.Movies(tmdb_id))
                mal_id, alt_name, anime = get_anime(search, i, tmdb_name)

            elif category == 2: #TV
                search.tv(query=filename, year=search_year)
                tmdb_name = search.results[i]['name']
                air_date = search.results[i]['first_air_date']
                dt = datetime.strptime(air_date, '%Y-%m-%d')
                tmdb_year = dt.year
                tmdb_id = search.results[i]['id']
                try:
                    imdb_id = tmdb.TV(tmdb_id).external_ids()['imdb_id']
                except: 
                    imdb_id = 0
                if 'original_name' in search.results[i]:
                    alt_name = f" AKA {search.results[i]['original_name']}"
                tmdb_keywords = get_keywords(tmdb.TV(tmdb_id))
                mal_id, alt_name, anime = get_anime(search, i, tmdb_name)

            difference = SequenceMatcher(None, tmdb_name, alt_name[5:]).ratio()
            if difference >= 0.6:
                alt_name = ""
            
            if click.confirm(f"Is {tmdb_name}{alt_name} ({tmdb_year}) correct?", default=True):
                pass
            else:
                i += 1
                continue
        except:
            # print(traceback.format_exc())
            filename = click.prompt("Please enter Show/Film name")
            category = click.prompt("Please enter Category", type=click.Choice(['MOVIE', "TV"], case_sensitive=False))
            if category.upper() == "MOVIE":
                category = 1
            elif category.upper() == "TV":
                category = 2
            i=0
            continue
        break
    if keywords == None:
        keywords = tmdb_keywords
    else:
        keywords = keywords + ', ' + tmdb_keywords
    if imdb_id != None:
        imdb_id = imdb_id.replace('tt', '')
    elif imdb_id == None or imdb_id == "":
        imdb_id = 0
    print(f"IMDB: {imdb_id}")
    return tmdb_id, tmdb_name, tmdb_year, category, alt_name, imdb_id, anime, mal_id, keywords

def get_romaji(tmdb_name):
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
    return romaji, mal_id

#Naming
def get_name(path, video, tmdb_name, alt_name, guess, resolution_name, cat_id, type_id, tmdb_year, filename, tag, anime, region, bdinfo, mi, filelist):
    mi = mi
    title = tmdb_name
    alt_title = alt_name
    year = tmdb_year
    resolution = resolution_name
    audio = get_audio_v2(mi, anime, bdinfo)



    three_d = is_3d(mi, bdinfo)
    tag = get_tag(tag, video)
    source = get_source(type_id, video, 1)
    uhd = get_uhd(type_id, guess, resolution_name, path)
    hdr = get_hdr(mi, bdinfo)
    if type_id == 1: #Disk
        region = get_region(path, region)
        video_codec = get_video_codec(bdinfo)
    else:
        video_codec = mi['media']['track'][1]['Format']
        video_encode = get_video_encode(mi, type_id, bdinfo)
    edition = get_edition(guess, video, bdinfo)


    #YAY NAMING FUN
    if cat_id == 1: #MOVIE SPECIFIC
        if type_id == 1: #Disk
            name = f"{title} {alt_title} {year} {edition} {three_d} {resolution} {region} {uhd} {source} {hdr} {video_codec} {audio}{tag}"
            convention = "Name Year Resolution Region Source Video-codec Audio-Tag"
        elif type_id == 3 and source == "BluRay": #BluRay Remux
            name = f"{title} {alt_title} {year} {edition} {three_d} {resolution} {uhd} {source} REMUX {hdr} {video_codec} {audio}{tag}" 
            convention = "Name Year Resolution Source Video-codec Audio-Tag"
        elif type_id == 3 and source in ("PAL DVD", "NTSC DVD"): #DVD Remux
            name = f"{title} {alt_title} {year} {edition} {source} REMUX  {audio}{tag}" 
            convention = "Name Year Encoding_system Format Source Audio-Tag"
        elif type_id == 12: #Encode
            name = f"{title} {alt_title} {year} {edition} {resolution} {uhd} {source} {audio} {hdr} {video_encode}{tag}"  
            convention = "Name Year Resolution Source Audio Video-Tag"
        elif type_id == 4: #WEB-DL
            service = get_service(guess, video)
            name = f"{title} {alt_title} {year} {edition} {resolution} {uhd} {service} WEB-DL {audio} {hdr} {video_encode}{tag}"
            convention = "Name Year Resolution Source Rip-type Audio Video-codec-Tag"
        elif type_id == 5: #WEBRip
            service = get_service(guess, video)
            name = f"{title} {alt_title} {year} {edition} {resolution} {uhd} {service} WEBRip {audio} {hdr} {video_encode}{tag}"
            convention = "Name Year Resolution Source Rip-type Audio Video-codec-Tag"
        elif type_id == 6: #HDTV
            name = f"{title} {alt_title} {year} {edition} {resolution} HDTV {audio} {video_encode}{tag}"
            convention = "Name Year Resolution Source Audio Video-Tag"
    elif cat_id == 2: #TV SPECIFIC
        try:
            season = "S" + str(guessit(video)["season"]).zfill(2)
        except:
            season = "S" + str(click.prompt("Unable to parse season, please enter season number", type=click.INT, default= 1)).zfill(2)
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
        if type_id == 1: #Disk
            name = f"{title} {alt_title} {season}{episode} {edition} {three_d} {resolution} {region} {uhd} {source} {hdr} {video_codec} {audio}{tag}"
            convention = "Name Year Resolution Region Source Video-codec Audio-Tag"
        elif type_id == 3 and source == "BluRay": #BluRay Remux
            name = f"{title} {alt_title} {season}{episode} {edition} {three_d} {resolution} {uhd} {source} REMUX {hdr} {video_codec} {audio}{tag}" #SOURCE
            convention = "Name Year Resolution Source Video-codec Audio-Tag"
        elif type_id == 3 and source in ("PAL DVD", "NTSC DVD"): #DVD Remux
            name = f"{title} {alt_title} {season}{episode} {edition} {source} REMUX {audio}{tag}" #SOURCE
            convention = "Name Year Encoding_system Format Source Audio-Tag"
        elif type_id == 12: #Encode
            name = f"{title} {alt_title} {season}{episode} {edition} {resolution} {uhd} {source} {audio} {hdr} {video_encode}{tag}" #SOURCE
            convention = "Name Year Resolution Source Audio Video-Tag"
        elif type_id == 4: #WEB-DL
            service = get_service(guess, video)
            name = f"{title} {alt_title} {season}{episode} {edition} {resolution} {uhd} {service} WEB-DL {audio} {hdr} {video_encode}{tag}"
            convention = "Name Year Resolution Source Rip-type Audio Video-Tag"
        elif type_id == 5: #WEBRip
            service = get_service(guess, video)
            name = f"{title} {alt_title} {season}{episode} {edition} {resolution} {uhd} {service} WEBRip {audio} {hdr} {video_encode}{tag}"
            convention = "Name Year Resolution Source Rip-type Audio Video-Tag"
        elif type_id == 6: #HDTV
            name = f"{title} {alt_title} {season}{episode} {edition} {resolution} HDTV {audio} {video_encode}{tag}"
            convention = "Name Year Resolution Source Audio Video-Tag"


    name = ' '.join(name.split())

    print(f"Convention: {convention}")
    while True:
        if click.confirm("Does this look correct? " + name):
            return name
        else:
            name = click.prompt("Enter correct title")


def get_video_encode(mi, type_id, bdinfo):
    video_encode = ""
    codec = ""
    try:
        format = mi['media']['track'][1]['Format']
        format_profile = mi['media']['track'][1]['Format_Profile']
    except:
        format = bdinfo['video'][0]['codec']
        format_profile = bdinfo['video'][0]['profile']
    if type_id in (12, 5): #ENCODE or WEBRIP
        if format == 'AVC':
            codec = 'x264'
        elif format == 'HEVC':
            codec = 'x265'
    elif type_id == 4: #WEB-DL
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

def get_audio(mi, anime):
    format = mi['media']['track'][2]['Format']
    try:
        additional = mi['media']['track'][2]['Format_AdditionalFeatures']
        format = f"{format} {additional}"
    except:
        pass
    channels = mi['media']['track'][2]['Channels']
    atmos = False
    extra = ""
    dual = ""
    #set audio codec
    if format == "DTS":
        codec = "DTS"
    elif format == "DTS XLL":
        codec = "DTS-HD MA"
    elif format == "DTS XLL X":
        codec = "DTS:X"
    elif format in ["AAC", "AAC LC"]:
        codec = "AAC"
    elif format == "AC-3":
        codec = "DD"
    elif format == "E-AC-3":
        codec = "DD+"
    elif format == "E-AC-3 JOC":
        codec = "DD+"
        atmos = True
    elif format == "MLP FBA":
        codec = "TrueHD"
    elif format == "MLP FBA 16-ch":
        codec = "TrueHD"
        atmos = True
    elif format == "FLAC":
        codec = "FLAC"
    elif format == "Opus":
        codec = "OPUS"
    elif format == 'Vorbis':
        codec = "VORBIS"
    elif format == "PCM":
        codec = "LPCM"
    else:
        cprint(f"CODEC: {format} NOT FOUND, Please report to L4G", 'grey', 'on_red')
        codec = click.prompt("Please input audio codec")

    #set audio channels
    if channels == "8":
        chan = "7.1"
    elif channels == "7":
        chan = "6.1"
    elif channels == "6":
        chan = "5.1"
    elif channels == "2":
        chan = "2.0"
    elif channels == "1":
        chan = "1.0"

    #Generate audio name
    if atmos == True:
        extra = " Atmos"
    if anime == True:
        eng, jap = False, False
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
    audio = f"{dual} {codec} {chan}{extra}"
    return audio


def get_tag(tag, video):
    if tag == None:
        try:
            tag = guessit(video)['release_group']
            tag = f"-{tag}"
        except:
            tag = click.prompt("Tag not found, please enter tag or leave blank for no tag", default="")
            tag = f"-{tag}"
    else:
        tag = f"-{tag}"
    if tag == "-":
        tag = ""
    return tag


def get_service(guess, video):
    try:
        service = guess['streaming_service']
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
            service = click.prompt("Enter WEB Source (AMZN, NF, DSNP, etc), leave blank for unknown", default="")
    return service


def get_uhd(type_id, guess, resolution_name, path):
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
    elif type_id in (1, 3, 12, 5):
        uhd = ""
        
    if type_id in (1, 3, 12) and resolution_name == "2160p":
        uhd = "UHD"

    return uhd

def get_hdr(mi, bdinfo):
    hdr = ""
    if bdinfo != "": #Disks
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

def get_source(type_id, video, i):
    try:
        if i == 1:
            try:
                source = guessit(video)['source']
            except:
                source = video
        else:
            source = video

        if source in ("Blu-ray", "Ultra HD Blu-ray", "BluRay", "BR"):
            if type_id == 1:
                source = "Blu-ray"
            elif type_id in (3, 12):
                source = "BluRay"
        elif source in ("DVD", "dvd"):
            try:
                other = guessit(video)['other']
                if "PAL" in other:
                    system = "PAL"
                elif "NTSC" in other:
                    system = "NTSC"
            except:
                system = click.prompt("Encoding system not found", type=click.Choice(["PAL", "NTSC"], case_sensitive=False))
            source = system + " DVD"
    except Exception:
        print(traceback.format_exc())
        prompt = click.prompt("Unable to find source, please choose one", type=click.Choice(["BR", "DVD"], case_sensitive=False), default="BR")

        source = get_source(type_id, prompt, 2)

    return source

def get_edition(guess, video, bdinfo):
    if bdinfo != "":
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
    # if edition == "None" or edition == None:
    #     edition = ""
    return edition

def create_torrent(name, path, filename, video, isdir, is_disk):
    if isdir == True:
        os.chdir(path)
        globs = glob.glob("*.mkv") + glob.glob("*.mp4")
        if len(globs) == 1:
            path = video
    name = clean_filename(name)
    if is_disk != "":
        include, exclude = "", ""
    else:
        exclude = ["*.*"] 
        include = ["*.mkv", "*.mp4"]
    torrent = Torrent(path,
        trackers = [announce],
        source = "BLU",
        private = True,
        exclude_globs = [exclude],
        include_globs = [include],
        created_by = "L4G's Upload Assistant")
    cprint("Creating .torrent", 'grey', 'on_yellow')
    torrent.piece_size_max = 16777216
    torrent.generate(callback=torf_cb, interval=5)
    torrent_path = f"{base_dir}/{filename}/{name}.torrent"
    torrent.write(f"{base_dir}/{filename}/{name}.torrent", overwrite=True)
    torrent.verify_filesize(path)
    cprint(".torrent created", 'grey', 'on_green')
    return torrent_path, torrent

def gen_desc(filename, desc, descfile, desclink, bd_summary, path, nfo):
    description = open(f"{base_dir}/{filename}/DESCRIPTION.txt", 'w', newline="")
    description.seek(0)
    if bd_summary != "":
        description.write("[code]")
        description.write(bd_summary)
        description.write("[/code]")
        description.write("\n")
    if nfo != False:
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
        elif desc != None:
            description.write(desc)
        description.write("\n")
    

def clean_filename(name):
    invalid = '<>:"/\|?*'
    for char in invalid:
        name = name.replace(char, '-')
    return name

def is_anon(anon):
    if anon == True:
        anon = 1
    else:
        anon = 0
    return anon

def stream_optimized(stream_opt):
    if stream_opt == True:
        stream = 1
    else:
        stream = 0
    return stream

def rtorrent(path, torrent_path, torrent, is_disk):
    rtorrent = xmlrpc.client.Server(rtorrent_url)
    metainfo = bencode.bread(torrent_path)
    try:
        meta = add_fast_resume(metainfo, path, torrent)
    except EnvironmentError as exc:
        cprint("Error making fast-resume data (%s)" % (exc,), 'grey', 'on_red')
        raise
    
        
    new_meta = bencode.bencode(meta)
    if new_meta != metainfo:
        fr_file = torrent_path.replace('.torrent', '-resume.torrent')
        print("Creating fast resume")
        bencode.bwrite(meta, fr_file)


    isdir = os.path.isdir(path)
    if is_disk != "":
        path = os.path.dirname(path)
    #Remote path mount
    if local_path in path:
        path = path.replace(local_path, remote_path)
        path = path.replace(os.sep, '/')
    if isdir == False:
        path = os.path.dirname(path)
    
    print(path)
    cprint("Adding and rechecking torrent", 'grey', 'on_yellow')
    rtorrent.load.start_verbose('', fr_file, f"d.directory_base.set={path}")


def qbittorrent(path, torrent):
    # isdir = os.path.isdir(path)
    # infohash = torrent.infohash
    #Remote path mount
    if local_path in path:
        path = path.replace(local_path, remote_path)
        path = path.replace(os.sep, '/')
    # if isdir == False:
    # # else:
    path = os.path.dirname(path)
    # cprint(path, 'yellow')

    qbt_client = qbittorrentapi.Client(host=config['DEFAULT']['qbit_url'], port=config['DEFAULT']['qbit_port'], username=config['DEFAULT']['qbit_user'], password=config['DEFAULT']['qbit_pass'])
    cprint("Adding and rechecking torrent", 'grey', 'on_yellow')
    try:
        qbt_client.auth_log_in()
    except qbittorrentapi.LoginFailed:
        cprint("INCORRECT QBIT LOGIN CREDENTIALS", 'grey', 'on_red')
        exit()
    qbt_client.torrents_add(torrent_files=torrent.dump(), save_path=path, use_auto_torrent_management=False, is_skip_checking=True)
    # qbt_client.torrents_recheck(torrent_hashes=infohash)
    # cprint("Rechecking File", 'grey', 'on_yellow')
    # while qbt_client.torrents_info(torrent_hashes=infohash)[0]['completed'] == 0:
    #     time.sleep(1)
    # qbt_client.torrents_resume(torrent_hashes=infohash)

def deluge(path, torrent_path, torrent):
    client = DelugeRPCClient(config['DEFAULT']['deluge_url'], int(config['DEFAULT']['deluge_port']), config['DEFAULT']['deluge_user'], config['DEFAULT']['deluge_pass'])
    # client = LocalDelugeRPCClient()
    client.connect()
    if client.connected == True:
        print("Deluge connected")    
        isdir = os.path.isdir(path)
        #Remote path mount
        if local_path in path:
            path = path.replace(local_path, remote_path)
            path = path.replace(os.sep, '/')
        # if isdir == False:
        else:
            path = os.path.dirname(path)

        client.call('core.add_torrent_file', torrent_path, base64.b64encode(torrent.dump()), {'download_location' : path, 'seed_mode' : True})

    else:
        cprint("Unable to connect to deluge", 'grey', 'on_red')


def search_existing(name, dupe):
    cprint("Searching for existing torrents on site...", 'grey', 'on_yellow')
    url = f"https://blutopia.xyz/api/torrents/filter?name={urllib.parse.quote(name)}&api_token={blu_api}"
    response = requests.get(url=url)
    response = response.json()
    appendages = [
        "(¬‿¬)", "(⌐■_■)", "(> _ <)", "REPLACEMENT", "(^-^)/", "\(^O^)/", "☜(ﾟヮﾟ☜)", "( .-. )",
        "( .o.)",  "( `·´ )",  "( ° ͜ ʖ °)",  "( ͡° ͜ʖ ͡°)",  "( ⚆ _ ⚆ )",  "( ︶︿︶)",  "( ﾟヮﾟ)",  
        "(\\/)(°,,,°)(\\/)",  "(¬_¬)",  "(¬º-°)¬",  "(¬‿¬)",  "(°ロ°)☝",  "(´・ω・)っ",  "(ó ì_í)",
        "(ʘᗩʘ')",  "(ʘ‿ʘ)",  "(̿▀̿ ̿Ĺ̯̿̿▀̿ ̿)̄",  "(͡° ͜ʖ ͡°)",  "(ಠ_ಠ)",  "(ಠ‿ಠ)",  "(ಠ⌣ಠ)",  "(ಥ_ಥ)",  "(ಥ﹏ಥ)",  "(ง ͠° ͟ل͜ ͡°)ง",  "(ง ͡ʘ ͜ʖ ͡ʘ)ง",
        "(ง •̀_•́)ง",  "(ง'̀-'́)ง",  "(ง°ل͜°)ง",  "(ง⌐□ل͜□)ง",
        "(ღ˘⌣˘ღ)",  "(ᵔᴥᵔ)",  "(•ω•)",  "(•◡•)/",  "(⊙ω⊙)",
        "(⌐■_■)",  "(─‿‿─)",  "(╯°□°）╯",  "(◕‿◕)",  "(☞ﾟ∀ﾟ)☞",  "(❍ᴥ❍ʋ)",  "(っ◕‿◕)っ",  "(づ｡◕‿‿◕｡)づ",  "(ノಠ益ಠ)ノ",  "(ノ・∀・)ノ",  "(；一_一)",  "(｀◔ ω ◔´)",  "(｡◕‿‿◕｡)",
        "(ﾉ◕ヮ◕)ﾉ",  "=^.^=",  "t(-.-t)",  "| (• ◡•)|",  "~(˘▾˘~)",  "¬_¬",  "¯(°_o)/¯",  "¯\_(ツ)_/¯",
        "°Д°",  "ɳ༼ຈل͜ຈ༽ɲ",  "ʅʕ•ᴥ•ʔʃ",  "ʕ´•ᴥ•`ʔ",  "ʕ•ᴥ•ʔ",  "ʕ◉.◉ʔ",  "ʕㅇ호ㅇʔ",  "ʕ；•`ᴥ•´ʔ",  "ʘ‿ʘ",  "͡° ͜ʖ ͡°",  "ζ༼Ɵ͆ل͜Ɵ͆༽ᶘ",  "Ѱζ༼ᴼل͜ᴼ༽ᶘѰ",  "ب_ب",  "٩◔̯◔۶",  "ಠ_ಠ",  "ಠoಠ",  "ಠ~ಠ",  "ಠ‿ಠ",
        "ಠ⌣ಠ",  "ಠ╭╮ಠ",  "ರ_ರ",  "ง ͠° ل͜ °)ง",  "๏̯͡๏﴿",  "༼ ºººººل͟ººººº ༽",  "༼ ºل͟º ༽",  "༼ ºل͟º༼",  "༼ ºل͟º༽",  "༼ ͡■ل͜ ͡■༽",  "༼ つ ◕_◕ ༽つ",  "༼ʘ̚ل͜ʘ̚༽",  "ლ(´ڡ`ლ)",  "ლ(́◉◞౪◟◉‵ლ)",  "ლ(ಠ益ಠლ)",
        "ᔑ•ﺪ͟͠•ᔐ",  "ᕕ( ᐛ )ᕗ",  "ᕙ(⇀‸↼‶)ᕗ",  "ᕙ༼ຈل͜ຈ༽ᕗ",  "ᶘ ᵒᴥᵒᶅ",  "‎‎(ﾉಥ益ಥ）ﾉ",  "≧☉_☉≦",  "⊙▃⊙",  "⊙﹏⊙",  "┌( ಠ_ಠ)┘",  "╚(ಠ_ಠ)=┐",
        "◉_◉",  "◔ ⌣ ◔",  "◔̯◔",  "◕‿↼",  "◕‿◕",  "☉_☉",  "☜(⌒▽⌒)☞",  "☼.☼",  "♥‿♥",  "⚆ _ ⚆",
        "✌(-‿-)✌",  "〆(・∀・＠)",  "ノ( º _ ºノ)",  "ノ( ゜-゜ノ)",  "ヽ( ͝° ͜ʖ͡°)ﾉ",  "ヽ(`Д´)ﾉ",  "ヽ༼° ͟ل͜ ͡°༽ﾉ",  "ヽ༼ʘ̚ل͜ʘ̚༽ﾉ",  "ヽ༼ຈل͜ຈ༽ง",  "ヽ༼ຈل͜ຈ༽ﾉ",
        "ヽ༼Ὸل͜ຈ༽ﾉ",  "ヾ(⌐■_■)ノ",  "꒰･◡･๑꒱",  "﴾͡๏̯͡๏﴿",  "｡◕‿◕｡",  "ʕノ◔ϖ◔ʔノ",  "꒰•̥̥̥̥̥̥̥ ﹏ •̥̥̥̥̥̥̥̥๑꒱",  "ಠ_ರೃ",  "(ू˃̣̣̣̣̣̣︿˂̣̣̣̣̣̣ ू)",  "(ꈨຶꎁꈨຶ)۶”",  "(ꐦ°᷄д°᷅)",
        "(۶ૈ ۜ ᵒ̌▱๋ᵒ̌ )۶ૈ=͟͟͞͞ ⌨",  "₍˄·͈༝·͈˄₎◞ ̑̑ෆ⃛",  "(*ﾟ⚙͠ ∀ ⚙͠)ﾉ❣",  "٩꒰･ัε･ั ꒱۶",  "ヘ（。□°）ヘ",  "˓˓(ृ　 ु ॑꒳’)ु(ृ’꒳ ॑ ृ　)ु˒˒˒",  "꒰✘Д✘◍꒱",  "૮( ᵒ̌ૢཪᵒ̌ૢ )ა",  "“ψ(｀∇´)ψ",  "ಠﭛಠ",  "(๑>ᴗ<๑)",
        "(۶ꈨຶꎁꈨຶ )۶ʸᵉᵃʰᵎ",  "٩(•̤̀ᵕ•̤́๑)ᵒᵏᵎᵎᵎᵎ",  "(oT-T)尸",  "(✌ﾟ∀ﾟ)☞",  "ಥ‿ಥ",
        "(⑅ ॣ•͈ᴗ•͈ ॣ)",  "ヾ(´￢｀)ﾉ",  "(•̀o•́)ง",  "(๑•॒̀ ູ॒•́๑)",  "⚈้̤͡ ˌ̫̮ ⚈้̤͡",  "=͟͟͞͞ =͟͟͞͞ ﾍ( ´Д`)ﾉ",  "(((╹д╹;)))",  "•̀.̫•́✧",  "(ᵒ̤̑ ₀̑ ᵒ̤̑)",  "\_(ʘ_ʘ)_/",
        "(✿ ◕‿◕) ᓄ✂╰U╯", "ლ(~•̀︿•́~)つ︻̷┻̿═━一", "ᕕ( ՞ ᗜ ՞ )ᕗ", "(◕⌂◕⊃⊃)", "໒( , ⊙ – ⊙ , )७", "☆*:. o(≧▽≦)o .:*☆", "ʕ ᓀ ᴥ ᓂ ʔ", "(V●ᴥ●V)"
        "ᕙ[  ͒ ﹏ ͒  ]ᕗ" , "(⁰ ◕〜◕ ⁰)" , "(∩╹□╹∩)" , "╰[ ⁰﹏⁰ ]╯" , "s( ^ ‿ ^)-b" , "s( ^ ‸ ^)-p" , "@( ◕ x ◕ )@",
        "@( ◕ x ◕ )@" , "ᕙ( ~ . ~ )ᕗ" , "┌( •́ ਊ •̀ )┐" , "〳 •́ ﹏ •̀ 〵" , "c( ⁰ 〰 ⁰ )੭" , "ლ ( ◕  ᗜ  ◕ ) ლ" , "(つ•̀ᴥ•́)つ*:･ﾟ✧",
        "ʕ⊙ᴥ⊙ʔ" , "(⊙ᗜ⊙)" , "╰(◕ᗜ◕)╯" , "░ ∗ ◕ ں ◕ ∗ ░" , "(^ ◕ᴥ◕ ^)" , "(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧" , "ʕ༼◕  ౪  ◕✿༽ʔ", "(⊹つ•۝•⊹)つ",  
        ]        
    if dupe == True:
        cprint('MANUAL RENAME TRIGGERED', 'grey', 'on_yellow')
        if click.confirm("Would you like to change the name and upload anyways?"):
            name = f"{name} {random.choice(appendages)}"
        else:
            exit()
    for each in response['data']:
        result = [each][0]['attributes']['name']
        print(result)
        difference = SequenceMatcher(None, name, result).ratio()
        if difference >= 0.1:
            if click.confirm(f"{result} already exists, is this a dupe?", default=False):
                if click.confirm("Would you like to change the name and upload anyways?"):
                    name = f"{name} {random.choice(appendages)}"
                else:
                    exit()
    cprint("No dupes found", 'grey', 'on_green')   
    return name
                
def get_disk(base_path, bdinfo_paste):
    is_disk = ""
    videoloc = base_path
    bdinfo = ""
    bd_summary = ""
    if bdinfo_paste == True:
        cprint("Please paste your BDInfo summary (Quick Summary ONLY):\n"
        "To end recording Press Ctrl+d on Linux/Mac on Crtl+z on Windows", 'grey', 'on_yellow')
        lines = []
        try:
            while True:
                lines.append(input())
        except EOFError:
            pass
        cprint("Parsing BDInfo Summary", 'grey', 'on_yellow')
        bdinfo_paste = "\n".join(lines)
        bd_summary = bdinfo_paste
        bdinfo = parse_bdinfo(bdinfo_paste)
        is_disk = "BDMV"
    else:
        for path, directories, files in os.walk(base_path):
            if "STREAM" in directories:
                is_disk = "BDMV"
                videoloc = os.path.join(path, "STREAM", get_largest(os.path.join(path, "STREAM"))) 
                bd_summary, bdinfo = get_bdinfo(base_path)
            elif "VIDEO_TS" in directories:
                is_disk = "DVD"
                videoloc = directories
                bd_summary, bdinfo = get_bdinfo(base_path) #Probably doesnt work
            
    return is_disk, videoloc, bdinfo, bd_summary

def get_largest(videoloc):
    os.chdir(videoloc)
    fileSizeTupleList = []
    largestSize = 0

    for i in os.listdir(os.curdir):
        if os.path.isfile(i):
            fileSizeTupleList.append((i, os.path.getsize(i)))

    for fileName, fileSize in fileSizeTupleList:
        if fileSize > largestSize:
            largestSize = fileSize
            largestFile = fileName
    
    return largestFile

def get_region(path, region):
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
        if region == "":
            region = click.prompt("Enter region, leave blank for unknown", default="")
        if region == None:
            region = ""
    return region

def get_bdinfo(path):
    cprint("Getting BDInfo", 'grey', 'on_yellow')
    save_dir = f"{base_dir}/tmp"
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)
    else:
        shutil.rmtree(f"{base_dir}/tmp")
        os.mkdir(save_dir)
    if sys.platform.startswith('linux'):
        try:
            Popen(['mono', f"{base_dir}/bin/BDInfo/BDInfo.exe", "-w", path, save_dir])
        except:
            cprint('mono not found, please install mono', 'grey', 'on_red')
            
    elif sys.platform.startswith('win32'):
        Popen([f"{base_dir}/bin/BDInfo/BDInfo.exe", "-w", path, save_dir])
        time.sleep(0.1)
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
            time.sleep(5)
            continue
        break
    with open(f"{save_dir}/BDINFO.txt", 'w') as f:
        f.write(bd_summary)
        f.close()
    bdinfo = parse_bdinfo(bd_summary)
    shutil.rmtree(f"{base_dir}/tmp")
    return bd_summary, bdinfo
        
def add_fast_resume(meta, datapath, torrent):
    """ Add fast resume data to a metafile dict.
    """
    # Get list of files
    files = meta["info"].get("files", None)
    single = files is None
    if single:
        if os.path.isdir(datapath):
            datapath = os.path.join(datapath, meta["info"]["name"])
        files = [Bunch(
            path=[os.path.abspath(datapath)],
            length=meta["info"]["length"],
        )]

    # Prepare resume data
    resume = meta.setdefault("libtorrent_resume", {})
    resume["bitfield"] = len(meta["info"]["pieces"]) // 20
    resume["files"] = []
    piece_length = meta["info"]["piece length"]
    offset = 0

    for fileinfo in files:
        # Get the path into the filesystem
        filepath = os.sep.join(fileinfo["path"])
        if not single:
            filepath = os.path.join(datapath, filepath.strip(os.sep))

        # Check file size
        if os.path.getsize(filepath) != fileinfo["length"]:
            raise OSError(errno.EINVAL, "File size mismatch for %r [is %d, expected %d]" % (
                filepath, os.path.getsize(filepath), fileinfo["length"],
            ))

        # Add resume data for this file
        resume["files"].append(dict(
            priority=1,
            mtime=int(os.path.getmtime(filepath)),
            completed=(offset+fileinfo["length"]+piece_length-1) // piece_length
                     - offset // piece_length,
        ))
        offset += fileinfo["length"]

    return meta

def torf_cb(torrent, filepath, pieces_done, pieces_total):
    print(f'{pieces_done/pieces_total*100:3.0f} % done')

def get_audio_v2(mi, anime, bdinfo):
    #Get formats
    if bdinfo != "": #Disks
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
        cprint(f"CODEC: {format} NOT FOUND, Please report to L4G", 'grey', 'on_red')
        codec = click.prompt("Please input audio codec")


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


def parse_bdinfo(bdinfo_input):
    bdinfo = dict()
    bdinfo['video'] = list()
    bdinfo['audio'] = list()
    lines = bdinfo_input.splitlines()
    for l in lines:
        line = l.strip().lower()
        if line.startswith("*"):
            line = l.replace("*", "").strip().lower()
            print(line)
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

def get_video_codec(bdinfo):
    codecs = {
        "MPEG-4 AVC Video" : "AVC",
        "MPEG-H HEVC Video" : "HEVC",
    }
    codec = codecs.get(bdinfo['video'][0]['codec'], "")
    return codec

def get_keywords(tmdb_info):
    if tmdb_info is not None:
        tmdb_keywords = tmdb_info.keywords()
        if tmdb_keywords.get('keywords') is not None:
            keywords=[f"{keyword['name'].replace(',',' ')}" for keyword in tmdb_keywords.get('keywords')]
        elif tmdb_keywords.get('results') is not None:
            keywords=[f"{keyword['name'].replace(',',' ')}" for keyword in tmdb_keywords.get('results')]
        return(', '.join(keywords))
    else:
        return ''

def is_3d(mi, bdinfo):
    if bdinfo != "":
        if bdinfo['video'][0]['3d'] != "":
            return "3D"
        else:
            return ""
    else:
        return ""

def get_anime(search, i,tmdb_name):
    alt_name = ""
    anime = False
    if search.results[i]['original_language'] == 'ja' and 16 in search.results[i]['genre_ids']:
        romaji, mal_id = get_romaji(tmdb_name)
        anime = True
        # mal = AnimeSearch(romaji)
        # mal_id = mal.results[0].mal_id
        alt_name = f" AKA {romaji}"
    else:
        mal_id = 0
    return mal_id, alt_name, anime


doTheThing()

