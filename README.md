# BluUpload 


**Usage:** `blu.py /downloads/path/etc`

```
  -s, --screens INTEGER             Number of screenshots
  -c, --category [MOVIE|TV]         Category
  -t, --type [DISK|REMUX|ENCODE|WEBDL|WEBRIP|HDTV]
                                    Type
  -r, --res [2160p|1080p|1080i|720p|576p|576i|480p|480i|8640p|4320p|OTHER]
                                    Resolution
  -g, --tag TEXT                    Group tag
  -d, --desc TEXT                   Custom description (String)
  -df, --descfile                   Custom description (Path to file)
  -hb, --desclink                   Custom description (Link to Hastebin)
  -a, --anon                        Anonymous upload
  -st, --stream                     Stream Optimized Upload
  --help                            Show this message and exit.
  
  ````
  
  
  ## Setup:
   - **REQUIRES AT LEAST PYTHON 3.6 AND PIP3**
   - Rename `example_config.ini` to `config.ini`
   - Edit `config.ini` to use your information
      - tmdb_api key can be obtained from https://developers.themoviedb.org/3/getting-started/introduction
      - img_api key can be obtained from your image host, confirmed working with https://imgbb.com
      - img_host_url is the url used to post images via api. Comes with imgbb prefilled
   - Install necessary python modules `pip3 install -r requirements.txt`
   I think thats it, probably
