import sys
import traceback
from typing import Union
import disnake
from disnake.ext import commands

from utils.music.converters import perms_translations, time_format


class GenericError(commands.CheckFailure):

    def __init__(self, text: str, delete: int = None):
        self.text = text
        self.delete = delete


class MissingSpotifyClient(commands.CheckFailure):
    pass


class NoPlayer(commands.CheckFailure):
    pass


class NoVoice(commands.CheckFailure):
    pass


class MissingVoicePerms(commands.CheckFailure):

    def __init__(self, voice_channel: Union[disnake.VoiceChannel, disnake.StageChannel]):
        self.voice_channel = voice_channel


class DiffVoiceChannel(commands.CheckFailure):
    pass


class NoSource(commands.CheckFailure):
    pass


class NotDJorStaff(commands.CheckFailure):
    pass


class NotRequester(commands.CheckFailure):
    pass


def parse_error(
        ctx: Union[disnake.ApplicationCommandInteraction, commands.Context, disnake.MessageInteraction],
        error: Exception
):

    error_txt = None

    error = getattr(error, 'original', error)

    if isinstance(error, NotDJorStaff):
        error_txt = "**Devi essere nell'elenco dei DJ o disporre dell'autorizzazione **Gestisci canali** " \
                    "per usare questo comando.**"

    elif isinstance(error, MissingVoicePerms):
        error_txt = f"**Non sono autorizzato a connettermi/parlare sul canale:** {error.voice_channel.mention}"

    elif isinstance(error, commands.NotOwner):
        error_txt = "**Solo i miei sviluppatori possono utilizzare questo comando.**"

    elif isinstance(error, commands.BotMissingPermissions):
        error_txt = "Non ho le seguenti autorizzazioni per eseguire questo comando: ```\n{}```" \
            .format(", ".join(perms_translations.get(perm, perm) for perm in error.missing_permissions))

    elif isinstance(error, commands.MissingPermissions):
        error_txt = "Non hai le seguenti autorizzazioni per eseguire questo comando: ```\n{}```" \
            .format(", ".join(perms_translations.get(perm, perm) for perm in error.missing_permissions))

    elif isinstance(error, GenericError):
        error_txt = error.text

    elif isinstance(error, NotRequester):
        error_txt = "**Devi aver richiesto la canzone corrente o essere nella lista dei DJ o avere il permesso di " \
                    "**Gestisci i canali** per saltare i brani.**"

    elif isinstance(error, DiffVoiceChannel):
        error_txt = "**Devi essere sul mio stesso canale vocale per usare questo comando.**"

    elif isinstance(error, NoSource):
        error_txt = "**Attualmente non ci sono brani in riproduzione.**"

    elif isinstance(error, NoVoice):
        error_txt = "**Devi entrare in un canale vocale per usare questo comando.**"

    elif isinstance(error, NoPlayer):
        error_txt = "**Non c'è nessun bot inizializzato sul server.**"

    elif isinstance(error, MissingSpotifyClient):
        error_txt = "**I links Spotify non sono supportati al momento.**"

    elif isinstance(error, commands.CommandOnCooldown):
        remaing = int(error.retry_after)
        if remaing < 1:
            remaing = 1
        error_txt = "**Devi attendere che {} utilizzi questo comando.**".format(time_format(int(remaing) * 1000))

    elif isinstance(error, commands.MaxConcurrencyReached):
        txt = f"{error.number} vezes " if error.number > 1 else ''
        txt = {
            commands.BucketType.member: f"hai già utilizzato questo comando {txt}sul server",
            commands.BucketType.guild: f"questo comando è già stato utilizzato {txt}sul server",
            commands.BucketType.user: f"hai già usato questo comando {txt}",
            commands.BucketType.channel: f"questo comando è già stato utilizzato {txt}nel canale corrente",
            commands.BucketType.category: f"questo comando è già stato utilizzato {txt}nella categoria del canale corrente",
            commands.BucketType.role: f"questo comando è già stato utilizzato {txt}da un membro che dispone del ruolo per farlo",
            commands.BucketType.default: f"questo comando è già stato utilizzato {txt}da qualcuno"
        }

        error_txt = f"{ctx.author.mention} **{txt[error.per]} e ancora non ho avuto il tuo{'s' if error.number > 1 else ''} " \
                    f"uso{'s' if error.number > 1 else ''} finito{'s' if error.number > 1 else ''}!**"

    if not error_txt:
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    return error_txt