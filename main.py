import discord
from discord.ext import commands
import os, youtube_dl, asyncio, random, pafy, threading, json
import googleapiclient.discovery
from urllib.parse import parse_qs, urlparse
from itertools import cycle

from youtubesearchpython import VideosSearch

storedsongdata = []
songqueue = []
loopSingle = False
loopQ = False

client = commands.Bot(command_prefix="")


# * Ignore Downloading if current and next are =
# Skip broken if loop

# Radio --> Random, Default (User based), Artist

def SaveJsonInfo():
    with open('data.txt', 'w') as outfile:
        json.dump(storedsongdata, outfile)


def LoadStoredSongs():
    global storedsongdata
    with open('data.txt') as json_file:
        storedsongdata = json.load(json_file)


def DownloadSong(name, arg):
    yops = {
        'format': 'bestaudio/best',
        'outtmpl': name
    }

    try:
        with youtube_dl.YoutubeDL(yops) as ydl:
            ydl.download(["https://www.youtube.com/watch?v=" + arg])
    except:
        print("Download Error")


def MakeMP3(arg, ctx):
    print("Make")
    print(arg)
    song = os.path.isfile("pong.mp3")

    if song:
        os.remove("pong.mp3")

    song2 = os.path.isfile("pong2.mp3")
    if song2:
        os.rename("pong2.mp3", "pong.mp3")
        # asyncio.run(PreDownload())
    else:
        DownloadSong("pong.mp3", arg)


async def SearchAndObtain(arg, ctx):
    await ctx.send("Searching YouTube for `" + arg + "`!")
    videosSearch = VideosSearch(arg, limit=1)
    res = videosSearch.result()
    print(res)
    eyedee = res["result"][0]["id"]
    await ctx.send("Found: `" + res["result"][0]["title"] + "`!")
    return eyedee


def ParseYTPlaylist(arg):
    print(arg)
    query = parse_qs(urlparse(arg).query, keep_blank_values=True)
    playlist_id = query["list"][0]
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey="AIzaSyDM1PCrOdZvXnyGdUolS5ovvcOeBb33Prk")
    request = youtube.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=50
    )
    response = request.execute()
    playlist_items = []
    while request is not None:
        response = request.execute()
        playlist_items += response["items"]
        request = youtube.playlistItems().list_next(request, response)

    retIDs = []
    for x in playlist_items:
        val = {"id": x["snippet"]["resourceId"]["videoId"]}
        retIDs.append(val)

    return retIDs


def GetAllInfo():
    for x in songqueue:
        GetIDInfo(x)
    print("All Songs Loaded")


def GetAllInfoCaller():
    download_thread = threading.Thread(target=GetAllInfo, name="Downloader")
    download_thread.start()


def FindStored(song):
    for x in storedsongdata:
        if x["id"] == song["id"]:
            return x
    return None


def AddtoStorage(song):
    storeitem = {}
    storeitem["title"] = song["title"]
    storeitem["length"] = song["length"]
    storeitem["id"] = song["id"]
    storeitem["users"] = [song["user"]]

    storedsongdata.append(storeitem)
    SaveJsonInfo()


def CheckUID(song, id):
    found = False
    for x in song["users"]:
        if x == id:
            found = True

    if not found:
        song["users"].append(id)
        return True

    return False


def GetIDInfo(val):
    if (val["length"] > 0):
        return

    storedsong = FindStored(val)

    if storedsong == None:
        url = "https://www.youtube.com/watch?v=" + val["id"]
        video = pafy.new(url)
        val["title"] = video.title
        val["length"] = video.length
        AddtoStorage(val)
    else:
        val["title"] = storedsong["title"]
        val["length"] = storedsong["length"]
        added = CheckUID(storedsong, val["user"])
        if added:
            SaveJsonInfo()


async def URLGrab(arg, UID, ctx):
    urllist = []
    if "youtu.be/" in arg:
        print("Song")
        startind = arg.index("youtu.be/") + 9
        val = arg[startind:startind + 11]
        urllist = [{"id": val}]
    elif "list=" in arg:
        print("List")
        urllist = ParseYTPlaylist(arg)
    elif "watch?v=" in arg:
        print("Song")
        startind = arg.index("watch?v=") + 8
        val = arg[startind:startind + 11]
        urllist = [{"id": val}]
    else:
        print("Search")
        urllist = [{"id": await SearchAndObtain(arg, ctx)}]

    for x in urllist:
        x["user"] = UID
        x["title"] = ""
        x["length"] = 0

    return urllist


async def PreDownload():
    print("Pre Download")
    song2 = os.path.isfile("pong2.mp3")
    if len(songqueue) > 1:
        if not song2:
            DownloadSong("pong2.mp3", songqueue[1])
    else:
        if song2:
            os.remove("pong2.mp3")


async def ReactionParse(ctx, msg, page, pagect):
    def getreact(reaction, user):
        return reaction.message.id == msg.id and user == ctx.message.author

    try:
        reaction, user = await client.wait_for('reaction_add', timeout=60.0, check=getreact)
    except asyncio.TimeoutError:
        await msg.clear_reactions()
        print("Timed Out")
    else:
        if str(reaction.emoji) == '⏩':
            page = page + 1
            if page > pagect:
                page = pagect
        elif str(reaction.emoji) == '⏪':
            page = page - 1
            if page < 1:
                page = 1

        embo = GenerateEmbed(page)
        await msg.edit(embed=embo)
        await msg.remove_reaction(reaction, user)
        await ReactionParse(ctx, msg, page, pagect)


def GenerateEmbed(page):
    pagect = ((len(songqueue) - 2) // 10) + 1
    queuestart = 1 + (10 * (page - 1))
    queueend = min(len(songqueue), 1 + (10 * page))

    ti = "Queued Items: `" + str(len(songqueue) - 1) + "` Song"
    if len(songqueue) != 2:
        ti += "s"

    page = "Page " + str(page) + "/" + str(pagect)
    output = ""
    GetIDInfo(songqueue[0])
    if (len(songqueue) == 1):
        output = "No Songs in Queue"
        page = "Page 0/0"
    else:
        for x in range(queuestart, queueend):
            GetIDInfo(songqueue[x])
            output += "`" + str(x) + ". [" + TimeFromSec(songqueue[x]["length"]) + "]` "
            if loopSingle and x == 1:
                output += " 🔂 "
            output += songqueue[x]["title"] + " - <@" + str(songqueue[x]["user"]) + ">\n"

    embo = discord.Embed(title=ti, description=output, color=discord.Color.red())

    if loopQ:
        page += " 🔁"

    embo.set_footer(text=page)
    return embo


def ClearSong(name):
    song = os.path.isfile(name)
    if song:
        os.remove(name)


async def CurrentlyPlaying(song, ctx):
    await ctx.send("`" + song["title"] + " [" + TimeFromSec(song["length"]) + "]` is currently playing!")


def TimeFromSec(secs):
    res = ""
    if secs >= 3600:
        hr = secs // 3600
        if hr < 10:
            res += "0"
        res += str(hr) + ":"
        secs -= 3600 * hr
    if secs > 60:
        mn = secs // 60
        if mn < 10:
            res += "0"
        res += str(mn) + ":"
        secs -= 60 * mn

    if secs < 10:
        res += "0"
    res += str(secs)
    return res


@client.command()
async def play(ctx, *, arg):
    VC = discord.utils.get(ctx.guild.voice_channels, name='General')
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if not voice or not voice.is_connected():
        await VC.connect()
        voice = discord.utils.get(client.voice_clients, guild=ctx.guild)

    arg = await URLGrab(arg, ctx.author.id, ctx)
    songqueue.extend(arg)

    print(arg)

    if not voice.is_playing():
        ClearSong("pong.mp3")
        ClearSong("pong2.mp3")
        MakeMP3(arg[0]["id"], ctx)
        voice.play(discord.FFmpegPCMAudio(executable="C:/Temp/ffmpeg/bin/ffmpeg.exe", source="pong.mp3"),
                   after=lambda e: next_song(ctx))

        GetIDInfo(arg[0])
        await ctx.send("Started Playing: " + arg[0]["title"] + " `" + TimeFromSec(arg[0]["length"]) + "`")
        if len(arg) > 1:
            await ctx.send("Added `" + str(len(arg) - 1) + "` Songs to the Queue!")
    else:
        await ctx.send("Added `" + str(len(arg)) + "` Songs to the Queue!")

    GetAllInfoCaller()
    # if len(songqueue) > 1:
    # await PreDownload()


def next_song(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    limit = 1
    if loopSingle or loopQ: limit = 0
    if len(songqueue) > limit:
        if not loopSingle:
            if loopQ:
                song = songqueue[0]
                songqueue.append(song)
            del songqueue[0]

        newsong = songqueue[0]["id"]
        if not loopSingle:
            MakeMP3(newsong, ctx)

        voice.play(discord.FFmpegPCMAudio(executable="C:/Temp/ffmpeg/bin/ffmpeg.exe", source="pong.mp3"),
                   after=lambda e: next_song(ctx))
    else:
        if len(songqueue) > 0:
            del songqueue[0]
            if not voice.is_playing():
                asyncio.run_coroutine_threadsafe(ctx.send("No more songs in queue."), client.loop)


@client.command()
async def leave(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_connected():
        await voice.disconnect()
    else:
        await ctx.send("Bot no in voice")


@client.command()
async def pause(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.pause()
        await ctx.send("Pausing `" + songqueue[0]["title"] + "`")
    else:
        await ctx.send("No music playing -.-")


@client.command()
async def resume(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_paused():
        voice.resume()
        await ctx.send("Resuming `" + songqueue[0]["title"] + "`")
    else:
        await ctx.send("Music aint paused boi -.-")


@client.command()
async def skip(ctx):
    global loopSingle
    temploop = loopSingle
    await ctx.send("Skipping: `" + songqueue[0]["title"] + "`")

    loopSingle = False
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    await CurrentlyPlaying(songqueue[1], ctx)
    voice.stop()
    loopSingle = temploop


@client.command()
async def stop(ctx):
    songqueue.clear()
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    voice.stop()
    await ctx.send("Stopped")


@client.command()
async def shuffle(ctx):
    id1 = songqueue.pop(0)
    random.shuffle(songqueue)
    songqueue.insert(0, id1)
    ClearSong("pong2.mp3")
    await ctx.send("Shuffling all `" + str(len(songqueue) - 1) + "` songs!")

    GetAllInfoCaller()
    # await PreDownload()


@client.command()
async def queue(ctx, *, arg=None):
    try:
        page = 0
        pagect = ((len(songqueue) - 2) // 10) + 1
        if arg != None:
            page = int(arg)

        if page <= 0 or page > pagect:
            page = 1

        embo = GenerateEmbed(page)

        await CurrentlyPlaying(songqueue[0], ctx)
        msg = await ctx.send(embed=embo)
        await msg.add_reaction('⏪')
        await msg.add_reaction('⏩')

        await ReactionParse(ctx, msg, page, pagect)

    except ValueError:
        await ctx.send("Please input a number for the queue or leave blank for page 1!")


@client.command()
async def nowplaying(ctx):
    print(songqueue[0])
    await CurrentlyPlaying(songqueue[0], ctx)


@client.command()
async def loop(ctx):
    global loopSingle
    loopSingle = not loopSingle
    await ctx.send("Loop Current Song: " + str(loopSingle))


@client.command()
async def loopqueue(ctx):
    global loopQ
    loopQ = not loopQ
    await ctx.send("Loop Queue: " + str(loopQ))


LoadStoredSongs()
client.run('ODgwNTAxMjIzMDMwMTUzMjU2.YSfMqg.6jxt8Zs8suNY6S0KxCLXYI6l3to')
