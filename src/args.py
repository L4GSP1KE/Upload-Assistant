# -*- coding: utf-8 -*-
import argparse
import urllib.parse
import os
import datetime
import traceback

from src.console import console


class Args():
    """
    Parse Args
    """
    def __init__(self, config):
        self.config = config
        pass
    

     
    def parse(self, args, meta):
        input = args
        parser = argparse.ArgumentParser()

        parser.add_argument('path', nargs='*', help="Path to file/directory")
        parser.add_argument('-s', '--screens', nargs='*', required=False, help="Number of screenshots", default=int(self.config['DEFAULT']['screens']))
        parser.add_argument('-c', '--category', nargs='*', required=False, help="Category [MOVIE, TV, FANRES]", choices=['movie', 'tv', 'fanres'])
        parser.add_argument('-t', '--type', nargs='*', required=False, help="Type [DISC, REMUX, ENCODE, WEBDL, WEBRIP, HDTV]", choices=['disc', 'remux', 'encode', 'webdl', 'web-dl', 'webrip', 'hdtv'])
        parser.add_argument('--source', nargs='*', required=False, help="Source [Blu-ray, BluRay, DVD, HDDVD, WEB, HDTV, UHDTV]", choices=['Blu-ray', 'BluRay', 'DVD', 'HDDVD', 'WEB', 'HDTV', 'UHDTV'], dest="manual_source")
        parser.add_argument('-res', '--resolution', nargs='*', required=False, help="Resolution [2160p, 1080p, 1080i, 720p, 576p, 576i, 480p, 480i, 8640p, 4320p, OTHER]", choices=['2160p', '1080p', '1080i', '720p', '576p', '576i', '480p', '480i', '8640p', '4320p', 'other'])
        parser.add_argument('-tmdb', '--tmdb', nargs='*', required=False, help="TMDb ID", type=str, dest='tmdb_manual')
        parser.add_argument('-imdb', '--imdb', nargs='*', required=False, help="IMDb ID", type=str)
        parser.add_argument('-mal', '--mal', nargs='*', required=False, help="MAL ID", type=str)
        parser.add_argument('-g', '--tag', nargs='*', required=False, help="Group Tag", type=str)
        parser.add_argument('-serv', '--service', nargs='*', required=False, help="Streaming Service", type=str)
        parser.add_argument('-dist', '--distributor', nargs='*', required=False, help="Disc Distributor e.g.(Criterion, BFI, etc.)", type=str)
        parser.add_argument('-edition', '--edition', '--repack', nargs='*', required=False, help="Edition/Repack String e.g.(Director's Cut, Uncut, Hybrid, REPACK, REPACK3)", type=str, dest='manual_edition', default="")
        parser.add_argument('-season', '--season', nargs='*', required=False, help="Season (number)", type=str)
        parser.add_argument('-episode', '--episode', nargs='*', required=False, help="Episode (number)", type=str)
        parser.add_argument('-daily', '--daily', nargs=1, required=False, help="Air date of this episode (YYYY-MM-DD)", type=datetime.date.fromisoformat, dest="manual_date")
        parser.add_argument('--no-season', dest='no_season', action='store_true', required=False, help="Remove Season from title")
        parser.add_argument('--no-year', dest='no_year', action='store_true', required=False, help="Remove Year from title")
        parser.add_argument('--no-aka', dest='no_aka', action='store_true', required=False, help="Remove AKA from title")
        parser.add_argument('--no-dub', dest='no_dub', action='store_true', required=False, help="Remove Dubbed from title")
        parser.add_argument('--no-tag', dest='no_tag', action='store_true', required=False, help="Remove Group Tag from title")
        parser.add_argument('-year', '--year', dest='manual_year', nargs='?', required=False, help="Year", type=int, default=0)
        parser.add_argument('-ptp', '--ptp', nargs='*', required=False, help="PTP torrent id/permalink", type=str)
        parser.add_argument('-blu', '--blu', nargs='*', required=False, help="BLU torrent id/link", type=str)
        parser.add_argument('-hdb', '--hdb', nargs='*', required=False, help="HDB torrent id/link", type=str)
        parser.add_argument('-d', '--desc', nargs='*', required=False, help="Custom Description (string)")
        parser.add_argument('-pb', '--desclink', nargs='*', required=False, help="Custom Description (link to hastebin/pastebin)")
        parser.add_argument('-df', '--descfile', nargs='*', required=False, help="Custom Description (path to file)")
        parser.add_argument('-ih', '--imghost', nargs='*', required=False, help="Image Host", choices=['imgbb', 'ptpimg', 'imgbox', 'pixhost', 'lensdump'])
        parser.add_argument('-siu', '--skip-imagehost-upload', dest='skip_imghost_upload', action='store_true', required=False, help="Skip Uploading to an image host")
        parser.add_argument('-th', '--torrenthash', nargs='*', required=False, help="Torrent Hash to re-use from your client's session directory")
        parser.add_argument('-nfo', '--nfo', action='store_true', required=False, help="Use .nfo in directory for description")
        parser.add_argument('-k', '--keywords', nargs='*', required=False, help="Add comma seperated keywords e.g. 'keyword, keyword2, etc'")
        parser.add_argument('-reg', '--region', nargs='*', required=False, help="Region for discs")
        parser.add_argument('-a', '--anon', action='store_true', required=False, help="Upload anonymously")
        parser.add_argument('-st', '--stream', action='store_true', required=False, help="Stream Optimized Upload")
        parser.add_argument('-webdv', '--webdv', action='store_true', required=False, help="Contains a Dolby Vision layer converted using dovi_tool")
        parser.add_argument('-hc', '--hardcoded-subs', action='store_true', required=False, help="Contains hardcoded subs", dest="hardcoded-subs")
        parser.add_argument('-pr', '--personalrelease', action='store_true', required=False, help="Personal Release")
        parser.add_argument('-sdc','--skip-dupe-check', action='store_true', required=False, help="Pass if you know this is a dupe (Skips dupe check)", dest="dupe")
        parser.add_argument('-debug', '--debug', action='store_true', required=False, help="Debug Mode, will run through all the motions providing extra info, but will not upload to trackers.")
        parser.add_argument('-ffdebug', '--ffdebug', action='store_true', required=False, help="Will show info from ffmpeg while taking screenshots.")
        parser.add_argument('-m', '--manual', action='store_true', required=False, help="Manual Mode. Returns link to ddl screens/base.torrent")
        parser.add_argument('-nh', '--nohash', action='store_true', required=False, help="Don't hash .torrent")
        parser.add_argument('-rh', '--rehash', action='store_true', required=False, help="DO hash .torrent")
        parser.add_argument('-dr', '--draft', action='store_true', required=False, help="Send to drafts (BHD)")
        parser.add_argument('-tc', '--torrent-creation', dest='torrent_creation', nargs='*', required=False, help="What tool should be used to create the base .torrent", choices=['torf', 'torrenttools', 'mktorrent'])
        parser.add_argument('-client', '--client', nargs='*', required=False, help="Use this torrent client instead of default")
        parser.add_argument('-qbt', '--qbit-tag', dest='qbit_tag', nargs='*', required=False, help="Add to qbit with this tag")
        parser.add_argument('-qbc', '--qbit-cat', dest='qbit_cat', nargs='*', required=False, help="Add to qbit with this category")
        parser.add_argument('-rtl', '--rtorrent-label', dest='rtorrent_label', nargs='*', required=False, help="Add to rtorrent with this label")
        parser.add_argument('-tk', '--trackers', nargs='*', required=False, help="Upload to these trackers, space seperated (--trackers blu bhd)")
        parser.add_argument('-rt', '--randomized', nargs='*', required=False, help="Number of extra, torrents with random infohash", default=0)
        parser.add_argument('-ua', '--unattended', action='store_true', required=False, help=argparse.SUPPRESS)
        parser.add_argument('-vs', '--vapoursynth', action='store_true', required=False, help="Use vapoursynth for screens (requires vs install)")
        parser.add_argument('-cleanup', '--cleanup', action='store_true', required=False, help="Clean up tmp directory")

        parser.add_argument('-fl', '--freeleech', nargs='*', required=False, help="Freeleech Percentage", default=0, dest="freeleech")
        args, before_args = parser.parse_known_args(input)
        args = vars(args)
        # console.print(args)
        if len(before_args) >= 1 and not os.path.exists(' '.join(args['path'])):
            for each in before_args:
                args['path'].append(each)
                if os.path.exists(' '.join(args['path'])):
                    if any(".mkv" in x for x in before_args):
                        if ".mkv" in ' '.join(args['path']):
                            break
                    else:
                        break
        
        if meta.get('tmdb_manual') != None or meta.get('imdb') != None:
            meta['tmdb_manual'] = meta['imdb'] = None
        for key in args:
            value = args.get(key)
            if value not in (None, []):
                if isinstance(value, list):
                    value2 = self.list_to_string(value)
                    if key == 'type':
                        meta[key] = value2.upper().replace('-','')
                    elif key == 'tag':
                        meta[key] = f"-{value2}"
                    elif key == 'screens':
                        meta[key] = int(value2)
                    elif key == 'season':
                        meta['manual_season'] = value2
                    elif key == 'episode':
                        meta['manual_episode'] = value2
                    elif key == 'manual_date':
                        meta['manual_date'] = value2
                    elif key == 'tmdb_manual':
                        meta['category'], meta['tmdb_manual'] = self.parse_tmdb_id(value2, meta.get('category'))
                    elif key == 'ptp':
                        if value2.startswith('http'):
                            parsed = urllib.parse.urlparse(value2)
                            try:
                                meta['ptp'] = urllib.parse.parse_qs(parsed.query)['torrentid'][0]
                            except:
                                console.print('[red]Your terminal ate  part of the url, please surround in quotes next time, or pass only the torrentid')
                                console.print('[red]Continuing without -ptp')
                        else:
                            meta['ptp'] = value2
                    elif key == 'blu':
                        if value2.startswith('http'):
                            parsed = urllib.parse.urlparse(value2)
                            try:
                                blupath = parsed.path
                                if blupath.endswith('/'):
                                    blupath = blupath[:-1]
                                meta['blu'] = blupath.split('/')[-1]
                            except:
                                console.print('[red]Unable to parse id from url')
                                console.print('[red]Continuing without --blu')
                        else:
                            meta['blu'] = value2
                    elif key == 'hdb':
                        if value2.startswith('http'):
                            parsed = urllib.parse.urlparse(value2)
                            try:
                                meta['hdb'] = urllib.parse.parse_qs(parsed.query)['id'][0]
                            except:
                                console.print('[red]Your terminal ate  part of the url, please surround in quotes next time, or pass only the torrentid')
                                console.print('[red]Continuing without -hdb')
                        else:
                            meta['hdb'] = value2

                    else:
                        meta[key] = value2
                else:
                    meta[key] = value
            elif key in ("manual_edition"):
                meta[key] = value
            elif key in ("freeleech"):
                meta[key] = 100
            elif key in ("tag") and value == []:
                meta[key] = ""
            else:
                meta[key] = meta.get(key, None)
            if key in ('trackers'):
                meta[key] = value
            # if key == 'help' and value == True:
                # parser.print_help()
        return meta, parser, before_args


    def list_to_string(self, list):
        if len(list) == 1:
            return str(list[0])
        try:
            result = " ".join(list)
        except:
            result = "None"
        return result


    def parse_tmdb_id(self, id, category):
        id = id.lower().lstrip()
        if id.startswith('tv'):
            id = id.split('/')[1]
            category = 'TV'
        elif id.startswith('movie'):
            id = id.split('/')[1]
            category = 'MOVIE'
        else:
            id = id
        return category, id















