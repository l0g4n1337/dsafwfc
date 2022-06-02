import datetime
from typing import Union
import disnake
import re
import json
from user_agent import generate_user_agent

URL_REG = re.compile(r'https?://(?:www\.)?.+')
YOUTUBE_VIDEO_REG = re.compile(r"(https?://)?(www\.)?youtube\.(com|nl)/watch\?v=([-\w]+)")


replaces = [
    ('&quot;', '"'),
    ('&amp;', '&'),
    ('(', '\u0028'),
    (')', '\u0029'),
    ('[', '【'),
    (']', '】'),
    ("  ", " "),
    ("*", '"'),
    ("_", ' '),
    ("{", "\u0028"),
    ("}", "\u0029"),
    ("`", "'")
]


perms_translations = {
	"create_instant_invite": "Crea un invito istantaneo",
	"kick_members": "Espelli membri",
	"ban_members": "Banna membri",
	"administrator": "Amminiistratore",
	"manage_channels": "Gestire canali",
	"manage_guild": "Gestire server",
	"add_reactions": "Aggiungere reazioni",
	"view_audit_log": "Ver o registro de auditoria",
	"priority_speaker": "Voz prioritária",
	"stream": "In onda sui canali vocali",
	"read_messages": "leggere i messaggi",
	"send_messages": "Manda messaggi",
	"send_tts_messages": "Invia messaggi in TTS",
	"manage_messages": "Gestire i messaggi",
	"embed_links": "inserire links",
	"attach_files": "Allegare files",
	"read_message_history": "Visualizza la cronologia dei messaggi",
	"mention_everyone": "Menzionare tutti",
	"external_emojis": "Usa emoji esterni",
	"view_guild_insights": "Visualizza le informazioni sul server",
	"connect": "Connetti",
	"speak": "Parlare",
	"mute_members": "Silenzia membri",
	"deafen_members": "Deafen membri",
	"move_members": "Spostare i membri",
	"use_voice_activation": "Usa attivazione vocale",
	"change_nickname": "Cambia nickname",
	"manage_nicknames": "Gestire i nicknames",
	"manage_roles": "Gestire i ruoli",
	"manage_webhooks": "Gestire i webhooks",
	"manage_emojis": "Gestire gli emojis",
	"use_slash_commands": "Usare comandii slash",
}

u_agent = generate_user_agent()


async def node_suggestions(inter, query: str):

    try:
        node = inter.bot.music.players[inter.guild.id].node
    except KeyError:
        node = None

    if not query:

        return [n.identifier for n in inter.bot.music.nodes.values() if n != node and n.available and n.is_available]

    return [n.identifier for n in inter.bot.music.nodes.values() if n != node
            and query.lower() in n.identifier.lower() and n.available and n.is_available]


async def google_search(bot, query: str, *, max_entries: int = 20) -> list:

    if URL_REG.match(query):
        return [query]

    async with bot.session.get(
            f"http://suggestqueries.google.com/complete/search?client=chrome&ds=yt&q={query}",
            headers={'User-Agent': u_agent}) as r:
        return json.loads(await r.text())[1][:max_entries]


async def search_suggestions(inter, query: str):

    if not query:
        return []

    if not inter.author.voice:
        return []

    return await google_search(inter.bot, query)


def queue_tracks(inter, query: str):

    if not inter.author.voice:
        return

    try:
        player = inter.bot.music.players[inter.guild.id]
    except KeyError:
        return

    return [f">pos {n+1} - {track.title}"[:100] for n, track in enumerate(player.queue) if query.lower() in track.title.lower()][:20]


def queue_playlist(inter, query: str):

    if not inter.author.voice:
        return

    try:
        player = inter.bot.music.players[inter.guild.id]
    except KeyError:
        return

    return list(set([track.playlist['name'] for track in player.queue if track.playlist and
                               query.lower() in track.playlist['name'].lower()]))[:20]


async def fav_list(inter, query: str, *, prefix=""):

    return [f"{prefix}{favname}" for favname in (await inter.bot.db.get_data(inter.author.id, db_name="users"))["fav_links"]
            if not query or query.lower() in favname.lower()][:20]


async def fav_add_autocomplete(inter, query: str):

    if not inter.author.voice:
        return [query]

    favs: list = await fav_list(inter, query, prefix="> fav: ")

    if not query or (favs_size:=len(favs)) >= 20:
        return favs

    return await google_search(inter.bot, query, max_entries=20-favs_size) + favs


def queue_author(inter, query):

    if not query:
        return

    if not inter.author.voice:
        return

    try:
        player = inter.bot.music.players[inter.guild.id]
    except KeyError:
        return

    return list(set([track.author for track in player.queue if query.lower() in track.author.lower()]))[:20]


def seek_suggestions(inter, query):

    if query:
        return

    try:
        player = inter.bot.music.players[inter.guild.id]
    except KeyError:
        return

    if not player.current or player.current.is_stream:
        return

    seeks = []

    if player.current.duration >= 90000:
        times = [int(n * 0.5 * 10) for n in range(20)]
    else:
        times = [int(n * 1 * 10) for n in range(20)]

    for p in times:
        percent = percentage(p, player.current.duration)
        seeks.append(f"{time_format(percent)} | {p}%")

    return seeks


def get_button_style(enabled: bool, red=True):
    if enabled:
        if red:
            return disnake.ButtonStyle.red
        return disnake.ButtonStyle.green
    return disnake.ButtonStyle.grey


def fix_characters(text: str, limit: int = 0):

    for r in replaces:
        text = text.replace(r[0], r[1])

    if limit:
        text = f"{text[:limit]}..." if len(text) > limit else text

    return text


def time_format(milliseconds: Union[int, float], use_names: bool = False) -> str:

    minutes, seconds = divmod(int(milliseconds / 1000), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    if use_names:

        times = []

        for time_, name in (
                (days, "giorno"),
                (hours, "ora"),
                (minutes, "minuto"),
                (seconds,"secondo")
        ):
            if not time_:
                continue

            times.append(f"{time_} {name}"[:-1] + ("i" if time_ > 1 else ""))

        try:
            last_time = times.pop()
        except IndexError:
            last_time = None
            times = ["1 secondo"]

        strings = ", ".join(t for t in times)

        if last_time:
            strings += f" e {last_time}" if strings else last_time

    else:

        strings = f"{minutes:02d}:{seconds:02d}"

        if hours:
            strings = f"{hours}:{strings}"

        if days:
            strings = (f"{days} giorni" if days > 1 else f"{days} giorno") + (f", {strings}" if strings != "00:00" else "")

    return strings


time_names = ["seconds", "minutes", "hours"]


def string_to_seconds(time):
    try:

        times = reversed(time.split(':'))
        time_dict = {}

        for n, t in enumerate(times):
            time_dict[time_names[n]] = int(t)

        return datetime.timedelta(**time_dict).total_seconds()

    except:
        return


def percentage(part, whole):
  return int((part * whole) / 100.0)


def queue_track_index(inter: disnake.AppCmdInter, query: str, check_all: bool = False):

    player = inter.bot.music.players[inter.guild.id]

    query_split = query.lower().split()

    tracklist = []

    for counter, track in enumerate(player.queue):

        track_title = track.title.lower().split()

        q_found = 0

        for q in query_split:
            for t in track_title:
                if q in t:
                    q_found += 1
                    track_title.remove(t)
                    break

        if q_found == len(query_split):

            tracklist.append((counter, track,))
            if not check_all:
                break

    return tracklist
