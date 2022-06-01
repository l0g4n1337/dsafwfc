from __future__ import annotations
import disnake
import humanize
from disnake.ext import commands
from typing import TYPE_CHECKING, Union
from utils.music.checks import user_cooldown
from utils.music.converters import time_format
from utils.others import send_idle_embed
from utils.music.models import LavalinkPlayer, YTDLPlayer

if TYPE_CHECKING:
    from utils.client import BotCore

other_bots_vc_opts = commands.option_enum(
    {
        "Attivo": "enable",
        "Disattivo": "disable",
    }
)


desc_prefix = "🔧 [Impostazioni] 🔧 | "


class MusicSettings(commands.Cog):

    def __init__(self, bot: BotCore):
        self.bot = bot


    # O nome desse comando está sujeito a alterações (tá ridiculo, mas não consegui pensar em um nome melhor no momento).
    @commands.has_guild_permissions(administrator=True)
    @commands.slash_command(description=f"{desc_prefix}Consenti/impediscimi di connettermi a un canale in cui sono presenti altri bot.")
    async def dont_connect_other_bot_vc(
            self, inter: disnake.ApplicationCommandInteraction,
            opt: str = commands.Param(
                choices=["Attivo", "Disattivo"], description="Scelta: attivo o disattivo")
    ):

        guild_data = await self.bot.db.get_data(inter.guild.id, db_name="guilds")

        guild_data["check_other_bots_in_vc"] = opt == "Attivo"

        await self.bot.db.update_data(inter.guild.id, guild_data, db_name="guilds")

        embed = disnake.Embed(
            color=self.bot.get_color(inter.guild.me),
            description="**Impostazione salvata con successo!\n"
                        f"Ora {'no ' if opt == 'Attivo' else ''}mi collegherò ai canali in cui sono presenti altri bot.**"
        )

        await inter.send(embed=embed, ephemeral=True)


    @commands.has_guild_permissions(administrator=True)
    @commands.bot_has_guild_permissions(manage_channels=True, create_public_threads=True)
    @commands.dynamic_cooldown(user_cooldown(1,30), commands.BucketType.guild)
    @commands.slash_command(description=f"{desc_prefix}Crea un canale dedicato per richiedere musica al bot e lasciarlo sempre attivo.")
    async def setup(self, inter: disnake.AppCmdInter):

        if inter.channel.category and inter.channel.category.permissions_for(inter.guild.me).send_messages:
            target = inter.channel.category
        else:
            target = inter.guild

        perms = {
            inter.guild.default_role: disnake.PermissionOverwrite(
                embed_links=False,
                send_messages=True,
                send_messages_in_threads=True,
                read_messages=True,
                read_message_history=True
            ),
            inter.guild.me: disnake.PermissionOverwrite(
                embed_links=True,
                send_messages=True,
                send_messages_in_threads=True,
                read_messages=True,
                create_public_threads=True,
                read_message_history=True,
                manage_messages=True,
                manage_channels=True,
                attach_files=True,
            )
        }

        channel = await target.create_text_channel(
            f"🎶︲{self.bot.user.name} ",
            overwrites=perms
        )

        player: LavalinkPlayer = self.bot.music.players.get(inter.guild_id)

        if player:
            player.text_channel = channel
            await player.destroy_message()
            player.static = True
            await player.invoke_np()
            message = player.message

        else:
            message = await send_idle_embed(channel, bot=self.bot)

        await message.create_thread(name="𝗥𝗶𝗰𝗵𝗶𝗲𝗱𝗶 𝘂𝗻𝗮 𝗰𝗮𝗻𝘇𝗼𝗻𝗲 🎵")

        guild_data = await self.bot.db.get_data(inter.guild.id, db_name="guilds")

        guild_data['player_controller']['channel'] = str(channel.id)
        guild_data['player_controller']['message_id'] = str(message.id)
        await self.bot.db.update_data(inter.guild.id, guild_data, db_name='guilds')

        embed = disnake.Embed(description=f"**Canale creato: {channel.mention}**\n\nObs: Caso queira reverter esta configuração, apenas delete o canal {channel.mention}", color=self.bot.get_color(inter.guild.me))
        await inter.send(embed=embed, ephemeral=True)


    @commands.has_guild_permissions(administrator=True)
    @commands.dynamic_cooldown(user_cooldown(1, 7), commands.BucketType.guild)
    @commands.slash_command(description=f"{desc_prefix}Aggiungi un ruolo all'elenco dei DJ del server.")
    async def add_dj_role(
            self,
            inter: disnake.ApplicationCommandInteraction,
            role: disnake.Role = commands.Param(name="ruolo", description="Ruolo")
    ):

        if role == inter.guild.default_role:
            await inter.send("Non puoi aggiungere questo ruolo.", ephemeral=True)
            return

        guild_data = await self.bot.db.get_data(inter.guild.id, db_name="guilds")

        if str(role.id) in guild_data['djroles']:
            await inter.send(f"Il ruolo {role.mention} è già nell'elenco dei DJ", ephemeral=True)
            return

        guild_data['djroles'].append(str(role.id))

        await self.bot.db.update_data(inter.guild.id, guild_data, db_name="guilds")

        await inter.send(f"Il ruolo {role.mention} é stato aggiunto all`elenco dei DJ", ephemeral=True)


    @commands.has_guild_permissions(administrator=True)
    @commands.dynamic_cooldown(user_cooldown(1, 7), commands.BucketType.guild)
    @commands.slash_command(description=f"{desc_prefix}Rimuovere un ruolo dall'elenco dei DJ del server.")
    async def remove_dj_role(
            self,
            inter: disnake.ApplicationCommandInteraction,
            role: disnake.Role = commands.Param(name="ruolo", description="Ruolo")
    ):

        guild_data = await self.bot.db.get_data(inter.guild.id, db_name="guilds")

        if not guild_data['djroles']:

            await inter.send("Non ci sono ruoli nella lista dei DJ.", ephemeral=True)
            return

        guild_data = await self.bot.db.get_data(inter.guild.id, db_name="guilds")

        if str(role.id) not in guild_data['djroles']:
            await inter.send(f"Il ruolo {role.mention} non è nell'elenco dei DJ\n\n" + "Ruoli:\n" +
                             " ".join(f"<#{r}>" for r in guild_data['djroles']), ephemeral=True)
            return

        guild_data['djroles'].remove(str(role.id))

        await self.bot.db.update_data(inter.guild.id, guild_data, db_name="guilds")

        await inter.send(f"Il ruolo {role.mention} è stato rimosso dall'elenco dei DJ", ephemeral=True)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.slash_command(description=f"{desc_prefix}Visualizza le informazioni dei server musicali.")
    async def nodeinfo(self, inter: disnake.ApplicationCommandInteraction):

        em = disnake.Embed(color=self.bot.get_color(inter.guild.me), title="Server musicali:")

        if not self.bot.music.nodes:
            em.description = "**Non ci sono server.**"
            await inter.send(embed=em)
            return

        for identifier, node in self.bot.music.nodes.items():

            if not node.available: continue

            txt = f"Regione: `{node.region.title()}`\n"

            try:
                current_player = node.players[inter.guild.id]
            except KeyError:
                current_player = None

            if node.stats:
                used = humanize.naturalsize(node.stats.memory_used)
                total = humanize.naturalsize(node.stats.memory_allocated)
                free = humanize.naturalsize(node.stats.memory_free)
                cpu_cores = node.stats.cpu_cores
                cpu_usage = f"{node.stats.lavalink_load * 100:.2f}"
                started = node.stats.players

                ram_txt = f'RAM: `{used}/{free} ({total})`'

                txt += f'{ram_txt}\n' \
                       f'CPU Cores: `{cpu_cores}`\n' \
                       f'Uso della CPU: `{cpu_usage}%`\n' \
                       f'Uptime: `{time_format(node.stats.uptime)}\n`'

                if started:
                    txt += "Players: "
                    players = node.stats.playing_players
                    idle = started - players
                    if players:
                        txt += f'`[▶️{players}]`' + (" " if idle else "")
                    if idle:
                        txt += f'`[💤{idle}]`'

                    txt += "\n"

                if node.website:
                    txt += f'[`Website del server`]({node.website})\n'

            if current_player:
                status = "🌟"
            else:
                status = "✔️" if node.is_available else '❌'

            em.add_field(name=f'**{identifier}** `{status}`', value=txt)

        await inter.send(embed=em, ephemeral=True)


def setup(bot: BotCore):
    bot.add_cog(MusicSettings(bot))
