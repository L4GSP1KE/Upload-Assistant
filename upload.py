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
    prep = Prep(path=path, screens=meta['screens'], config=config)
    meta = await prep.gather_prep(meta=meta) 
    meta['name_notag'], meta['name'], meta['clean_name'] = await prep.get_name(meta)

    if meta.get('uploaded_screens', False) == False:
        prep.upload_screens(meta, meta['screens'], 1, 1)
        meta['uploaded_screens'] = True

    if len(glob(f"{meta['base_dir']}/tmp/{meta['uuid']}/BASE.torrent")) == 0:
        prep.create_torrent(meta, Path(meta['path']))
           

    confirm = get_confirmation(meta)
    while confirm == False:
        # help.print_help()
        args = cli_ui.ask_string("Input args that need correction e.g.(--tag NTb --category tv)")

        meta, help = parser.parse(args.split(), meta)
        meta = await prep.tmdb_other_meta(meta)
        meta['name_notag'], meta['name'], meta['clean_name'] = await prep.get_name(meta)
        confirm = get_confirmation(meta)
    
    trackers = ['BLU']
    for tracker in trackers:
        if tracker == "BLU":
            if cli_ui.ask_yes_no("Upload to BLU?", default=False):
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
    print()
    cli_ui.info_section(cli_ui.yellow, "Is this correct?")
    cli_ui.info(f"Name: {meta['name']}")
    confirm = cli_ui.ask_yes_no("Correct?", default=False)
    return confirm

def dupe_check(dupes, meta):
    if not dupes:
            cprint("No dupes found", 'grey', 'on_green')
            meta['upload'] = True   
            return meta
    else:
        dupe_text = "\n•".join(dupes)
        dupe_text = f"```{dupe_text}```"
        print()
        cli_ui.info_section(cli_ui.yellow, "Are these dupes?")
        cli_ui.info(dupe_text)
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
        