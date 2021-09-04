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
        torrent = Torrent.read(torrent_path)
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
        
        local_path = self.config['TORRENT_CLIENTS'][default_torrent_client]['local_path']
        remote_path = self.config['TORRENT_CLIENTS'][default_torrent_client]['remote_path']
        cprint(f"Adding to {torrent_client}", 'grey', 'on_yellow')
        if torrent_client.lower() == "rtorrent":
            self.rtorrent(meta['path'], torrent_path, torrent, meta, local_path, remote_path, client)
        elif torrent_client == "qbit":
            await self.qbittorrent(meta['path'], torrent, local_path, remote_path, client, meta['is_disc'])
        elif torrent_client.lower() == "deluge":
            if meta['type'] == "DISC":
                path = os.path.dirname(meta['path'])
            self.deluge(meta['path'], torrent_path, torrent, local_path, remote_path, client, meta)
        elif torrent_client.lower() == "watch":
            shutil.copy(torrent_path, client['watch_folder'])
        pass
   
        
















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
        if local_path in path:
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


    async def qbittorrent(self, path, torrent, local_path, remote_path, client, is_disc):
        # infohash = torrent.infohash
        #Remote path mount
        isdir = os.path.isdir(path)
        # if not isdir:
        #     path = os.path.dirname(path)
        if is_disc != "":
            path = os.path.dirname(path)
        if local_path in path:
            path = path.replace(local_path, remote_path)
            path = path.replace(os.sep, '/')
        
        qbt_client = qbittorrentapi.Client(host=client['qbit_url'], port=client['qbit_port'], username=client['qbit_user'], password=client['qbit_pass'])
        cprint("Adding and rechecking torrent", 'grey', 'on_yellow')
        try:
            qbt_client.auth_log_in()
        except qbittorrentapi.LoginFailed:
            cprint("INCORRECT QBIT LOGIN CREDENTIALS", 'grey', 'on_red')
            exit()
        qbt_client.torrents_add(torrent_files=torrent.dump(), save_path=path, use_auto_torrent_management=False, is_skip_checking=True)
        qbt_client.torrents_resume(torrent.infohash)
        
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
            if local_path in path:
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