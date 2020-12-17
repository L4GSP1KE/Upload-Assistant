# BluUpload 


**Usage:** `python3 blu.py /downloads/path/etc`

```
Options:
  -s, --screens INTEGER           Number of screenshots
  -c, --category [MOVIE|TV]       Category
  -test, --test                   Used for testing features
  -t, --type [DISK|REMUX|ENCODE|WEBDL|WEBRIP|HDTV]
                                  Type
  -r, --res [2160p|1080p|1080i|720p|576p|576i|480p|480i|8640p|4320p|OTHER]
                                  Resolution
  -g, --tag TEXT                  Group tag
  -d, --desc TEXT                 Custom description (String)
  -df, --descfile PATH            Custom description (Path to File)
  -hb, --desclink TEXT            Custom description (Link to hastebin)
  -bdinfo, --bdinfo               Choose BDInfo paste prompt instead of scan
  -nfo, --nfo                     Use nfo from directory as description
  -a, --anon                      Anonymous upload
  -st, --stream                   Stream Optimized Upload
  -r, --region TEXT               Disk Region
  --help                          Show this message and exit.
  
  ````
  
  
  ## Setup:
   - **REQUIRES AT LEAST PYTHON 3.6 AND PIP3**
   - Rename `example_config.ini` to `config.ini`
   - Edit `config.ini` to use your information
      - tmdb_api (v3) key can be obtained from https://developers.themoviedb.org/3/getting-started/introduction
   - Install necessary python modules `pip3 install -r requirements.txt`
   I think thats it, probably
