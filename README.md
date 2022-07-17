# L4G's Upload Assistant

A simple tool to take the work out of uploading. Now with a Discord Bot interface for people who don't like command line!

## What It Can Do:
  - Generates and Parses MediaInfo/BDInfo.
  - Generates and Uploads screenshots.
  - Uses srrdb to fix scene filenames
  - Can grab descriptions from PTP (automatically on filename match or arg) / BLU (arg)
  - Obtains TMDb/IMDb/MAL identifiers.
  - Converts absolute to season episode numbering for Anime
  - Generates custom .torrents without useless top level folders/nfos.
  - Can re-use existing torrents instead of hashing new
  - Generates proper name for your upload using Mediainfo/BDInfo and TMDb/IMDb conforming to site rules
  - Checks for existing releases already on site
  - Uploads to BLU/BHD/Aither/THR/STC/R4E(limited)/STT/HP/ACM/LCD
  - Adds to your client with fast resume, seeding instantly (rtorrent/qbittorrent/deluge/watch folder)
  - ALL WITH MINIMAL INPUT!
  - Currently works with .mkv/.mp4/Blu-ray/DVD/HD-DVDs



## Coming Soon:
  - Features


  

## **Setup:**
   - **REQUIRES AT LEAST PYTHON 3.7 AND PIP3**
   - Needs [mono](https://www.mono-project.com/) on linux systems for BDInfo
   - Also needs MediaInfo and ffmpeg installed on your system
      - On Windows systems, ffmpeg must be added to PATH (https://windowsloop.com/install-ffmpeg-windows-10/)
      - On linux systems, get it from your favorite package manager
   - Clone the repo to your system `git clone https://github.com/L4GSP1KE/Upload-Assistant.git`
   - Copy and Rename `data/example-config.py` to `data/config.py`
   - Edit `config.py` to use your information (more detailed information in the [wiki](https://github.com/L4GSP1KE/Upload-Assistant/wiki))
      - tmdb_api (v3) key can be obtained from https://developers.themoviedb.org/3/getting-started/introduction
      - image host api keys can be obtained from their respective sites
      - discord bot token can be obtained from https://discord.com/developers/
   - Install necessary python modules `pip3 install --user -U -r requirements.txt`
     
   

   **Additional Resources are found in the [wiki](https://github.com/L4GSP1KE/Upload-Assistant/wiki)**
   
   Feel free to contact me if you need help, I'm not that hard to find.

## **Updating:**
  - To update first navigate into the Upload-Assistant directory: `cd Upload-Assistant`
  - Run a `git pull` to grab latest updates
  - Run `pip3 install --user -U -r requirements.txt` to ensure dependencies are up to date
  ## **CLI Usage:**
  
  `python3 upload.py /downloads/path/to/content --args`
  
  Args are OPTIONAL, for a list of acceptable args, pass `--help`
