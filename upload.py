from argparse import ArgumentParser
import requests
from src.trackers.RF import RF
from src.args import Args
from src.clients import Clients
from src.prep import Prep
from src.search import Search
from src.trackers.COMMON import COMMON
from src.trackers.BLU import BLU
from src.trackers.BHD import BHD
from src.trackers.AITHER import AITHER
from src.trackers.STC import STC
from src.trackers.R4E import R4E
from src.trackers.THR import THR
from src.trackers.STT import STT
from src.trackers.HP import HP
from src.trackers.PTP import PTP
from src.trackers.SN import SN
from src.trackers.ACM import ACM
from src.trackers.HDB import HDB
from src.trackers.LCD import LCD
import json
from termcolor import cprint
from pathlib import Path
import asyncio
import os
import sys
import platform
import multiprocessing
import logging
import glob
import cli_ui

from rich.console import Console
from rich.markdown import Markdown
from rich.style import Style
from rich import print

console = Console()
cli_ui.setup(color='always', title="L4G's Upload Assistant")
from pprint import pprint
import traceback

base_dir = os.path.abspath(os.path.dirname(__file__))

try:
    from data.config import config
except:
    if not os.path.exists(os.path.abspath(f"{base_dir}/data/config.py")):
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
    else:
        print(traceback.print_exc())
client = Clients(config=config)
parser = Args(config)

async def do_the_thing(base_dir):
    meta = dict()
    meta['base_dir'] = base_dir
    paths = []
    for each in sys.argv[1:]:
        if os.path.exists(each):
            paths.append(each)
        else:
            break
    meta, help, before_args = parser.parse(tuple(' '.join(sys.argv[1:]).split(' ')), meta)
    path = meta['path']
    path = os.path.abspath(path)
    if path.endswith('"'):
        path = path[:-1]
    queue = []
    if os.path.exists(path):
            meta, help, before_args = parser.parse(tuple(' '.join(sys.argv[1:]).split(' ')), meta)
            queue = [path]
    else:
        # Search glob if dirname exists
        if os.path.exists(os.path.dirname(path)):
            escaped_path = path.replace('[', '[[]')
            globs = glob.glob(escaped_path)
            queue = globs
            md_text = "\n - ".join(queue)
            print("\n[bold green]Queuing these files:[/bold green]", end='')
            print(Markdown(f"- {md_text.rstrip()}\n\n", style=Style(color='cyan')))
            print("\n\n")
        elif len(paths) != 1:
            queue = paths
            md_text = "\n - ".join(queue)
            print("\n[bold green]Queuing these files:[/bold green]", end='')
            print(Markdown(f"- {md_text.rstrip()}\n\n", style=Style(color='cyan')))
            print("\n\n")
        else:
            # Add Search Here
            cprint(f"Path: {path} does not exist", 'grey', 'on_red')
            exit()


    base_meta = meta
    for path in queue:
        meta = base_meta
        meta['path'] = path
        try:
            with open(f"{base_dir}/tmp/{os.path.basename(path)}/meta.json") as f:
                meta = json.load(f)
                f.close()
        except FileNotFoundError:
            pass
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
            meta['image_list'], dummy_var = prep.upload_screens(meta, meta['screens'], 1, 0, meta['screens'],[], return_dict)
            if meta['debug']:
                pprint(meta['image_list'])
            # meta['uploaded_screens'] = True

        if meta.get('torrenthash', None) != None or meta.get('ext_torrenthash', None) != None:
            if meta.get('rehash', False) == False:
                reuse_torrent = await client.find_existing_torrent(meta)
                if reuse_torrent != None:
                    prep.create_base_from_existing_torrent(reuse_torrent, meta['base_dir'], meta['uuid'])

        if not os.path.exists(os.path.abspath(f"{meta['base_dir']}/tmp/{meta['uuid']}/BASE.torrent")):
            if meta['nohash'] == False:
                prep.create_torrent(meta, Path(meta['path']))
            else:
                meta['client'] = "none"
        if int(meta.get('randomized', 0)) >= 1:
            prep.create_random_torrents(meta['base_dir'], meta['uuid'], meta['randomized'], meta['path'])
            
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
            editargs = cli_ui.ask_string("Input args that need correction e.g.(--tag NTb --category tv --tmdb 12345)")
            editargs = (meta['path'],) + tuple(editargs.split())
            if meta['debug']:
                editargs = editargs + ("--debug",)
            meta, help, before_args = parser.parse(editargs, meta)
            # meta = await prep.tmdb_other_meta(meta)
            meta['edit'] = True
            meta = await prep.gather_prep(meta=meta, mode='cli') 
            meta['name_notag'], meta['name'], meta['clean_name'], meta['potential_missing'] = await prep.get_name(meta)
            confirm = get_confirmation(meta)
        
        if isinstance(trackers, list) == False:
            trackers = [trackers]
        trackers = [s.strip().upper() for s in trackers]
        if meta.get('manual', False):
            trackers.insert(0, "MANUAL")
        


        ####################################
        #######  Upload to Trackers  #######
        ####################################
        common = COMMON(config=config)
        unit3d_trackers = ['BLU', 'AITHER', 'STC', 'R4E', 'STT', 'RF', 'ACM','LCD']
        tracker_class_map = {'BLU' : BLU, 'BHD': BHD, 'AITHER' : AITHER, 'STC' : STC, 'R4E' : R4E, 'THR' : THR, 'STT' : STT, 'HP' : HP, 'PTP' : PTP, 'RF' : RF, 'SN' : SN, 'ACM' : ACM, 'HDB' : HDB,'LCD':LCD}

        for tracker in trackers:
            tracker = tracker.replace(" ", "").upper().strip()
            if meta['debug']:
                debug = "(DEBUG)"
            else:
                debug = ""
            
            if tracker in unit3d_trackers:
                tracker_class = tracker_class_map[tracker](config=config)
                if meta['unattended']:
                    upload_to_tracker = True
                else:
                    upload_to_tracker = cli_ui.ask_yes_no(f"Upload to {tracker_class.tracker}? {debug}", default=meta['unattended'])
                if upload_to_tracker:
                    print(f"Uploading to {tracker_class.tracker}")
                    dupes = await tracker_class.search_existing(meta)
                    meta = dupe_check(dupes, meta)
                    if meta['upload'] == True:
                        await tracker_class.upload(meta)
                        await client.add_to_client(meta, tracker_class.tracker)
            
            if tracker == "MANUAL":
                if meta['unattended']:                
                    do_manual = True
                else:
                    do_manual = cli_ui.ask_yes_no(f"Get files for manual upload?", default=True)
                if do_manual:
                    for manual_tracker in trackers:
                        if manual_tracker != 'MANUAL':
                            manual_tracker = manual_tracker.replace(" ", "").upper().strip()
                            tracker_class = tracker_class_map[manual_tracker](config=config)
                            if manual_tracker in unit3d_trackers:
                                await common.unit3d_edit_desc(meta, tracker_class.tracker, tracker_class.signature)
                            else:
                                await tracker_class.edit_desc(meta)
                    url = await prep.package(meta)
                    if url == False:
                        cprint(f"Unable to upload prep files, they can be found at `tmp/{meta['uuid']}", 'grey', 'on_yellow')
                    else:
                        cprint(meta['name'], 'grey', 'on_green')
                        cprint(f"Files can be found at {url}", 'grey', 'on_green')  

            if tracker == "BHD":
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
            
            if tracker == "THR":
                if meta['unattended']:
                    upload_to_thr = True
                else:
                    upload_to_thr = cli_ui.ask_yes_no(f"Upload to THR? {debug}", default=meta['unattended'])
                if upload_to_thr:
                    print("Uploading to THR")
                    #Unable to get IMDB id/Youtube Link
                    if meta.get('imdb_id', '0') == '0':
                        imdb_id = cli_ui.ask_string("Unable to find IMDB id, please enter e.g.(tt1234567)")
                        meta['imdb_id'] = imdb_id.replace('tt', '').zfill(7)
                    if meta.get('youtube', None) == None:
                        youtube = cli_ui.ask_string("Unable to find youtube trailer, please link one e.g.(https://www.youtube.com/watch?v=dQw4w9WgXcQ)")
                        meta['youtube'] = youtube
                    thr = THR(config=config)
                    try:
                        with requests.Session() as session:
                            cprint("Logging in to THR", 'grey', 'on_yellow')
                            session = thr.login(session)
                            cprint("Searching for Dupes", 'grey', 'on_yellow')
                            dupes = thr.search_existing(session, meta.get('imdb_id'))
                            meta = dupe_check(dupes, meta)
                            if meta['upload'] == True:
                                await thr.upload(session, meta)
                                await client.add_to_client(meta, "THR")
                    except:
                        print(traceback.print_exc())

            if tracker == "SN":
                if meta['unattended']:
                    upload_to_sn = True
                else:
                    upload_to_sn = cli_ui.ask_yes_no(f"Upload to Swarmazon? {debug}", default=meta['unattended'])
                if upload_to_sn:
                    print("Uploading to Swarmazon")
                    sn = SN(config=config)
                    cprint("Dupe Search on Swarmazon, Currently not supported so assuming no Dupes", 'grey', 'on_red')
                    meta['upload'] = True
                    if meta['upload'] == True:
                        await sn.upload(meta)
                        await client.add_to_client(meta, "SN")

            if tracker == "PTP":
                if meta['unattended']:
                    upload_to_ptp = True
                else:
                    upload_to_ptp = cli_ui.ask_yes_no(f"Upload to {tracker}? {debug}", default=meta['unattended'])
                if upload_to_ptp:
                    print(f"Uploading to {tracker}")
                    if meta.get('imdb_id', '0') == '0':
                        imdb_id = cli_ui.ask_string("Unable to find IMDB id, please enter e.g.(tt1234567)")
                        meta['imdb_id'] = imdb_id.replace('tt', '').zfill(7)
                    ptp = PTP(config=config)
                    try:
                        cprint("Searching for Group ID", 'grey', 'on_yellow')
                        groupID = await ptp.get_group_by_imdb(meta['imdb_id'])
                        if groupID == None:
                            cprint("No Existing Group found", 'grey', 'on_yellow')
                            if meta.get('youtube', None) == None or "youtube" not in str(meta.get('youtube', '')):
                                youtube = cli_ui.ask_string("Unable to find youtube trailer, please link one e.g.(https://www.youtube.com/watch?v=dQw4w9WgXcQ)", default="")
                                meta['youtube'] = youtube
                            meta['upload'] = True
                        else:
                            cprint("Searching for Existing Releases", 'grey', 'on_yellow')
                            dupes = await ptp.search_existing(groupID, meta)
                            meta = dupe_check(dupes, meta)
                        if meta.get('imdb_info', {}) == {}:
                            meta['imdb_info'] = await prep.get_imdb_info(meta['imdb_id'], meta)
                        if meta['upload'] == True:
                            ptpUrl, ptpData = await ptp.fill_upload_form(groupID, meta)
                            await ptp.upload(meta, ptpUrl, ptpData)
                            await asyncio.sleep(5)
                            await client.add_to_client(meta, "PTP")
                    except:
                        print(traceback.print_exc())
            
            if tracker == 'HDB':
                if meta['unattended']:
                    upload_to_hdb = True
                else:
                    upload_to_hdb = cli_ui.ask_yes_no(f"Upload to {tracker}? {debug}", default=meta['unattended'])
                if upload_to_hdb:
                    print(f"Uploading to {tracker}")
                    hdb = HDB(config=config)
                    if await hdb.validate_credentials(meta) == True:
                        dupes = await hdb.search_existing(meta)
                        meta = dupe_check(dupes, meta)
                        if meta['upload'] == True:
                            await hdb.upload(meta)
                            await client.add_to_client(meta, hdb.tracker)



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
    if int(meta.get('tmdb', 0)) != 0:
        cli_ui.info(f"TMDB: https://www.themoviedb.org/{meta['category'].lower()}/{meta['tmdb']}")
    if int(meta.get('imdb_id', '0')) != 0:
        cli_ui.info(f"IMDB: https://www.imdb.com/title/tt{meta['imdb_id']}")
    if int(meta.get('tvdb_id', '0')) != 0:
        cli_ui.info(f"TVDB: https://www.thetvdb.com/?id={meta['tvdb_id']}&tab=series")
    if int(meta.get('mal_id', 0)) != 0:
        cli_ui.info(f"MAL : https://myanimelist.net/anime/{meta['mal_id']}")
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
    if meta.get('personalrelease', False) == True:
        cli_ui.info("Personal Release!")
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
            if each.split('|')[0].replace('--', '').strip() in ["imdb"]:
                cli_ui.info(cli_ui.red, each)
            else:
                cli_ui.info(each)

    print()
    return

if __name__ == '__main__':
    pyver = platform.python_version_tuple()
    if int(pyver[0]) != 3:
        cprint("Python2 Detected, please use python3", 'grey', 'on_red')
        exit()
    else:
        if int(pyver[1]) <= 6:
            cprint("Python <= 3.6 Detected, please use Python >=3.7", 'grey', 'on_red')
            loop = asyncio.get_event_loop()
            loop.run_until_complete(do_the_thing(base_dir))
        else:
            asyncio.run(do_the_thing(base_dir))
        
