import asyncio
import datetime
import json
import logging
import configparser
from pathlib import Path

import discord
from discord.ext import commands




def config_load():
    # JSON Config
    with open('data/config.json', 'r', encoding='utf-8') as doc:
         #  Please make sure encoding is correct, especially after editing the config file
        return json.load(doc)

async def run():
    """
    Where the bot gets started. If you wanted to create an database connection pool or other session for the bot to use,
    it's recommended that you create it here and pass it to the bot as a kwarg.
    """
    config = config_load()
    bot = Bot(config=config,
              description=config['DISCORD']['discord_bot_description'])
    try:
        await bot.start(config['DISCORD']['discord_bot_token'])
    except KeyboardInterrupt:
        await bot.logout()


class Bot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(
            command_prefix=self.get_prefix_,
            description=kwargs.pop('description')
        )
        self.start_time = None
        self.app_info = None
        self.config = config_load()
        self.loop.create_task(self.track_start())
        self.loop.create_task(self.load_all_extensions())

    async def track_start(self):
        """
        Waits for the bot to connect to discord and then records the time.
        Can be used to work out uptime.
        """
        await self.wait_until_ready()
        self.start_time = datetime.datetime.utcnow()

    async def get_prefix_(self, bot, message):
        """
        A coroutine that returns a prefix.

        I have made this a coroutine just to show that it can be done. If you needed async logic in here it can be done.
        A good example of async logic would be retrieving a prefix from a database.
        """
        prefix = [self.config['DISCORD']['command_prefix']]
        return commands.when_mentioned_or(*prefix)(bot, message)

    async def load_all_extensions(self):
        """
        Attempts to load all .py files in /cogs/ as cog extensions
        """
        await self.wait_until_ready()
        await asyncio.sleep(1)  # ensure that on_ready has completed and finished printing
        cogs = [x.stem for x in Path('cogs').glob('*.py')]
        for extension in cogs:
            try:
                self.load_extension(f'cogs.{extension}')
                print(f'loaded {extension}')
            except Exception as e:
                error = f'{extension}\n {type(e).__name__} : {e}'
                print(f'failed to load extension {error}')
            print('-' * 10)
        

    async def on_ready(self):
        """
        This event is called every time the bot connects or resumes connection.
        """
        print('-' * 10)
        self.app_info = await self.application_info()
        print(f'Logged in as: {self.user.name}\n'
              f'Using discord.py version: {discord.__version__}\n'
              f'Owner: {self.app_info.owner}\n')
        print('-' * 10)
        channel = self.get_channel(int(self.config['DISCORD']['discord_channel_id']))
        await channel.send(f'{self.user.name} is now online')

    async def on_message(self, message):
        """
        This event triggers on every message received by the bot. Including one's that it sent itself.

        If you wish to have multiple event listeners they can be added in other cogs. All on_message listeners should
        always ignore bots.
        """
        if message.author.bot:
            return  # ignore all bots
        await self.process_commands(message)


    
    


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
