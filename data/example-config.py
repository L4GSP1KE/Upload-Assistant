config = {
    "DEFAULT" : {
        "tmdb_api" : "tmdb_api key",
        "imgbb_api" : "imgbb api key",
        "freeimage_api" : "6d207e02198a847aa98d0a2a901485a5",
        "ptpimg_api" : "ptpimg api key",

        # Order of image hosts, and backup image hosts
        "img_host_1": "imgbb",
        "img_host_2": "freeimage.host",
        "img_host_3": "ptpimg",
        "img_host_4": "imgbox",

        "screens" : "6",


        # The name of your default torrent client, set in the torrent client sections below
        "default_torrent_client" : "Client1"


    },

    "TRACKERS" : {
        # Which trackers do you want to upload to?
        "default_trackers" : "BLU, BHD, AITHER, STC, THR, UHDHEAVEN, R4E",

        "BLU" : {
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
            "ApiUser" : None,
            "ApiKey" : None,
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
        "STC" :{
            "api_key" : "STC",
            "announce_url" : "https://skipthecommericals.xyz/announce/customannounceurl",
            # "anon" : "False"
        },
        "UHDHEAVEN" :{
            "api_key" : "UHDHEAVEN api key",
            "announce_url" : "https://uhd-heaven.xyz/announce/customannounceurl",
            # "anon" : "False"
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


        "MANUAL" : {
            # Uncomment and replace link with filebrowser link to the Upload-Assistant directory, this will link to your filebrowser instead of uploading to uguu.se
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

            # Remote path mapping (docker/etc.)
            # "local_path" : "/LocalPath",
            # "remote_path" : "/RemotePath"
        },
        "qbit_sample" : {
            "torrent_client" : "qbit",
            "qbit_url" : "http://127.0.0.1",
            "qbit_port" : "8080",
            "qbit_user" : "username",
            "qbit_pass" : "password",
            # "qbit_tag" : "tag",
            # "torrent_storage_dir" : "path/to/BT_backup folder"
            
            # Remote path mapping (docker/etc.)
            # "local_path" : "E:\\downloads\\tv",
            # "remote_path" : "/remote/downloads/tv"
        },

        "rtorrent_sample" : {
            "torrent_client" : "rtorrent",
            "rtorrent_url" : "https://user:password@server.host.tld:443/username/rutorrent/plugins/httprpc/action.php",
            # "torrent_storage_dir" : "path/to/session folder"
            # Remote path mapping (docker/etc.)
            # "local_path" : "/LocalPath",
            # "remote_path" : "/RemotePath"

        },
        "deluge_sample" : {
            "torrent_client" : "deluge",
            "deluge_url" : "localhost",
            "deluge_port" : "8080",
            "deluge_user" : "username",
            "deluge_pass" : "password",
            
            # Remote path mapping (docker/etc.)
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
                "MANUAL" : "📩",
                "UPLOAD" : "✅",
                "CANCEL" : "🚫"
        }
    }
}
