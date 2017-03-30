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
import io
import re
import os
import json
import base64
import asyncio
import discord
import aiohttp
import async_timeout
from time import time
from html import unescape
from random import choice
from cogs.utils import checks
from collections import Counter
from discord.ext import commands
from binascii import Error as PaddingError
from bs4 import BeautifulSoup

class Misc(object):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession(loop=self.bot.loop)

    @commands.command()
    async def ping(self, ctx):
        '''
        Test the bot's connection ping
        '''
        msg = "P{0}ng".format(choice("aeiou"))
        a = time()
        ping = await ctx.send(msg)
        b = time()
        await self.bot.edit_message(ping, " ".join([msg,"`{:.3f}ms`".format((b-a)*1000)]))

    @commands.command()
    async def info(self, ctx):
        """Bot Info"""
        result = ['**About Me:**']
        result.append('- Author: Henry#6174 (Discord ID: 122739797646245899)')
        result.append('- Library: discord.py (Python)')
        result.append('- Uptime: {}'.format(await self.bot.get_bot_uptime()))
        result.append('- Servers: {}'.format(len(self.bot.guilds)))
        result.append('- Commands Run: {}'.format(sum(self.bot.commands_used.values())))

        total_members = sum(len(s.members) for s in self.bot.guilds)
        total_online = sum(1 for m in self.bot.get_all_members() if m.status != discord.Status.offline)
        unique_members = set(self.bot.get_all_members())
        unique_online = sum(1 for m in unique_members if m.status != discord.Status.offline)
        channel_types = Counter(isinstance(c, discord.TextChannel) for c in self.bot.get_all_channels())
        voice = channel_types[False]
        text = channel_types[True]
        result.append('- Total Members: {} ({} online)'.format(total_members, total_online))
        result.append('- Unique Members: {} ({} online)'.format(len(unique_members), unique_online))
        result.append('- {} text channels, {} voice channels'.format(text, voice))

        await ctx.send('\n'.join(result), delete_after=20)

    @commands.command()
    async def totalcmds(self, ctx):
        '''Get totals of commands and their number of uses'''
        await ctx.send('\n'.join("{0}: {1}".format(val[0], val[1]) for val in self.bot.commands_used.items()))

    @commands.command()
    async def source(self, ctx, command: str = None):
        """Displays my full source code or for a specific command.
        To display the source code of a subcommand you have to separate it by
        periods, e.g. tag.create for the create subcommand of the tag command.
        """
        source_url = 'https://github.com/henry232323/Typheus'
        if command is None:
            await ctx.send(source_url)
            return

        code_path = command.split('.')
        obj = self.bot
        for cmd in code_path:
            try:
                obj = obj.get_command(cmd)
                if obj is None:
                    await ctx.send('Could not find the command ' + cmd)
                    return
            except AttributeError:
                await ctx.send('{0.name} command has no subcommands'.format(obj))
                return

        # since we found the command we're looking for, presumably anyway, let's
        # try to access the code itself
        src = obj.callback.__code__

        if not obj.callback.__module__.startswith('discord'):
            # not a built-in command
            location = os.path.relpath(src.co_filename).replace('\\', '/')
            final_url = '<{}/tree/master/{}#L{}>'.format(source_url, location, src.co_firstlineno)
        else:
            location = obj.callback.__module__.replace('.', '/') + '.py'
            base = 'https://github.com/Rapptz/discord.py'
            final_url = '<{}/blob/master/{}#L{}>'.format(base, location, src.co_firstlineno)

        await ctx.send(final_url)

    @commands.command()
    async def undertext(self, ctx, sprite: str, text: str):
        """Create an Undertale style text box
        https://github.com/valrus/undertale-dialog-generator
        Example Usage: ;undertext sprites/Papyrus/1.png "Sans!!!\""""
        try:
            words = text.split()
            lens = map(len, words)
            lines = []
            ctr = 0
            brk = 0
            for ix, leng in enumerate(lens):
                if ctr+leng > 25:
                    lines.append(" ".join(words[brk:ix]))
                    brk = ix
                    ctr = 0
                ctr += leng + 1
            lines.append(" ".join(words[brk:ix]))
            text = "\n".join(lines)
            async with ctx.channel.typing():
                async with aiohttp.ClientSession() as session:
                    sprite = "undertale/static/images/" + sprite
                    async with session.get('http://ianmccowan.nfshost.com/undertale/submit',
                                           params={'text': text,
                                                   'moodImg': sprite}) as response:
                        data = await response.read()
                    fp = io.BytesIO(base64.b64decode(data))
                    await ctx.send(file=fp, filename=text + ".png")
        except PaddingError:
            await ctx.send("API failure! Error Code: {} (You probably got the image path wrong)".format(response.status))


    @commands.command()
    async def uptime(self, ctx):
        """Check bot's uptime"""
        await ctx.send("```{}```".format(await self.bot.get_bot_uptime()))

    async def fetch(self, url):
        with async_timeout.timeout(10):
            async with self.session.get(url) as response:
                return await response.text()

    @commands.command()
    async def pol(self, ctx):
        """Do you like /pol?"""
        with ctx.channel.typing():
            for x in range(5):
                try:
                    api = json.loads(await self.fetch('https://a.4cdn.org/pol/catalog.json'))
                    html = choice(api[0]["threads"])["com"]
                    snd = BeautifulSoup(html, 'html.parser').get_text()
                    break
                except IndexError:
                    pass
            else:
                snd = "Failed to get a post!"
            print(snd)
            await ctx.send(snd, delete_after=300)

    @commands.command()
    @checks.nsfw_channel()
    async def fchan(self, ctx, board: str):
        """4 cham"""
        with ctx.channel.typing():
            for x in range(5):
                try:
                    api = json.loads(await self.fetch('https://a.4cdn.org/{}/catalog.json'.format(board)))
                    html = choice(api[0]["threads"])["com"]
                    snd = BeautifulSoup(html, 'html.parser').get_text()
                    break
                except IndexError:
                    pass
            else:
                snd = "Failed to get a post!"

            print(snd)
            await ctx.send(snd, delete_after=300)