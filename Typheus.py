#!/usr/bin/python3
# Copyright (c) 2016-2017, rhodochrosite.xyz
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
import asyncio
import discord
from discord.ext import commands

import markovify

import os
import sys
import json
import logging
import datetime
from collections import Counter

from cogs import *
from WebServer import CmdRunner

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass


class Typheus(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.owner_id = 122739797646245899
        self.lounge_id = 166349353999532035
        self.uptime = datetime.datetime.utcnow()
        self.commands_used = Counter()
        self.debug = "debug" in sys.argv
        self.shutdowns = []
        self.cogs = {"Admin": Admin.Admin(self),
                     "Misc": Misc.Misc(self),
                     "ChannelUtils": ChannelUtils.ChannelUtils(self),
                     "RPG": RPG.RPG(self)}
        self.running = True

        with open("resources/dave.txt", "rb") as tsf:
            self._model_base = tsf.read().decode("utf-8", 'replace')
        self._markov_model = markovify.NewlineText(self._model_base)

        self.logger = logging.getLogger('discord')  # Discord Logging
        self.logger.setLevel(logging.DEBUG)
        self.handler = logging.FileHandler(filename=os.path.join('resources', 'discord.log'), encoding='utf-8', mode='w')
        self.handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.logger.addHandler(self.handler)

        asyncio.ensure_future(self.runserv())

    async def on_ready(self):
        for cog in self.cogs.values():
            self.add_cog(cog)
        # Login info
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

        for guild in self.guilds:
            try:
                print("\t".join((guild.id, guild.name,)))
            except UnicodeEncodeError:
                print("\t".join((guild.id, "Unknown Characters")))
            except TypeError:
                pass

        await self.change_presence(game=discord.Game(name=";help for help!"))

    async def on_message(self, message):
        if message.author.bot:
            return

        if self.user.mentioned_in(message):
            try:
                await self.markov_mention(message)
            except discord.errors.Forbidden:
                pass

        await self.process_commands(message)

    async def on_command(self, ctx):
        command = ctx.command
        self.commands_used[command.name] += 1
        if isinstance(ctx.message.channel, (discord.DMChannel, discord.GroupChannel)):  # Log command usage in discord logs
            destination = 'Private Message'
        else:
            destination = '#{0.channel.name} ({0.guild.name})'.format(ctx.message)

        self.logger.info('{0.created_at}: {0.author.name} in {1}: {0.content}'.format(ctx.message, destination))

    async def on_command_error(self, error, ctx):
        """
        Universal handling for discord errors, will print unknown errors,
        and silently pass Forbidden errors.
        """
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send('This command cannot be used in private messages.')
        elif isinstance(error, commands.DisabledCommand):
            await ctx.send('Sorry. This command is disabled and cannot be used.')
        elif isinstance(error, discord.errors.Forbidden):
            pass
        elif isinstance(error, commands.CommandInvokeError):
            try:
                await ctx.send('```python\n'+str(error)+'\n```')
            except discord.errors.Forbidden:
                pass
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("You do not have permission to use this command or it is disabled here!")

    async def markov_mention(self, message):
        response = self._markov_model.make_sentence(tries=100)
        await message.channel.send(response)

    async def get_bot_uptime(self):
        """Get time between now and when the bot went up"""
        now = datetime.datetime.utcnow()
        delta = now - self.uptime
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        if days:
            fmt = '{d} days, {h} hours, {m} minutes, and {s} seconds'
        else:
            fmt = '{h} hours, {m} minutes, and {s} seconds'

        return fmt.format(d=days, h=hours, m=minutes, s=seconds)

    async def runserv(self):
        self.cmd = CmdRunner(self)
        self.webserv = self.cmd.app
        srv = self.webserv.start('0.0.0.0', 5000)
        await srv

def main():
    with open("resources/auth", 'rb') as ath:
        auth = json.loads(ath.read().decode("utf-8", "replace"))[0]

    loop = asyncio.get_event_loop()
    prefix = ';' if 'debug' not in sys.argv else '$'
    invlink = "https://discordapp.com/oauth2/authorize?client_id=284456340879966231&scope=bot&permissions=305196074"
    description = "Typheus, a little discord bot by Henry#6174\n{invlink}".format(invlink=invlink)
    async def starter():
        typheus = Typheus(
            loop=loop,
            description=description,
            command_prefix=prefix,
            pm_help=True)

        await typheus.start(*auth)
        for shutdown in typheus.shutdowns:
            await shutdown()

        while typheus.running:
            typheus = Typheus(
                              loop=loop,
                              description=description,
                              command_prefix=prefix,
                              pm_help=True)

            await typheus.start(*auth)
            for shutdown in typheus.shutdowns:
                await shutdown

    loop.run_until_complete(starter())

if __name__ == "__main__":
    main()