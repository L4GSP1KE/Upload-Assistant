from requests import NullHandler
from src.args import Args
from src.clients import Clients
from src.prep import Prep
from src.search import Search
from src.trackers.BLU import BLU
from src.trackers.BHD import BHD
from src.trackers.THR import THR

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
with open(f"{base_dir}/data/config.json", 'r', encoding="utf-8-sig") as f:
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
    meta, help, before_args = parser.parse("", dict())
    help.print_help()
    exit()
cli_ui.setup(color='always', title="L4G's Upload Assistant")

async def do_the_thing(path, args, base_dir):
    meta = dict()
    meta['base_dir'] = base_dir
    path = os.path.abspath(path)
    if os.path.exists(path):
            meta['path'] = path
            meta, help, before_args = parser.parse(args, meta)
    else:
        cprint("Path does not exist", 'grey', 'on_red')
        exit()
    if meta['imghost'] == None:
        meta['imghost'] = config['DEFAULT']['img_host_1']
    if not meta['unattended']:
        ua = config['DEFAULT'].get('auto_mode', False)
        if str(ua).lower() == "true":
            meta['unattended'] = True
            cprint("Running in Auto Mode", 'yellow')
    
    
    
    prep = Prep(path=path, screens=meta['screens'], img_host=meta['imghost'], config=config)
    meta = await prep.gather_prep(meta=meta, mode='cli') 
    meta['name_notag'], meta['name'], meta['clean_name'], meta['potential_missing'] = await prep.get_name(meta)

    if meta.get('image_list', False) == False:
        return_dict = {}
        meta['image_list'], dummy_var = prep.upload_screens(meta, meta['screens'], 1, 0, return_dict)
        if meta['debug']:
            pprint(meta['image_list'])
        # meta['uploaded_screens'] = True

    if len(glob(f"{meta['base_dir']}/tmp/{meta['uuid']}/BASE.torrent")) == 0:
        if meta['nohash'] == False:
            prep.create_torrent(meta, Path(meta['path']))
        else:
            meta['client'] = "none"
           
    if meta.get('trackers', None) != None:
        trackers = meta['trackers']
    else:
        trackers = config['TRACKERS']['default_trackers']
    if "," in trackers:
        trackers = trackers.split(',')
    confirm = get_confirmation(meta)  
    while confirm == False:
        # help.print_help()
        args = cli_ui.ask_string("Input args that need correction e.g.(--tag NTb --category tv)")

        meta, help, before_args = parser.parse(args.split(), meta)
        # meta = await prep.tmdb_other_meta(meta)
        meta['edit'] = True
        meta = await prep.gather_prep(meta=meta, mode='cli') 
        meta['name_notag'], meta['name'], meta['clean_name'], meta['potential_missing'] = await prep.get_name(meta)
        confirm = get_confirmation(meta)
    
    if isinstance(trackers, list) == False:
        trackers = [trackers]
    if meta.get('manual', False):
        trackers.insert(0, "MANUAL")
    

    for tracker in trackers:
        tracker = tracker.replace(" ", "")
        if meta['debug']:
            debug = "(DEBUG)"
        else:
            debug = ""
        
        if tracker.upper() == "MANUAL":
            do_manual = cli_ui.ask_yes_no(f"Get files for manual upload?", default=True)
            if do_manual:
                for manual_tracker in trackers:
                    manual_tracker = manual_tracker.replace(" ", "")
                    if manual_tracker.upper() == "BLU":
                        blu = BLU(config=config) 
                        await blu.edit_desc(meta)
                    if manual_tracker.upper() == "BHD":
                        bhd = BHD(config=config)
                        await bhd.edit_desc(meta)       
                url = await prep.package(meta)
                if url == False:
                    cprint(f"Unable to upload prep files, they can be found at `tmp/{meta['title']}-{meta['uuid']}.tar", 'grey', 'on_yellow')
                else:
                    cprint(meta['name'], 'grey', 'on_green')
                    cprint(f"Files can be found at {url} or `tmp/{meta['title']}-{meta['uuid']}.tar`", 'grey', 'on_green')  
        if tracker.upper() == "BLU":
            if meta['unattended']:
                upload_to_blu = True
            else:
                upload_to_blu = cli_ui.ask_yes_no(f"Upload to BLU? {debug}", default=meta['unattended'])
            if upload_to_blu:
                print("Uploading to BLU")
                blu = BLU(config=config)
                dupes = await blu.search_existing(meta)
                meta = dupe_check(dupes, meta)
                if meta['upload'] == True:
                    await blu.upload(meta)
                    await client.add_to_client(meta, "BLU")
        if tracker.upper() == "BHD":
            bhd = BHD(config=config)
            draft_int = await bhd.get_live(meta)
            if draft_int == 0:
                draft = "Draft"
            else:
                draft = "Live"
            if meta['unattended']:
                upload_to_bhd = True
            else:
                upload_to_bhd = cli_ui.ask_yes_no(f"Upload to BHD? ({draft}) {debug}", default=meta['unattended'])
            if upload_to_bhd:
                print("Uploading to BHD")
                dupes = await bhd.search_existing(meta)
                meta = dupe_check(dupes, meta)
                if meta['upload'] == True:
                    await bhd.upload(meta)
                    await client.add_to_client(meta, "BHD")
        if tracker.upper() == "THR":
            if meta['unattended']:
                upload_to_thr = True
            else:
                upload_to_thr = cli_ui.ask_yes_no(f"Upload to THR? {debug}", default=meta['unattended'])
            if upload_to_thr:
                print("Uploading to THR")
                thr = THR(config=config)
                #Unable to get IMDB id/Youtube Link
                if meta.get('imdb_id', '0') == '0':
                    imdb_id = cli_ui.ask_string("Unable to find IMDB id, please enter e.g.(tt1234567)")
                    meta['imdb'] = imdb_id.replace('tt', '')
                if meta.get('youtube', None) == None:
                    youtube = cli_ui.ask_string("Unable to find youtube trailer, please link one e.g.(https://www.youtube.com/watch?v=dQw4w9WgXcQ)")
                    meta['youtube'] = youtube
                # try:
                cprint("Logging in to THR", 'grey', 'on_yellow')
                thr_browser = await thr.login_and_get_cookies(meta)
                cprint("Searching for Dupes", 'grey', 'on_yellow')
                dupes = thr.search_existing(meta.get('imdb_id'), thr_browser)
                meta = dupe_check(dupes, meta)
                if meta['upload'] == True:
                    await thr.upload(meta, thr_browser)
                    await client.add_to_client(meta, "THR")
                else:
                    thr_browser.close()
                # except:
                #     try:
                #         thr_browser.close()
                #     except:
                #         pass
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
    cli_ui.info(f"Category: {meta['category']}")
    cli_ui.info(f"TMDb: {meta['tmdb']}")
    cli_ui.info(f"IMDb: {meta['imdb_id']}")
    cli_ui.info(f"TVDb: {meta['tvdb_id']}")
    print()
    if meta['tag'] == "":
            tag = ""
    else:
        tag = f" / {meta['tag'][1:]}"
    if meta['is_disc'] == "DVD":
        res = meta['source']
    else:
        res = meta['resolution']

    cli_ui.info(f"{res} / {meta['type']}{tag}")
    print()
    if meta.get('unattended', False) == False:
        get_missing(meta)
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
        print()    
        dupe_text = "\n".join(dupes)
        print()
        cli_ui.info_section(cli_ui.bold, "Are these dupes?")
        cli_ui.info(dupe_text)
        if meta['unattended']:
            if meta.get('dupe', False) == False:
                cprint("Found potential dupes. Aborting. If this is not a dupe, or you would like to upload anyways, pass --dupe", 'grey', 'on_red')
                exit()
            else:
                cprint("Found potential dupes. -dupe/--dupe was passed. Uploading anyways", 'grey', 'on_yellow')
                upload = True
        print()
        if not meta['unattended']:
            upload = cli_ui.ask_yes_no("Upload Anyways?", default=False)

        if upload == False:
            meta['upload'] = False
        else:
            meta['upload'] = True
            for each in dupes:
                if each == meta['name']:
                    meta['name'] = f"{meta['name']} DUPE?"

        return meta

def get_missing(meta):
    info_notes = {
        'edition' : 'Special Edition/Release',
        'description' : "Please include Remux/Encode Notes if possible (either here or edit your upload)",
        'service' : "WEB Service e.g.(AMZN, NF)",
        'region' : "Disc Region",
    }

    if len(meta['potential_missing']) > 0:
        cli_ui.info_section(cli_ui.yellow, "Potentially missing information:")
        for each in meta['potential_missing']:
            if meta.get(each, '').replace(' ', '') == "": 
                cli_ui.info(f"--{each} | {info_notes.get(each)}")
    print()
    return

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(do_the_thing(path, args, base_dir))
        