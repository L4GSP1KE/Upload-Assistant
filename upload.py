from requests import NullHandler
from src.args import Args
from src.clients import Clients
from src.prep import Prep
from src.search import Search
from src.trackers.BLU import BLU
from src.trackers.BHD import BHD
from src.trackers.AITHER import AITHER
from src.trackers.STC import STC
import json
from termcolor import cprint
from pathlib import Path
import asyncio
import os
import sys
import platform
import multiprocessing
import logging
from glob import glob
import cli_ui
cli_ui.setup(color='always', title="L4G's Upload Assistant")
from pprint import pprint
import traceback

base_dir = os.path.abspath(os.path.dirname(__file__))

try:
    from data.config import config
except:
    try:
        if os.path.exists(os.path.abspath(f"{base_dir}/data/config.json")):
            with open(f"{base_dir}/data/config.json", 'r', encoding='utf-8-sig') as f:
                json_config = json.load(f)
                f.close()
            with open(f"{base_dir}/data/config.py", 'w') as f:
                f.write(f"config = {json.dumps(json_config, indent=4)}")
                f.close()
            cli_ui.info(cli_ui.green, "Successfully updated config from .json to .py")    
            cli_ui.info(cli_ui.green, "It is now safe for you to delete", cli_ui.yellow, "data/config.json", "if you wish")    
            from data.config import config
        else:
            raise NotImplementedError
    except:
        cli_ui.info(cli_ui.red, "We have switched from .json to .py for config to have a much more lenient experience")
        cli_ui.info(cli_ui.red, "Looks like the auto updater didnt work though")
        cli_ui.info(cli_ui.red, "Updating is just 2 easy steps:")
        cli_ui.info(cli_ui.red, "1: Rename", cli_ui.yellow, "data/config.json", cli_ui.red, "to", cli_ui.green, "data/config.py" )
        cli_ui.info(cli_ui.red, "2: Add", cli_ui.green, "config = ", cli_ui.red, "to the beginning of", cli_ui.green, "data/config.py")
        exit()
    
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

async def do_the_thing(path, args, base_dir):
    meta = dict()
    meta['base_dir'] = base_dir
    path = os.path.abspath(path)
    try:
        with open(f"{base_dir}/tmp/{os.path.basename(path)}/meta.json") as f:
            meta = json.load(f)
            f.close()
    except FileNotFoundError:
        pass
    if os.path.exists(path):
            meta['path'] = path
            meta, help, before_args = parser.parse(args, meta)
    else:
        cprint("Path does not exist", 'grey', 'on_red')
        exit()
    cprint(f"Gathering info for {os.path.basename(path)}", 'grey', 'on_green')
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
        meta['image_list'], dummy_var = prep.upload_screens(meta, meta['screens'], 1, 0, meta['screens'], return_dict)
        if meta['debug']:
            pprint(meta['image_list'])
        # meta['uploaded_screens'] = True

    if not os.path.exists(os.path.abspath(f"{meta['base_dir']}/tmp/{meta['uuid']}/BASE.torrent")):
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
    with open (f"{meta['base_dir']}/tmp/{meta['uuid']}/meta.json", 'w') as f:
        json.dump(meta, f, indent=4)
        f.close()
    confirm = get_confirmation(meta)  
    while confirm == False:
        # help.print_help()
        args = cli_ui.ask_string("Input args that need correction e.g.(--tag NTb --category tv --tmdb 12345)")

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
                    if manual_tracker.upper() == "AITHER":
                        aither = AITHER(config=config)
                        await aither.edit_desc(meta)    
                    if manual_tracker.upper() == "STC":
                        stc = STC(config=config)
                        await aither.edit_desc(meta)    
                    if manual_tracker.upper() == "THR":
                        from src.trackers.THR import THR
                        thr = THR(config=config)
                        await thr.edit_desc(meta)
                url = await prep.package(meta)
                if url == False:
                    cprint(f"Unable to upload prep files, they can be found at `tmp/{meta['uuid']}", 'grey', 'on_yellow')
                else:
                    cprint(meta['name'], 'grey', 'on_green')
                    cprint(f"Files can be found at {url}", 'grey', 'on_green')  
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
        if tracker.upper() == "AITHER":
            if meta['unattended']:
                upload_to_aither = True
            else:
                upload_to_aither = cli_ui.ask_yes_no(f"Upload to Aither? {debug}", default=meta['unattended'])
            if upload_to_aither:
                print("Uploading to Aither")
                aither = AITHER(config=config)
                dupes = await aither.search_existing(meta)
                meta = dupe_check(dupes, meta)
                if meta['upload'] == True:
                    await aither.upload(meta)
                    await client.add_to_client(meta, "AITHER")
        if tracker.upper() == "STC":
            if meta['unattended']:
                upload_to_stc = True
            else:
                upload_to_stc = cli_ui.ask_yes_no(f"Upload to STC? {debug}", default=meta['unattended'])
            if upload_to_stc:
                print("Uploading to STC")
                stc = STC(config=config)
                dupes = await stc.search_existing(meta)
                meta = dupe_check(dupes, meta)
                if meta['upload'] == True:
                    await stc.upload(meta)
                    await client.add_to_client(meta, "STC")
        if tracker.upper() == "THR":
            if meta['unattended']:
                upload_to_thr = True
            else:
                upload_to_thr = cli_ui.ask_yes_no(f"Upload to THR? {debug}", default=meta['unattended'])
            if upload_to_thr:
                print("Uploading to THR")
                #Unable to get IMDB id/Youtube Link
                if meta.get('imdb_id', '0') == '0':
                    imdb_id = cli_ui.ask_string("Unable to find IMDB id, please enter e.g.(tt1234567)")
                    meta['imdb'] = imdb_id.replace('tt', '')
                if meta.get('youtube', None) == None:
                    youtube = cli_ui.ask_string("Unable to find youtube trailer, please link one e.g.(https://www.youtube.com/watch?v=dQw4w9WgXcQ)")
                    meta['youtube'] = youtube
                from src.trackers.THR import THR
                thr = THR(config=config)
                try:
                    cprint("Logging in to THR", 'grey', 'on_yellow')
                    thr_browser = await thr.login_and_get_cookies(meta)
                    cprint("Searching for Dupes", 'grey', 'on_yellow')
                    dupes = thr.search_existing(meta.get('imdb_id'), thr_browser)
                    meta = dupe_check(dupes, meta)
                    if meta['upload'] == True:
                        await thr.upload(meta, thr_browser)
                        await client.add_to_client(meta, "THR")
                        thr_browser.close()
                    else:
                        thr_browser.close()
                except:
                    print(traceback.format_exc())
                    try:
                        thr_browser.close()
                    except:
                        pass
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
        'imdb' : 'IMDb ID (tt1234567)',
        'distributor' : "Disc Distributor e.g.(BFI, Criterion, etc)"
    }
    missing = []
    if meta.get('imdb_id', '0') == '0':
        meta['imdb_id'] = '0'
        meta['potential_missing'].append('imdb_id')
    if len(meta['potential_missing']) > 0:
        for each in meta['potential_missing']:
            if str(meta.get(each, '')).replace(' ', '') in ["", "None", "0"]:
                if each == "imdb_id":
                    each = 'imdb' 
                missing.append(f"--{each} | {info_notes.get(each)}")
    if missing != []:
        cli_ui.info_section(cli_ui.yellow, "Potentially missing information:")
        for each in missing:
            cli_ui.info(each)

    print()
    return

if __name__ == '__main__':
    pyver = platform.python_version_tuple()
    if int(pyver[0]) != 3:
        cprint("Python2 Detected, please use python3")
        exit()
    else:
        if int(pyver[1]) <= 6:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(do_the_thing(path, args, base_dir))
        else:
            asyncio.run(do_the_thing(path, args, base_dir))
        