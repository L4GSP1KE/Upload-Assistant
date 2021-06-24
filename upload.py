from src.args import Args
from src.clients import Clients
from src.prep import Prep
from src.search import Search
from src.trackers.BLU import Blu

import json
from termcolor import cprint
from pathlib import Path
import asyncio
import os
import sys
import multiprocessing
import logging
from glob import glob
import cli_ui
from pprint import pprint

base_dir = os.path.abspath(os.path.dirname(__file__))
with open(f"{base_dir}/data/config.json", 'r', encoding="utf-8") as f:
    config = json.load(f)
    

client = Clients(config=config)
parser = Args(config)
file = sys.argv[0]
path = sys.argv[1]
try:
    args = sys.argv[2:]
except:
    args = []

if path in ['-h', '--help']:
    meta, help = parser.parse("", dict())
    help.print_help()
    exit()


async def do_the_thing(path, args, base_dir):
    meta = dict()
    meta['base_dir'] = base_dir
    path = os.path.abspath(path)
    if os.path.exists(path):
            meta['path'] = path
            meta, help = parser.parse(args, meta)
    else:
        cprint("Path does not exist", 'grey', 'on_red')
    if meta['imghost'] == None:
        meta['imghost'] = config['DEFAULT']['img_host_1']
    if not meta['unattended']:
        ua = config['DEFAULT'].get('auto_mode', False)
        if str(ua).lower() == "true":
            meta['unattended'] = True
            cprint("Running in Auto Mode", 'yellow')
    
    
    
    prep = Prep(path=path, screens=meta['screens'], img_host=meta['imghost'], config=config)
    meta = await prep.gather_prep(meta=meta) 
    meta['name_notag'], meta['name'], meta['clean_name'] = await prep.get_name(meta)

    if meta.get('image_list', False) == False:
        return_dict = {}
        meta['image_list'] = prep.upload_screens(meta, meta['screens'], 1, 1, return_dict)
        if meta['debug']:
            pprint(meta['image_list'])
        # meta['uploaded_screens'] = True

    if len(glob(f"{meta['base_dir']}/tmp/{meta['uuid']}/BASE.torrent")) == 0:
        if meta['nohash'] == False:
            prep.create_torrent(meta, Path(meta['path']))
        else:
            meta['client'] = "none"
           
    if meta.get('manual', False):  
        url = await prep.package(meta)
        if url == False:
            cprint(f"Unable to upload prep files, they can be found at `tmp/{meta['title']}.tar`", 'grey', 'on_yellow')
        else:
            cprint(meta['name'], 'grey', 'on_green')
            cprint(f"Files can be found at {url} or `tmp/{meta['title']}.tar`", 'grey', 'on_green')
        exit()
    confirm = get_confirmation(meta)  
    while confirm == False:
        # help.print_help()
        args = cli_ui.ask_string("Input args that need correction e.g.(--tag NTb --category tv)")

        meta, help = parser.parse(args.split(), meta)
        # meta = await prep.tmdb_other_meta(meta)
        meta['edit'] = True
        meta = await prep.gather_prep(meta=meta) 
        meta['name_notag'], meta['name'], meta['clean_name'] = await prep.get_name(meta)
        confirm = get_confirmation(meta)
    
    trackers = ['BLU']
    for tracker in trackers:
        if tracker == "BLU":
            if meta['unattended']:
                upload_to_blu = True
            else:
                upload_to_blu = cli_ui.ask_yes_no("Upload to BLU?", default=meta['unattended'])
            if upload_to_blu:
                print("Uploading to BLU")
                blu = Blu(config=config)
                dupes = await blu.search_existing(meta)
                meta = dupe_check(dupes, meta)
                if meta['upload'] == True:
                    await blu.upload(meta)
                    await client.add_to_client(meta, "BLU")
        if tracker == "BHD":
            if cli_ui.ask_yes_no("Upload to BHD?", default=False):
                print("BHD support coming soon")



def get_confirmation(meta):
    if meta['debug'] == True:
        cprint("DEBUG: True", 'grey', 'on_red')
    print(f"Prep material saved to {meta['base_dir']}/tmp/{meta['uuid']}")
    print()
    cli_ui.info_section(cli_ui.yellow, "Database Info")
    cli_ui.info(f"Title: {meta['title']} ({meta['year']})")
    print()
    cli_ui.info(f"Overview: {meta['overview']}")
    print()
    cli_ui.info(f"TMDb: {meta['tmdb']}")
    cli_ui.info(f"IMDb: {meta['imdb_id']}")
    cli_ui.info(f"TVDb: {meta['tvdb_id']}")
    print()
    if meta['tag'] == "":
            tag = ""
    else:
        tag = f" / {meta['tag'][1:]}"
    cli_ui.info(f"{meta['resolution']} / {meta['type']}{tag}")
    print()
    if meta.get('unattended', False) == False:
        cli_ui.info_section(cli_ui.yellow, "Is this correct?")
        cli_ui.info(f"Name: {meta['name']}")
        confirm = cli_ui.ask_yes_no("Correct?", default=False)
    else:
        cli_ui.info(f"Name: {meta['name']}")
        confirm = True
    return confirm

def dupe_check(dupes, meta):
    if not dupes:
            cprint("No dupes found", 'grey', 'on_green')
            meta['upload'] = True   
            return meta
    else:    
        dupe_text = "\n•".join(dupes)
        cli_ui.info(dupe_text)

        if meta['unattended']:
            if meta.get('dupe', False) == False:
                cprint("Found potential dupes. Aborting. If this is not a dupe, or you would like to upload anyways, pass --dupe", 'grey', 'on_red')
                exit()
            else:
                cprint("Found potential dupes. -dupe/--dupe was passed. Uploading anyways", 'grey', 'on_yellow')
        print()
        cli_ui.info_section(cli_ui.yellow, "Are these dupes?")
        print()
        upload = cli_ui.ask_yes_no("Upload Anyways?", default=False)

        if upload == False:
            meta['upload'] = False
        else:
            meta['upload'] = True
            for each in dupes:
                if each == meta['name']:
                    meta['name'] = f"{meta['name']} DUPE?"

        return meta



if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(do_the_thing(path, args, base_dir))
        