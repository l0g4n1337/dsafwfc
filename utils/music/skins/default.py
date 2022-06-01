import datetime
from typing import Union

from ..models import LavalinkPlayer, YTDLPlayer
import disnake
from ..converters import fix_characters, time_format
import itertools


def load(player: Union[LavalinkPlayer, YTDLPlayer]) -> dict:

    data = {
        "content": None,
        "embeds": None
    }

    embed = disnake.Embed(color=player.bot.get_color(player.guild.me))
    embed_queue = None
    position_txt = ""
    vc_txt = ""

    if not player.paused:
        embed.set_author(
            name="In riproduzione:",
            icon_url="https://i.giphy.com/8L0Pbbkno5BI8n4CaI.gif"
        )

        if not player.current.is_stream:
            position_txt = f"\n> ⏲️ **⠂Termina:** " f"<t:{int((disnake.utils.utcnow() + datetime.timedelta(milliseconds=player.current.duration - player.position)).timestamp())}:R>"

    else:
        embed.set_author(
            name="In Pausa:",
            icon_url="https://cdn.discordapp.com/emojis/959006158151098388.png"
        )

    embed.set_footer(
        text=str(player),
        icon_url="https://cdn.discordapp.com/attachments/480195401543188483/907119505971486810/speaker-loud-speaker.gif"
    )

    if player.static:
        queue_size = 20
        queue_text_size = 33
        queue_img = ""
        playlist_text_size = 20

        try:
            vc_txt = f"\n> <:microphoneline:958987946525069332> **⠂Canale Vocale:** [`{player.guild.me.voice.channel.name}`](http://discordapp.com/channels/{player.guild.id}/{player.guild.me.voice.channel.id})"
        except AttributeError:
            pass

    else:
        queue_size = 3
        queue_text_size = 31
        queue_img = "https://i.imgur.com/lKRifSD.png"
        playlist_text_size = 13

    duration = "> 🔴 **⠂Durata:** `Livestream`" if player.current.is_stream else \
        f"> ⏰ **⠂Durata:** `{time_format(player.current.duration)}`"

    txt = f"[`{player.current.single_title}`]({player.current.uri})\n\n" \
          f"{duration}\n" \
          f"> <:albumauthorduotone:958976606003683369> **⠂Autore:** {player.current.authors_md}\n" \
          f"> <:faceheadphone:958985516357943337> **⠂Richiesto da:** {player.current.requester.mention}\n" \
          f"> <:volumehigh:958986651940556830> **⠂Volume:** `{player.volume}%`"

    if player.current.track_loops:
        txt += f"\n> 🔂 **⠂Ripetizioni restanti:** `{player.current.track_loops}`"

    if player.nightcore:
        txt += f"\n> 🇳 **⠂Effetto nightcore:** `Attivato`"

    if player.current.album:
        txt += f"\n> <:queue:959000316290945054> **⠂Album:** [`{fix_characters(player.current.album['name'], limit=playlist_text_size)}`]({player.current.album['url']})"

    if player.current.playlist:
        txt += f"\n> <:playlist:959485050901114940> **⠂Playlist:** [`{fix_characters(player.current.playlist['name'], limit=playlist_text_size)}`]({player.current.playlist['url']})"

    if player.nonstop:
        txt += "\n> <:reppeat:959001381052756039> **⠂Loop:** `Attivato`"

    if player.restrict_mode:
        txt += f"\n> 🔒 **⠂Restrizione:** `Attivata`"

    txt += f"{vc_txt}{position_txt}\n"

    if player.command_log:
        txt += f"```ini\n [Ultima Interazione]```**┕ {player.command_log_emoji} ⠂**{player.command_log}\n"

    if len(player.queue):

        queue_txt = "\n".join(
            f"`{n + 1}) [{time_format(t.duration) if not t.is_stream else '🔴 Livestream'}]` [`{fix_characters(t.title, queue_text_size)}`]({t.uri})"
            for n, t in (enumerate(itertools.islice(player.queue, queue_size)))
        )

        embed_queue = disnake.Embed(title=f"Brani in coda: {len(player.queue)}", color=player.bot.get_color(player.guild.me),
                                    description=f"\n{queue_txt}")

        if not player.nonstop:

            queue_duration = 0

            for t in player.queue:
                if not t.is_stream:
                    queue_duration += t.duration

            embed_queue.description += f"\n`[ <:hourglasx:959071281251246110> Tempo restante dei brani in coda` <t:{int((disnake.utils.utcnow() + datetime.timedelta(milliseconds=(queue_duration + player.current.duration) - player.position)).timestamp())}:R> `<:hourglasx:959071281251246110> ]`"

        embed_queue.set_image(url=queue_img)

    embed.description = txt

    if player.static:
        embed.set_image(url=player.current.thumb)
    else:
        embed.set_image(
            url="https://i.imgur.com/lKRifSD.png")
        embed.set_thumbnail(url=player.current.thumb)

    data["embeds"] = [embed_queue, embed] if embed_queue else [embed]

    return data
