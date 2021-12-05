# L4G's Upload Assistant

A simple tool to take the work out of uploading. Now with a Discord Bot interface for people who don't like command line!

## What It Does:
  - Generates and Parses MediaInfo/BDInfo.
  - Generates and Uploads screenshots.
  - Obtains TMDb/IMDb/MAL identifiers.
  - Generates custom .torrents without useless top level folders/nfos.
  - Generates proper name for your sites.
  - Uploads to BLU/BHD/Aither/THR
  - Adds to your client, seeding instantly
  - ALL WITH MINIMAL INPUT!

  - Currently works with .mkv/.mp4/Blu-ray/DVD/HD-DVDs



## Coming Soon:
  - Hit me with feature requests


  

## **Setup:**
   - **REQUIRES AT LEAST PYTHON 3.6 AND PIP3**
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

   - For THR: 
      - `pip3 install --user -U -r webdriver_manager selenium`
      - Also **REQUIRES** Firefox to be installed (check this with `firefox -v`). `apt install firefox` or ask your seedbox provider
      
   

   **Additional Resources are found in the [wiki](https://github.com/L4GSP1KE/Upload-Assistant/wiki)**
   
   Feel free to contact me if you need help, I'm not that hard to find.

## **Updating:**
  - To update first navigate into the Upload-Assistant directory: `cd Upload-Assistant`
  - Run a `git pull` to grab latest updates
  - Run `pip3 install --user -U -r requirements.txt` to ensure dependencies are up to date
  ## **CLI Usage:**
  
  `python3 upload.py /downloads/path/to/content --args`
  
  Args are OPTIONAL


## **Discord Bot Usage:** 
  **To start the bot** `python3 discordbot.py`
  I recommend running this in screen
  
  **Commands:**
  - `!upload "/path/to/file" --args`: 
      - Works the same as the CLI version. You will get a nice looking confirmation message after the bot has done it's prep work. React to the trackers you want to upload to and then react to the Confirmation emoji to upload.
      - Example: `!upload "/downloads/movie.mp4"`
  - `!edit [ID] --args`:
      - This is used if the bot gets something wrong and needs to be manually changed. The ID can be found in the bottom left corner of the confirmation message.
      - Example: `!edit BWYiPX5siCtUxyKLZkfjZm --group MyGroup`
  - `!search [search terms]`:
      - This is the lazy man's `!upload`. It searches your predefined search directory for any files that match the search term(s). If one result is found, it gives the option to upload it. If more than one result is found it returns a list so you can try again and be more specific. **Note:** This only works with single files, for directories use `!search dir [search terms]`
  - `!search dir [search terms]`:
      - This is `!search` for directories. Use this for things like season packs/discs/etc.
  - `!args`:
      - This returns a message containing all usable arguments

  
  Feel free to pester me if you need help/want features/etc.
