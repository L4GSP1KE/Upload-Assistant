import re 

# Bold - KEEP
# Italic - KEEP
# Underline - KEEP
# Strikethrough - KEEP
# Color - KEEP
# URL - KEEP
# QUOTE - KEEP
# PARSING - Probably not exist in uploads
# Spoiler - KEEP

# PRE - CONVERT to CODE
# Hide - CONVERT to SPOILER
# COMPARISON - CONVERT

# LIST - REMOVE TAGS/REPLACE with * or something

# Size - REMOVE TAGS

# Align - REMOVE (ALL LEFT ALIGNED)
# VIDEO - REMOVE
# HR - REMOVE
# MEDIAINFO - REMOVE
# MOVIE - REMOVE
# PERSON - REMOVE
# USER - REMOVE
# IMG - REMOVE?
# INDENT - Probably not an issue, but maybe just remove tags


class BBCODE:
    def __init__(self):
        pass

    def clean_ptp_description(self, desc, is_disc):
        # End my suffering
        desc = desc.replace('\r\n', '\n')
        # Remove links to PTP
        desc = desc.replace('http://passthepopcorn.me', '').replace('https://passthepopcorn.me', '')

        # Remove Mediainfo Tags / Attempt to regex out mediainfo
        mediainfo_tags = re.findall("\[mediainfo\][\s\S]*?\[\/mediainfo\]",  desc)
        if len(mediainfo_tags) >= 1:
            desc = re.sub("\[mediainfo\][\s\S]*?\[\/mediainfo\]", "", desc)
        elif is_disc != "BDMV":
            desc = re.sub("(^general\nunique)(.*?)^$", "", desc, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
            desc = re.sub("(^(video|audio|text)( #\d+)?\nid)(.*?)^$", "", desc, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
            desc = re.sub("(^(menu)( #\d+)?\n)(.*?)^$", "", desc, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
        elif is_disc == "BDMV":
            return ""

        # Remove Images in IMG tags:
        desc = re.sub("\[img\][\s\S]*?\[\/img\]", "", desc)
        desc = re.sub("\[img=[\s\S]*?\]", "", desc)

        # Remove Alignments:
        desc = re.sub("\[align=.*?\]", "", desc)
        desc = desc.replace("[/align]", "")
        # Remove Videos
        desc = re.sub("\[video\][\s\S]*?\[\/video\]", "", desc)

        #Remove Movie/Person/User/hr/Indent
        remove_list = [
            '[movie]', '[/movie]',
            '[artist]', '[/artist]',
            '[user]', '[/user]',
            '[indent]', '[/indent]',
            '[size]', '[/size]',
            '[hr]'
        ]
        for each in remove_list:
            desc = desc.replace(each, '')
     
       

        # Strip blank lines:
        desc = desc.rstrip()
        desc = re.sub("\n\n+", "\n\n", desc)

        if desc.replace('\n', '') == '':
            return ""
        return desc

    
    def convert_pre_to_code(self, desc):
        desc = desc.replace('[pre]', '[code]')
        desc = desc.replace('[/pre]', '[/code]')
        return desc
    

    def convert_hide_to_spoiler(self, desc):
        desc = desc.replace('[hide', '[spoiler')
        desc = desc.replace('[/hide]', '[/spoiler]')
        return desc
    
    

 
    def convert_comparison_to_collapse(self, desc, max_width):
        comparisons = re.findall("\[comparison=[\s\S]*?\[\/comparison\]", desc)
        for comp in comparisons:
            line = []
            output = []
            comp_sources = comp.split(']', 1)[0].replace('[comparison=', '').replace(' ', '').split(',')
            comp_images = comp.split(']', 1)[1].replace('[/comparison]', '').split('\n')
            screens_per_line = len(comp_sources)
            img_size = max_width / screens_per_line
            if img_size > 350:
                img_size = 350
            for img in comp_images:
                if img != "":
                    bb = f"[url={img}][img={img_size}]{img}[/img][/url]"
                    line.append(bb)
                    if len(line) == screens_per_line:
                        output.append(''.join(line))
                        line = []
            output = '\n'.join(output)
            new_bbcode = f"[spoiler={' vs '.join(comp_sources)}][center]{' | '.join(comp_sources)}[/center]\n{output}[/spoiler]"
            desc = desc.replace(comp, new_bbcode)
        return desc