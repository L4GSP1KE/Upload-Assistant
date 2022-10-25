config = {
    "DEFAULT" : {
        "tmdb_api" : "tmdb_api key",
        "imgbb_api" : "imgbb api key",
        "ptpimg_api" : "ptpimg api key",

        # Order of image hosts, and backup image hosts
        "img_host_1": "imgbb",
        "img_host_2": "ptpimg",
        "img_host_3": "imgbox",
        # "img_host_4": "",


        "screens" : "6",
        # Enable lossless PNG Compression (True/False)
        "optimize_images" : True,


        # The name of your default torrent client, set in the torrent client sections below
        "default_torrent_client" : "Client1"


    },

    "TRACKERS" : {
        # Which trackers do you want to upload to?
        "default_trackers" : "BLU, BHD, AITHER, STC, STT, SN, THR, R4E, HP, ACM, PTP, LCD, LST, PTER",

        "BLU" : {
            "useAPI" : False, # Set to True if using BLU
            "api_key" : "BLU api key",
            "announce_url" : "https://blutopia.xyz/announce/customannounceurl",
            # "anon" : "False"
        },
        "BHD" : {
            "api_key" : "BHD api key",
            "announce_url" : "https://beyond-hd.me/announce/customannounceurl",
            "draft_default" : "True",
            # "anon" : "False"
        },
        "PTP" : {
            "useAPI" : False, # Set to True if using PTP
            "ApiUser" : "ptp api user",
            "ApiKey" : 'ptp api key',
            "username" : "",
            "password" : "",
            "announce_url" : ""
        },
        "AITHER" :{
            "api_key" : "AITHER api key",
            "announce_url" : "https://aither.cc/announce/customannounceurl",
            # "anon" : "False"
        },
        "R4E" :{
            "api_key" : "R4E api key",
            "announce_url" : "https://racing4everyone.eu/announce/customannounceurl",
            # "anon" : "False"
        },
        "HUNO" : {
            "api_key" : "HUNO api key",
            "announce_url" : "https://hawke.uno/announce/customannounceurl",
            # "anon" : "False"
        },
        "STC" :{
            "api_key" : "STC",
            "announce_url" : "https://skipthecommericals.xyz/announce/customannounceurl",
            # "anon" : "False"
        },
        "STT" :{
            "api_key" : "STC",
            "announce_url" : "https://stt.xyz/announce/customannounceurl",
            # "anon" : "False"
        },
        "SN": {
            "api_key": "6Z1tMrXzcYpIeSdGZueQWqb3BowlS6YuIoZLHe3dvIqkSfY0Ws5SHx78oGSTazG0jQ1agduSqe07FPPE8sdWTg",
            "announce_url": "https://tracker.swarmazon.club:8443/<YOUR_PASSKEY>/announce",
        },
        "HP" :{
            "api_key" : "HP",
            "announce_url" : "https://hidden-palace.net/announce/customannounceurl",
            # "anon" : "False"
        },
        "ACM" :{
            "api_key" : "ACM api key",
            "announce_url" : "https://asiancinema.me/announce/customannounceurl",
            # "anon" : "False",

            # FOR INTERNAL USE ONLY:
            # "internal" : True,
            # "internal_groups" : ["What", "Internal", "Groups", "Are", "You", "In"],
        },
        "NBL" : {
            "api_key" : "NBL api key",
            "announce_url" : "https://nebulance.io/customannounceurl",
        },
        "THR" : {
            "username" : "username",
            "password" : "password",
            "img_api" : "get this from the forum post",
            "announce_url" : "http://www.torrenthr.org/announce.php?passkey=yourpasskeyhere",
            "pronfo_api_key" : "pronfo api key",
            "pronfo_theme" : "pronfo theme code",
            "pronfo_rapi_id" : "pronfo remote api id",
            # "anon" : "False"
        },
        "LCD" : {
            "api_key" : "LCD api key",
            "announce_url" : "https://locadora.xyz/announce/customannounceurl",
            # "anon" : "False"
        },
        "LST" : {
            "api_key" : "LST api key",
            "announce_url" : "https://lst.gg/announce/customannounceurl",
            # "anon" : "False"
        },
	    "LT" : {
            "api_key" : "LT api key",
            "announce_url" : "https://lat-team.com/announce/customannounceurl",
            # "anon" : "False"
        },
	    "TDB" : {
            "passkey" : "TDB api key",
            "announce_url" : "https://torrentdb.net/announce/customannounceurl",
            # "anon" : "False"
        },
        "PTER" : {
            "passkey":'passkey',
            "img_rehost" : False,
            "username" : "",
            "password" : "",
            "ptgen_api": "",
            "anon": True,
        },

        "MANUAL" : {
            # Uncomment and replace link with filebrowser (https://github.com/filebrowser/filebrowser) link to the Upload-Assistant directory, this will link to your filebrowser instead of uploading to uguu.se
            # "filebrowser" : "https://domain.tld/filebrowser/files/Upload-Assistant/"
        },
    },


    "TORRENT_CLIENTS" : {
        # Name your torrent clients here, for example, this example is named "Client1"
        "Client1" : {
            "torrent_client" : "qbit",
            "qbit_url" : "http://127.0.0.1",
            "qbit_port" : "8080",
            "qbit_user" : "username",
            "qbit_pass" : "password",

            # Remote path mapping (docker/etc.) CASE SENSITIVE
            # "local_path" : "/LocalPath",
            # "remote_path" : "/RemotePath"
        },
        "qbit_sample" : {
            "torrent_client" : "qbit",
            "enable_search" : True,
            "qbit_url" : "http://127.0.0.1",
            "qbit_port" : "8080",
            "qbit_user" : "username",
            "qbit_pass" : "password",
            # "qbit_tag" : "tag",
            # "torrent_storage_dir" : "path/to/BT_backup folder"
            
            # Enable automatic torrent management if path(s) are set
                # If using remote path mapping, use remote path
                # For using multiple paths, use a list ["path1", "path2"] 
            # "automatic_management_paths" : ""


            # Remote path mapping (docker/etc.) CASE SENSITIVE
            # "local_path" : "E:\\downloads\\tv",
            # "remote_path" : "/remote/downloads/tv"
        },

        "rtorrent_sample" : {
            "torrent_client" : "rtorrent",
            "rtorrent_url" : "https://user:password@server.host.tld:443/username/rutorrent/plugins/httprpc/action.php",
            # "torrent_storage_dir" : "path/to/session folder"

            # Remote path mapping (docker/etc.) CASE SENSITIVE
            # "local_path" : "/LocalPath",
            # "remote_path" : "/RemotePath"

        },
        "deluge_sample" : {
            "torrent_client" : "deluge",
            "deluge_url" : "localhost",
            "deluge_port" : "8080",
            "deluge_user" : "username",
            "deluge_pass" : "password",
            
            # Remote path mapping (docker/etc.) CASE SENSITIVE
            # "local_path" : "/LocalPath",
            # "remote_path" : "/RemotePath"
        },
        "watch_sample" : {
            "torrent_client" : "watch",
            "watch_folder" : "/Path/To/Watch/Folder"
        },

    },







    "DISCORD" :{
        "discord_bot_token" : "discord bot token",
        "discord_bot_description" : "L4G's Upload Assistant",
        "command_prefix" : "!",
        "discord_channel_id" : "discord channel id for use",
        "admin_id" : "your discord user id",

        "search_dir" : "Path/to/downloads/folder/   this is used for search",
        # Alternatively, search multiple folders:
        # "search_dir" : [
        #   "/downloads/dir1",
        #   "/data/dir2",
        # ]
        "discord_emojis" : {
                "BLU": "💙",
                "BHD": "🎉",
                "AITHER": "🛫",
                "STC": "📺",
                "ACM": "🍙",
                "MANUAL" : "📩",
                "UPLOAD" : "✅",
                "CANCEL" : "🚫"
        }
    }
}
