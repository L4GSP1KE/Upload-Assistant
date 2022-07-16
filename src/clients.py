# -*- coding: utf-8 -*-
from pprint import pprint
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

from termcolor import cprint



class Clients():
    """
    Add to torrent client
    """
    def __init__(self, config):
        self.config = config
        pass
    

    async def add_to_client(self, meta, tracker):
        torrent_path = f"{meta['base_dir']}/tmp/{meta['uuid']}/[{tracker}]{meta['clean_name']}.torrent"
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
        
        local_path = list_local_path = self.config['TORRENT_CLIENTS'][default_torrent_client].get('local_path','/LocalPath')
        remote_path = list_remote_path = self.config['TORRENT_CLIENTS'][default_torrent_client].get('remote_path', '/RemotePath')
        if isinstance(local_path, list):
            for i in range(len(local_path)):
                if os.path.normpath(local_path[i]).lower() in meta['path'].lower():
                    list_local_path = local_path[i]
                    list_remote_path = remote_path[i]
            
        local_path = os.path.normpath(list_local_path)
        remote_path = os.path.normpath(list_remote_path)
        if local_path.endswith(os.sep):
            remote_path = remote_path + os.sep
        
        cprint(f"Adding to {torrent_client}", 'grey', 'on_yellow')
        if torrent_client.lower() == "rtorrent":
            self.rtorrent(meta['path'], torrent_path, torrent, meta, local_path, remote_path, client)
        elif torrent_client == "qbit":
            await self.qbittorrent(meta['path'], torrent, local_path, remote_path, client, meta['is_disc'], meta['filelist'])
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
        if meta.get('client', None) == 'none':
            return None
        client = self.config['TORRENT_CLIENTS'][default_torrent_client]
        torrent_storage_dir = client.get('torrent_storage_dir', None)
        torrent_client = client.get('torrent_client', None).lower()
        if torrent_storage_dir == None and torrent_client != "watch":
            cprint(f'Missing torrent_storage_dir for {default_torrent_client}', 'grey', 'on_red')
        if torrent_storage_dir != None:
            if meta.get('torrenthash', None) != None:
                torrenthash = meta['torrenthash']
            elif meta.get('ext_torrenthash', None) != None:
                torrenthash = meta['ext_torrenthash']
            if torrent_client in ('qbit', 'deluge'):
                torrenthash = torrenthash.lower()
            elif torrent_client == 'rtorrent':
                torrenthash = torrenthash.upper()
            torrent_path = f"{torrent_storage_dir}/{torrenthash}.torrent"
            reuse = None
            if os.path.exists(torrent_path):
                # Reuse if disc
                if meta.get('is_disc', None) != None:
                    reuse = torrent_path
                torrent = Torrent.read(torrent_path)
                # If one file, check for folder
                if len(torrent.files) == len(meta['filelist']) == 1:
                    if str(torrent.files[0]) == os.path.basename(torrent.files[0]):
                        reuse = torrent_path
                # Check if number of files matches number of videos
                elif len(torrent.files) == len(meta['filelist']):
                    torrent_filepath = os.path.commonpath(torrent.files)
                    actual_filepath = os.path.commonpath(meta['filelist'])
                    if torrent_filepath in actual_filepath:
                        
                        reuse = torrent_path
            else:
                cprint(f'NO .torrent WITH INFOHASH {torrenthash} FOUND', 'grey', 'on_yellow')
            if reuse != None:
                 if os.path.exists(torrent_path):
                    reuse_torrent = Torrent.read(torrent_path)
                    if reuse_torrent.pieces >= 5000 and reuse_torrent.piece_size < 16777216:
                        cprint("Too many pieces exist in current hash. REHASHING", 'grey', 'on_yellow')
                        reuse = None
                    elif reuse_torrent.piece_size < 32768:
                        cprint("Piece size too small to reuse", 'grey', 'on_yellow')
                        reuse = None
                    else:
                        cprint(f'REUSING .torrent with infohash: {torrenthash}', 'grey', 'on_green')
            else:
                cprint('Unwanted Files/Folders Identified', 'grey', 'on_yellow')
            return reuse
        return None















    def rtorrent(self, path, torrent_path, torrent, meta, local_path, remote_path, client):
        rtorrent = xmlrpc.client.Server(client['rtorrent_url'], context=ssl._create_stdlib_context())
        metainfo = bencode.bread(torrent_path)
        try:
            fast_resume = self.add_fast_resume(metainfo, path, torrent)
        except EnvironmentError as exc:
            cprint("Error making fast-resume data (%s)" % (exc,), 'grey', 'on_red')
            raise
        
            
        new_meta = bencode.bencode(fast_resume)
        if new_meta != metainfo:
            fr_file = torrent_path.replace('.torrent', '-resume.torrent')
            print("Creating fast resume")
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
        
        
        cprint("Adding and starting torrent", 'grey', 'on_yellow')
        rtorrent.load.start_verbose('', fr_file, f"d.directory_base.set={path}")
        
        # Delete modified fr_file location
        if modified_fr:
            os.remove(f"{path_dir}/fr.torrent")
        if meta['debug']:
            cprint(f"Path: {path}", 'cyan')
        return


    async def qbittorrent(self, path, torrent, local_path, remote_path, client, is_disc, filelist):
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
        qbt_client = qbittorrentapi.Client(host=client['qbit_url'], port=client['qbit_port'], username=client['qbit_user'], password=client['qbit_pass'])
        cprint("Adding and rechecking torrent", 'grey', 'on_yellow')
        try:
            qbt_client.auth_log_in()
        except qbittorrentapi.LoginFailed:
            cprint("INCORRECT QBIT LOGIN CREDENTIALS", 'grey', 'on_red')
            exit()
        qbt_client.torrents_add(torrent_files=torrent.dump(), save_path=path, use_auto_torrent_management=False, is_skip_checking=True, content_layout='Original')
        qbt_client.torrents_resume(torrent.infohash)
        if client.get('qbit_tag', None) != None:
            qbt_client.torrents_add_tags(tags=client.get('qbit_tag'), torrent_hashes=torrent.infohash)
        
        print(f"Added to: {path}")
        # qbt_client.torrents_recheck(torrent_hashes=infohash)
        # cprint("Rechecking File", 'grey', 'on_yellow')
        # while qbt_client.torrents_info(torrent_hashes=infohash)[0]['completed'] == 0:
        #     time.sleep(1)
        # qbt_client.torrents_resume(torrent_hashes=infohash)


    def deluge(self, path, torrent_path, torrent, local_path, remote_path, client, meta):
        client = DelugeRPCClient(client['deluge_url'], int(client['deluge_port']), client['deluge_user'], client['deluge_pass'])
        # client = LocalDelugeRPCClient()
        client.connect()
        if client.connected == True:
            print("Deluge connected")    
            isdir = os.path.isdir(path)
            #Remote path mount
            if local_path.lower() in path.lower() and local_path.lower() != remote_path.lower():
                path = path.replace(local_path, remote_path)
                path = path.replace(os.sep, '/')
            # if isdir == False:
            else:
                path = os.path.dirname(path)

            client.call('core.add_torrent_file', torrent_path, base64.b64encode(torrent.dump()), {'download_location' : path, 'seed_mode' : True})
            if meta['debug']:
                cprint(f"Path: {path}", 'cyan')
        else:
            cprint("Unable to connect to deluge", 'grey', 'on_red')




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