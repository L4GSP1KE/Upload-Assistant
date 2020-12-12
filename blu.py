import os
import sys
import configparser
from pathlib import Path
from datetime import datetime
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
import pprint
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

base_dir = os.path.abspath(os.path.dirname(__file__))
os.chdir(base_dir)

config = configparser.ConfigParser()
config.read('config.ini')
tmdb.API_KEY = config['DEFAULT']['tmdb_api']
announce = config['DEFAULT']['announce_url']
blu_api = config['DEFAULT']['blu_api']
user_id = config['DEFAULT']['blu_pid']
rtorrent_url = config['DEFAULT']['rtorrent_url']
remote_path = config['DEFAULT']['remote_path']
local_path = config['DEFAULT']['local_path']
torrent_client = config['DEFAULT']['torrent_client']


# base_dir = os.getcwd()
search = tmdb.Search()



#TODO

#FAST RESUME
#FANRES/TRAILER SUPPORT <- probably not
#DISK SUPPORT <- maybe???
#tmdb/imdb id input argument
#HDR vs DV vs HLG vs whatever else <- hlg done, hdr done, need DV
#Dual Audio anime, is channel based off default audio track or original lang eg. 5.1 eng but 2.0 jap?
#Audio formats I may have missed
#Rework audio to use commercial name
#Description feature is pretty meh
#Remove upload screens prompt
#Replace cprint with something more windows friendly
#Make less sloppy



#Do the thingy
@click.command()
@click.argument('path',type=click.Path('r'))
@click.option('--screens', '-s', help="Number of screenshots", default=0)
@click.option('--category', '-c', type=click.Choice(['MOVIE', 'TV'], case_sensitive=False), help="Category")
@click.option('--type', '-t', type=click.Choice(['DISK', 'REMUX', 'ENCODE', 'WEBDL', 'WEBRIP', 'HDTV'], case_sensitive=False), help="Type")
@click.option('--res', '-r',type=click.Choice(['2160p', '1080p', '1080i', '720p', '576p', '576i', '480p', '480i', '8640p', '4320p', 'OTHER'], case_sensitive=False), help="Resolution")
@click.option('--tag', '-g', help="Group tag")
@click.option('--desc', '-d', help="Custom description (String)")
@click.option('--descfile', '-df', help="Custom description (Path to File)", type=click.Path('rb'))
@click.option('--desclink', '-hb', help="Custom description (Link to hastebin)")
@click.option('--nfo', '-nfo', help="Use nfo from directory as description", is_flag=True)
@click.option('--anon', '-a', help="Anonymous upload", is_flag=True)
@click.option('--stream', '-st', help="Stream Optimized Upload", is_flag=True)
def doTheThing(path, screens, category, type, res, tag, desc, descfile, desclink, nfo, anon, stream):
    path = os.path.abspath(path)
    if descfile != None:
        descfile = os.path.abspath(descfile)
    isdir = os.path.isdir(path)
    is_disk, videoloc, bdinfo = get_disk(path)
    videopath = get_video(videoloc)

    #Is scene
    video, scene = is_scene(videopath)
    #Guess Name
    if is_disk != "":
        filename = guessit(path)['title']
    else:
        filename = guessit(ntpath.basename(video))["title"]
    guess = guessit(path)

    #Get type
    type = get_type(video, scene, is_disk)

    #Guess Category ID
    cat_id = get_cat(category, video)

    #Guess Type ID
    type_id = get_type_id(type)

    #Export Mediainfo
    mi_dump = exportInfo(videopath, filename, isdir)

    #Get resolution
    resolution_id, resolution_name, sd = get_resolution(filename, guess)

    #Get ids/name
    tmdb_id, tmdb_name, tmdb_year, cat_id, alt_name, imdb_id, anime, mal_id = get_tmdb(filename, cat_id)

    #Create description
    gen_desc(filename, desc, descfile, desclink, bdinfo, path, nfo)

    #Generate Screenshots
    screenshots(videopath, filename, screens)

    #Upload Screenshots
    if click.confirm("Upload Screens?", default=True):
        upload_screens(filename, screens)
    #Generate name
    name = get_name(path, video, tmdb_name, alt_name, guess, resolution_name, cat_id, type_id, tmdb_year, filename, tag, anime)

    #Search for existing release
    search_existing(name)
    
    #Create torrent
    torrent_path, torrent = create_torrent(name, path, filename, video, isdir, is_disk)

    #Add to client
    if torrent_client == "rtorrent":
        rtorrent(path, torrent_path, torrent)
    elif torrent_client == "qbit":
        qbittorrent(path, torrent)


    anon = is_anon(anon)
    stream_opt = stream_optimized(stream)
    

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
            'user_id' : user_id,
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
        url = f"https://blutopia.xyz/api/torrents/upload?api_token={blu_api}"
        response = requests.post(url=url, files=files, data=data)
        print(response.text)
    
    if click.confirm("Clean up?", default=True):
        shutil.rmtree(f"{base_dir}/{filename}")
    


#Get first video
def get_video(videoloc):
    if os.path.isdir(videoloc):
        os.chdir(videoloc)
        video = glob.glob('*.mkv') + glob.glob('*.mp4') + glob.glob('*.m2ts')
        video = video[0]        
    else:
        video = videoloc
    return video

#Check if scene
def is_scene(video):
    scene = False
    base = os.path.basename(video)
    base = os.path.splitext(base)[0]
    base = urllib.parse.quote(base)
    url = f"https://www.srrdb.com/api/search/r:{base}"
    response = requests.get(url)
    response = response.json()
    if response['resultsCount'] != "0":
        video = f"{response['results'][0]['release']}.mkv"
        scene = True
    return video, scene
#Get type
def get_type(video, scene, is_disk):
    filename = video.lower()
    if "remux" in filename:
        type = "REMUX"
    elif any(word in filename for word in [" web ", ".web.", "web-dl"]):
        type = "WEBDL"
    elif "webrip" in filename:
        type = "WEBRip"
    elif scene == True:
        type = "ENCODE"
    elif is_disk != "":
        type = "DISK"
    else:
        print("Unable to determine type, please input or use -t next time")
        type = click.prompt("Please enter type", type=click.Choice(['DISK', 'REMUX', 'ENCODE', 'WEBDL', 'WEBRIP', 'HDTV'], case_sensitive=False))
    return type

#Export MediaINfo
def exportInfo(video, filename, isdir):
    cprint("Exporting MediaInfo...", "grey", "on_yellow")
    #MediaInfo to text
    if isdir == False:
        os.chdir(os.path.dirname(video))
    media_info = MediaInfo.parse(os.path.basename(video), output="STRING", full=False)
    Path(f"{base_dir}/{filename}").mkdir(parents=True, exist_ok=True)
    export = open(f"{base_dir}/{filename}/MEDIAINFO-{filename}.txt", 'w', newline="")
    export.write(media_info)
    export.close()
    mi_dump = media_info

    #MediaInfo to JSON
    media_info = MediaInfo.parse(video, output="JSON")
    export = open(f"{base_dir}/{filename}/MediaInfo.json", 'w')
    export.write(media_info)
    export.close()
    cprint("MediaInfo Exported.", "grey", "on_green")
    
    return mi_dump

#Generate Screenshots
def screenshots(path, filename, screens):
    cprint("Saving Screens...", "grey", "on_yellow")
    with open(f"{base_dir}/{filename}/MediaInfo.json") as f:
        mi = json.load(f)
        length = mi['media']['track'][1]['Duration']
        length = round(float(length))
        for i in range(screens):
            (
                ffmpeg
                .input(path, ss=random.randint(round(length/5) , round(length - length/5)))
                .output(f"{base_dir}/{filename}/{filename}-{i}.png", vframes=1)
                .overwrite_output()
                .run()
            )
    cprint("Screens saved.", "grey", "on_green")

#Upload images & write description
def upload_screens(filename, screens):
    os.chdir(f"{base_dir}/{filename}")
    i=1
    description = open(f"{base_dir}/{filename}/DESCRIPTION.txt", 'a', newline="")
    
    #freeimage.host (64MB cap)
    for image in glob.glob("*.png"):
        url = "https://freeimage.host/api/1/upload"
        data = {
            'key': "6d207e02198a847aa98d0a2a901485a5",
            'image': base64.b64encode(open(image, "rb").read())
        }
        response = requests.post(url, data = data)
        response = response.json()
        img_url = response['image']['url']
        web_url = response['image']['url_viewer']
        description.write(f"[url={web_url}][img=400]{img_url}[/img][/url]")
        if i % 3 == 0:
            description.write("\n")
        print(f"{i}/{screens}")
        i += 1
    description.write("[center]Created by L4G's Upload Assistant[/center]")
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
        category = click.prompt("Unable to guess category. Please select one:", type=click.Choice['MOVIE', "TV"], case_sensitive=False)
        get_cat(category, video)
    return category

#Get Type ID
def get_type_id(type):
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
        resolution_name = "576o"
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
        width = mi['media']['track'][1]['Width']
        height = mi['media']['track'][1]['Height']
        framerate = mi['media']['track'][1]['FrameRate']
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
        width_list = [3840, 1920, 1280, 720, 15360, 7680]
        height_list = [2160, 1080, 720, 576, 480, 8640, 4320]
        width = closest(width_list, int(width))
        height = closest(height_list, int(height))
        res = f"{width}x{height}{scan}"
        resolution_id = mi_resolution(res, guess)

    return resolution_id

def closest(lst, K):
    return lst[min(range(len(lst)), key = lambda i: abs(lst[i]-K))]
#Get TMDB Name/ID/year
def get_tmdb(filename, category):
    i = 0
    while True:
        alt_name = ""
        anime = False
        mal_id = 0
        try:
            if category == 1: #MOVIE
                search.movie(query=filename)
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

            elif category == 2: #TV
                search.tv(query=filename)
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

            if search.results[i]['original_language'] == 'ja' and 16 in search.results[i]['genre_ids']:
                romaji = get_romaji(tmdb_name)
                anime = True
                mal = AnimeSearch(romaji)
                mal_id = mal.results[0].mal_id
                alt_name = f" AKA {romaji}"
            else:
                mal_id = 0


            difference = SequenceMatcher(None, tmdb_name, alt_name[5:]).ratio()
            if difference >= 0.6:
                alt_name = ""
            if click.confirm(f"Is {tmdb_name}{alt_name} ({tmdb_year}) correct?", default=True):
                pass
            else:
                i += 1
                continue
        except Exception as e:
            filename = click.prompt("Please enter Show/Film name")
            category = click.prompt("Please enter Category", type=click.Choice(['MOVIE', "TV"], case_sensitive=False))
            if category == "MOVIE":
                category = 1
            elif category == "TV":
                category = 2
            continue
        break
    imdb_id = int(imdb_id.replace('tt', ''))
    return tmdb_id, tmdb_name, tmdb_year, category, alt_name, imdb_id, anime, mal_id

def get_romaji(tmdb_name):
    query = '''
        query ($search: String) { 
            Media (search: $search, type: ANIME) { 
                id
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
    return romaji

#Naming
def get_name(path, video, tmdb_name, alt_name, guess, resolution_name, cat_id, type_id, tmdb_year, filename, tag, anime):
    with open(rf'{base_dir}/{filename}/MediaInfo.json', 'r') as f:
        mi = json.load(f)
        title = tmdb_name
        alt_title = alt_name
        year = tmdb_year
        resolution = resolution_name
        audio = get_audio(mi, anime)
        video_encode = get_video_encode(mi, type_id)
        video_codec = mi['media']['track'][1]['Format']
        tag = get_tag(tag, video)
        source = get_source(type_id, video, 1)
        uhd = get_uhd(type_id, guess)
        hdr = get_hdr(mi)
        if type_id == 1: #Disk
            region = get_region(path)
        edition = get_edition(guess, path)


        #YAY NAMING FUN
        if cat_id == 1: #MOVIE SPECIFIC
            if type_id == 1: #Disk
                name = f"{title} {alt_title} {year} {edition} {resolution} {region} {uhd}{source} {hdr}{video_codec} {audio}{tag}"
                convention = "Name Year Resolution Region Source Video-codec Audio-Tag"
            elif type_id == 3 and source == "BluRay": #BluRay Remux
                name = f"{title} {alt_title} {year} {edition} {resolution} {uhd}{source} REMUX {hdr}{video_codec} {audio}{tag}" 
                convention = "Name Year Resolution Source Video-codec Audio-Tag"
            elif type_id == 3 and source in ("PAL DVD", "NTSC DVD"): #DVD Remux
                name = f"{title} {alt_title} {year} {edition} {source} REMUX  {audio}{tag}" 
                convention = "Name Year Encoding_system Format Source Audio-Tag"
            elif type_id == 12: #Encode
                name = f"{title} {alt_title} {year} {edition} {resolution} {uhd}{source} {audio} {hdr}{video_encode}{tag}"  
                convention = "Name Year Resolution Source Audio Video-Tag"
            elif type_id == 4: #WEB-DL
                service = get_service(guess, video)
                name = f"{title} {alt_title} {year} {edition} {resolution} {uhd}{service} WEB-DL {audio} {hdr}{video_encode}{tag}"
                convention = "Name Year Resolution Source Rip-type Audio Video-codec-Tag"
            elif type_id == 5: #WEBRip
                service = get_service(guess, video)
                name = f"{title} {alt_title} {year} {edition} {resolution} {uhd}{service} WEBRip {audio} {hdr}{video_encode}{tag}"
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
                episode = "E" + str(guess["episode"]).zfill(2)
            except:
                episode = ""
            if type_id == 1: #Disk
                name = f"{title} {alt_title} {season}{episode} {edition} {resolution} {region} {uhd}{source} {hdr}{video_codec} {audio}{tag}"
                convention = "Name Year Resolution Region Source Video-codec Audio-Tag"
            elif type_id == 3 and source == "BluRay": #BluRay Remux
                name = f"{title} {alt_title} {season}{episode} {edition} {resolution} {uhd}{source} REMUX {hdr}{video_codec} {audio}{tag}" #SOURCE
                convention = "Name Year Resolution Source Video-codec Audio-Tag"
            elif type_id == 3 and source in ("PAL DVD", "NTSC DVD"): #DVD Remux
                name = f"{title} {alt_title} {season}{episode} {edition} {source} REMUX {audio}{tag}" #SOURCE
                convention = "Name Year Encoding_system Format Source Audio-Tag"
            elif type_id == 12: #Encode
                name = f"{title} {alt_title} {season}{episode} {edition} {resolution} {uhd}{source} {audio} {hdr}{video_encode}{tag}" #SOURCE
                convention = "Name Year Resolution Source Audio Video-Tag"
            elif type_id == 4: #WEB-DL
                service = get_service(guess, video)
                name = f"{title} {alt_title} {season}{episode} {edition} {resolution} {uhd}{service} WEB-DL {audio} {hdr}{video_encode}{tag}"
                convention = "Name Year Resolution Source Rip-type Audio Video-Tag"
            elif type_id == 5: #WEBRip
                service = get_service(guess, video)
                name = f"{title} {alt_title} {season}{episode} {edition} {resolution} {uhd}{service} WEBRip {audio} {hdr}{video_encode}{tag}"
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


def get_video_encode(mi, type_id):
    video_encode = ""
    codec = ""
    format = mi['media']['track'][1]['Format']
    format_profile = mi['media']['track'][1]['Format_Profile']
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
    except:
        if "HMAX" in video:
            service = "HMAX"
        elif "DSNP" in video:
            service = "DSNP"
        else:
            service = click.prompt("Enter WEB Source, leave blank for unknown", default="")
    return service


def get_uhd(type_id, guess):
    try:
        source = guess['Source']
        other = guess['Other']
    except:
        source = ""
        other = ""
    uhd = ""
    if source == 'Blu-ray' and other == "Ultra HD" or source == "Ultra HD Blu-ray":
        uhd = "UHD"
    elif type_id in (1, 3, 12, 5):
        uhd = ""

    return uhd

def get_hdr(mi):
    try:
        hdr = mi['media']['track'][1]['colour_primaries']
    except:
        hdr = ""
    if hdr in ("BT.2020", "REC.2020"):
        hdr = "HDR"
        if mi['media']['track'][1]['Format_Profile'] == "High 10":
            hdr = "HDR10+"
        try:
            if "HLG" in mi['media']['track'][1]['transfer_characteristics_Original']:
                hdr = "HLG"
        except:
            pass

    else:
        hdr = ""
    return hdr

def get_source(type_id, video, i):
    try:
        if i == 1:
            source = guessit(video)['source']
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
                system = click.prompt("Encoding system not found", type=click.Choice("PAL", "NTSC"), case_sensitive=False)
            source = system + " DVD"
    except Exception:
        prompt = click.prompt("Unable to find source, please choose one", type=click.Choice(["BR", "DVD"], case_sensitive=False))

        source = get_source(type_id, prompt, 2)

    return source

def get_edition(guess, path):
    try:
        edition = guess['edition']
    except:
        edition = ""
    if "REPACK" in path:
        edition = "REPACK"
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
        piece_size = 16777216,
        created_by = "L4G's Upload Assistant")
    cprint("Creating .torrent", 'grey', 'on_yellow')
    torrent.generate(callback=torf_cb, interval=5)
    torrent_path = f"{base_dir}/{filename}/{name}.torrent"
    torrent.write(f"{base_dir}/{filename}/{name}.torrent", overwrite=True)
    torrent.verify_filesize(path)
    cprint(".torrent created", 'grey', 'on_green')
    return torrent_path, torrent

def gen_desc(filename, desc, descfile, desclink, bdinfo, path, nfo):
    description = open(f"{base_dir}/{filename}/DESCRIPTION.txt", 'a', newline="")
    description.seek(0)
    description.write("[code]")
    if bdinfo != "":
        description.write(bdinfo)
    if nfo != None:
        nfo = glob.glob("*.nfo")[0]
        description.write(open(nfo, 'r').read())
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
            description.write("\n")
        elif desc != None:
            description.write(desc)
            description.write("\n")
    description.write("[/code]")

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

def rtorrent(path, torrent_path, torrent):
    rtorrent = xmlrpc.client.Server(rtorrent_url)
    cprint("Adding and rechecking torrent", 'grey', 'on_yellow')
    # torrent = Torrent(torrent_path)
    metainfo = bencode.bread(torrent_path)
    try:
        meta = add_fast_resume(metainfo, path, torrent)
    except EnvironmentError as exc:
        cprint("Error making fast-resume data (%s)" % (exc,), 'grey', 'on_red')
        raise
    
        
    new_meta = bencode.bencode(meta)
    if new_meta != metainfo:
        fr_file = torrent_path.replace('.torrent', '-resume.torrent')
        print("Writing %r..." % fr_file)
        bencode.bwrite(meta, fr_file)

    # pprint.pprint(meta)

    isdir = os.path.isdir(path)
    #Remote path mount
    if local_path in path:
        path = path.replace(local_path, remote_path)
        path = path.replace(os.sep, '/')
    if isdir == False:
        path = os.path.dirname(path)
    
    
    rtorrent.load.start_verbose('', fr_file, f"d.directory_base.set={path}")


def qbittorrent(path, torrent):
    cprint("Adding and rechecking torrent", 'grey', 'on_yellow')
    isdir = os.path.isdir(path)
    infohash = torrent.infohash
    #Remote path mount
    if local_path in path:
        path = path.replace(local_path, remote_path)
        path = path.replace(os.sep, '/')
    if isdir == False:
        path = os.path.dirname(path)

    qbt_client = qbittorrentapi.Client(host=config['DEFAULT']['qbit_url'], port=config['DEFAULT']['qbit_port'], username=config['DEFAULT']['qbit_user'], password=config['DEFAULT']['qbit_pass'])
    try:
        qbt_client.auth_log_in()
    except qbittorrentapi.LoginFailed as e:
        cprint("INCORRECT LOGIN CREDENTIALS", 'grey', 'on_red')
        exit()
    qbt_client.torrents_add(torrent_files=torrent.dump(), save_path=path, is_paused=True)
    qbt_client.torrents_recheck(torrent_hashes=infohash)
    cprint("Rechecking File", 'grey', 'on_yellow')
    while qbt_client.torrents_info(torrent_hashes=infohash)[0]['completed'] == 0:
        time.sleep(.1)
    qbt_client.torrents_resume(torrent_hashes=infohash)

def search_existing(name):
    cprint("Searching for existing torrents on site...", 'grey', 'on_yellow')
    url = f"https://blutopia.xyz/api/torrents/filter?name={urllib.parse.quote(name)}&api_token={blu_api}"
    response = requests.get(url=url)
    response = response.json()
    for each in response['data']:
        result = [each][0]['attributes']['name']
        difference = SequenceMatcher(None, name, result).ratio()
        if difference >= 0.1:
            if click.confirm(f"{result} already exists, is this a dupe?", default=False):
                exit()
    cprint("No dupes found", 'grey', 'on_green')
                
def get_disk(base_path):
    is_disk = ""
    videoloc = base_path
    bdinfo = ""
    for path, directories, files in os.walk(base_path):
        if "STREAM" in directories:
            is_disk = "BDMV"
            videoloc = os.path.join(path, "STREAM", get_largest(os.path.join(path, "STREAM"))) 
            bdinfo = get_bdinfo(base_path)
        elif "VIDEO_TS" in directories:
            is_disk = "DVD"
            videoloc = directories
            bdinfo = get_bdinfo(base_path)
            
    return is_disk, videoloc, bdinfo

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

def get_region(path):
    if "USA" in path:
        region = "USA"
    elif "FRE" in path:
        region = "FRE"
    elif "GBR" in path:
        region = "GBR"
    elif "GER" in path:
        region = "GER"
    elif "CZE" in path:
        region = "CZE"
    elif "EUR" in path:
        region = "EUR"
    elif "CAN" in path:
        region = "CAN"
    elif "TWN" in path:
        region = "TWN"
    elif "AUS" in path:
        region = "AUS"
    elif "BRA" in path:
        region = "BRA"
    elif "ITA" in path:
        region = "ITA"
    elif "ESP" in path:
        region = "ESP"
    elif "HKG" in path:
        region = "HKG"
    elif "JPN" in path:
        region = "JPN"
    elif "NOR" in path:
        region = "NOR"
    elif "FRA" in path:
        region = "FRA"
    else:
        region = click.prompt("Enter region, leave blank for unknown", default="")
    return region

def get_bdinfo(path):
    cprint("Getting BDInfo", 'grey', 'on_yellow')
    save_dir = f"{base_dir}/tmp"
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)
    if sys.platform.startswith('linux'):
        cprint('Due to needing root for linux to emulate keystrokes, push the BDInfo buttons yourself', 'grey', 'on_red')
        time.sleep(2)
        p = Popen(['mono', f"{base_dir}/BDInfo/BDInfo.exe", path, save_dir])
    elif sys.platform.startswith('win32'):
        p = Popen([f"{base_dir}/BDInfo/BDInfo.exe", path, save_dir])
        time.sleep(2)
        output, err = p.communicate(input=[keyboard.send(['1', 'enter']), keyboard.send(['q', 'enter'])])
    for file in os.listdir(save_dir):
        if file.startswith("BDINFO"):
            bdinfo_text = save_dir + "/" + file
    with open(bdinfo_text, 'r') as f:
        text = f.read()
        result = text.split("QUICK SUMMARY:", 1)
        prettyBDInfo = f"QUICK SUMMARY:{result[1]}".rstrip("\n")
        f.close()
    with open(f"{save_dir}/BDINFO.txt", 'w') as f:
        f.write(prettyBDInfo)
        f.close()
    shutil.rmtree(f"{base_dir}/tmp")
    return prettyBDInfo
        
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

doTheThing()

