from discord.ext.commands.errors import CommandInvokeError
from src.prep import Prep
from src.args import Args
from src.clients import Clients
from src.search import Search
from src.trackers.BLU import Blu
import discord
from discord.ext import commands
import os
from datetime import datetime
import asyncio
import json
import shutil
import multiprocessing
from pathlib import Path
from pprint import pprint
from glob import glob
from termcolor import cprint



with open('data/config.json', 'r', encoding="utf-8") as f:
    config = json.load(f)
    f.close()




class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """
        This event receives the the guild when the bot joins.
        """
        print(f'Joined {guild.name} with {guild.member_count} users!')

    @commands.command(aliases=['up'])
    async def upload(self, ctx, path=None, *args):
        f"""
        Upload: for a list of arguments do {config['DISCORD']['command_prefix']}args
        """
        if ctx.channel.id != int(config['DISCORD']['discord_channel_id']):
            return

        if path == None:
            await ctx.send("Missing Path")
            return
        parser = Args(config)
        meta = dict()
        meta['base_dir'] = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        path = os.path.abspath(path)
        if os.path.exists(path):
            meta['path'] = path
            meta, help = parser.parse(args, meta)
            # await ctx.message.delete()
            prep = Prep(path=path, screens=meta['screens'], img_host=meta['img_host'], config=config)
            await ctx.send(f"Preparing to upload: `{path}`")
            meta = await prep.gather_prep(meta=meta)
            # await ctx.send(file=discord.File(f"{base_dir}/tmp/{folder_id}/Mediainfo.json"))
            await self.send_embed_and_upload(ctx, meta)
        else:
            await ctx.send("Invalid Path")


    @commands.command()
    async def args(self, ctx):
        f"""
        Arguments for {config['DISCORD']['command_prefix']}upload
        """
        await ctx.send("""
        ```Optional arguments:
    
            -s, --screens [SCREENS]
                                Number of screenshots
            -c, --category [{movie,tv,fanres}]
                                Category
            -t, --type [{disc,remux,encode,webdl,web-dl,webrip,hdtv}]
                                Type
            -res, --resolution 
                    [{2160p,1080p,1080i,720p,576p,576i,480p,480i,8640p,4320p,other}]
                                Resolution
            -tmdb, --tmdb [TMDB]
                                TMDb ID
            -g, --tag [TAG]
                                Group Tag
            -serv, --service [SERVICE]
                                Streaming Service
            -edition, --edition [EDITION]
                                Edition
            -d, --desc [DESC]
                                Custom Description (string)
            -nfo, --nfo           
                                Use .nfo in directory for description
            -k, --keywords [KEYWORDS]
                                Add comma seperated keywords e.g. 'keyword, keyword2, etc'
            -reg, --region [REGION]
                                Region for discs
            -a, --anon          Upload anonymously
            -st, --stream       Stream Optimized Upload
            -debug, --debug     Debug Mode```""")


    # @commands.group(invoke_without_command=True)
    # async def foo(self, ctx):
        # """
        # check out my subcommands!
        # """
        # await ctx.send('check out my subcommands!')
    
    # @foo.command(aliases=['an_alias'])
    # async def bar(self, ctx):
    #     """
    #     I have an alias!, I also belong to command 'foo'
    #     """
    #     await ctx.send('foo bar!')

  

    
    
    @commands.command()
    async def edit(self, ctx, uuid=None, *args):
        """
        Edit uuid w/ args
        """
        if ctx.channel.id != int(config['DISCORD']['discord_channel_id']):
            return
        if uuid == None:
            await ctx.send("Missing ID, please try again using the ID in the footer")
        parser = Args(config)
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        try:
            with open(f"{base_dir}/tmp/{uuid}/meta.json") as f:
                meta = json.load(f)
                f.close()
        except FileNotFoundError:
            await ctx.send("ID not found, please try again using the ID in the footer")
            return
        prep = Prep(path=Path(meta['path']), screens=meta['screens'], img_host=meta['img_host'], config=config) 
        meta, help = parser.parse(args, meta)
        msg = await ctx.fetch_message(meta['embed_msg_id'])
        await msg.delete()
        meta = await prep.tmdb_other_meta(meta)
        await self.send_embed_and_upload(ctx, meta)






    @commands.group(invoke_without_command=True)
    async def search(self, ctx, *, args=None):
        """
        Search for a file to upload
        """
        if ctx.channel.id != int(config['DISCORD']['discord_channel_id']):
            return
        search = Search(config=config)
        if args == None:
            await ctx.send("Missing search term(s)")
            return
        files_total = await search.searchFile(args)
        if files_total == []:
            await ctx.send("Nothing Found")
            return
        files = "\n\n• ".join(files_total)
        if not files_total:
            embed = discord.Embed(description="No files found")
        elif len(files_total) >= 2:
            embed = discord.Embed(title=f"File search results for: `{args}`", color=0x00ff40, description=f"```• {files}```")
            embed.add_field(name="What Now?", value=f"Please be more specific or use `{config['DISCORD']['command_prefix']}search dir` to find a directory")
            await ctx.send(embed=embed)
            return
        elif len(files_total) == 1:
            embed = discord.Embed(title=f"File search results for: {args}", color=0x00ff40, description=f"```{files}```")
            embed.set_footer(text=f"{config['DISCORD']['discord_emojis']['UPLOAD']} to Upload")
            message = await ctx.send(embed=embed)
            await message.add_reaction(config['DISCORD']['discord_emojis']['UPLOAD'])
            channel = message.channel


            def check(reaction, user):
                if reaction.message.id == message.id:
                    if str(user.id) == config['DISCORD']['admin_id']: 
                        if str(reaction.emoji) == config['DISCORD']['discord_emojis']['UPLOAD']:
                            return reaction
            

            try:
                await self.bot.wait_for("reaction_add", timeout=120, check=check)
            except asyncio.TimeoutError:
                await channel.send(f"Search: `{args}`timed out")
            else:
                await self.upload(ctx, files_total[0])



    @search.command()
    async def dir(self, ctx, *, args=None):
        """
        Search for a directory to upload
        """
        if ctx.channel.id != int(config['DISCORD']['discord_channel_id']):
            return
        search = Search(config=config)
        if args == None:
            await ctx.send("Missing search term(s)")
            return
        folders_total = await search.searchFolder(args)
        if folders_total == []:
            await ctx.send("Nothing Found")
            return
        folders = "\n\n• ".join(folders_total)
        if not folders_total:
            embed = discord.Embed(description="No files found")
        elif len(folders_total) >= 2:
            embed = discord.Embed(title=f"Directory search results for: `{args}`", color=0x00ff40, description=f"```• {folders}```")
            embed.add_field(name="What Now?", value=f"Please be more specific or use `{config['DISCORD']['command_prefix']}search dir` to find a directory")
            await ctx.send(embed=embed)
            return
        elif len(folders_total) == 1:
            embed = discord.Embed(title=f"Directory search results for: {args}", color=0x00ff40, description=f"```{folders}```")
            embed.set_footer(text=f"{config['DISCORD']['discord_emojis']['UPLOAD']} to Upload")
            message = await ctx.send(embed=embed)
            await message.add_reaction(config['DISCORD']['discord_emojis']['UPLOAD'])
            channel = message.channel


            def check(reaction, user):
                if reaction.message.id == message.id:
                    if str(user.id) == config['DISCORD']['admin_id']: 
                        if str(reaction.emoji) == config['DISCORD']['discord_emojis']['UPLOAD']:
                            return reaction
            

            try:
                await self.bot.wait_for("reaction_add", timeout=120, check=check)
            except asyncio.TimeoutError:
                await channel.send(f"Search: `{args}`timed out")
            else:
                await self.upload(ctx, folders_total[0])
        await ctx.send(folders_total)
    
    
    
    
    
    
    
    
    async def send_embed_and_upload(self,ctx,meta):
        prep = Prep(path=Path(meta['path']), screens=meta['screens'], img_host=meta['img_host'], config=config)
        meta['name_notag'], meta['name'], meta['clean_name'] = await prep.get_name(meta)
        #Upload Screens
        # await prep.upload_screens(meta, meta['screens'], 1, i=1)
        
        if meta.get('uploaded_screens', False) == False:
            u = multiprocessing.Process(target = prep.upload_screens, args=(meta, meta['screens'], 1, 1))
            u.start()
            while u.is_alive() == True:
                await asyncio.sleep(3)
            meta['uploaded_screens'] = True

        #Create base .torrent
        
        if len(glob(f"{meta['base_dir']}/tmp/{meta['uuid']}/BASE.torrent")) == 0:
            p = multiprocessing.Process(target = prep.create_torrent, args=(meta, Path(meta['path'])))
            p.start()
            while p.is_alive() == True:
                await asyncio.sleep(5)


        #Format for embed
        if meta['tag'] == "":
            tag = ""
        else:
            tag = f" / {meta['tag'][1:]}"
        if meta['imdb_id'] == "0":
            imdb = ""
        else:
            imdb = f" / [IMDb](https://www.imdb.com/title/{meta['imdb_id']})"
        if meta['tvdb_id'] == "0":
            tvdb = ""
        else:
            tvdb = f" / [TVDb](https://www.thetvdb.com/?id={meta['tvdb_id']}&tab=series)"


        embed=discord.Embed(title=f"Upload: {meta['title']}", url=f"https://www.themoviedb.org/{meta['category'].lower()}/{meta['tmdb']}", description=meta['overview'], color=0x0080ff, timestamp=datetime.utcnow())
        embed.add_field(name="Links", value=f"[TMDb](https://www.themoviedb.org/{meta['category'].lower()}/{meta['tmdb']}){imdb}{tvdb}")
        embed.add_field(name=f"{meta['resolution']} / {meta['type']}{tag}", value=f"```{meta['name']}```", inline=False)
        # embed.add_field(name=meta['type'], value=meta['resolution'], inline=True)
        embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/original{meta['poster']}")
        embed.set_footer(text=meta['uuid'])
        embed.set_author(name="L4G's Upload Assistant", url="https://github.com/L4GSP1KE/BluUpload", icon_url="https://images2.imgbox.com/6e/da/dXfdgNYs_o.png")
        message = await ctx.send(embed=embed)
        channel = message.channel
        await message.add_reaction(config['DISCORD']['discord_emojis']['BLU'])
        await asyncio.sleep(0.3)
        await message.add_reaction(config['DISCORD']['discord_emojis']['BHD'])
        await asyncio.sleep(0.3)
        await message.add_reaction(config['DISCORD']['discord_emojis']['MANUAL'])
        await asyncio.sleep(0.3)
        await message.add_reaction(config['DISCORD']['discord_emojis']['CANCEL'])
        await asyncio.sleep(0.3)
        await message.add_reaction(config['DISCORD']['discord_emojis']['UPLOAD'])

        meta['embed_msg_id'] = message.id
        #Save meta to json
        with open (f"{meta['base_dir']}/tmp/{meta['uuid']}/meta.json", 'w') as f:
            json.dump(meta, f, indent=4)
            f.close()
        
        
        def check(reaction, user):
            if reaction.message.id == meta['embed_msg_id']:
                if str(user.id) == config['DISCORD']['admin_id']: 
                    if str(reaction.emoji) == config['DISCORD']['discord_emojis']['UPLOAD']:
                        return reaction
                    if str(reaction.emoji) == config['DISCORD']['discord_emojis']['CANCEL']:
                        if meta['embed_msg_id']:
                            pass
                        raise CancelException
                    if str(reaction.emoji) == config['DISCORD']['discord_emojis']['MANUAL']:
                        raise ManualException
        try:
            await self.bot.wait_for("reaction_add", timeout=43200, check=check)
        except asyncio.TimeoutError:
            try:
                msg = await ctx.fetch_message(message.id)
                await channel.send(f"{meta['uuid']} timed out")
                return
            except:
                print("timeout after edit")
                pass
        except CancelException:
            await channel.send(f"{meta['title']} cancelled")
            return
        except ManualException:
            archive_url = await prep.package(meta)
            if archive_url == False:
                await channel.send(f"Unable to upload prep files, they can be found at `tmp/{meta['title']}.tar`")
            else:
                await channel.send(f"Files can be found at {archive_url} or `tmp/{meta['title']}.tar`")
            return
        else:
            
            #Check which are selected and upload to them
            msg = await ctx.fetch_message(message.id)
            tracker_list = list()
            tracker_emojis = config['DISCORD']['discord_emojis']
            while not tracker_list:
                await asyncio.sleep(1)
                for each in msg.reactions:
                    if each.count >= 2:
                        tracker = list(config['DISCORD']['discord_emojis'].keys())[list(config['DISCORD']['discord_emojis'].values()).index(str(each))]
                        if tracker not in ("UPLOAD"):
                            tracker_list.append(tracker)
                
            await channel.send(f"Uploading `{meta['name']}` to {tracker_list}")


            

            client = Clients(config=config)
            if "BLU" in tracker_list:
                blu = Blu(config=config)
                dupes = await blu.search_existing(meta)
                meta = await self.dupe_embed(dupes, meta, tracker_emojis, channel)
                if meta['upload'] == True:
                    await blu.upload(meta)
                    await client.add_to_client(meta, "BLU")
                    await channel.send(f"Uploaded `{meta['name']}`to BLU")
                    return
            if "BHD" in tracker_list:
                await channel.send("Uploading to BHD (coming soon:tm:)")
            return None
    
    
    
    async def dupe_embed(self, dupes, meta, emojis, channel):
        if not dupes:
            cprint("No dupes found", 'grey', 'on_green')
            meta['upload'] = True   
            return meta
        else:
            dupe_text = "\n\n•".join(dupes)
            dupe_text = f"```•{dupe_text}```"
            embed = discord.Embed(title="Are these dupes?", description=dupe_text, color=0xff0000)
            embed.set_footer(text=f"{emojis['CANCEL']} to abort upload | {emojis['UPLOAD']} to upload anyways") 
            message = await channel.send(embed=embed)
            await message.add_reaction(emojis['CANCEL'])
            await asyncio.sleep(0.3)
            await message.add_reaction(emojis['UPLOAD'])

            def check(reaction, user):
                if reaction.message.id == message.id:
                    if str(user.id) == config['DISCORD']['admin_id']: 
                        if str(reaction.emoji) == emojis['UPLOAD']:
                            return reaction
                        if str(reaction.emoji) == emojis['CANCEL']:
                            if meta['embed_msg_id']:
                                pass
                            raise CancelException

            try:
                await self.bot.wait_for("reaction_add", timeout=600, check=check)
            except asyncio.TimeoutError:
                try:
                    await channel.send(f"{meta['uuid']} timed out")
                    meta['upload'] = False
                except:
                    return
            except CancelException:
                await channel.send(f"{meta['title']} cancelled")
                meta['upload'] = False
            else:
                meta['upload'] = True
                for each in dupes:
                    if each == meta['name']:
                        meta['name'] = f"{meta['name']} DUPE?"

        return meta



def setup(bot):
    bot.add_cog(Commands(bot))





class CancelException(Exception):
    pass

class ManualException(Exception):
    pass
