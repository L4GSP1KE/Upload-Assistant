# -*- coding: utf-8 -*-
import argparse
from pprint import pprint
import time
from termcolor import cprint
import traceback


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
        
        parser.add_argument('-s', '--screens', nargs='*', required=False, help="Number of screenshots", default=int(self.config['DEFAULT']['screens']))
        parser.add_argument('-c', '--category', nargs='*', required=False, help="Category [MOVIE, TV, FANRES]", choices=['movie', 'tv', 'fanres'])
        parser.add_argument('-t', '--type', nargs='*', required=False, help="Type [DISC, REMUX, ENCODE, WEBDL, WEBRIP, HDTV]", choices=['disc', 'remux', 'encode', 'webdl', 'web-dl', 'webrip', 'hdtv'])
        parser.add_argument('-res', '--resolution', nargs='*', required=False, help="Resolution [2160p, 1080p, 1080i, 720p, 576p, 576i, 480p, 480i, 8640p, 4320p, OTHER]", choices=['2160p', '1080p', '1080i', '720p', '576p', '576i', '480p', '480i', '8640p', '4320p', 'other'])
        parser.add_argument('-tmdb', '--tmdb', nargs='*', required=False, help="TMDb ID", type=str)
        parser.add_argument('-imdb', '--imdb', nargs='*', required=False, help="IMDb ID", type=str)
        parser.add_argument('-g', '--tag', nargs='?', required=False, help="Group Tag", type=str)
        parser.add_argument('-serv', '--service', nargs='*', required=False, help="Streaming Service", type=str)
        parser.add_argument('-edition', '--edition', nargs='*', required=False, help="Edition", type=str)
        parser.add_argument('-season', '--season', nargs='*', required=False, help="Season (number)", type=str)
        parser.add_argument('-episode', '--episode', nargs='*', required=False, help="Episode (number)", type=str)
        parser.add_argument('-d', '--desc', nargs='*', required=False, help="Custom Description (string)")
        parser.add_argument('-ih', '--imghost', nargs='*', required=False, help="Image Host", choices=['imgbb', 'ptpimg', 'freeimage.host', 'imgbox'])
        parser.add_argument('-df', '--descfile', nargs='*', required=False, help="Custom Description (path to file)")
        parser.add_argument('-hb', '--desclink', nargs='*', required=False, help="Custom Description (link to hastebin)")
        parser.add_argument('-nfo', '--nfo', action='store_true', required=False, help="Use .nfo in directory for description")
        parser.add_argument('-k', '--keywords', nargs='*', required=False, help="Add comma seperated keywords e.g. 'keyword, keyword2, etc'")
        parser.add_argument('-reg', '--region', nargs='*', required=False, help="Region for discs")
        parser.add_argument('-a', '--anon', action='store_true', required=False, help="Upload anonymously")
        parser.add_argument('-st', '--stream', action='store_true', required=False, help="Stream Optimized Upload")
        parser.add_argument('-dupe', '--dupe', action='store_true', required=False, help="Pass if you know this is a dupe")
        parser.add_argument('-debug', '--debug', action='store_true', required=False, help="Debug Mode, will run through all the motions providing extra info, but will not upload to trackers.")
        parser.add_argument('-m', '--manual', action='store_true', required=False, help="Manual Mode. Returns link to ddl screens/base.torrent")
        parser.add_argument('-nh', '--nohash', action='store_true', required=False, help="Don't hash .torrent")
        parser.add_argument('-dr', '--draft', action='store_true', required=False, help="Send to drafts (BHD)")
        parser.add_argument('-client', '--client', nargs='*', required=False, help="Use this torrent client instead of default")
        parser.add_argument('-tk', '--trackers', nargs='*', required=False, help="Upload to these trackers")
        parser.add_argument('-ua', '--unattended', action='store_true', required=False, help=argparse.SUPPRESS)
        
        args, before_args = parser.parse_known_args(input)
        args = vars(args)

        for key in args:
            value = args.get(key)
            if value != None:
                # if type(value) == str:
                #     while value.startswith(" "):
                #         value = value[1:]
                if isinstance(value, list):
                    meta[key] = self.list_to_string(value)
                    if key == 'type':
                        meta[key] = meta[key].upper().replace('-','')
                    elif key == 'tag':
                        meta[key] = f"-{meta[key]}"
                    elif key == 'screens':
                        meta[key] = int(meta[key])
                    elif key == 'season':
                        meta['manual_season'] = meta[key]
                    elif key == 'episode':
                        meta['manual_episode'] = meta[key]
                    elif key == 'tmdb':
                        meta['category'], meta['tmdb'] = self.parse_tmdb_id(meta[key], meta.get('category'))
                else:
                    meta[key] = value
            else:
                meta[key] = meta.get(key, None)
            if key == 'trackers':
                meta[key] = value
            # if key == 'help' and value == True:
            #     parser.print_help()
        
        return meta, parser, before_args


    def list_to_string(self, list):
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















