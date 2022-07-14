import re
import html
import urllib.parse
from termcolor import cprint

# Bold - KEEP
# Italic - KEEP
# Underline - KEEP
# Strikethrough - KEEP
# Color - KEEP
# URL - KEEP
# PARSING - Probably not exist in uploads
# Spoiler - KEEP

# QUOTE - CONVERT to CODE
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
        # Convert Bullet Points to -
        desc = desc.replace("&bull;", "-")

        # Unescape html
        desc = html.unescape(desc)
        # End my suffering
        desc = desc.replace('\r\n', '\n')

        # Remove url tags with PTP links
        ptp_url_tags = re.findall("(\[url[\=\]]https?:\/\/passthepopcorn\.m[^\]]+)([^\[]+)(\[\/url\])?", desc)
        if ptp_url_tags != []:
            for ptp_url_tag in ptp_url_tags:
                ptp_url_tag = ''.join(ptp_url_tag)
                url_tag_removed = re.sub("(\[url[\=\]]https?:\/\/passthepopcorn\.m[^\]]+])", "", ptp_url_tag)
                url_tag_removed = url_tag_removed.replace("[/url]", "")
                desc = desc.replace(ptp_url_tag, url_tag_removed)

        # Remove links to PTP
        desc = desc.replace('http://passthepopcorn.me', 'PTP').replace('https://passthepopcorn.me', 'PTP')

        # Remove Mediainfo Tags / Attempt to regex out mediainfo
        mediainfo_tags = re.findall("\[mediainfo\][\s\S]*?\[\/mediainfo\]",  desc)
        if len(mediainfo_tags) >= 1:
            desc = re.sub("\[mediainfo\][\s\S]*?\[\/mediainfo\]", "", desc)
        elif is_disc != "BDMV":
            desc = re.sub("(^general\nunique)(.*?)^$", "", desc, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
            desc = re.sub("(^(Format[\s]{2,}:))(.*?)^$", "", desc, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
            desc = re.sub("(^(video|audio|text)( #\d+)?\nid)(.*?)^$", "", desc, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
            desc = re.sub("(^(menu)( #\d+)?\n)(.*?)^$", "", f"{desc}\n\n", flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
        elif is_disc in ["BDMV", "DVD"]:
            return ""


        # Convert Quote tags:
        desc = re.sub("\[quote.*?\]", "[code]", desc)
        desc = desc.replace("[/quote]", "[/code]")
       
        # Remove Alignments:
        desc = re.sub("\[align=.*?\]", "", desc)
        desc = desc.replace("[/align]", "")

        # Remove size tags
        desc = re.sub("\[size=.*?\]", "", desc)
        desc = desc.replace("[/size]", "")

        # Remove Videos
        desc = re.sub("\[video\][\s\S]*?\[\/video\]", "", desc)

        # Remove Staff tags
        desc = re.sub("\[staff[\s\S]*?\[\/staff\]", "", desc)


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
     
       #Catch Stray Images
        comps = re.findall("\[comparison=[\s\S]*?\[\/comparison\]", desc)
        hides = re.findall("\[hide[\s\S]*?\[\/hide\]", desc)
        comps.extend(hides)
        nocomp = desc
        comp_placeholders = []

        # Replace comparison/hide tags with placeholder because sometimes uploaders use comp images as loose images
        for i in range(len(comps)):
            nocomp = nocomp.replace(comps[i], '')
            desc = desc.replace(comps[i], f"COMPARISON_PLACEHOLDER-{i}")
            comp_placeholders.append(comps[i])


        # Remove Images in IMG tags:
        desc = re.sub("\[img\][\s\S]*?\[\/img\]", "", desc)
        desc = re.sub("\[img=[\s\S]*?\]", "", desc)
        # Replace Images
        loose_images = re.findall("(https?:\/\/.*\.(?:png|jpg))", nocomp, flags=re.IGNORECASE)
        if len(loose_images) >= 1:
            for image in loose_images:
                desc = desc.replace(image, '')
        # Re-place comparisons
        if comp_placeholders != []:
            for i, comp in enumerate(comp_placeholders):
                desc = desc.replace(f"COMPARISON_PLACEHOLDER-{i}", comp)

        # Strip blank lines:
        desc = desc.rstrip()
        desc = re.sub("\n\n+", "\n\n", desc)
        while desc.startswith('\n'):
            desc = desc.replace('\n', '', 1)
        desc = desc.rstrip()

        if desc.replace('\n', '') == '':
            return ""
        return desc

    
    def clean_unit3d_description(self, desc, site):
        # Unescape html
        desc = html.unescape(desc)
        # End my suffering
        desc = desc.replace('\r\n', '\n')

        # Remove links to site
        site_netloc = urllib.parse.urlparse(site).netloc
        site_regex = f"(\[url[\=\]]https?:\/\/{site_netloc}/[^\]]+])([^\[]+)(\[\/url\])?"
        site_url_tags = re.findall(site_regex, desc)
        if site_url_tags != []:
            for site_url_tag in site_url_tags:
                site_url_tag = ''.join(site_url_tag)
                url_tag_regex = f"(\[url[\=\]]https?:\/\/{site_netloc}[^\]]+])"
                url_tag_removed = re.sub(url_tag_regex, "", site_url_tag)
                url_tag_removed = url_tag_removed.replace("[/url]", "")
                desc = desc.replace(site_url_tag, url_tag_removed)

        desc = desc.replace(site_netloc, site_netloc.split('.')[0])

        # Temporarily hide spoiler tags
        spoilers = re.findall("\[spoiler[\s\S]*?\[\/spoiler\]", desc)
        nospoil = desc
        spoiler_placeholders = []
        for i in range(len(spoilers)):
            nospoil = nospoil.replace(spoilers[i], '')
            desc = desc.replace(spoilers[i], f"SPOILER_PLACEHOLDER-{i}")
            spoiler_placeholders.append(spoilers[i])
        
        # Get Images from outside spoilers
        imagelist = []
        url_tags = re.findall("\[url=[\s\S]*?\[\/url\]", desc)
        if url_tags != []:
            for tag in url_tags:
                image = re.findall("\[img[\s\S]*?\[\/img\]", tag)
                if len(image) == 1:
                    image_dict = {}
                    img_url = image[0].lower().replace('[img]', '').replace('[/img]', '')
                    image_dict['img_url'] = image_dict['raw_url'] = re.sub("\[img[\s\S]*\]", "", img_url)
                    url_tag = tag.replace(image[0], '')
                    image_dict['web_url'] = re.match("\[url=[\s\S]*?\]", url_tag, flags=re.IGNORECASE)[0].lower().replace('[url=', '')[:-1]
                    imagelist.append(image_dict)
                    desc = desc.replace(tag, '')

        # Remove bot signatures
        desc = desc.replace("[img=35]https://blutopia/favicon.ico[/img] [b]Uploaded Using [url=https://github.com/HDInnovations/UNIT3D]UNIT3D[/url] Auto Uploader[/b] [img=35]https://blutopia/favicon.ico[/img]", '')
        desc = re.sub("\[center\].*Created by L4G's Upload Assistant.*\[\/center\]", "", desc, flags=re.IGNORECASE)

        # Replace spoiler tags
        if spoiler_placeholders != []:
            for i, spoiler in enumerate(spoiler_placeholders):
                desc = desc.replace(f"SPOILER_PLACEHOLDER-{i}", spoiler)

        # Check for empty [center] tags
        centers = re.findall("\[center[\s\S]*?\[\/center\]", desc)
        if centers != []:
            for center in centers:
                full_center = center
                replace = ['[center]', ' ', '\n', '[/center]']
                for each in replace:
                    center = center.replace(each, '')
                if center == "":
                    desc = desc.replace(full_center, '')

        # Convert Comparison spoilers to [comparison=]
        if spoilers != []:
            for i in range(len(spoilers)):
                tag = spoilers[i]
                images = re.findall("\[img[\s\S]*?\[\/img\]", tag)
                if len(images) >= 6:
                    comp_images = []
                    final_sources = []
                    for image in images:
                        image_url = re.sub("\[img[\s\S]*\]", "", image.replace('[/img]', ''))
                        comp_images.append(image_url)
                    sources = re.match("\[spoiler=[\s\S]*?\]", tag)[0].replace('[spoiler=', '')[:-1]
                    sources = re.sub("comparison", "", sources, flags=re.IGNORECASE)
                    for each in ['vs', ',', '|']:
                        sources = sources.split(each)
                        sources = "$".join(sources)
                    sources = sources.split("$")
                    for source in sources:
                        final_sources.append(source.strip())
                    comp_images = '\n'.join(comp_images)
                    final_sources = ', '.join(final_sources)
                    spoil2comp = f"[comparison={final_sources}]{comp_images}[/comparison]"
                    desc = desc.replace(tag, spoil2comp)

        
        # Strip blank lines:
        desc = desc.rstrip()
        desc = re.sub("\n\n+", "\n\n", desc)
        while desc.startswith('\n'):
            desc = desc.replace('\n', '', 1)
        desc = desc.rstrip()

        if desc.replace('\n', '') == '':
            return "", imagelist
        
        return desc, imagelist

















    def convert_pre_to_code(self, desc):
        desc = desc.replace('[pre]', '[code]')
        desc = desc.replace('[/pre]', '[/code]')
        return desc
    

    def convert_hide_to_spoiler(self, desc):
        desc = desc.replace('[hide', '[spoiler')
        desc = desc.replace('[/hide]', '[/spoiler]')
        return desc
    
    def convert_spoiler_to_hide(self, desc):
        desc = desc.replace('[spoiler', '[hide')
        desc = desc.replace('[/spoiler]', '[/hide]')
        return desc
    
    def convert_code_to_quote(self, desc):
        desc = desc.replace('[code', '[quote')
        desc = desc.replace('[/code]', '[/quote]')

 
    def convert_comparison_to_collapse(self, desc, max_width):
        comparisons = re.findall("\[comparison=[\s\S]*?\[\/comparison\]", desc)
        for comp in comparisons:
            line = []
            output = []
            comp_sources = comp.split(']', 1)[0].replace('[comparison=', '').replace(' ', '').split(',')
            comp_images = comp.split(']', 1)[1].replace('[/comparison]', '').replace(',', '\n').replace(' ', '\n')
            comp_images = re.findall("(https?:\/\/.*\.(?:png|jpg))", comp_images, flags=re.IGNORECASE)
            screens_per_line = len(comp_sources)
            img_size = int(max_width / screens_per_line)
            if img_size > 350:
                img_size = 350
            for img in comp_images:
                img = img.strip()
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


    def convert_comparison_to_centered(self, desc, max_width):
        comparisons = re.findall("\[comparison=[\s\S]*?\[\/comparison\]", desc)
        for comp in comparisons:
            line = []
            output = []
            comp_sources = comp.split(']', 1)[0].replace('[comparison=', '').replace(' ', '').split(',')
            comp_images = comp.split(']', 1)[1].replace('[/comparison]', '').replace(',', '\n').replace(' ', '\n')
            comp_images = re.findall("(https?:\/\/.*\.(?:png|jpg))", comp_images, flags=re.IGNORECASE)
            screens_per_line = len(comp_sources)
            img_size = int(max_width / screens_per_line)
            if img_size > 350:
                img_size = 350
            for img in comp_images:
                img = img.strip()
                if img != "":
                    bb = f"[url={img}][img={img_size}]{img}[/img][/url]"
                    line.append(bb)
                    if len(line) == screens_per_line:
                        output.append(''.join(line))
                        line = []
            output = '\n'.join(output)
            new_bbcode = f"[center]{' | '.join(comp_sources)}\n{output}[/center]"
            desc = desc.replace(comp, new_bbcode)
        return desc