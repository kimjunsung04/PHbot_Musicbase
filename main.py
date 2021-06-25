# -*- coding: utf-8 -*-
import discord
import os, requests
import numpy as np
import random, datetime
import nacl, ffmpeg
import youtube_dl
import asyncio
import time
import math

from youtubesearchpython import VideosSearch
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.tools import argparser

client = discord.Client()

queues = {}
musiclist = {}
nowplay = {}
vote = {}

token = "봇 토큰"
prf = "봇 접두사"


def print_progress(
    iteration, total, prefix="Progress:", suffix="Complete", decimals=1, bar_length=10
):
    str_format = "{0:." + str(decimals) + "f}"
    current_progress = iteration / float(total)
    percents = str_format.format(100 * current_progress)
    filled_length = int(round(bar_length * current_progress))
    bar = ":yellow_square:" * filled_length + ":black_large_square:" * (
        bar_length - filled_length
    )
    return bar


def hms(s):
    hours = s // 3600
    s = s - hours * 3600
    mu = s // 60
    ss = s - mu * 60
    data = f"[{hours}:{mu}:{ss}]"
    return data


@client.event
async def on_ready():
    print("ready")
    print(client.user.id)
    print(client.user.name)
    print(f"{len(client.guilds)}개의 서버에 참여중")
    print(f"{len(client.users)}명이 이용중")
    print("=====================================")


@client.event
async def on_message(message):

    if message.author.bot:
        return

    def check_queue(id, user_id):
        try:
            if id in nowplay:  # 지금노래
                nowplay[id].pop(0)
            now_p = musiclist[id][0]
            start = time.time()
            now_p = [now_p[0], now_p[1], now_p[2], now_p[3], start]
            if id in nowplay:  # 지금노래
                nowplay[id].append(now_p)
            else:
                nowplay[id] = [now_p]  # 딕셔너리 쌍 추가
            now_vol = 1
            player = discord.PCMVolumeTransformer(queues[id].pop(0), volume=now_vol)
            musiclist[id].pop(0)
            message.guild.voice_client.play(
                player, after=lambda e: check_queue(message.guild.id, message.author.id)
            )
        except IndexError:  # 대기열 비었을때 - 예약했다가 다 끝남
            try:
                del nowplay[id]
            except KeyError:
                pass
        except KeyError:  # 대기열 없을때
            try:
                del nowplay[id]
            except KeyError:
                pass
        except AttributeError:
            del musiclist[id]
            del queues[id]
            try:
                del nowplay[id]
            except KeyError:
                pass
            try:
                del vote[id]
            except KeyError:
                pass

    if message.content.startswith(f"{prf}재생"):
        try:
            url = message.content[4:]
            print(url)
            server = message.guild
            if url == "":
                return await message.channel.send(
                    "+재생 `유튜브 링크` - 입력한 유튜브 링크를 재생해줍니다.\n+재생 `노래제목` - 입력한 노래제목을 유튜브에서 찾아줍니다."
                )
            try:
                if (
                    message.guild.voice_client.channel.id
                    != message.author.voice.channel.id
                ):
                    if server.id in nowplay:
                        return await message.channel.send(
                            f"이미 **{message.guild.voice_client.channel}** 에서 재생중입니다."
                        )
                    else:
                        await message.guild.voice_client.disconnect()
            except AttributeError:
                pass
            try:
                cash_d = message.author.voice.channel.id
            except AttributeError:
                return await message.channel.send("먼저 음성채널에 참가해주세요!")
            if "http" in url:
                if "playlist?list=" in url:
                    return await message.channel.send(
                        embed=discord.Embed(
                            title=f"재생▶",
                            description=f"재생목록은 재생할수 없습니다.",
                            color=0x0170ED,
                        )
                    )
                if ("?list=" in url) or ("&list=" in url):
                    if "?list=" in url:
                        if "&v=" in url:
                            url = str(url.split("&v=")[1])
                            url = f"https://www.youtube.com/watch?v={url}"
                        else:
                            url = str(url.split("?list=")[0])
                    elif "&list=" in url:
                        url = str(url.split("&list=")[0])
                ydl = youtube_dl.YoutubeDL({"outtmpl": "%(id)s%(ext)s"})
                # Add all the available extractors
                ydl.add_default_info_extractors()

                result = ydl.extract_info(
                    url, download=False  # We just want to extract the info
                )

                if "entries" in result:
                    # Can be a playlist or a list of videos
                    Video = result["entries"][0]
                else:
                    m_url = result

                    title = m_url["title"]

                    msd = int(m_url["duration"])

                    live = m_url["is_live"]

                    m_url = m_url["formats"][1]["url"]
                m_urld = url
            else:
                if ":" in url:
                    url = str(url.replace(":", ""))
                try:
                    videosSearch = VideosSearch(f"{url}", limit=1)
                except Exception:
                    videosSearch = VideosSearch(f"{url}", limit=1)
                ytde = videosSearch.result()
                y_id = ytde["result"][0]["id"]
                url = f"https://www.youtube.com/watch?v={y_id}"
                ydl = youtube_dl.YoutubeDL({"outtmpl": "%(id)s%(ext)s"})
                # Add all the available extractors
                ydl.add_default_info_extractors()

                result = ydl.extract_info(
                    url, download=False  # We just want to extract the info
                )

                if "entries" in result:
                    # Can be a playlist or a list of videos
                    Video = result["entries"][0]
                else:
                    m_url = result

                    title = m_url["title"]

                    msd = int(m_url["duration"])

                    live = m_url["is_live"]

                    m_url = m_url["formats"][1]["url"]
                m_urld = f"https://www.youtube.com/watch?v={y_id}"
            try:
                is_p = message.guild.voice_client.is_playing()
            except AttributeError:
                is_p = False
            if is_p == True:  # 예약
                now_vol = 1
                player = discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(
                        source=m_url,
                        before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                    ),
                    volume=now_vol,
                )
                if server.id in queues:
                    queues[server.id].append(player)
                else:
                    queues[server.id] = [player]  # 딕셔너리 쌍 추가
                dgy = len(queues[server.id])
                if live == True:
                    msd = "LIVE"
                mdp = [m_urld, title, message.author.id, msd]
                if server.id in musiclist:
                    musiclist[server.id].append(mdp)
                else:
                    musiclist[server.id] = [mdp]  # 딕셔너리 쌍 추가
                if live == True:
                    cho = f"[**{mdp[3]}**]"
                else:
                    cho = f"**{hms(mdp[3])}**"
                mant = f"[{title}]({m_urld}) {cho} 를\n**{dgy}번** 대기열에 예약하였습니다!"
                return await message.channel.send(
                    embed=discord.Embed(
                        title=f"예약📥", description=f"{mant}", color=0x0170ED
                    )
                )
            server = message.guild
            if live == True:
                msd = "LIVE"
                start = 0
            else:
                start = time.time()
            now_p = [m_urld, title, message.author.id, msd, start]
            if live == True:
                cho = f"[**{now_p[3]}**]"
            else:
                cho = f"**{hms(now_p[3])}**"
            if server.id in nowplay:  # 지금노래
                nowplay[server.id].append(now_p)
            else:
                nowplay[server.id] = [now_p]  # 딕셔너리 쌍 추가
            mant = f"[{title}]({m_urld}) {cho} 를 재생합니다!"
            now_vol = 1
            source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(
                    source=m_url,
                    before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                ),
                volume=now_vol,
            )
            try:
                mis = message.guild.voice_client.is_connected()
            except AttributeError:
                mis = False
            if mis == False:
                voice = await client.get_channel(
                    message.author.voice.channel.id
                ).connect()
                voice.play(
                    source,
                    after=lambda e: check_queue(message.guild.id, message.author.id),
                )
            else:
                message.guild.voice_client.play(
                    source,
                    after=lambda e: check_queue(message.guild.id, message.author.id),
                )

            await message.channel.send(
                embed=discord.Embed(title=f"재생▶", description=f"{mant}", color=0x0170ED)
            )
        except youtube_dl.utils.DownloadError:
            return await message.channel.send(
                embed=discord.Embed(
                    title=f"재생▶",
                    description=f"알수없는 링크입니다.\n링크를 다시한번 확인해주세요,",
                    color=0x0170ED,
                )
            )
        except discord.errors.Forbidden:
            print("메세지 전송실패")
        except IndexError:
            return await message.channel.send(
                embed=discord.Embed(
                    title=f"재생▶",
                    description=f"알수없는 링크입니다.\n링크를 다시한번 확인해주세요,",
                    color=0x0170ED,
                )
            )

    if message.content.startswith(f"{prf}검색"):
        url = message.content[4:]
        print(url)
        if "http" in url:
            return await message.channel.send(
                embed=discord.Embed(
                    title=f"검색🔍", description=f"링크는 검색할수 없습니다!", color=0x0170ED
                )
            )
        server = message.guild
        author = message.author
        url_md = message.content[4:]
        if len(url_md) >= 15:
            url_mdk = f"{url_md[:15]}..."
        else:
            url_mdk = url_md
        try:
            videosSearch = VideosSearch(f"{url_md}", limit=5)
        except Exception:
            videosSearch = VideosSearch(f"{url_md}", limit=5)
        ytde = videosSearch.result()
        i = 0
        con = ""
        url_cash = "https://www.youtube.com/watch?v="
        while i <= 4:
            if i == 0:
                ca = "1️⃣"
            elif i == 1:
                ca = "2️⃣"
            elif i == 2:
                ca = "3️⃣"
            elif i == 3:
                ca = "4️⃣"
            elif i == 4:
                ca = "5️⃣"
            try:
                con += f"{ca} [{ytde['result'][i]['title']}]({url_cash}{ytde['result'][i]['id']}) [{ytde['result'][i]['duration']}]\n"
            except IndexError:
                con = "검색결과 없음"
                break
            i += 1
        tg = await message.channel.send(
            embed=discord.Embed(
                title=f"{url_mdk}에 대한 검색결과🔍", description=f"{con}", color=0x0170ED
            )
        )
        try:
            await tg.add_reaction("1️⃣")
            await tg.add_reaction("2️⃣")
            await tg.add_reaction("3️⃣")
            await tg.add_reaction("4️⃣")
            await tg.add_reaction("5️⃣")
            await tg.add_reaction("❌")
        except discord.errors.Forbidden:
            return await message.channel.send(
                f"PH봇이 반응을 추가할수 없습니다!\n`반응 추가하기` 권한을 확인해주세요!\n<@{message.author.id}>"
            )
        try:

            def diary_write_check(reaction, user):
                return (
                    user == author
                    and str(reaction) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "❌"]
                    and tg.id == reaction.message.id
                )  # 이모지 리액션 부분

            reaction, user = await client.wait_for(
                "reaction_add", timeout=30.0, check=diary_write_check
            )  # 이모지 리액션 부분
        except asyncio.exceptions.TimeoutError:
            return await message.channel.send("입력시간 시간초과")
        if str(reaction.emoji) == "1️⃣":
            await tg.clear_reactions()
            y_id = ytde["result"][0]["id"]
        if str(reaction.emoji) == "2️⃣":
            await tg.clear_reactions()
            y_id = ytde["result"][1]["id"]
        if str(reaction.emoji) == "3️⃣":
            await tg.clear_reactions()
            y_id = ytde["result"][2]["id"]
        if str(reaction.emoji) == "4️⃣":
            await tg.clear_reactions()
            y_id = ytde["result"][3]["id"]
        if str(reaction.emoji) == "5️⃣":
            await tg.clear_reactions()
            y_id = ytde["result"][4]["id"]
        if str(reaction.emoji) == "❌":
            await tg.clear_reactions()
            return await tg.edit(
                embed=discord.Embed(
                    title=f"검색🔍", description=f"검색을 취소하였습니다!", color=0x0170ED
                )
            )

        url = f"https://www.youtube.com/watch?v={y_id}"
        ydl = youtube_dl.YoutubeDL({"outtmpl": "%(id)s%(ext)s"})
        # Add all the available extractors
        ydl.add_default_info_extractors()

        result = ydl.extract_info(
            url, download=False  # We just want to extract the info
        )

        if "entries" in result:
            # Can be a playlist or a list of videos
            Video = result["entries"][0]
        else:
            m_url = result

            title = m_url["title"]

            msd = int(m_url["duration"])

            m_url = m_url["formats"][1]["url"]
        m_urld = url
        mant = f"[{title}]({m_urld}) 를 재생합니다!"
        try:
            is_p = message.guild.voice_client.is_playing()
        except AttributeError:
            is_p = False
        if is_p == True:  # 예약
            now_vol = 1
            player = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(
                    source=m_url,
                    before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                ),
                volume=now_vol,
            )
            if server.id in queues:
                queues[server.id].append(player)
            else:
                queues[server.id] = [player]  # 딕셔너리 쌍 추가
            dgy = len(queues[server.id])
            mant = f"[{title}]({m_urld}) 를\n**{dgy}번** 대기열에 예약하였습니다!"
            start = time.time()
            mdp = [m_urld, title, message.author.id, msd]
            if server.id in musiclist:
                musiclist[server.id].append(mdp)
            else:
                musiclist[server.id] = [mdp]  # 딕셔너리 쌍 추가
            return await tg.edit(
                embed=discord.Embed(title=f"예약📥", description=f"{mant}", color=0x0170ED)
            )
        server = message.guild
        start = time.time()
        now_p = [m_urld, title, message.author.id, msd, start]
        if server.id in nowplay:  # 지금노래
            nowplay[server.id].append(now_p)
        else:
            nowplay[server.id] = [now_p]  # 딕셔너리 쌍 추가
        now_vol = 1
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                source=m_url,
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            ),
            volume=now_vol,
        )
        try:
            mis = message.guild.voice_client.is_connected()
        except AttributeError:
            mis = False
        if mis == False:
            voice = await client.get_channel(message.author.voice.channel.id).connect()
            voice.play(
                source, after=lambda e: check_queue(message.guild.id, message.author.id)
            )
        else:
            message.guild.voice_client.play(
                source, after=lambda e: check_queue(message.guild.id, message.author.id)
            )
        await tg.edit(
            embed=discord.Embed(title=f"검색🔍", description=f"{mant}", color=0x0170ED)
        )

    if message.content == f"{prf}스킵":
        server = message.guild
        try:
            client.get_channel(message.author.voice.channel.id)
        except AttributeError:
            return await message.channel.send("먼저 음성채널에 참가해주세요!")
        try:
            if message.guild.voice_client.channel.id == message.author.voice.channel.id:
                try:
                    qd = nowplay[message.guild.id][0]
                    is_p = message.guild.voice_client.is_playing()
                except AttributeError:
                    return await message.channel.send("현재 노래가 재생중이 아닙니다!")
                except KeyError:
                    return await message.channel.send("현재 노래가 재생중이 아닙니다!")
                if is_p == True:
                    if int(qd[2]) == message.author.id:
                        if server.id in vote:
                            del vote[server.id]
                        message.guild.voice_client.stop()
                        return await message.channel.send(
                            embed=discord.Embed(
                                title=f"스킵⏭",
                                description=f"노래가 스킵되었습니다!",
                                color=0x0170ED,
                            )
                        )
                    else:
                        mvm = message.author.voice.channel.members
                        mvm_num = int(len(mvm))
                        server = message.guild
                        if server.id not in vote:
                            vote[server.id] = []
                        vote_d = [message.author.id]
                        if f"{message.author.id}" in str(vote[server.id]):
                            return await message.channel.send(
                                embed=discord.Embed(
                                    title=f"스킵⏭",
                                    description=f"이미 스킵에 투표하였습니다.",
                                    color=0x0170ED,
                                )
                            )
                        if server.id in vote:
                            vote[server.id].append(vote_d)
                        else:
                            vote[server.id] = [vote_d]  # 딕셔너리 쌍 추가
                        if mvm_num > 3:  # 2명보다 크다면
                            mvm_num_nng = int(round(mvm_num - 2, 2))
                            if int(len(vote[server.id])) == mvm_num_nng:
                                del vote[server.id]
                                message.guild.voice_client.stop()
                                return await message.channel.send(
                                    embed=discord.Embed(
                                        title=f"스킵⏭",
                                        description=f"재생중인 노래가 투표에 의해 스킵되었습니다.",
                                        color=0x0170ED,
                                    )
                                )
                            else:
                                return await message.channel.send(
                                    embed=discord.Embed(
                                        title=f"스킵⏭",
                                        description=f"스킵투표를 하였습니다. ({(len(vote[server.id]))}/{mvm_num_nng})투표",
                                        color=0x0170ED,
                                    )
                                )
                        else:
                            return await message.channel.send(
                                embed=discord.Embed(
                                    title=f"스킵⏭",
                                    description=f"참가인원이 2명밖에 없어 투표할수 없습니다.\n노래를 재생한사람이 스킵해주세요!",
                                    color=0x0170ED,
                                )
                            )

                        return await message.channel.send(
                            embed=discord.Embed(
                                title=f"스킵⏭",
                                description=f"자신이 추가한 노래만 스킵할 수 있습니다!",
                                color=0x0170ED,
                            )
                        )
                else:
                    await message.channel.send("현재 노래가 재생중이 아닙니다!")
            else:
                return await message.channel.send("PH봇과 같은 음성채널에 있어야합니다!")
        except AttributeError:
            return await message.channel.send(
                embed=discord.Embed(
                    title=f"스킵⏭", description=f"노래가 재생중이 아닙니다!", color=0x0170ED
                )
            )

    if message.content == f"{prf}지금노래":
        try:
            server = message.guild
            if server.id in nowplay:
                now_p = nowplay[server.id][0]
            else:
                return await message.channel.send("현재는 재생중인 노래가 없습니다.")
            if str(now_p[3]) == "LIVE":
                return await message.channel.send(
                    embed=discord.Embed(
                        title=f"지금노래🎵",
                        description=f"[{now_p[1]}]({now_p[0]}) [**{now_p[3]}**] 가 재생중입니다.\n재생한 사람 : <@{now_p[2]}>",
                        color=0x0170ED,
                    )
                )
            await message.channel.send(
                embed=discord.Embed(
                    title=f"지금노래🎵",
                    description=f"[{now_p[1]}]({now_p[0]}) 가 재생중입니다.\n{print_progress(int(time.time()) - int(now_p[4]),now_p[3])}**{hms((time.time()) - int(now_p[4]))}/{now_p[3]}**\n재생한 사람 : <@{now_p[2]}>",
                    color=0x0170ED,
                )
            )
        except IndexError:
            return await message.channel.send("현재는 재생중인 노래가 없습니다.")

    if message.content.startswith(f"{prf}대기열삭제"):
        try:
            client.get_channel(message.author.voice.channel.id)
        except AttributeError:
            return await message.channel.send("먼저 음성채널에 참가해주세요!")
        try:
            if message.guild.voice_client.channel.id == message.author.voice.channel.id:
                try:
                    num = int(message.content[7:])
                    server = message.guild
                    pd_n = len(musiclist[server.id])
                except IndexError:
                    return await message.channel.send(
                        embed=discord.Embed(
                            title=f"대기열삭제🗑",
                            description=f"노래가 재생중이 아닙니다.",
                            color=0x0170ED,
                        )
                    )
                except KeyError:
                    return await message.channel.send(
                        embed=discord.Embed(
                            title=f"대기열삭제🗑",
                            description=f"노래가 재생중이 아닙니다.",
                            color=0x0170ED,
                        )
                    )
                except ValueError:
                    return await message.channel.send(
                        embed=discord.Embed(
                            title=f"대기열삭제🗑",
                            description=f"명령어 사용법을 확인해주세요!\n!대기열삭제 [대기열번호(정수)]",
                            color=0x0170ED,
                        )
                    )
                try:
                    qd = musiclist[server.id][num - 1]
                except IndexError:
                    return await message.channel.send(
                        embed=discord.Embed(
                            title=f"대기열삭제🗑",
                            description=f"일치하는 대기열번호가 없습니다.",
                            color=0x0170ED,
                        )
                    )
                if num == 0:
                    return await message.channel.send(
                        embed=discord.Embed(
                            title=f"대기열삭제🗑",
                            description=f"일치하는 대기열번호가 없습니다.",
                            color=0x0170ED,
                        )
                    )
                if int(qd[2]) == message.author.id:
                    del queues[server.id][num - 1]
                    del musiclist[server.id][num - 1]
                    await message.channel.send(
                        embed=discord.Embed(
                            title=f"대기열삭제🗑",
                            description=f"대기열 **{num}**번이 삭제되었습니다.",
                            color=0x0170ED,
                        )
                    )
                else:
                    await message.channel.send(
                        embed=discord.Embed(
                            title=f"대기열삭제🗑",
                            description=f"자신이 추가한 노래만 삭제 가능합니다!",
                            color=0x0170ED,
                        )
                    )
            else:
                return await message.channel.send("PH봇과 같은 음성채널에 있어야합니다!")
        except AttributeError:
            return await message.channel.send(
                embed=discord.Embed(
                    title=f"대기열삭제🗑", description=f"노래가 재생중이 아닙니다!", color=0x0170ED
                )
            )

    if message.content == f"{prf}대기열":
        server = message.guild
        author = message.author
        try:
            con = ""
            num = 1
            i = 0
            try:
                while True:
                    da = musiclist[server.id][i]
                    if str(da[3]) == "LIVE":
                        da_cho = f"[**{da[3]}**]"
                    else:
                        da_cho = f"**{hms(da[3])}**"
                    con += f"{num}번 - [{da[1]}]({da[0]}) {da_cho} - <@{da[2]}>\n"
                    num += 1
                    i += 1
                    if i == 10:
                        break
            except:
                pass
            page_d = len(musiclist[server.id])
            if page_d > 10:

                page_d_m = page_d / 10
                max_p = math.ceil(page_d_m)
                page = 1
                embed = discord.Embed(
                    title="대기열🗃",
                    description=f"{con}",
                    color=0x0170ED,
                    timestamp=message.created_at,
                )
                embed.set_footer(
                    text=f"페이지 : {page} / {max_p}", icon_url=client.user.avatar_url
                )
                tg = await message.channel.send(embed=embed)
                while True:
                    await tg.add_reaction("◀")
                    await tg.add_reaction("⏹")
                    await tg.add_reaction("▶")

                    def diary_write_check(reaction, user):
                        return (
                            user == author
                            and str(reaction) in ["◀", "⏹", "▶"]
                            and tg.id == reaction.message.id
                        )  # 이모지 리액션 부분

                    reaction, user = await client.wait_for(
                        "reaction_add", timeout=30.0, check=diary_write_check
                    )  # 이모지 리액션 부분
                    if str(reaction.emoji) == "◀":
                        await tg.clear_reactions()
                        if page - 1 == 0:
                            con = ""
                            num = 1
                            i = 0
                            try:
                                while True:
                                    da = musiclist[server.id][i]
                                    if str(da[3]) == "LIVE":
                                        da_cho = f"[**{da[3]}**]"
                                    else:
                                        da_cho = f"**{hms(da[3])}**"
                                    con += f"{num}번 - [{da[1]}]({da[0]}) {da_cho} - <@{da[2]}>\n"
                                    num += 1
                                    i += 1
                                    if i == 10:
                                        break
                            except:
                                pass
                        else:
                            page = 1
                            con = ""
                            num = 1
                            i = 0
                            try:
                                while True:
                                    da = musiclist[server.id][i]
                                    if str(da[3]) == "LIVE":
                                        da_cho = f"[**{da[3]}**]"
                                    else:
                                        da_cho = f"**{hms(da[3])}**"
                                    con += f"{num}번 - [{da[1]}]({da[0]}) {da_cho} - <@{da[2]}>\n"
                                    num += 1
                                    i += 1
                                    if i == 10:
                                        break
                            except:
                                pass
                    if str(reaction.emoji) == "▶":
                        await tg.clear_reactions()
                        if page == max_p:
                            pass
                        else:
                            con = ""
                            fd = page * 10
                            num = fd + 1
                            i = fd
                            i_max = i + 10
                            try:
                                while True:
                                    da = musiclist[server.id][i]
                                    if str(da[3]) == "LIVE":
                                        da_cho = f"[**{da[3]}**]"
                                    else:
                                        da_cho = f"**{hms(da[3])}**"
                                    con += f"{num}번 - [{da[1]}]({da[0]}) {da_cho} - <@{da[2]}>\n"
                                    num += 1
                                    i += 1
                                    if i == i_max:
                                        break
                            except:
                                pass
                            page += 1

                    if str(reaction.emoji) == "⏹":
                        await tg.clear_reactions()
                        break

                    embed = discord.Embed(
                        title="대기열🗃",
                        description=f"{con}",
                        color=0x0170ED,
                        timestamp=message.created_at,
                    )
                    embed.set_footer(
                        text=f"페이지 : {page} / {max_p}", icon_url=client.user.avatar_url
                    )
                    await tg.edit(embed=embed)

            else:

                if con == "":
                    return await message.channel.send(
                        embed=discord.Embed(
                            title=f"대기열🗃",
                            description=f"현재 대기열이 비어있습니다.",
                            color=0x0170ED,
                        )
                    )
                await message.channel.send(
                    embed=discord.Embed(
                        title=f"대기열🗃", description=f"{con}", color=0x0170ED
                    )
                )
        except KeyError:
            await message.channel.send("대기중인 노래가 없습니다.")
        except asyncio.exceptions.TimeoutError:
            await tg.clear_reactions()


client.run(token)
