# L4G's Upload Assistant



```
Options:
  -h, --help              show this help message and exit

  -s, --screens           Number of screenshots

  -c, --category          Category [MOVIE, TV, FANRES]

  -t, --type              Type [DISC, REMUX, ENCODE, WEBDL, WEBRIP, HDTV]

  -res, --resolution      Resolution [2160p, 1080p, 1080i, 720p, 576p, 576i, 480p, 480i, 8640p, 4320p, OTHER]

  -tmdb, --tmdb           TMDb ID

  -g, --tag               Group Tag

  -serv, --service        Streaming Service

  -edition, --edition     Edition

  -d, --desc              Custom Description (string)

  -nfo, --n               Use .nfo in directory for description

  -k, --keywords          Add comma seperated keywords e.g. 'keyword, keyword2, etc'

  -reg, --region          Region for discs

  -a, --ano               Upload anonymously

  -st, --st               Stream Optimized Upload

  -debug, --debug         Debug Mode

  -client, --client       Override default torrent client

  -tk, --trackers         Override default torrent client

  ````
  

## **Setup:**
   - **REQUIRES AT LEAST PYTHON 3.6 AND PIP3**
   - Clone the repo to your system `git clone https://github.com/L4GSP1KE/Upload-Assistant.git`
   - Copy and Rename `data/example-config.json` to `data/config.json`
   - Edit `config.json` to use your information (more detailed information in the wiki(coming soon))
      - tmdb_api (v3) key can be obtained from https://developers.themoviedb.org/3/getting-started/introduction
      - image host api keys can be obtained from their respective sites
      - discord bot token can be obtained from https://discord.com/developers/
   - Install necessary python modules `pip3 install -r requirements.txt`
   

   **Additional Resources are found in the [wiki](https://github.com/L4GSP1KE/Upload-Assistant/wiki)**
   
   Feel free to contact me if you need help, I'm not that hard to find.

  ## **CLI Usage:**
  
  `python3 upload.py /downloads/path/to/content --args`
  
  Args are OPTIONAL

## **Discord Bot Usage:** 
  **To start the bot** `python3 bot.py`
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
