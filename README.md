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

  -debug, -               Debug Mode

  -client, --client       Override default torrent client

  -tk, --trackers         Override default torrent client

  ````
  **CLI Usage:** `python3 uplad.py /downloads/path/to/content`

  **Discord Bot Usage:** `python3 bot.py`

  ## Setup:
   - **REQUIRES AT LEAST PYTHON 3.6 AND PIP3**
   - Clone the repo to your system `git clone https://github.com/L4GSP1KE/Upload-Assistant.git`
   - Copy and Rename `data/example-config.json` to `data/config.json`
   - Edit `config.json` to use your information (more detailed information in the wiki(coming soon))
      - tmdb_api (v3) key can be obtained from https://developers.themoviedb.org/3/getting-started/introduction
      - image host api keys can be obtained from their respective sites
      - discord bot token can be obtained from https://discord.com/developers/
   - Install necessary python modules `pip3 install -r requirements.txt`
   I think thats it, probably
   Feel free to contact me if you need help

