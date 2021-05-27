import platform
import asyncio
import os

class Search():
    """
    Logic for searching
    """
    def __init__(self, config):
        self.config = config
        pass


    async def searchFile(self, filename):
        os_info = platform.platform()
        filename = filename.lower()
        files_total = []
        if filename == "":
            print("nothing entered")
            return
        file_found = False
        words = filename.split()
        for root, dirs, files in os.walk(self.config['DISCORD']['search_dir'], topdown=False):
            for name in files:
                if not name.endswith('.nfo'):
                    l_name = name.lower()
                    os_info = platform.platform()
                    if await self.file_search(l_name, words):
                        file_found = True
                        if('Windows' in os_info):
                            files_total.append(root+'\\'+name)
                        else:
                            files_total.append(root+'/'+name)
        return files_total

    async def searchFolder(self, foldername):
        os_info = platform.platform()
        foldername = foldername.lower()
        folders_total = []
        if foldername == "":
            print("nothing entered")
            return
        folders_found = False
        words = foldername.split()

        for root, dirs, files in os.walk(self.config['DISCORD']['search_dir'], topdown=False):

            for name in dirs:
                l_name = name.lower()

                os_info = platform.platform()

                if await self.file_search(l_name, words):
                    folder_found = True
                    if('Windows' in os_info):
                        folders_total.append(root+'\\'+name)
                    else:
                        folders_total.append(root+'/'+name)
        
        return folders_total

    async def file_search(self, name, name_words):
        check = True
        for word in name_words:
            if word not in name:
                check = False
                break
        return check