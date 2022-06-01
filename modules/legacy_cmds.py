from __future__ import annotations
import asyncio
import os
import shutil
import json
import subprocess
from io import BytesIO
from typing import Union, Optional, TYPE_CHECKING
import disnake
import wavelink
from disnake.ext import commands
from utils.client import BotCore
from utils.music.checks import check_voice, check_requester_channel
from utils.music.interactions import AskView
from utils.music.models import LavalinkPlayer, YTDLPlayer
from utils.others import sync_message
from utils.owner_panel import panel_command, PanelView
from utils.music.errors import GenericError
from jishaku.shell import ShellReader
if TYPE_CHECKING:
    from utils.others import CustomContext

os_quote = "\"" if os.name == "nt" else "'"
git_format = f"--pretty=format:{os_quote}%H*****%h*****%s*****%ct{os_quote}"


def format_git_log(data_list: list):

    data = []

    for d in data_list:
        if not d:
            continue
        t = d.split("*****")
        data.append({"commit": t[0], "abbreviated_commit": t[1], "subject": t[2], "timestamp": t[3]})

    return data


def replaces(txt):

    if os.name == "nt":
        return txt.replace("\"", f"\\'").replace("'", "\"")

    return txt.replace("\"", f"\\\"").replace("'", "\"")


async def run_command(cmd):

    result = []

    with ShellReader(cmd) as reader:

        async for x in reader:
            result.append(x)

    result_txt = "\n".join(result)

    if "[stderr]" in result_txt:
        raise Exception(result_txt)

    return result_txt


def run_command_old(cmd):
    return subprocess.check_output(cmd, shell=True).decode('utf-8').strip()


class Owner(commands.Cog):

    def __init__(self, bot: BotCore):
        self.bot = bot
        self.git_init_cmds = [
            "git init",
            f'git remote add origin {self.bot.config["SOURCE_REPO"]}',
            'git fetch origin',
            'git checkout -b main -f --track origin/main'
        ]
        self.owner_view: Optional[PanelView] = None


    def format_log(self, data: list):
        return "\n".join(f"[`{c['abbreviated_commit']}`]({self.bot.remote_git_url}/commit/{c['commit']}) `- "
                         f"{(c['subject'][:60] + '...') if len(c['subject']) > 59 else c['subject']}`" for c in data)

    @commands.is_owner()
    @panel_command(aliases=["rd", "ricaricare"], description="Ricarica i moduli.", emoji="🔄",
                   alt_name="Carica/Ricarica moduli.")
    async def reload(self, ctx: Union[commands.Context, disnake.MessageInteraction]):

        data = self.bot.load_modules()

        txt = ""

        if data["loaded"]:
            txt += f'**Moduli caricati:** ```ansi\n[0;34m{" [0;37m| [0;34m".join(data["loaded"])}```\n'

        if data["reloaded"]:
            txt += f'**Moduli ricaricati:** ```ansi\n[0;32m{" [0;37m| [0;32m".join(data["reloaded"])}```\n'

        if data["error"]:
            txt += f'**Moduli che hanno fallito:** ```ansi\n[0;31m{" [0;37m| [0;31m".join(data["error"])}```\n'

        if not txt:
            txt = "**Nessun modulo trovato...**"

        if isinstance(ctx, commands.Context):
            embed = disnake.Embed(colour=self.bot.get_color(ctx.me), description=txt)
            await ctx.send(embed=embed, view=self.owner_view)
        else:
            return txt


    @commands.is_owner()
    @commands.max_concurrency(1, commands.BucketType.default)
    @panel_command(aliases=["up", "atualizar"], description="Atualizar meu code usando o git.",
                   emoji="<:git:944873798166020116>", alt_name="Atualizar Bot")
    async def update(self, ctx: Union[commands.Context, disnake.MessageInteraction], *,
                     opts: str = ""): #TODO: Rever se há alguma forma de usar commands.Flag sem um argumento obrigatório, ex: --pip.

        out_git = ""

        git_log = []

        force = "--force" in opts

        requirements_old = ""
        try:
            with open("./requirements.txt") as f:
                requirements_old = f.read()
        except:
            pass

        if not os.path.isdir("./.git") or force:

            out_git += await self.cleanup_git(force=force)

        else:

            try:
                await ctx.response.defer()
            except:
                pass

            try:
                run_command_old("git reset --hard")
            except:
                pass

            try:
                pull_log = run_command_old("git pull --allow-unrelated-histories -X theirs")
                if "Already up to date" in pull_log:
                    raise GenericError("Já estou com os ultimos updates instalados...")
                out_git += pull_log

            except GenericError as e:
                return str(e)

            except Exception as e:

                if "Already up to date" in str(e):
                    raise GenericError("Já estou com os ultimos updates instalados...")

                elif not "Fast-forward" in str(e):
                    out_git += await self.cleanup_git(force=True)

            commit = ""

            for l in out_git.split("\n"):
                if l.startswith("Updating"):
                    commit = l.replace("Updating ", "").replace("..", "...")
                    break

            data = (run_command_old(f"git log {commit} {git_format}")).split("\n")

            git_log += format_git_log(data)

        text = "`Reinicie o bot após as alterações.`"

        if "--pip" in opts:
            run_command_old("pip3 install -U -r requirements.txt")

        else:

            with open("./requirements.txt") as f:
                requirements_new = f.read()

            if requirements_old != requirements_new:

                view = AskView(timeout=45, ctx=ctx)

                embed = disnake.Embed(
                    description="**Será necessário atualizar as dependências, escolha sim para instalar.**\n\n"
                                "Nota: Caso não tenha no mínimo 150mb de ram livre, escolha **Não**, mas dependendo "
                                "da hospedagem você deverá usar o comando abaixo: ```sh\npip3 install -U -r requirements.txt``` "
                                "(ou apenas upar o arquivo requirements.txt)",
                    color=self.bot.get_color(ctx.guild.me)
                )

                try:
                    await ctx.edit_original_message(embed=embed, view=view)
                except AttributeError:
                    await ctx.send(embed=embed, view=view)

                await view.wait()

                if view.selected:
                    embed.description = "**Instalando dependências...**"
                    await view.interaction_resp.response.edit_message(embed=embed)
                    run_command_old("pip3 install -U -r requirements.txt")

                try:
                    await (await view.interaction_resp.original_message()).delete()
                except:
                    pass

        txt = f"`✅` **[Atualização realizada com sucesso!]({self.bot.remote_git_url}/commits/main)**"

        if git_log:
            txt += f"\n\n{self.format_log(git_log[:10])}"

        txt += f"\n\n`📄` **Log:** ```py\n{out_git[:1000]}```\n{text}"

        if isinstance(ctx, commands.Context):
            embed = disnake.Embed(
                description=txt,
                color=self.bot.get_color(ctx.guild.me)
            )
            await ctx.send(embed=embed, view=self.owner_view)

        else:
            return txt


    async def cleanup_git(self, force=False):

        if force:
            try:
                shutil.rmtree("./.git")
            except FileNotFoundError:
                pass

        out_git = ""

        for c in self.git_init_cmds:
            try:
                out_git += run_command_old(c) + "\n"
            except Exception as e:
                out_git += f"{e}\n"

        self.bot.commit = run_command_old("git rev-parse --short HEAD")
        self.bot.remote_git_url = self.bot.config["SOURCE_REPO"][:-4]

        return out_git


    @commands.is_owner()
    @panel_command(aliases=["latest", "lastupdate"], description="Guarda i miei ultimi aggiornamenti.", emoji="📈",
                   alt_name="Ultimi aggiornamenti")
    async def updatelog(self, ctx: Union[commands.Context, disnake.MessageInteraction], amount: int = 10):

        if not os.path.isdir("./.git"):
            raise GenericError("Non è presente alcun repository avviato nella directory del bot...\nNota: utilizzare il comando update.")

        if not self.bot.remote_git_url:
            self.bot.remote_git_url = self.bot.config["SOURCE_REPO"][:-4]

        git_log = []

        data = (run_command_old(f"git log -{amount or 10} {git_format}")).split("\n")

        git_log += format_git_log(data)

        txt = f"🔰 ** | [Aggiornamenti recenti:]({self.bot.remote_git_url}/commits/main)**\n\n" + self.format_log(git_log)

        if isinstance(ctx, commands.Context):

            embed = disnake.Embed(
                description=txt,
                color=self.bot.get_color(ctx.guild.me)
            )

            await ctx.send(embed=embed, view=self.owner_view)

        else:
            return txt


    @commands.has_guild_permissions(manage_guild=True)
    @commands.command(description="Sincronizza/Registra i comandi slash sul server.", hidden=True)
    async def syncguild(self, ctx: Union[commands.Context, disnake.MessageInteraction]):

        embed = disnake.Embed(
            color=self.bot.get_color(ctx.guild.me),
            description="**Questo comando non deve più essere utilizzato (la sincronizzazione dei comandi è "
                        f"automatica adesso).**\n\n{sync_message(self.bot)}"
        )

        await ctx.send(embed=embed)


    @commands.is_owner()
    @panel_command(aliases=["sync"], description="Sincronizza i comandi slash manualmente.", emoji="<:slash:944875586839527444>",
                   alt_name="Sincronizza i comandi manualmente.")
    async def synccmds(self, ctx: Union[commands.Context, disnake.MessageInteraction]):

        if self.bot.config["AUTO_SYNC_COMMANDS"] is True:
            raise GenericError(f"**Non può essere utilizzato con la sincronizzazione automatica abilitata...**\n\n{sync_message(self.bot)}")

        await self.bot._sync_application_commands()

        txt = f"**I comandi slash sono stati sincronizzati con successo!**\n\n{sync_message(self.bot)}"

        if isinstance(ctx, commands.Context):

            embed = disnake.Embed(
                color=self.bot.get_color(ctx.guild.me),
                description=txt
            )

            await ctx.send(embed=embed, view=self.owner_view)

        else:
            return txt


    @commands.command(name="help", aliases=["ajuda"], hidden=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def help_(self, ctx: commands.Context):

        embed = disnake.Embed(color=self.bot.get_color(ctx.me), title="I miei comandi:", description="")

        if self.bot.slash_commands:
            embed.description += "`Veja meus comandos de barra usando:` **/**"

        if ctx.me.avatar:
            embed.set_thumbnail(url=ctx.me.avatar.with_static_format("png").url)

        for cmd in self.bot.commands:

            if cmd.hidden:
                continue

            embed.description += f"**{cmd.name}**"

            if cmd.aliases:
                embed.description += f" [{', '.join(a for a in cmd.aliases)}]"

            if cmd.description:
                embed.description += f" ```ldif\n{cmd.description}```"

            if cmd.usage:
                embed.description += f" ```ldif\n{ctx.clean_prefix}{cmd.name} {cmd.usage}```"

            embed.description += "\n"

        await ctx.reply(embed=embed)

    @commands.has_guild_permissions(administrator=True)
    @commands.cooldown(1, 10, commands.BucketType.guild)
    @commands.command(
        aliases=["cambia prefisso", "prefix", "changeprefix"],
        description="Cambia il prefisso del server",
        usage="prefix"
    )
    async def setprefix(self, ctx: commands.Context, prefix: str):

        data = await self.bot.db.get_data(ctx.guild.id, db_name="guilds")
        data["prefix"] = prefix
        await self.bot.db.update_data(ctx.guild.id, data, db_name="guilds")

        embed = disnake.Embed(
            description=f"**Il prefisso del server è ora:** {prefix}",
            color=self.bot.get_color(ctx.guild.me)
        )

        await ctx.send(embed=embed)


    @commands.is_owner()
    @panel_command(aliases=["export"], description="Esporta le mie configurazioni/segreti/env in un file in DM.", emoji="🔐",
                   alt_name="Esporta env/config")
    async def exportenv(self, ctx: Union[commands.Context, disnake.MessageInteraction]):

        fp = BytesIO(bytes(json.dumps(self.bot.config, indent=4), 'utf-8'))
        try:
            embed = disnake.Embed(
                description="**Non rivelare/mostrare questo file a nessuno, fai molta attenzione quando pubblichi le stampe "
                "dei tuoi contenuti; non aggiungere questo file in luoghi pubblici come github, repl.it, "
                "glitch.com, etc!**",
                color=self.bot.get_color(ctx.guild.me))
            embed.set_footer(text="Come misura di sicurezza, questo messaggio verrà cancellato entro 60 secondi.")
            await ctx.author.send(embed=embed,
                                  file=disnake.File(fp=fp, filename="config.json"), delete_after=60)

        except disnake.Forbidden:
            raise GenericError("Il tuoi DM sono disattivati!")

        if isinstance(ctx, commands.Context):
            await ctx.message.add_reaction("👍")
        else:
            return "File di configurazione inviato con successo nei tuoi DM."


    @check_voice()
    @commands.command(description='inizializzare un player sul server.', aliases=["spawn", "sp", "spw", "smn"])
    async def summon(self, ctx: commands.Context):

        try:
            self.bot.music.players[ctx.guild.id]  # type ignore
            raise GenericError("**C'è già un player avviato sul server.**")
        except KeyError:
            pass

        node: wavelink.Node = self.bot.music.get_best_node()

        if not node:
            raise GenericError("**Nessun server musicale disponibile!**")

        guild_data = await self.bot.db.get_data(ctx.guild.id, db_name="guilds")

        static_player = guild_data['player_controller']

        try:
            channel = ctx.guild.get_channel(int(static_player['channel'])) or ctx.channel
            message = await channel.fetch_message(int(static_player.get('message_id')))
        except (KeyError, TypeError):
            channel = ctx.channel
            message = None

        player: Union[LavalinkPlayer, YTDLPlayer] = self.bot.music.get_player(
            node_id=node.identifier,
            guild_id=ctx.guild.id,
            cls=LavalinkPlayer,
            requester=ctx.author,
            guild=ctx.guild,
            channel=channel,
            message=message,
            static=bool(static_player['channel'])
        )

        channel = ctx.author.voice.channel

        await player.connect(channel.id)

        self.bot.loop.create_task(ctx.message.add_reaction("👍"))

        while not ctx.guild.me.voice:
            await asyncio.sleep(1)

        if isinstance(channel, disnake.StageChannel):

            stage_perms =  channel.permissions_for(ctx.guild.me)
            if stage_perms.manage_permissions:
                await ctx.guild.me.edit(suppress=False)
            elif stage_perms.request_to_speak:
                await ctx.guild.me.request_to_speak()

            await asyncio.sleep(1.5)

        await player.process_next()

    async def cog_check(self, ctx: CustomContext) -> bool:
        return await check_requester_channel(ctx)

    async def cog_load(self) -> None:
        self.owner_view =  PanelView(self.bot)


def setup(bot: BotCore):
    bot.remove_command("help")
    bot.add_cog(Owner(bot))
