# -*- coding: utf-8 -*-
# import discord
import asyncio
from torf import Torrent
import requests
import json
import glob
from difflib import SequenceMatcher
from termcolor import cprint
from pprint import pprint
import platform
import base64
import os
import pickle
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from webdriver_manager.firefox import GeckoDriverManager #Webdriver_manager

# from pprint import pprint

class THR():
    """
    Edit for Tracker:
        Edit BASE.torrent with announce and source
        Check for duplicates
        Set type/category IDs
        Upload
    """
    def __init__(self, config):
        self.config = config
        self.login_url = "https://www.torrenthr.org/login.php"
        self.upload_url = "https://www.torrenthr.org/upload.php"
        pass
    
    async def upload(self, meta, browser):
        await self.edit_torrent(meta)
        cat_id = await self.get_cat_id(meta)
        subs = self.get_subtitles(meta)
        pronfo = await self.edit_desc(meta)


        if meta['bdinfo'] != None:
            mi_file = None
            # bd_file = f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8'
        else:
            mi_file = os.path.abspath(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt")
            # bd_file = None
        desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[THR]DESCRIPTION.txt", 'r').read()
        torrent_path = os.path.abspath(f"{meta['base_dir']}/tmp/{meta['uuid']}/[THR]{meta['clean_name']}.torrent")
        
        #Upload Form
        print("Filling out Upload Form")
        browser.get(self.upload_url)
        upload_torrent = browser.find_element(By.NAME, "tfile")
        upload_torrent.send_keys(torrent_path)
        await asyncio.sleep(3)
        name = browser.find_element(By.NAME, "name")
        name.send_keys(meta['name'].replace("DD+", "DDP"))
        if pronfo == False:
            nfo = browser.find_element(By.NAME, "nfo")
            nfo.send_keys(mi_file)
            await asyncio.sleep(3)

        if len(subs) >= 1:
            if 'hr' in subs:
                checkboxes = browser.find_element(By.XPATH, "//td[contains(text(),'Hrvatski')]")
                checkboxes.find_element(By.NAME, 'subs[]').click()
            if 'en' in subs:
                checkboxes = browser.find_element(By.XPATH, "//td[contains(text(),'Engleski')]")
                checkboxes.find_element(By.NAME, 'subs[]').click()
            if 'bs' in subs:
                checkboxes = browser.find_element(By.XPATH, "//td[contains(text(),'Bosanski')]")
                checkboxes.find_element(By.NAME, 'subs[]').click()
            if 'sr' in subs:
                checkboxes = browser.find_element(By.XPATH, "//td[contains(text(),'Srpski')]")
                checkboxes.find_element(By.NAME, 'subs[]').click()
            if 'sl' in subs:
                checkboxes = browser.find_element(By.XPATH, "//td[contains(text(),'Slovenski')]")
                checkboxes.find_element(By.NAME, 'subs[]').click()
            
        description = browser.find_element(By.NAME, "descr")
        description.send_keys(desc)
        category_dropdown = Select(browser.find_element(By.NAME, 'type'))
        category_dropdown.select_by_value(cat_id)
        imdb_link = browser.find_element(By.NAME, "url")
        imdb_link.send_keys(f"https://www.imdb.com/title/tt{meta.get('imdb_id').replace('tt', '')}/")
        yt_link = browser.find_element(By.NAME, "tube")
        yt_link.send_keys(meta.get('youtube', ""))

        #Submit
        submit = browser.find_element(By.XPATH, "//*[@type='submit']")
        if meta['debug'] == False:
            submit.submit()
            await asyncio.sleep(3)
            print("Uploaded")
            
    
    
    
    async def get_cat_id(self, meta):
        if meta['category'] == "MOVIE":
            if meta.get('is_disc') == "BMDV":
                cat = '40'
            elif meta.get('is_disc') == "DVD" or meta.get('is_disc') == "HDDVD":
                cat = '14'
            else:
                if meta.get('sd') == 1:
                    cat = '4'
                else:
                    cat = '17'
        elif meta['category'] == "TV":
            if meta.get('sd') == 1:
                cat = '7'
            else:
                cat = '34'
        elif meta.get('anime') != False:
            cat = '31'
        return cat

    def get_subtitles(self, meta):
        with open(f"{meta.get('base_dir')}/tmp/{meta.get('uuid')}/MediaInfo.json", 'r', encoding='utf-8') as f:
            mi = json.load(f)
        subs = []
        for track in mi['media']['track']:
            if track['@type'] == "Text":
                if track.get('Language') in ['hr', 'en', 'bs', 'sr', 'sl']:
                    subs.append(track.get('Language'))
        return subs





    async def edit_torrent(self, meta):
        THR_torrent = Torrent.read(f"{meta['base_dir']}/tmp/{meta['uuid']}/BASE.torrent")
        THR_torrent.metainfo['announce'] = self.config['TRACKERS']['THR']['announce_url']
        THR_torrent.metainfo['info']['source'] = "[https://www.torrenthr.org] TorrentHR.org"
        THR_torrent.metainfo['comment'] = "Created by L4G's Upload Assistant"
        Torrent.copy(THR_torrent).write(f"{meta['base_dir']}/tmp/{meta['uuid']}/[THR]{meta['clean_name']}.torrent")
        return 
        
    async def edit_desc(self, meta):
        pronfo = False
        base = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'r').read()
        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[THR]DESCRIPTION.txt", 'w') as desc:
            desc.write(base)
            # REHOST IMAGES
            os.chdir(f"{meta['base_dir']}/tmp/{meta['uuid']}")
            image_glob = glob.glob("*.png")
            image_list = []
            for image in image_glob:
                url = "https://img2.torrenthr.org/api/1/upload"
                data = {
                    'key' : self.config['TRACKERS']['THR'].get('img_api'),
                    'source' : base64.b64encode(open(image, "rb").read()).decode('utf8')
                }
                response = requests.post(url, data = data).json()
                
                try:
                    # med_url = response['image']['medium']['url']
                    img_url = response['image']['url']
                    image_list.append(img_url)
                except:
                    cprint("Failed to upload image", 'yellow')
            
            desc.write("[align=center]")
            # ProNFO
            pronfo_url = f"https://www.pronfo.com/api/v1/access/upload/{self.config['TRACKERS']['THR'].get('pronfo_api_key', "")}"
            data = {
                'content' : open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt", 'r').read(),
                'theme' : self.config['TRACKERS']['THR'].get('pronfo_theme'),
                'rapi' : self.config['TRACKERS']['THR'].get('pronfo_rapi_id')
            }
            response = requests.post(pronfo_url, data=data).json()
            if response.get('error', True) == False:
                mi_img = response.get('url')
                desc.write(f"[img]{mi_img}[/img]")
                pronfo = True

            for each in image_list:
                desc.write(f"[img]{each}[/img]")
            desc.write("\n[url=https://www.torrenthr.org/forums.php?action=viewtopic&topicid=8977]Created by L4G's Upload Assistant[/url][/align]")
            desc.close()
        return pronfo

   


    def search_existing(self, imdb_id, browser):
        search_url = f"https://www.torrenthr.org/browse.php?search={imdb_id}&blah=2&incldead=1"
        browser.get(search_url)
        results = browser.find_elements(By.XPATH, "//*[starts-with(@href, 'details.php')]")
        dupes = []
        if isinstance(results, list) and len(results) >= 1:
            for result in results:
                result = result.get_attribute('onmousemove')
                if result != None:
                    dupe = result.split("','/images")
                    dupe = dupe[0].replace("return overlibImage('", "")        
                    dupes.append(dupe)
        return dupes

    async def login_and_get_cookies(self, meta):
        os.environ['WDM_LOCAL'] = '1'
        os.environ['WDM_LOG_LEVEL'] = '0'
        options = Options()
        if platform.system() == "Windows":
            if not meta['debug']:
                options.add_argument("--headless")
            s = Service(GeckoDriverManager().install())
            browser = Firefox(service=s, options=options)
        elif platform.system() == "Linux":
            browser = Firefox(executable_path=GeckoDriverManager().install(), options=options)
        try:
            browser.get(self.login_url)
            username_input = browser.find_element(By.NAME, "username")
            password_input = browser.find_element(By.NAME, "password")
            username_input.send_keys(self.config['TRACKERS']['THR'].get('username'))
            password_input.send_keys(self.config['TRACKERS']['THR'].get('password'))
            login_attempt = browser.find_element(By.XPATH, "//*[@type='submit']")
            login_attempt.submit()
            await asyncio.sleep(2)
            #Check If login information is good
            logincheck = browser.find_element(By.CLASS_NAME, 'glavni_txt')
            if "Unijeli ste pogrešno korisničko ime ili lozinku!" in logincheck.text:
                raise NotImplementedError
            # Get and Save Cookies and Load cookies
            cookiepath = os.path.abspath(f"{meta['base_dir']}/tmp/{meta['uuid']}/THR_cookies.pkl")
            pickle.dump(browser.get_cookies(), open(cookiepath, "wb"))
            cookies = pickle.load(open(cookiepath, "rb"))
            for cookie in cookies:
                browser.add_cookie(cookie)
        except NotImplementedError:
            cprint("INCORRECT LOGIN (Unijeli ste pogrešno korisničko ime ili lozinku!)", 'grey', 'on_red')
        return browser