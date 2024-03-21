# -*- coding: utf-8 -*-
from torf import Torrent
import xmlrpc.client
import bencode
import os
import qbittorrentapi
from deluge_client import DelugeRPCClient, LocalDelugeRPCClient
import base64
from pyrobase.parts import Bunch
import errno
import asyncio
import ssl
import shutil
import time


from src.console import console 



class Clients():
    """
    Add to torrent client
    """
    def __init__(self, config):
        self.config = config
        pass
    

    async def add_to_client(self, meta, tracker):
        torrent_path = f"{meta['base_dir']}/tmp/{meta['uuid']}/[{tracker}]{meta['clean_name']}.torrent"
        if meta.get('no_seed', False) == True:
            console.print(f"[bold red]--no-seed was passed, so the torrent will not be added to the client")
            console.print(f"[bold yellow]Add torrent manually to the client")
            return
        if os.path.exists(torrent_path):
            torrent = Torrent.read(torrent_path)
        else:
            return
        if meta.get('client', None) == None:
            default_torrent_client = self.config['DEFAULT']['default_torrent_client']
        else:
            default_torrent_client = meta['client']
        if meta.get('client', None) == 'none':
            return
        if default_torrent_client == "none":
            return 
        client = self.config['TORRENT_CLIENTS'][default_torrent_client]
        torrent_client = client['torrent_client']
        
        local_path, remote_path = await self.remote_path_map(meta)
        
        console.print(f"[bold green]Adding to {torrent_client}")
        if torrent_client.lower() == "rtorrent":
            self.rtorrent(meta['path'], torrent_path, torrent, meta, local_path, remote_path, client)
        elif torrent_client == "qbit":
            await self.qbittorrent(meta['path'], torrent, local_path, remote_path, client, meta['is_disc'], meta['filelist'], meta)
        elif torrent_client.lower() == "deluge":
            if meta['type'] == "DISC":
                path = os.path.dirname(meta['path'])
            self.deluge(meta['path'], torrent_path, torrent, local_path, remote_path, client, meta)
        elif torrent_client.lower() == "watch":
            shutil.copy(torrent_path, client['watch_folder'])
        return
   
        

    async def find_existing_torrent(self, meta):
        if meta.get('client', None) == None:
            default_torrent_client = self.config['DEFAULT']['default_torrent_client']
        else:
            default_torrent_client = meta['client']
        if meta.get('client', None) == 'none' or default_torrent_client == 'none':
            return None
        client = self.config['TORRENT_CLIENTS'][default_torrent_client]
        torrent_storage_dir = client.get('torrent_storage_dir', None)
        torrent_client = client.get('torrent_client', None).lower()
        if torrent_storage_dir == None and torrent_client != "watch":
            console.print(f'[bold red]Missing torrent_storage_dir for {default_torrent_client}')
            return None
        elif not os.path.exists(str(torrent_storage_dir)) and torrent_client != "watch":
            console.print(f"[bold red]Invalid torrent_storage_dir path: [bold yellow]{torrent_storage_dir}")
        torrenthash = None
        if torrent_storage_dir != None and os.path.exists(torrent_storage_dir):
            if meta.get('torrenthash', None) != None:
                valid, torrent_path = await self.is_valid_torrent(meta, f"{torrent_storage_dir}/{meta['torrenthash']}.torrent", meta['torrenthash'], torrent_client, print_err=True)
                if valid:
                    torrenthash = meta['torrenthash']
            elif meta.get('ext_torrenthash', None) != None:
                valid, torrent_path = await self.is_valid_torrent(meta, f"{torrent_storage_dir}/{meta['ext_torrenthash']}.torrent", meta['ext_torrenthash'], torrent_client, print_err=True)
                if valid:
                    torrenthash = meta['ext_torrenthash']
            if torrent_client == 'qbit' and torrenthash == None and client.get('enable_search') == True:
                torrenthash = await self.search_qbit_for_torrent(meta, client)
                if not torrenthash:
                    console.print("[bold yellow]No Valid .torrent found")
            if not torrenthash:
                return None
            torrent_path = f"{torrent_storage_dir}/{torrenthash}.torrent"
            valid2, torrent_path = await self.is_valid_torrent(meta, torrent_path, torrenthash, torrent_client, print_err=False)
            if valid2:
                return torrent_path
        
        return None


    async def is_valid_torrent(self, meta, torrent_path, torrenthash, torrent_client, print_err=False):
        valid = False
        wrong_file = False
        err_print = ""
        if torrent_client in ('qbit', 'deluge'):
            torrenthash = torrenthash.lower().strip()
            torrent_path = torrent_path.replace(torrenthash.upper(), torrenthash)
        elif torrent_client == 'rtorrent':
            torrenthash = torrenthash.upper().strip()
            torrent_path = torrent_path.replace(torrenthash.upper(), torrenthash)
        if meta['debug']:
            console.log(torrent_path)
        if os.path.exists(torrent_path):
            torrent = Torrent.read(torrent_path)
            # Reuse if disc and basename matches
            if meta.get('is_disc', None) != None:
                torrent_filepath = os.path.commonpath(torrent.files)
                if os.path.basename(meta['path']) in torrent_filepath:
                    valid = True
            # If one file, check for folder
            if len(torrent.files) == len(meta['filelist']) == 1:
                if os.path.basename(torrent.files[0]) == os.path.basename(meta['filelist'][0]):
                    if str(torrent.files[0]) == os.path.basename(torrent.files[0]):
                        valid = True
                else:
                    wrong_file = True
            # Check if number of files matches number of videos
            elif len(torrent.files) == len(meta['filelist']):
                torrent_filepath = os.path.commonpath(torrent.files)
                actual_filepath = os.path.commonpath(meta['filelist'])
                local_path, remote_path = await self.remote_path_map(meta)
                if local_path.lower() in meta['path'].lower() and local_path.lower() != remote_path.lower():
                    actual_filepath = torrent_path.replace(local_path, remote_path)
                    actual_filepath = torrent_path.replace(os.sep, '/')
                if meta['debug']:
                    console.log(f"torrent_filepath: {torrent_filepath}")
                    console.log(f"actual_filepath: {actual_filepath}")
                if torrent_filepath in actual_filepath:
                    valid = True
        else:
            console.print(f'[bold yellow]{torrent_path} was not found')
        if valid:
            if os.path.exists(torrent_path):
                reuse_torrent = Torrent.read(torrent_path)
                if (reuse_torrent.pieces >= 7000 and reuse_torrent.piece_size < 8388608) or (reuse_torrent.pieces >= 4000 and reuse_torrent.piece_size < 4194304): # Allow up to 7k pieces at 8MiB or 4k pieces at 4MiB or less
                    err_print = "[bold yellow]Too many pieces exist in current hash. REHASHING"
                    valid = False
                elif reuse_torrent.piece_size < 32768:
                    err_print = "[bold yellow]Piece size too small to reuse"
                    valid = False
                elif wrong_file == True:
                    err_print = "[bold red] Provided .torrent has files that were not expected"
                    valid = False
                else:
                    err_print = f'[bold green]REUSING .torrent with infohash: [bold yellow]{torrenthash}'
        else:
            err_print = '[bold yellow]Unwanted Files/Folders Identified'
        if print_err:
            console.print(err_print)
        return valid, torrent_path


    async def search_qbit_for_torrent(self, meta, client):
        console.print("[green]Searching qbittorrent for an existing .torrent")
        torrent_storage_dir = client.get('torrent_storage_dir', None)
        if torrent_storage_dir == None and client.get("torrent_client", None) != "watch":
            console.print(f"[bold red]Missing torrent_storage_dir for {self.config['DEFAULT']['default_torrent_client']}")
            return None

        try:
            qbt_client = qbittorrentapi.Client(host=client['qbit_url'], port=client['qbit_port'], username=client['qbit_user'], password=client['qbit_pass'], VERIFY_WEBUI_CERTIFICATE=client.get('VERIFY_WEBUI_CERTIFICATE', True))
            qbt_client.auth_log_in()
        except qbittorrentapi.LoginFailed:
            console.print("[bold red]INCORRECT QBIT LOGIN CREDENTIALS")
            return None
        except qbittorrentapi.APIConnectionError:
            console.print("[bold red]APIConnectionError: INCORRECT HOST/PORT")
            return None

        # Remote path map if needed
        remote_path_map = False
        local_path, remote_path = await self.remote_path_map(meta)
        if local_path.lower() in meta['path'].lower() and local_path.lower() != remote_path.lower():
            remote_path_map = True

        torrents = qbt_client.torrents.info()
        for torrent in torrents:
            try:
                torrent_path = torrent.get('content_path', f"{torrent.save_path}{torrent.name}")
            except AttributeError:
                if meta['debug']:
                    console.print(torrent)
                    console.print_exception()
                continue
            if remote_path_map:
                torrent_path = torrent_path.replace(remote_path, local_path)
                torrent_path = torrent_path.replace(os.sep, '/').replace('/', os.sep)

            if meta['is_disc'] in ("", None) and len(meta['filelist']) == 1:
                if torrent_path == meta['filelist'][0] and len(torrent.files) == len(meta['filelist']):
                    valid, torrent_path = await self.is_valid_torrent(meta, f"{torrent_storage_dir}/{torrent.hash}.torrent", torrent.hash, 'qbit', print_err=False)
                    if valid:
                        console.print(f"[green]Found a matching .torrent with hash: [bold yellow]{torrent.hash}")
                        return torrent.hash
            elif meta['path'] == torrent_path:
                valid, torrent_path = await self.is_valid_torrent(meta, f"{torrent_storage_dir}/{torrent.hash}.torrent", torrent.hash, 'qbit', print_err=False)
                if valid:
                    console.print(f"[green]Found a matching .torrent with hash: [bold yellow]{torrent.hash}")
                    return torrent.hash
        return None












    def rtorrent(self, path, torrent_path, torrent, meta, local_path, remote_path, client):
        rtorrent = xmlrpc.client.Server(client['rtorrent_url'], context=ssl._create_stdlib_context())
        metainfo = bencode.bread(torrent_path)
        try:
            fast_resume = self.add_fast_resume(metainfo, path, torrent)
        except EnvironmentError as exc:
            console.print("[red]Error making fast-resume data (%s)" % (exc,))
            raise
        
            
        new_meta = bencode.bencode(fast_resume)
        if new_meta != metainfo:
            fr_file = torrent_path.replace('.torrent', '-resume.torrent')
            console.print("Creating fast resume")
            bencode.bwrite(fast_resume, fr_file)


        isdir = os.path.isdir(path)
        # if meta['type'] == "DISC":
        #     path = os.path.dirname(path)
        #Remote path mount
        modified_fr = False
        if local_path.lower() in path.lower() and local_path.lower() != remote_path.lower():
            path_dir = os.path.dirname(path)
            path = path.replace(local_path, remote_path)
            path = path.replace(os.sep, '/')
            shutil.copy(fr_file, f"{path_dir}/fr.torrent")
            fr_file = f"{os.path.dirname(path)}/fr.torrent"
            modified_fr = True
        if isdir == False:
            path = os.path.dirname(path)
        
        
        console.print("[bold yellow]Adding and starting torrent")
        rtorrent.load.start_verbose('', fr_file, f"d.directory_base.set={path}")
        time.sleep(1)
        # Add labels
        if client.get('rtorrent_label', None) != None:
            rtorrent.d.custom1.set(torrent.infohash, client['rtorrent_label'])
        if meta.get('rtorrent_label') != None:
            rtorrent.d.custom1.set(torrent.infohash, meta['rtorrent_label'])

        # Delete modified fr_file location
        if modified_fr:
            os.remove(f"{path_dir}/fr.torrent")
        if meta['debug']:
            console.print(f"[cyan]Path: {path}")
        return


    async def qbittorrent(self, path, torrent, local_path, remote_path, client, is_disc, filelist, meta):
        # infohash = torrent.infohash
        #Remote path mount
        isdir = os.path.isdir(path)
        if not isdir and len(filelist) == 1:
            path = os.path.dirname(path)
        if len(filelist) != 1:
            path = os.path.dirname(path)
        if local_path.lower() in path.lower() and local_path.lower() != remote_path.lower():
            path = path.replace(local_path, remote_path)
            path = path.replace(os.sep, '/')
        if not path.endswith(os.sep):
            path = f"{path}/"
        qbt_client = qbittorrentapi.Client(host=client['qbit_url'], port=client['qbit_port'], username=client['qbit_user'], password=client['qbit_pass'], VERIFY_WEBUI_CERTIFICATE=client.get('VERIFY_WEBUI_CERTIFICATE', True))
        console.print("[bold yellow]Adding and rechecking torrent")
        try:
            qbt_client.auth_log_in()
        except qbittorrentapi.LoginFailed:
            console.print("[bold red]INCORRECT QBIT LOGIN CREDENTIALS")
            return
        auto_management = False
        am_config = client.get('automatic_management_paths', '')
        if isinstance(am_config, list):
            for each in am_config:
                if os.path.normpath(each).lower() in os.path.normpath(path).lower(): 
                    auto_management = True
        else:
            if os.path.normpath(am_config).lower() in os.path.normpath(path).lower() and am_config.strip() != "": 
                auto_management = True
        qbt_category = client.get("qbit_cat") if not meta.get("qbit_cat") else meta.get('qbit_cat')

        content_layout = client.get('content_layout', 'Original')
        
        qbt_client.torrents_add(torrent_files=torrent.dump(), save_path=path, use_auto_torrent_management=auto_management, is_skip_checking=True, is_paused=False, content_layout=content_layout, category=qbt_category, tags=client.get('qbit_tag'))
        console.print(f"Added to: {path}")
        


    def deluge(self, path, torrent_path, torrent, local_path, remote_path, client, meta):
        client = DelugeRPCClient(client['deluge_url'], int(client['deluge_port']), client['deluge_user'], client['deluge_pass'])
        # client = LocalDelugeRPCClient()
        client.connect()
        if client.connected == True:
            console.print("Connected to Deluge")    
            isdir = os.path.isdir(path)
            #Remote path mount
            if local_path.lower() in path.lower() and local_path.lower() != remote_path.lower():
                path = path.replace(local_path, remote_path)
                path = path.replace(os.sep, '/')
            
            path = os.path.dirname(path)

            client.call('core.add_torrent_file', torrent_path, base64.b64encode(torrent.dump()), {'download_location' : path, 'seed_mode' : True})
            if meta['debug']:
                console.print(f"[cyan]Path: {path}")
        else:
            console.print("[bold red]Unable to connect to deluge")




    def add_fast_resume(self, metainfo, datapath, torrent):
        """ Add fast resume data to a metafile dict.
        """
        # Get list of files
        files = metainfo["info"].get("files", None)
        single = files is None
        if single:
            if os.path.isdir(datapath):
                datapath = os.path.join(datapath, metainfo["info"]["name"])
            files = [Bunch(
                path=[os.path.abspath(datapath)],
                length=metainfo["info"]["length"],
            )]

        # Prepare resume data
        resume = metainfo.setdefault("libtorrent_resume", {})
        resume["bitfield"] = len(metainfo["info"]["pieces"]) // 20
        resume["files"] = []
        piece_length = metainfo["info"]["piece length"]
        offset = 0

        for fileinfo in files:
            # Get the path into the filesystem
            filepath = os.sep.join(fileinfo["path"])
            if not single:
                filepath = os.path.join(datapath, filepath.strip(os.sep))

            # Check file size
            if os.path.getsize(filepath) != fileinfo["length"]:
                raise OSError(errno.EINVAL, "File size mismatch for %r [is %d, expected %d]" % (
                    filepath, os.path.getsize(filepath), fileinfo["length"],
                ))

            # Add resume data for this file
            resume["files"].append(dict(
                priority=1,
                mtime=int(os.path.getmtime(filepath)),
                completed=(offset+fileinfo["length"]+piece_length-1) // piece_length
                        - offset // piece_length,
            ))
            offset += fileinfo["length"]

        return metainfo


    async def remote_path_map(self, meta):
        if meta.get('client', None) == None:
            torrent_client = self.config['DEFAULT']['default_torrent_client']
        else:
            torrent_client = meta['client']
        local_path = list_local_path = self.config['TORRENT_CLIENTS'][torrent_client].get('local_path','/LocalPath')
        remote_path = list_remote_path = self.config['TORRENT_CLIENTS'][torrent_client].get('remote_path', '/RemotePath')
        if isinstance(local_path, list):
            for i in range(len(local_path)):
                if os.path.normpath(local_path[i]).lower() in meta['path'].lower():
                    list_local_path = local_path[i]
                    list_remote_path = remote_path[i]
            
        local_path = os.path.normpath(list_local_path)
        remote_path = os.path.normpath(list_remote_path)
        if local_path.endswith(os.sep):
            remote_path = remote_path + os.sep

        return local_path, remote_path
