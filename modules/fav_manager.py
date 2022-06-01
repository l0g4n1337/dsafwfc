from __future__ import annotations
import asyncio
import disnake
from disnake.ext import commands
from typing import TYPE_CHECKING
from utils.music.converters import URL_REG, fav_list
from utils.music.errors import GenericError
from io import BytesIO
import json

if TYPE_CHECKING:
    from utils.client import BotCore

desc_prefix = "⭐ [Preferiti] ⭐ | "


class FavManager(commands.Cog):

    def __init__(self, bot: BotCore):
        self.bot = bot


    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.slash_command(name="fav")
    async def fav(self, inter: disnake.ApplicationCommandInteraction):
        pass


    @fav.sub_command(description=f"{desc_prefix}Aggiungi un link (consigliato: playlist) all'elenco dei preferiti.")
    async def add(
            self,
            inter: disnake.ApplicationCommandInteraction,
            name: str = commands.Param(name="nome", description="Nome del preferito."),
            url: str = commands.Param(name="link", description="link ai preferiti (consigliato: dalla playlist)"),
    ):

        if len(name) > (max_name_chars := self.bot.config["USER_FAV_MAX_NAME_LENGTH"]):
            raise GenericError(f"**Numero massimo di caratteri consentiti nel nome: {max_name_chars}**")

        if len(url) > (max_url_chars := self.bot.config["USER_FAV_MAX_URL_LENGTH"]):
            raise GenericError(f"**Numero massimo di caratteri consentiti nel link: {max_url_chars}**")

        if not URL_REG.match(url):
            raise GenericError("**Non hai aggiunto un link valido...**")

        await inter.response.defer(ephemeral=True)

        user_data = await self.bot.db.get_data(inter.author.id, db_name="users")

        if len(user_data["fav_links"]) > (max_favs:=self.bot.config["MAX_USER_FAVS"]) and not \
                (await self.bot.is_owner(inter.author)):
            raise GenericError(f"**Hai superato il numero di preferiti consentito ({max_favs}).**")

        try:
            del user_data["fav_links"][name.lower()]
        except KeyError:
            pass

        user_data["fav_links"][name] = url

        await self.bot.db.update_data(inter.author.id, user_data, db_name="users")

        await inter.edit_original_message(content="Link salvato/aggiornato con successo ai tuoi preferiti!\n"
                                          "Apparirà quando usi il comando /play (nella ricerca di completamento automatico).")


    @fav.sub_command(description=f"{desc_prefix}Modifica un elemento dall'elenco dei preferiti.")
    async def edit(
            self,
            inter: disnake.ApplicationCommandInteraction,
            item: str = commands.Param(autocomplete=fav_list, description="elemento dei preferiti da modificare."), *,
            name: str = commands.Param(name="novo_nome", default="", description="Nuovo nome per il preferito."),
            url: str = commands.Param(name="novo_link", default="", description="Nuovo link per il preferito.")
    ):

        if not name and not url:
            raise GenericError("**Non hai specificato nessuno degli elementi facoltativi: nuovo_nome e nuovo_link.**")

        if len(name) > (max_name_chars := self.bot.config["USER_FAV_MAX_NAME_LENGTH"]):
            raise GenericError(f"**Numero massimo di caratteri consentiti nel nome: {max_name_chars}**")

        if len(url) > (max_url_chars := self.bot.config["USER_FAV_MAX_URL_LENGTH"]):
            raise GenericError(f"**Numero massimo di caratteri consentiti nel link: {max_url_chars}**")

        await inter.response.defer(ephemeral=True)

        user_data = await self.bot.db.get_data(inter.author.id, db_name="users")

        try:
            if name:
                new_url = str(user_data["fav_links"][item])
                del user_data["fav_links"][item]
                user_data["fav_links"][name] = url or new_url

            elif url:
                user_data["fav_links"][item] = url

        except KeyError:
            raise GenericError(f"**Non esiste un preferito con il nome:** {item}")

        await self.bot.db.update_data(inter.author.id, user_data, db_name="users")

        await inter.edit_original_message(content="Preferito modificato con successo!")


    @fav.sub_command(description=f"{desc_prefix}Rimuovere un link dall'elenco dei preferiti.")
    async def remove(
            self,
            inter: disnake.ApplicationCommandInteraction,
            item: str = commands.Param(autocomplete=fav_list, description="Preferito da rimuovere."),
    ):

        await inter.response.defer(ephemeral=True)

        user_data = await self.bot.db.get_data(inter.author.id, db_name="users")

        try:
            del user_data["fav_links"][item]
        except:
            raise GenericError(f"**Non esiste un preferito con il nome:** {item}")

        await self.bot.db.update_data(inter.author.id, user_data, db_name="users")

        await inter.edit_original_message(content="Link rimosso con successo!")


    @fav.sub_command(name="clear", description=f"{desc_prefix}Cancella la tua lista dei preferiti.")
    async def clear_(self, inter: disnake.ApplicationCommandInteraction):

        await inter.response.defer(ephemeral=True)

        data = await self.bot.db.get_data(inter.author.id, db_name="users")

        if not data["fav_links"]:
            raise GenericError("**Non hai link preferiti!**")

        data["fav_links"].clear()

        await self.bot.db.update_data(inter.author.id, data, db_name="users")

        embed = disnake.Embed(
            description="La tua lista dei preferiti è stata cancellata con successo!",
            color=self.bot.get_color(inter.guild.me)
        )

        await inter.edit_original_message(embed=embed)


    @fav.sub_command(name="list", description=f"{desc_prefix}Visualizza la tua lista dei preferiti.")
    async def list_(
            self, inter: disnake.ApplicationCommandInteraction,
            hidden: bool = commands.Param(
                name="nascondere",
                description="Solo tu puoi vedere l'elenco dei preferiti.",
                default=False)
    ):

        await inter.response.defer(ephemeral=hidden)

        user_data = await self.bot.db.get_data(inter.author.id, db_name="users")

        if not user_data["fav_links"]:
            raise GenericError(f"**Non hai link preferiti..\n"
                               f"Puoi aggiungere usando il comando: /{self.add.name}**")

        embed = disnake.Embed(
            color=self.bot.get_color(inter.guild.me),
            title="I tuoi link preferiti:",
            description="\n".join(f"{n+1}) [`{f[0]}`]({f[1]})" for n, f in enumerate(user_data["fav_links"].items()))
        )

        embed.set_footer(text="Puoi usarli col comando /play")

        await inter.edit_original_message(embed=embed)


    @fav.sub_command(name="import", description=f"{desc_prefix}Importa i tuoi preferiti da un file.")
    async def import_(
            self,
            inter: disnake.ApplicationCommandInteraction,
            file: disnake.Attachment = commands.Param(name="file", description="file in formato .json")
    ):

        if file.size > 2097152:
            raise GenericError("**La dimensione del file non può superare 2Mb!**")

        if not file.filename.endswith(".json"):
            raise GenericError("**Tipo di file non valido!**")


        await inter.response.defer(ephemeral=True)

        try:
            data = (await file.read()).decode('utf-8')
            json_data = json.loads(data)
        except Exception as e:
            raise GenericError("**Si è verificato un errore durante la lettura del file, rivedilo e utilizza di nuovo il comando.**\n"
                               f"```py\n{repr(e)}```")

        for url in json_data.values():

            if len(url) > (max_url_chars := self.bot.config["USER_FAV_MAX_URL_LENGTH"]):
                raise GenericError(f"**Un elemento dal tuo archivio {url} supera il numero di caratteri consentito:{max_url_chars}**")

            if not isinstance(url, str) or not URL_REG.match(url):
                raise GenericError(f"Il tuo file contiene un link non valido: ```ldif\n{url}```")

        user_data = await self.bot.db.get_data(inter.author.id, db_name="users")

        for name in json_data.keys():
            if len(name) > (max_name_chars := self.bot.config["USER_FAV_MAX_NAME_LENGTH"]):
                raise GenericError(f"**Un elemento dal tuo archivio ({name}) supera il numero di caratteri consentito:{max_name_chars}**")
            try:
                del user_data["fav_links"][name.lower()]
            except KeyError:
                continue

        if self.bot.config["MAX_USER_FAVS"] > 0 and not (await self.bot.is_owner(inter.author)):

            if (json_size:=len(json_data)) > self.bot.config["MAX_USER_FAVS"]:
                raise GenericError(f"La quantità di elementi nel tuo file preferito supera "
                                   f"l'importo massimo consentito ({self.bot.config['MAX_USER_FAVS']}).")

            if (json_size + (user_favs:=len(user_data["fav_links"]))) > self.bot.config["MAX_USER_FAVS"]:
                raise GenericError("Non hai abbastanza spazio per aggiungere tutti i tuoi preferiti al tuo file...\n"
                                   f"Limite corrente: {self.bot.config['MAX_USER_FAVS']}\n"
                                   f"Numero di preferiti salvati: {user_favs}\n"
                                   f"Devi: {(json_size + user_favs)-self.bot.config['MAX_USER_FAVS']}")

        user_data["fav_links"].update(json_data)

        await self.bot.db.update_data(inter.author.id, user_data, db_name="users")

        await inter.edit_original_message(
            embed = disnake.Embed(
                color=self.bot.get_color(inter.guild.me),
                description = "**I links sono stati importati con successo!**\n"
                              "**Saranno disponibili quando si utilizza il comando /play (completare automaticamente la ricerca).**",
            )
        )


    @fav.sub_command(description=f"{desc_prefix}Esporta i tuoi preferiti in un file nei tuoi DM.")
    async def export(self, inter: disnake.ApplicationCommandInteraction):

        await inter.response.defer(ephemeral=True)

        user_data = await self.bot.db.get_data(inter.author.id, db_name="users")

        if not user_data["fav_links"]:
            raise GenericError(f"**Non hai link preferiti..\n"
                               f"Puoi aggiungerli usando il comando: /{self.add.name}**")

        fp = BytesIO(bytes(json.dumps(user_data["fav_links"], indent=4), 'utf-8'))

        embed = disnake.Embed(
            description=f"I tuoi preferiti sono qui.\nPuoi importarli usando il comando: `/{self.import_.name}`",
            color=self.bot.get_color(inter.guild.me))

        await inter.edit_original_message(embed=embed, file=disnake.File(fp=fp, filename="favoritos.json"))


def setup(bot: BotCore):
    bot.add_cog(FavManager(bot))
