import requests
import asyncio
from src.console import console
import traceback
from torf import Torrent
import xml.etree.ElementTree

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
            print("Piece size is OVER 16M and wont Work on MTV, Please Generate a new torrent and replace BASE.torrent")


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
            'auth': self.config['TRACKERS'][self.tracker].get('auth'),
            'anonymous': '0'
        }

        cookie = {'sid': self.config['TRACKERS'][self.tracker].get('sid'), 'cid': self.config['TRACKERS'][self.tracker].get('cid')}

        param = {
        }

        if meta['imdb_id'] != "0":
            param['imdbid'] = "tt" + meta['imdb_id']
        if meta['tmdb'] != 0:
            param['tmdbid'] = meta['tmdb']
        if meta['tvdb_id'] != 0:
            param['thetvdbid'] = meta['tvdb_id']
        if meta['tvmaze_id'] != 0:
            param['tvmazeid'] = meta['tvmaze_id']
        # if meta['mal_id'] != 0:
        #     param['malid'] = meta['mal_id']


        if meta['debug'] == False:
            response = requests.request("POST", url=self.upload_url, data=data, files=files, cookies=cookie)
            try:
                if str(response.url).__contains__("torrents.php"):
                    console.print(response.url)
                else:
                    if str(response.url).__contains__("authkey.php"):
                        console.print(f"[red]No DL link in response, So unable to download torrent but It may have uploaded, go check")
                        print(response.content)
                        console.print(f"[red]Got response code = {response.status_code}")
                        print(data)
                    else:
                        console.print(f"[red]Upload Failed, Doesnt look like you are logged in, Please check SID, CID and auth in config.py")
                        print(response.content)
                        print(data)
            except:
                console.print(f"[red]It may have uploaded, go check")
                console.print(data)
                print(traceback.print_exc())
                return
        else:
            # get stuff needed for uploading
            self.login()
            console.print(f"[cyan]Request Data:")
            console.print(data)

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
                    th_url = images[each]['th_url']
                    desc.write(f"[url={raw_url}][img=250]{th_url}[/img][/url]")
                desc.write(f"[/spoiler]")
            desc.write(f"\n\n{base}")
            desc.close()
        return

    async def edit_group_desc(self, meta):
        description = ""
        if meta['imdb_id'] != "0":
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
        if str(meta['tag']).lower().__contains__("swan"):
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

        # sub tags
        tags += " " + "subtitles" if str(meta['has_subs']) == 1 else ""

        # audio tags
        tags += " " + "ddp.audio" if str(meta['audio']).lower().__contains__('dd+')  else ""
        tags += " " + "atmos.audio" if str(meta['audio']).lower().__contains__('atmos') else ""
        tags += " " + "aac.audio" if str(meta['audio']).lower().__contains__('aac') else ""
        tags += " " + "truehd.audio" if str(meta['audio']).lower().__contains__('true') else ""
        tags += " " + "mp3.audio" if str(meta['audio']).lower().__contains__('mp3') else ""
        tags += " " + "mp2.audio" if str(meta['audio']).lower().__contains__('mp2') else ""

        # adding nogrp if no group detected
        tags += " " + str(meta['tag'])[1:].replace(' ', '.').lower() + ".release" if str(meta['tag']) != "" else " nogrp.release "
        return tags

    def login(self):
        url = 'https://www.morethantv.me/login'
        payload = {
            'username' : self.config['TRACKERS'][self.tracker].get('username'),
            'password' : self.config['TRACKERS'][self.tracker].get('password'),
            'keeploggedin' : 1,
            'cinfo' : '1920|1080|24|0',
            'submit' : 'login'
            # 'ssl' : 'yes'
        }
        res = requests.get(url="https://www.morethantv.me/login")
        token = str(res.content).rsplit('name="token" value="', 1)[1][:48]
        # token and CID from cookie needed for post to login
        payload["token"] = token
        # cook = res.cookies
        # adding token and cid from cookie to post.
        resp = requests.request("POST", url=url, data=payload, cookies=res.cookies)

        # checking if logged in
        if str(resp.content).__contains__('authkey='):
            auth = str(resp.content).rsplit('authkey=', 1)[1][:32]
            #printing auth and cid so you can add to config
            print('auth = ' + auth)
            print('cid = ' + resp.cookies.get_dict()['cid'])
            if 'sid' in resp.cookies.get_dict():
                print('sid = ' + resp.cookies.get_dict()['sid'])
            else:
                test = resp.history[0].cookies.get_dict()
                print('sid = ' + test['sid'])
            console.print('[green]Successfully logged in')
        return

    async def search_existing(self, meta):
        dupes = []
        console.print("[yellow]Searching for existing torrents on site...")
        params = {
            't' : 'search',
            'apikey' : self.config['TRACKERS'][self.tracker]['api_key'].strip(),
            'q' : ""
        }
        if meta['imdb_id'] != "0":
            params['imdbid'] = "tt" + meta['imdb_id']
            if meta['category'] == 'TV':
                params['season'] = meta.get('season_int', '')
                if meta.get('episode_int', '') != "0":
                    params['ep'] = meta.get('episode_int', '')
        elif meta['tmdb'] != "0":
            params['tmdbid'] = meta['tmdb']
            if meta['category'] == 'TV':
                params['season'] = meta.get('season_int', '')
                if meta.get('episode_int', '') != "0":
                    params['ep'] = meta.get('episode_int', '')
        elif meta['tvdb_id'] != 0:
            params['tvdbid'] = meta['tvdb_id']
            if meta['category'] == 'TV':
                params['season'] = meta.get('season_int', '')
                if meta.get('episode_int', '') != "0":
                    params['ep'] = meta.get('episode_int', '')
        else:
            params['q'] = meta['title'].replace(': ', ' ').replace('’', '').replace("'", '')
            if meta['category'] == 'TV':
                params['season'] = meta.get('season_int', '')
                if meta.get('episode_int', '') != "0":
                    params['ep'] = meta.get('episode_int', '')
            else:
                # params['q'] = params['q'] + f" {meta.get('year', '')}"
                params['season'] = meta.get('season_int', '')
                if meta.get('episode_int', '') != "0":
                    params['ep'] = meta.get('episode_int', '')
        if not meta['sd']:
            params['q'] = params['q'] + f" {meta.get('resolution', '')}"


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
            console.print(f"[red]Unable to search for existing torrents on site. Most likely the site is down or Jackett is down.")
            dupes.append("FAILED SEARCH")
            print(traceback.print_exc())
            await asyncio.sleep(5)

        return dupes
