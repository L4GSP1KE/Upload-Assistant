import os
import shutil
import traceback
import sys
import asyncio
from glob import glob
from pymediainfo import MediaInfo
from collections import OrderedDict
import json

from src.console import console
    
    
class DiscParse():
    def __init__(self):
        pass

    """
    Get and parse bdinfo
    """
    async def get_bdinfo(self, discs, folder_id, base_dir, meta_discs):
        save_dir = f"{base_dir}/tmp/{folder_id}"
        if not os.path.exists(save_dir):
            os.mkdir(save_dir)
        for i in range(len(discs)):
            bdinfo_text = None
            path = os.path.abspath(discs[i]['path'])
            for file in os.listdir(save_dir):
                if file == f"BD_SUMMARY_{str(i).zfill(2)}.txt":
                    bdinfo_text = save_dir + "/" + file
            if bdinfo_text == None or meta_discs == []:
                if os.path.exists(f"{save_dir}/BD_FULL_{str(i).zfill(2)}.txt"):
                    bdinfo_text = os.path.abspath(f"{save_dir}/BD_FULL_{str(i).zfill(2)}.txt")
                else:
                    bdinfo_text = ""
                    if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
                        try:
                            # await asyncio.subprocess.Process(['mono', "bin/BDInfo/BDInfo.exe", "-w", path, save_dir])
                            console.print(f"[bold green]Scanning {path}")
                            proc = await asyncio.create_subprocess_exec('mono', f"{base_dir}/bin/BDInfo/BDInfo.exe", '-w', path, save_dir)
                            await proc.wait()
                        except:
                            console.print('[bold red]mono not found, please install mono')

                    elif sys.platform.startswith('win32'):
                        # await asyncio.subprocess.Process(["bin/BDInfo/BDInfo.exe", "-w", path, save_dir])
                        console.print(f"[bold green]Scanning {path}")
                        proc = await asyncio.create_subprocess_exec(f"{base_dir}/bin/BDInfo/BDInfo.exe", "-w", path, save_dir)
                        await proc.wait()
                        await asyncio.sleep(1)
                    else:
                        console.print("[red]Not sure how to run bdinfo on your platform, get support please thanks.")
                while True:
                    try:
                        if bdinfo_text == "":
                            for file in os.listdir(save_dir):
                                if file.startswith(f"BDINFO"):
                                    bdinfo_text = save_dir + "/" + file
                        with open(bdinfo_text, 'r') as f:
                            text = f.read()
                            result = text.split("QUICK SUMMARY:", 2)
                            files = result[0].split("FILES:", 2)[1].split("CHAPTERS:", 2)[0].split("-------------")
                            result2 = result[1].rstrip(" \n")
                            result = result2.split("********************", 1)
                            bd_summary = result[0].rstrip(" \n")
                            f.close()
                        with open(bdinfo_text, 'r') as f: # parse extended BDInfo
                            text = f.read()
                            result = text.split("[code]", 3)
                            result2 = result[2].rstrip(" \n")
                            result = result2.split("FILES:", 1)
                            ext_bd_summary = result[0].rstrip(" \n")
                            f.close()
                        try:
                            shutil.copyfile(bdinfo_text, f"{save_dir}/BD_FULL_{str(i).zfill(2)}.txt")
                            os.remove(bdinfo_text)
                        except shutil.SameFileError:
                            pass
                    except Exception:
                        console.print(traceback.format_exc())
                        await asyncio.sleep(5)
                        continue
                    break
                with open(f"{save_dir}/BD_SUMMARY_{str(i).zfill(2)}.txt", 'w') as f:
                    f.write(bd_summary.strip())
                    f.close()
                with open(f"{save_dir}/BD_SUMMARY_EXT.txt", 'w') as f: # write extended BDInfo file
                    f.write(ext_bd_summary.strip())
                    f.close()
                
                bdinfo = self.parse_bdinfo(bd_summary, files[1], path)
        
                discs[i]['summary'] = bd_summary.strip()
                discs[i]['bdinfo'] = bdinfo
                # shutil.rmtree(f"{base_dir}/tmp")
            else:
                discs = meta_discs
        
        return discs, discs[0]['bdinfo']
        
            

    def parse_bdinfo(self, bdinfo_input, files, path):
        bdinfo = dict()
        bdinfo['video'] = list()
        bdinfo['audio'] = list()
        bdinfo['subtitles'] = list()
        bdinfo['path'] = path
        lines = bdinfo_input.splitlines()
        for l in lines:
            line = l.strip().lower()
            if line.startswith("*"):
                line = l.replace("*", "").strip().lower()
            if line.startswith("playlist:"):
                playlist = l.split(':', 1)[1]
                bdinfo['playlist'] = playlist.split('.',1)[0].strip()
            if line.startswith("disc size:"):
                size = l.split(':', 1)[1]
                size = size.split('bytes', 1)[0].replace(',','')
                size = float(size)/float(1<<30)
                bdinfo['size'] = size
            if line.startswith("length:"):
                length = l.split(':', 1)[1]
                bdinfo['length'] = length.split('.',1)[0].strip()
            if line.startswith("video:"):
                split1 = l.split(':', 1)[1]
                split2 = split1.split('/', 12)
                while len(split2) != 9:
                    split2.append("")
                n=0
                if "Eye" in split2[2].strip():
                    n = 1
                    three_dim = split2[2].strip()
                else:
                    three_dim = ""
                try:
                    bit_depth = split2[n+6].strip()
                    hdr_dv = split2[n+7].strip()
                    color = split2[n+8].strip()
                except:
                    bit_depth = ""
                    hdr_dv = ""
                    color = ""
                bdinfo['video'].append({
                    'codec': split2[0].strip(), 
                    'bitrate': split2[1].strip(), 
                    'res': split2[n+2].strip(), 
                    'fps': split2[n+3].strip(), 
                    'aspect_ratio' : split2[n+4].strip(),
                    'profile': split2[n+5].strip(),
                    'bit_depth' : bit_depth,
                    'hdr_dv' : hdr_dv, 
                    'color' : color,
                    '3d' : three_dim,
                    })
            elif line.startswith("audio:"):
                if "(" in l:
                    l = l.split("(")[0]
                l = l.strip()
                split1 = l.split(':', 1)[1]
                split2 = split1.split('/')
                n = 0
                if "Atmos" in split2[2].strip():
                    n = 1
                    fuckatmos = split2[2].strip()
                else:
                    fuckatmos = ""
                try:
                    bit_depth = split2[n+5].strip()
                except:
                    bit_depth = ""
                bdinfo['audio'].append({
                    'language' : split2[0].strip(), 
                    'codec' : split2[1].strip(), 
                    'channels' : split2[n+2].strip(), 
                    'sample_rate' : split2[n+3].strip(), 
                    'bitrate' : split2[n+4].strip(), 
                    'bit_depth' : bit_depth, # Also DialNorm, but is not in use anywhere yet
                    'atmos_why_you_be_like_this': fuckatmos,
                    })
            elif line.startswith("disc title:"):
                title = l.split(':', 1)[1]
                bdinfo['title'] = title
            elif line.startswith("disc label:"):
                label = l.split(':', 1)[1]
                bdinfo['label'] = label
            elif line.startswith('subtitle:'):
                split1 = l.split(':', 1)[1]
                split2 = split1.split('/')
                bdinfo['subtitles'].append(split2[0].strip())
        files = files.splitlines()
        bdinfo['files'] = []
        for line in files:
            try:
                stripped = line.split()
                m2ts = {}
                bd_file = stripped[0]
                time_in = stripped[1]
                bd_length = stripped[2]
                bd_size = stripped[3]
                bd_bitrate = stripped[4]
                m2ts['file'] = bd_file
                m2ts['length'] = bd_length
                bdinfo['files'].append(m2ts)
            except:
                pass
        return bdinfo


    
    """
    Parse VIDEO_TS and get mediainfos
    """
    async def get_dvdinfo(self, discs):
        for each in discs:
            path = each.get('path')
            os.chdir(path)
            files = glob(f"VTS_*.VOB")
            files.sort()
            # Switch to ordered dictionary
            filesdict = OrderedDict()
            main_set = []
            # Use ordered dictionary in place of list of lists
            for file in files:
                trimmed = file[4:]
                if trimmed[:2] not in filesdict:
                    filesdict[trimmed[:2]] = []
                filesdict[trimmed[:2]].append(trimmed)
            main_set_duration = 0
            for vob_set in filesdict.values():
                # Parse media info for this VOB set
                vob_set_mi = MediaInfo.parse(f"VTS_{vob_set[0][:2]}_0.IFO", output='JSON')
                vob_set_mi = json.loads(vob_set_mi)
                vob_set_duration = vob_set_mi['media']['track'][1]['Duration']
                      
                
                # If the duration of the new vob set > main set by more than 10% then it's our new main set
                # This should make it so TV shows pick the first episode 
                if (float(vob_set_duration) * 1.00) > (float(main_set_duration) * 1.10) or len(main_set) < 1:
                    main_set = vob_set
                    main_set_duration = vob_set_duration
            each['main_set'] = main_set
            set = main_set[0][:2]
            each['vob'] = vob = f"{path}/VTS_{set}_1.VOB"
            each['ifo'] = ifo = f"{path}/VTS_{set}_0.IFO"
            each['vob_mi'] = MediaInfo.parse(os.path.basename(vob), output='STRING', full=False, mediainfo_options={'inform_version' : '1'}).replace('\r\n', '\n')
            each['ifo_mi'] = MediaInfo.parse(os.path.basename(ifo), output='STRING', full=False, mediainfo_options={'inform_version' : '1'}).replace('\r\n', '\n')
            each['vob_mi_full'] = MediaInfo.parse(vob, output='STRING', full=False, mediainfo_options={'inform_version' : '1'}).replace('\r\n', '\n')
            each['ifo_mi_full'] = MediaInfo.parse(ifo, output='STRING', full=False, mediainfo_options={'inform_version' : '1'}).replace('\r\n', '\n')
            

            size = sum(os.path.getsize(f) for f in os.listdir('.') if os.path.isfile(f))/float(1<<30)
            if size <= 7.95:
                dvd_size = "DVD9"
                if size <= 4.37:
                    dvd_size = "DVD5"
            each['size'] = dvd_size
        return discs
    
    async def get_hddvd_info(self, discs):
        for each in discs:
            path = each.get('path')
            os.chdir(path)
            files = glob("*.EVO")
            size = 0
            largest = files[0]
            # get largest file from files
            for file in files:
                file_size = os.path.getsize(file)
                if file_size > size:
                    largest = file
                    size = file_size
            each['evo_mi'] = MediaInfo.parse(os.path.basename(largest), output='STRING', full=False, mediainfo_options={'inform_version' : '1'})
            each['largest_evo'] = os.path.abspath(f"{path}/{largest}")
        return discs
