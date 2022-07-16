import requests
import asyncio
import re
from termcolor import cprint
import os
from pathlib import Path
import traceback
import json
import glob
from unidecode import unidecode
from urllib.parse import urlparse, quote
from src.trackers.COMMON import COMMON
from src.bbcode import BBCODE
from src.exceptions import *


from pprint import pprint

class HDB():

    def __init__(self, config):
        self.config = config
        self.tracker = 'HDB'
        self.source_flag = 'HDBits'
        self.username = config['TRACKERS']['HDB'].get('username', '').strip()
        self.passkey = config['TRACKERS']['HDB'].get('passkey', '').strip()
        self.rehost_images = config['TRACKERS']['HDB'].get('img_rehost', False)
        self.signature = None
    

    async def get_type_category_id(self, meta):
        cat_id = "EXIT"
        # 6 = Audio Track
        # 8 = Misc/Demo
        # 4 = Music
        # 5 = Sport
        # 7 = PORN
        # 1 = Movie
        if meta['category'] == 'MOVIE':
            cat_id = 1
        # 2 = TV
        if meta['category'] == 'TV':
            cat_id = 2
        # 3 = Documentary
        if 'documentary' in meta.get("genres", "").lower() or 'documentary' in meta.get("keywords", "").lower():
            cat_id = 3
        return cat_id

    async def get_type_codec_id(self, meta):
        codecmap = {
            "AVC" : 1, "H.264" : 1,
            "HEVC" : 5, "H.265" : 5,
            "MPEG-2" : 2,
            "VC-1" : 3,
            "XviD" : 4,
            "VP9" : 6
        }
        searchcodec = meta.get('video_codec', meta.get('video_encode'))
        codec_id = codecmap.get(searchcodec, "EXIT")
        return codec_id

    async def get_type_medium_id(self, meta):
        medium_id = "EXIT"
        # 1 = Blu-ray / HD DVD
        if meta.get('is_disc', '') in ("BDMV", "HD DVD"):
            medium_id = 1
        # 4 = Capture
        if meta.get('type', '') == "HDTV":
            medium_id = 4
            if meta.get('has_encode_settings', False) == True:
                medium_id = 3  
        # 3 = Encode
        if meta.get('type', '') in ("ENCODE", "WEBRIP"):
            medium_id = 3
        # 5 = Remux
        if meta.get('type', '') == "REMUX":
            medium_id = 5
        # 6 = WEB-DL
        if meta.get('type', '') == "WEBDL":
            medium_id = 6
        return medium_id

    async def get_res_id(self, resolution):
        resolution_id = {
            '8640p':'10', 
            '4320p': '1', 
            '2160p': '2', 
            '1440p' : '3',
            '1080p': '3',
            '1080i':'4', 
            '720p': '5',  
            '576p': '6', 
            '576i': '7',
            '480p': '8', 
            '480i': '9'
            }.get(resolution, '10')
        return resolution_id

    async def get_tags(self, meta):
        tags = []

        # Web Services:
        service_dict = {
            "AMZN" : 28,
            "NF" : 29,
            "HULU" : 34,
            "DSNP" : 33,
            "HMAX" : 30,
            "ATVP" : 27,
            "iT" : 38,
            "iP" : 56,
            "STAN" : 32,
            "PCOK" : 31,
            "CR" : 72,
            "PMTP" : 69,
            "MA" : 77,
            "SHO" : 76,
            "BCORE" : 66, "CORE" : 66,
            "CRKL" : 73,
            "FUNI" : 74,
            "HLMK" : 71
        }
        if meta.get('service') in service_dict.keys():
            tags.append(service_dict.get(meta['service']))

        # Collections
        # Masters of Cinema, The Criterion Collection, Warner Archive Collection
        distributor_dict = {
            "WARNER ARCHIVE" : 68, "WARNER ARCHIVE COLLECTION" : 68, "WAC" : 68,
            "CRITERION" : 18, "CRITERION COLLECTION" : 18, "CC" : 18,
            "MASTERS OF CINEMA" : 19, "MOC" : 19,
            "KINO LORBER" : 55, "KINO" : 55,
            "BFI VIDEO" : 63, "BFI" : 63, "BRITISH FILM INSTITUTE" : 63,
            "STUDIO CANAL" : 65,
            "ARROW" : 64            
        }
        if meta.get('distributor') in distributor_dict.keys():
            tags.append(distributor_dict.get(meta['distributor']))
        

        # 4K Remaster, 
        if "IMAX" in meta.get('edition', ''):
            tags.append(14)
        if "OPEN MATTE" in meta.get('edition', '').upper():
            tags.append(58)

        # Audio
        # DTS:X, Dolby Atmos, Auro-3D, Silent
        if "DTS:X" in meta['audio']:
            tags.append(7)
        if "Atmos" in meta['audio']:
            tags.append(5)
        if meta.get('silent', False) == True:
            cprint('zxx audio track found, suggesting you tag as silent', 'yellow') #57

        # Video Metadata
        # HDR10, HDR10+, Dolby Vision, 10-bit, 
        if "HDR" in meta.get('hdr', ''):
            if "HDR10+" in meta['hdr']:
                tags.append(25) #HDR10+
            else:
                tags.append(9) #HDR10
        if "DV" in meta.get('hdr', ''):
            tags.append(6) #DV
        if "HLG" in meta.get('hdr', ''):
            tags.append(10) #HLG

        return tags

    async def edit_name(self, meta):
        hdb_name = meta['name']
        hdb_name = hdb_name.replace('H.265', 'HEVC')
        if meta.get('source', '').upper() == 'WEB':
            hdb_name = hdb_name.replace(f"{meta.get('service', '')} ", '')
        if 'DV' in meta.get('hdr', ''):
            hdb_name = hdb_name.replace(' DV ', ' DoVi ')
        if meta.get('type') in ('WEBDL', 'WEBRIP', 'ENCODE'):
            hdb_name = hdb_name.replace(meta['audio'], meta['audio'].replace(' ', '', 1))
        hdb_name = hdb_name.replace(meta.get('aka', ''), '').replace(meta['title'], meta['imdb_info']['aka'])
        if meta['year'] != meta.get('imdb_info', {}).get('year', meta['year']):
            hdb_name = hdb_name.replace(str(meta['year']), str(meta['imdb_info']['year']))
        # Remove Dubbed from title
        hdb_name = hdb_name.replace('Dubbed', '')
        hdb_name = ' '.join(hdb_name.split())

        return hdb_name 


    ###############################################################
    ######   STOP HERE UNLESS EXTRA MODIFICATION IS NEEDED   ######
    ###############################################################

    async def upload(self, meta):
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        await self.edit_desc(meta)
        hdb_name = await self.edit_name(meta)
        cat_id = await self.get_type_category_id(meta)
        codec_id = await self.get_type_codec_id(meta)
        medium_id = await self.get_type_medium_id(meta)
        hdb_tags = await self.get_tags(meta)

        for each in (cat_id, codec_id, medium_id):
            if each == "EXIT":
                cprint("Something didn't map correctly, or this content is not allowed", 'yellow')
                return
        # FORM
            # file : .torent file (needs renaming)
            # name : name
            # type_category : get_type_category_id
            # type_codec : get_type_codec_id
            # type_medium : get_type_medium_id
            # type_origin : 0 unless internal (1)
            # descr : description
            # techinfo : mediainfo only, no bdinfo
            # tags[] : get_tags
            # imdb : imdb link
            # tvdb_id : tvdb id
            # season : season number
            # episode : episode number
            # anidb_id
        # POST > upload/upload

        # Download new .torrent from site
        hdb_desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'r').read()
        torrent_path = f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]{meta['clean_name']}.torrent"
        with open(torrent_path, 'rb') as torrentFile:
            torrentFileName = unidecode(os.path.basename(meta['video']).replace(' ', '.'))
            files = {
                'file' : (f"{torrentFileName}.torrent", torrentFile, "application/x-bittorent")
            }
            data = {
                'name' : hdb_name,
                'category' : cat_id,
                'codec' : codec_id,
                'medium' : medium_id,
                'origin' : 0,
                'descr' : hdb_desc.rstrip(),
                'techinfo' : '',
                'tags[]' : hdb_tags,
                'imdb' : f"https://www.imdb.com/title/tt{meta.get('imdb_id', '').replace('tt', '')}/",
            }

            # If internal, set 1
            if self.config['TRACKERS'][self.tracker].get('internal', False) == True:
                if meta['tag'] != "" and (meta['tag'][1:] in self.config['TRACKERS'][self.tracker].get('internal_groups', [])):
                    data['internal'] = 1
            # If not BDMV fill mediainfo
            if meta.get('is_disc', '') != "BDMV":
                data['techinfo'] = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO_CLEANPATH.txt", 'r', encoding='utf-8').read()
            # If tv, submit tvdb_id/season/episode
            if meta.get('tvdb_id', 0) != 0:
                data['tvdb'] = meta['tvdb_id']
            if meta.get('category') == 'TV':
                data['tvdb_season'] = int(meta.get('season_int', 1))
                data['tvdb_episode'] = int(meta.get('episode_int', 1))
            # aniDB


            # Submit
            if meta['debug']:
                pprint(url)
                pprint(data)
            else:
                url = "https://hdbits.org/upload/upload"
                with requests.Session() as session:
                    cookiefile = f"{meta['base_dir']}/data/cookies/HDB.txt"
                    session.cookies.update(await common.parseCookieFile(cookiefile))
                    up = session.post(url=url, data=data, files=files)
                    torrentFile.close()

                    # Match url to verify successful upload
                    match = re.match(r".*?hdbits\.org/details\.php\?id=(\d+)&uploaded=(\d+)", up.url)
                    if match is not None:
                        id = re.search(r"(id=)(\d+)", urlparse(up.url).query).group(2)
                        await self.download_new_torrent(id, torrent_path)
                    else:
                        pprint(data)
                        print("\n\n\n\n")
                        pprint(up.text)
                        raise UploadException(f"Upload to HDB Failed: result URL {up.url} ({up.status_code}) was not expected", 'red')
        return


    async def search_existing(self, meta):
        dupes = []
        cprint("Searching for existing torrents on site...", 'grey', 'on_yellow')
        url = "https://hdbits.org/api/torrents"
        data = {
            'username' : self.username,
            'passkey' : self.passkey,
            'category' : await self.get_type_category_id(meta),
            'codec' : await self.get_type_codec_id(meta),
            'medium' : await self.get_type_medium_id(meta),
            'search' : meta['resolution']
        }
        if int(meta.get('imdb_id', '0').replace('tt', '0')) != 0:
            data['imdb'] = {'id' : meta['imdb_id']}
        if int(meta.get('tvdb_id', '0')) != 0:
            data['tvdb'] = {'id' : meta['tvdb_id']}
        try:
            response = requests.get(url=url, data=json.dumps(data))
            response = response.json()
            for each in response['data']:
                result = each['name']
                dupes.append(result)
        except:
            cprint('Unable to search for existing torrents on site. Either the site is down or your passkey is incorrect', 'grey', 'on_red')
            print(traceback.print_exc())
            await asyncio.sleep(5)

        return dupes

    


    async def validate_credentials(self, meta):
        vapi =  await self.validate_api()
        vcookie = await self.validate_cookies(meta)
        if vapi != True:
            cprint('Failed to validate API. Please confirm that the site is up and your passkey is valid.', 'red')
            return False
        if vcookie != True:
            cprint('Failed to validate cookies. Please confirm that the site is up and your passkey is valid.', 'red')
            return False
        return True
    
    async def validate_api(self):
        url = "https://hdbits.org/api/test"
        data = {
            'username' : self.username,
            'passkey' : self.passkey
        }
        try:
            r = requests.post(url, data=json.dumps(data)).json()
            if r.get('status', 5) == 0:
                return True
            return False
        except:
            return False
    
    async def validate_cookies(self, meta):
        common = COMMON(config=self.config)
        url = "https://hdbits.org"
        cookiefile = f"{meta['base_dir']}/data/cookies/HDB.txt"
        if os.path.exists(cookiefile):
            with requests.Session() as session:
                session.cookies.update(await common.parseCookieFile(cookiefile))
                resp = session.get(url=url)
                if meta['debug']:
                    cprint('Cookies:', 'cyan')
                    pprint(session.cookies.get_dict())
                    print("\n\n\n\n\n\n")
                    pprint(resp.text)
                if resp.text.find("""<a href="/logout.php">Logout</a>""") != -1:
                    return True
                else:
                    return False
        else:
            cprint("Missing Cookie File. (data/cookies/HDB.txt)", 'red')
            return False

    async def download_new_torrent(self, id, torrent_path):
        # Get HDB .torrent filename
        api_url = "https://hdbits.org/api/torrents"
        data = {
            'username' : self.username,
            'passkey' : self.passkey,
            'id' : id
        }
        r = requests.get(url=api_url, data=json.dumps(data))
        filename = r.json()['data'][0]['filename']

        # Download new .torrent
        download_url = f"https://hdbits.org/download.php/{quote(filename)}"
        params = {
            'passkey' : self.passkey,
            'id' : id
        }

        r = requests.get(url=download_url, params=params)
        with open(torrent_path, "wb") as tor:
            tor.write(r.content)
        return

    async def edit_desc(self, meta):
        base = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'r').read()
        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'w') as descfile:
            from src.bbcode import BBCODE
            # Add This line for all web-dls
            if meta['type'] == 'WEBDL' and meta.get('service_longname', '') != '' and meta.get('description', None) == None:
                descfile.write(f"[center][quote]This release is sourced from {meta['service_longname']}[/quote][/center]")
            bbcode = BBCODE()
            if meta.get('discs', []) != []:
                discs = meta['discs']
                if discs[0]['type'] == "DVD":
                    descfile.write(f"[quote=VOB MediaInfo]{discs[0]['vob_mi']}[/quote]\n")
                    descfile.write("\n")
                if discs[0]['type'] == "BDMV":
                    descfile.write(f"[quote]{discs[0]['summary'].rstrip()}[/quote]\n")
                    descfile.write("\n")
                if len(discs) >= 2:
                    for each in discs[1:]:
                        if each['type'] == "BDMV":
                            descfile.write(f"[quote={each.get('name', 'BDINFO')}]{each['summary']}[/quote]\n")
                            descfile.write("\n")
                            pass
                        if each['type'] == "DVD":
                            descfile.write(f"{each['name']}:\n")
                            descfile.write(f"[quote={os.path.basename(each['vob'])}][{each['vob_mi']}[/quote] [quote={os.path.basename(each['ifo'])}][{each['ifo_mi']}[/quote]\n")
                            descfile.write("\n")
            desc = base
            desc = bbcode.convert_code_to_quote(desc)
            desc = bbcode.convert_spoiler_to_hide(desc)
            desc = bbcode.convert_comparison_to_centered(desc, 1000)
            desc = desc.replace('[img]', '[imgw]').replace('[/img]', '[/imgw]')
            desc = re.sub("(\[img=\d+)]", "[imgw]", desc, flags=re.IGNORECASE)
            descfile.write(desc)
            if self.rehost_images == True:
                cprint("Rehosting Images...", 'green')
                hdbimg_bbcode = await self.hdbimg_upload(meta)
                descfile.write(f"{hdbimg_bbcode}")
            else:
                images = meta['image_list']
                if len(images) > 0: 
                    descfile.write("[center]")
                    for each in range(len(images)):
                        img_url = images[each]['img_url']
                        descfile.write(f"[imgw={img_url}]")
                    descfile.write("[/center]")
            if self.signature != None:
                descfile.write(self.signature)
            descfile.close()

    
    async def hdbimg_upload(self, meta):
        images = glob.glob(f"{meta['base_dir']}/tmp/{meta['uuid']}/{meta['filename']}-*.png")
        url = "https://img.hdbits.org/upload_api.php"
        data = {
            'username' : self.username,
            'passkey' : self.passkey,
            'galleryoption' : 1,
            'galleryname' : meta['name'],
            'thumbsize' : 'w300'
        }
        files = {}
        for i in range(len(images)):
            files[f'images_files[{i}]'] = open(images[i], 'rb')
        r = requests.post(url=url, data=data, files=files)
        image_bbcode = r.text
        return image_bbcode