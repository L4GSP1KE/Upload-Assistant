import requests
import asyncio
from src.console import console
import traceback
from torf import Torrent
import xml.etree.ElementTree
import os
import cli_ui
import pickle
from src.trackers.COMMON import COMMON


class MTV():
    """
    Edit for Tracker:
        Edit BASE.torrent with announce and source
        Check for duplicates
        Set type/category IDs
        Upload
    """

    def __init__(self, config):
        self.config = config
        self.tracker = 'MTV'
        self.source_flag = 'MTV'
        self.upload_url = 'https://www.morethantv.me/upload.php'
        self.forum_link = 'https://www.morethantv.me/wiki.php?action=article&id=73'
        self.search_url = 'https://www.morethantv.me/api/torznab'
        pass

    async def upload(self, meta):
        common = COMMON(config=self.config)
        cookiefile = os.path.abspath(f"{meta['base_dir']}/data/cookies/MTV.pkl")

        await common.edit_torrent(meta, self.tracker, self.source_flag)

        new_torrent = Torrent.read(f"{meta['base_dir']}/tmp/{meta['uuid']}/BASE.torrent")

        if new_torrent.piece_size == 262144:  # 256 MiB
            # print("256k")
            pass
        elif new_torrent.piece_size == 524288:  # 1 GiB
            # piece_size = "512K"
            pass
        elif new_torrent.piece_size == 1048576:  # 2 GiB
            # piece_size = "1M"
            pass
        elif new_torrent.piece_size == 2097152:  # 4 GiB
            # piece_size = "2M"
            pass
        elif new_torrent.piece_size == 4194304:  # 8 GiB
            # piece_size = "4M"
            pass
        elif new_torrent.piece_size == 8388608:  # 16 GiB
            # piece_size = "8M"
            pass
        elif new_torrent.piece_size == 16777216:  # 16 GiB
            print("Piece size is 16M and wont Work on MTV, Please Generate a new torrent and replace BASE.torrent")
        else:
            print("Piece size is OVER 8M and wont Work on MTV, Please Generate a new torrent and replace BASE.torrent")


        # getting category HD Episode, HD Movies, SD Season, HD Season, SD Episode, SD Movies
        cat_id = await self.get_cat_id(meta)
        # res 480 720 1080 1440 2160 4k 6k Other
        resolution_id = await self.get_res_id(meta['resolution'])
        # getting source HDTV SDTV TV Rip DVD DVD Rip VHS BluRay BDRip WebDL WebRip Mixed Unknown
        source_id = await self.get_source_id(meta)
        # get Origin Internal Scene P2P User Mixed Other. P2P will be selected if not scene
        origin_id = await self.get_origin_id(meta)
        # getting tags
        des_tags = await self.get_tags(meta)
        # getting description
        await self.edit_desc(meta)
        # getting groups des so things like imdb link, tmdb link etc..
        group_desc = await self.edit_group_desc(meta)
        #poster is optional so no longer getting it as its a pain with having to use supported image provider
        # poster = await self.get_poster(meta)

        desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'r').read()

        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]{meta['clean_name']}.torrent", 'rb') as f:
            tfile = f.read()
            f.close()

        ## todo need to check the torrent and make sure its not more than 8MB

        # need to pass the name of the file along with the torrent
        files = {
            'file_input': (f"{meta['name']}.torrent", tfile)
        }

        data = {
            # 'image': poster,
            'image': '',
            'title': meta['name'] + "-NoGrp".replace(' ','.').replace(':.','.').replace('’','').replace('\'','').replace('DD+', 'DDP') if meta['name'].lower().endswith("264") or meta['name'].lower().endswith("265") or meta['name'].lower().endswith("hvec") or meta['name'].lower().endswith("xvid") else meta['name'].replace(' ','.').replace(':.','.').replace('’','').replace('\'','').replace('DD+', 'DDP'),
            'category': cat_id,
            'Resolution': resolution_id,
            'source': source_id,
            'origin': origin_id,
            'taglist': des_tags,
            'desc': desc,
            'groupDesc': group_desc,
            'ignoredupes': '1',
            'submit': 'true',
            'genre_tags': '---',
            'autocomplete_toggle': 'on',
            'fontfont': '-1',
            'fontsize': '-1',
            'auth': self.get_auth(cookiefile),
            'anonymous': '0'
        }

        # cookie = {'sid': self.config['TRACKERS'][self.tracker].get('sid'), 'cid': self.config['TRACKERS'][self.tracker].get('cid')}

        param = {
        }

        if meta['imdb_id'] not in ("0", "", None):
            param['imdbID'] = "tt" + meta['imdb_id']
        if meta['tmdb'] != 0:
            param['tmdbID'] = meta['tmdb']
        if meta['tvdb_id'] != 0:
            param['thetvdbID'] = meta['tvdb_id']
        if meta['tvmaze_id'] != 0:
            param['tvmazeID'] = meta['tvmaze_id']
        # if meta['mal_id'] != 0:
        #     param['malid'] = meta['mal_id']


        if meta['debug'] == False:
            with requests.Session() as session:
                with open(cookiefile, 'rb') as cf:
                    session.cookies.update(pickle.load(cf))
                response = session.post(url=self.upload_url, data=data, files=files)
                try:
                    if "torrents.php" in response.url:
                        console.print(response.url)
                    else:
                        if "authkey.php" in response.url:
                            console.print(f"[red]No DL link in response, So unable to download torrent but It may have uploaded, go check")
                            print(response.content)
                            console.print(f"[red]Got response code = {response.status_code}")
                            print(data)
                        else:
                            console.print(f"[red]Upload Failed, Doesnt look like you are logged in")
                            print(response.content)
                            print(data)
                except:
                    console.print(f"[red]It may have uploaded, go check")
                    console.print(data)
                    print(traceback.print_exc())
        else:
            console.print(f"[cyan]Request Data:")
            console.print(data)
        return


    async def edit_desc(self, meta):
        base = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'r').read()
        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'w') as desc:
            # adding bd_dump to description if it exits and adding empty string to mediainfo
            if meta['bdinfo'] != None:
                mi_dump = None
                bd_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8').read()
            else:
                mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO_CLEANPATH.txt", 'r', encoding='utf-8').read()
                bd_dump = None
            if bd_dump:
                desc.write("[mediainfo]" + bd_dump + "[/mediainfo]\n\n")
            elif mi_dump:
                desc.write("[mediainfo]" + mi_dump + "[/mediainfo]\n\n")
            images = meta['image_list']
            if len(images) > 0:
                desc.write(f"[spoiler=Screenshots]")
                for each in range(len(images)):
                    raw_url = images[each]['raw_url']
                    img_url = images[each]['img_url']
                    desc.write(f"[url={raw_url}][img=250]{img_url}[/img][/url]")
                desc.write(f"[/spoiler]")
            desc.write(f"\n\n{base}")
            desc.close()
        return

    async def edit_group_desc(self, meta):
        description = ""
        if meta['imdb_id'] not in ("0", "", None): 
            description += f"https://www.imdb.com/title/tt{meta['imdb_id']}"
        if meta['tmdb'] != 0:
            description += f"\nhttps://www.themoviedb.org/{str(meta['category'].lower())}/{str(meta['tmdb'])}"
        if meta['tvdb_id'] != 0:
            description += f"\nhttps://www.thetvdb.com/?id={str(meta['tvdb_id'])}"
        if meta['tvmaze_id'] != 0:
            description += f"\nhttps://www.tvmaze.com/shows/{str(meta['tvmaze_id'])}"
        if meta['mal_id'] != 0:
            description += f"\nhttps://myanimelist.net/anime/{str(meta['mal_id'])}"

        return description

    # Not needed as its optional
    # async def get_poster(self, meta):
    #     if 'poster_image' in meta:
    #         return meta['poster_image']
    #     else:
    #         if meta['poster'] is not None:
    #             poster = meta['poster']
    #         else:
    #             if 'cover' in meta['imdb_info'] and meta['imdb_info']['cover'] is not None:
    #                 poster = meta['imdb_info']['cover']
    #             else:
    #                 console.print(f'[red]No poster can be found for this EXITING!!')
    #                 return
    #         with requests.get(url=poster, stream=True) as r:
    #             with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/{meta['clean_name']}-poster.jpg",
    #                       'wb') as f:
    #                 shutil.copyfileobj(r.raw, f)
    #
    #         url = "https://api.imgbb.com/1/upload"
    #         data = {
    #             'key': self.config['DEFAULT']['imgbb_api'],
    #             'image': base64.b64encode(open(f"{meta['base_dir']}/tmp/{meta['uuid']}/{meta['clean_name']}-poster.jpg", "rb").read()).decode('utf8')
    #         }
    #         try:
    #             console.print("[yellow]uploading poster to imgbb")
    #             response = requests.post(url, data=data)
    #             response = response.json()
    #             if response.get('success') != True:
    #                 console.print(response, 'red')
    #             img_url = response['data'].get('medium', response['data']['image'])['url']
    #             th_url = response['data']['thumb']['url']
    #             web_url = response['data']['url_viewer']
    #             raw_url = response['data']['image']['url']
    #             meta['poster_image'] = raw_url
    #             console.print(f'[green]{raw_url} ')
    #         except Exception:
    #             console.print("[yellow]imgbb failed to upload cover")
    #
    #         return raw_url

    async def get_res_id(self, resolution):
        resolution_id = {
            '8640p':'0',
            '4320p': '4000',
            '2160p': '2160',
            '1440p' : '1440',
            '1080p': '1080',
            '1080i':'1080',
            '720p': '720',
            '576p': '0',
            '576i': '0',
            '480p': '480',
            '480i': '480'
            }.get(resolution, '10')
        return resolution_id

    async def get_cat_id(self, meta):
        if meta['category'] == "MOVIE":
            if meta['sd'] == 1:
                return 2
            else:
                return 1
        if meta['category'] == "TV":
            if meta['tv_pack'] == 1:
                if meta['sd'] == 1:
                    return 6
                else:
                    return 5
            else:
                if meta['sd'] == 1:
                    return 4
                else:
                    return 3


    async def get_source_id(self, meta):
        if meta['is_disc'] == 'DVD':
            return '1'
        elif meta['is_disc'] == 'BDMV' or meta['type'] == "REMUX":
            return '7'
        else:
            type_id = {
                'DISC': '1',
                'WEBDL': '9',
                'WEBRIP': '10',
                'HDTV': '1',
                'SDTV': '2',
                'TVRIP': '3',
                'DVD': '4',
                'DVDRIP': '5',
                'BDRIP': '8',
                'VHS': '6',
                'MIXED': '11',
                'Unknown': '12',
                'ENCODE': '7'
                }.get(meta['type'], '0')
        return type_id


    async def get_origin_id(self, meta):
        if meta['personalrelease']:
            return '4'
        elif meta['scene']:
            return '2'
        # returning P2P
        else:
            return '3'


    async def get_tags(self, meta):
        tags = ""
        tags += str(meta['genres']).lower().replace(',', '')
        tags += " " + str(meta['type']).lower()
        tags += " " + str(meta['resolution']).lower()
        tags += " " + str(meta['service_longname']).lower().replace(' ', '.') + ".source" if str(meta['service_longname']).lower() != "" else ""

        # series tags
        # series tags sd
        tags += " " + "episode.release sd.episode" if meta['sd'] == 1 and meta['category'] == "TV" and 'tv_pack' in meta and meta['tv_pack'] != 1 else ""
        # series tags hd
        tags += " " + "episode.release hd.episode" if meta['category'] == "TV" and 'tv_pack' in meta and meta['tv_pack'] != 1 else ""
        # series tag season
        tags += " " + "sd.season" if meta['sd'] == 1 else " " + "hd.season" if 'tv_pack' in meta and meta['tv_pack'] == 1 else ""

        # movie tags
        tags += " " + "sd.movie" if meta['category'] == "MOVIE" and meta['sd'] == 1 else ""
        tags += " " + "hd.movie" if meta['category'] == "MOVIE" and meta['sd'] == 0 else ""

        # audio tags
        for each in ['ddp', 'atmos', 'aac', 'truehd', 'mp3', 'mp2']:
            if each in meta['audio'].replace('+', 'p'):
                tags += f" {each}.audio"

        # adding nogrp if no group detected
        tags += " " + str(meta['tag'])[1:].replace(' ', '.').lower() + ".release" if str(meta['tag']) != "" else " nogrp.release "
        return tags



    async def validate_credentials(self, meta):
        cookiefile = os.path.abspath(f"{meta['base_dir']}/data/cookies/MTV.pkl")
        if not os.path.exists(cookiefile):
            await self.login(cookiefile)
        vcookie = await self.validate_cookies(meta)
        if vcookie != True:
            console.print('[red]Failed to validate cookies. Please confirm that the site is up and your username and password is valid.')
            recreate = cli_ui.ask_yes_no("Log in again and create new session?")
            if recreate == True:
                if os.path.exists(cookiefile):
                    os.remove(cookiefile)
                await self.login(cookiefile)
                vcookie = await self.validate_cookies(meta, cookiefile)
                return vcookie
            else:
                return False
        vapi = await self.validate_api()
        if vapi != True:
            console.print('[red]Failed to validate API. Please confirm that the site is up and your API key is valid.')
        return True

    async def validate_api(self):
        url = self.search_url
        params = {
            'apikey' : self.config['TRACKERS'][self.tracker]['api_key'].strip(),
        }
        try:
            r = requests.get(url, params=params)
            if not r.ok:
                if "unauthorized api key" in r.text.lower():
                    console.print("[red]Invalid API Key")
                return False
            return True
        except:
            return False

    async def validate_cookies(self, meta, cookiefile):
        url = "https://www.morethantv.me/index.php"
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

    async def get_auth(self, cookiefile):
        url = "https://www.morethantv.me/index.php"
        if os.path.exists(cookiefile):
            with requests.Session() as session:
                with open(cookiefile, 'rb') as cf:
                    session.cookies.update(pickle.load(cf))
                resp = session.get(url=url)
                auth = resp.text.rsplit('authkey=', 1)[1][:32]
                return auth

    async def login(self, cookiefile):
        with requests.Session() as session:
            url = 'https://www.morethantv.me/login'
            payload = {
                'username' : self.config['TRACKERS'][self.tracker].get('username'),
                'password' : self.config['TRACKERS'][self.tracker].get('password'),
                'keeploggedin' : 1,
                'cinfo' : '1920|1080|24|0',
                'submit' : 'login'
                # 'ssl' : 'yes'
            }
            res = session.get(url="https://www.morethantv.me/login")
            token = res.text.rsplit('name="token" value="', 1)[1][:48]
            # token and CID from cookie needed for post to login
            payload["token"] = token
            # cook = res.cookies
            # adding token and cid from cookie to post.
            resp = session.post(url=url, data=payload)

            # checking if logged in
            if 'authkey=' in resp.text:
                # auth = resp.text.rsplit('authkey=', 1)[1][:32]
                # #printing auth and cid so you can add to config
                # print('auth = ' + auth)
                # print('cid = ' + resp.cookies.get_dict()['cid'])
                # if 'sid' in resp.cookies.get_dict():
                #     print('sid = ' + resp.cookies.get_dict()['sid'])
                # else:
                #     test = resp.history[0].cookies.get_dict()
                #     print('sid = ' + test['sid'])
                console.print('[green]Successfully logged in to MTV')
                with open(cookiefile, 'wb') as cf:
                    pickle.dump(session.cookies, cf)
            else:
                console.print('[bold red]Something went wrong while trying to log into FL')
                await asyncio.sleep(1)
                console.print(resp.url)
        return

    async def search_existing(self, meta):
        dupes = []
        console.print("[yellow]Searching for existing torrents on site...")
        params = {
            't' : 'search',
            'apikey' : self.config['TRACKERS'][self.tracker]['api_key'].strip(),
            'q' : ""
        }
        if meta['imdb_id'] not in ("0", "", None):
            params['imdbid'] = "tt" + meta['imdb_id']
        elif meta['tmdb'] != "0":
            params['tmdbid'] = meta['tmdb']
        elif meta['tvdb_id'] != 0:
            params['tvdbid'] = meta['tvdb_id']
        else:
            params['q'] = meta['title'].replace(': ', ' ').replace('’', '').replace("'", '')

        try:
            rr = requests.get(url=self.search_url, params=params)
            if rr is not None:
                # process search results
                response_xml = xml.etree.ElementTree.fromstring(rr.text)
                for each in response_xml.find('channel').findall('item'):
                    result = each.find('title').text
                    dupes.append(result)
            else:
                if 'status_message' in rr:
                    console.print(f"[yellow]{rr.get('status_message')}")
                    await asyncio.sleep(5)
                else:
                    console.print(f"[red]Site Seems to be down or not responding to API")
        except:
            console.print(f"[red]Unable to search for existing torrents on site. Most likely the site is down.")
            dupes.append("FAILED SEARCH")
            print(traceback.print_exc())
            await asyncio.sleep(5)

        return dupes
