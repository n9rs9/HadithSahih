import discord
from discord.ext import commands
from discord import ui
import os
import logging
import random
from typing import List, Tuple

# --- Configuration du Logger ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('HadithSahih')

# --- Configuration du Bot et des Intents ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='hs!', intents=intents)

# --- Classe View pour la Sélection de Langue ---

class LanguageSelect(ui.View):
    """Vue interactive pour permettre à l'utilisateur de sélectionner une langue (FR/ENG)
    pour l'affichage du résultat d'une commande (sauf ping)."""

    def __init__(self, command_name: str, ctx: commands.Context):
        super().__init__(timeout=60)
        self.command_name = command_name
        self.ctx = ctx
        self.language = None

    async def on_timeout(self):
        """Désactive les boutons si le temps d'attente est écoulé."""
        for item in self.children:
            item.disabled = True
        try:
            await self.ctx.message.edit(view=self)
        except discord.NotFound:
            pass
        except Exception as e:
            logger.error(f"Erreur lors de la désactivation des boutons en timeout: {e}")

    def check_author(self, interaction: discord.Interaction) -> bool:
        """Vérifie si l'utilisateur qui clique est l'auteur de la commande."""
        if interaction.user != self.ctx.author:
            error_message = "This is not your command! / Ce n'est pas ta commande!"
            interaction.response.send_message(error_message, ephemeral=True)
            return False
        return True

    @ui.button(label="FR", style=discord.ButtonStyle.primary, emoji="🇫🇷")
    async def french_button(self, interaction: discord.Interaction, button: ui.Button):
        self.language = "FR"
        if not self.check_author(interaction):
            return
        await self.show_command_result(interaction)

    @ui.button(label="ENG", style=discord.ButtonStyle.secondary, emoji="🇬🇧")
    async def english_button(self, interaction: discord.Interaction, button: ui.Button):
        self.language = "ENG"
        if not self.check_author(interaction):
            return
        await self.show_command_result(interaction)

    async def show_command_result(self, interaction: discord.Interaction):
        """Génère l'embed de résultat et édite le message pour l'afficher."""
        for item in self.children:
            item.disabled = True

        embed_generators = {
            "commands": lambda lang: get_commands_embed(lang),
            "info": lambda lang: get_info_embed(lang, len(bot.guilds)),
            "hadith": lambda lang: get_hadith_embed(lang),
        }

        embed_func = embed_generators.get(self.command_name)
        if embed_func:
            result_embed = embed_func(self.language)
        else:
            result_embed = discord.Embed(
                title="Erreur / Error",
                description="Commande inconnue / Unknown command",
                color=discord.Color.red()
            )

        await interaction.response.edit_message(embed=result_embed, view=self)

# --- Fonctions de Génération d'Embeds ---

def get_commands_embed(lang: str) -> discord.Embed:
    """Génère l'embed de la liste des commandes."""
    if lang == "FR":
        embed = discord.Embed(
            title="Commandes de HadithSahih",
            description="Toutes les commandes de ce bot :satellite:",
            color=discord.Color.purple()
        )
        commands_list = [
            (" • hs!hadith", "*Affiche un hadith sahih aléatoire*"),
            (" • hs!commands", "*Toutes les commandes du bot*"),
            (" • hs!ping", "*Vérifie la latence du bot (réponse directe)*"),
            (" • hs!info", "*Informations sur le bot*"),
            (" • hs!book", "*Affiche une liste de livres islamiques en français*")
        ]
        footer_text = "- @n9rs9"
    else:
        embed = discord.Embed(
            title="HadithSahih's Commands",
            description="All commands for this bot :satellite:",
            color=discord.Color.purple()
        )
        commands_list = [
            (" • hs!hadith", "*Displays a random Sahih hadith*"),
            (" • hs!commands", "*All commands for this bot*"),
            (" • hs!ping", "*Check the bot's latency (direct response)*"),
            (" • hs!info", "*Bot information*"),
            (" • hs!book", "*Displays a list of Islamic books in French*")
        ]
        footer_text = "- @n9rs9"

    for name, value in commands_list:
        embed.add_field(name=name, value=value, inline=False)

    embed.set_footer(text=footer_text)
    return embed


def get_info_embed(lang: str, server_count: int) -> discord.Embed:
    """Génère l'embed d'information sur le bot."""
    if lang == "FR":
        embed = discord.Embed(
            title=" • HadithSahih",
            description="Des Hadiths Sahih pour vous chaque jour ! :books:",
            color=discord.Color.pink())
        embed.add_field(name="Propriétaire", value="@n9rs9", inline=True)
        embed.add_field(name="Serveurs", value=str(server_count), inline=True)
    else:
        embed = discord.Embed(
            title=" • HadithSahih",
            description="Sahih Hadiths for you every day! :books:",
            color=discord.Color.pink())
        embed.add_field(name="Owner", value="@n9rs9", inline=True)
        embed.add_field(name="Servers", value=str(server_count), inline=True)
    return embed


def get_hadith_embed(lang: str) -> discord.Embed:
    """Génère l'embed d'un Hadith aléatoire."""
    if lang == "FR":
        hadith_text = get_random_hadith("hadiths_fr.txt")
        embed = discord.Embed(title="✨ Hadith Sahih Aléatoire",
                              description=hadith_text,
                              color=discord.Color.blue())
        footer_text = "رَبِّ زِدْنِي عِلْمًا - Rabbi zidnī 'ilman - Mon Seigneur, augmente ma connaissance"
    else:
        hadith_text = get_random_hadith("hadiths_eng.txt")
        embed = discord.Embed(title="✨ Random Sahih Hadith",
                              description=hadith_text,
                              color=discord.Color.blue())
        footer_text = "رَبِّ زِدْنِي عِلْمًا - Rabbi zidnī 'ilman - My Lord, increase me in knowledge"

    embed.set_footer(text=footer_text)
    return embed

# --- Fonctions Utilitaires de Fichier ---

def get_random_hadith(file_path: str = "hadiths_eng.txt") -> str:
    """Lit un fichier et renvoie une ligne aléatoire."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            hadiths = f.readlines()
            hadiths = [h.strip() for h in hadiths if h.strip()]
            if hadiths:
                return random.choice(hadiths)
            else:
                return "Le fichier de hadiths est vide / The hadiths file is empty."
    except FileNotFoundError:
        logger.error(f"Fichier non trouvé: {file_path}")
        return f"Erreur: Fichier {file_path} introuvable / Error: {file_path} not found."
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier: {e}")
        return "Une erreur est survenue / An error occurred."


def get_books_fr(file_path: str = "book_fr.txt") -> List[Tuple[str, str]] | None:
    """Lit le fichier des livres et renvoie une liste de (titre, lien)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            books = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if "[" in line and "]" in line:
                    parts = line.split("[", 1)
                    link = parts[0].strip()
                    title = parts[1].replace("]", "").strip()
                    books.append((title, link))

            return books

    except FileNotFoundError:
        logger.error(f"Fichier non trouvé: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier {file_path}: {e}")
        return None

# --- Événements du Bot ---

@bot.event
async def on_ready():
    """Se déclenche lorsque le bot est prêt."""
    logger.info(f'{bot.user} is connected to Discord!')
    logger.info(f'Bot ID: {bot.user.id}')
    logger.info(f'Connected servers: {len(bot.guilds)}')
    logger.info(f'Prefix: hs!')

# --- Commandes du Bot ---

async def send_language_select(ctx: commands.Context, command_name: str):
    """Fonction utilitaire pour envoyer l'embed de sélection de langue."""
    embed = discord.Embed(
        title=":abcd: Choisissez votre langue / Choose your language",
        description="*Cliquez sur un bouton ci-dessous*\n*Click a button below*",
        color=discord.Color.red())
    view = LanguageSelect(command_name, ctx)
    await ctx.send(embed=embed, view=view)


@bot.command(name='commands')
async def list_commands(ctx: commands.Context):
    """Affiche la liste des commandes avec sélection de langue."""
    await send_language_select(ctx, "commands")


@bot.command(name='ping')
async def ping(ctx: commands.Context):
    """Affiche directement la latence du bot dans le format souhaité (une seule fois)."""
    latency_ms = round(bot.latency * 1000)

    # Format exact demandé : @nomutilisateur :small_blue_diamond: Latence : **Xms**
    response = f"{ctx.author.mention} :small_blue_diamond: Latence : **{latency_ms}ms**"

    # CECI EST LA SEULE LIGNE D'ENVOI. Si la réponse est en double,
    # c'est que le bot est lancé deux fois.
    await ctx.send(response)


@bot.command(name='info')
async def info(ctx: commands.Context):
    """Affiche les informations du bot avec sélection de langue."""
    await send_language_select(ctx, "info")


@bot.command(name='hadith')
async def hadith(ctx: commands.Context):
    """Affiche un Hadith aléatoire avec sélection de langue."""
    await send_language_select(ctx, "hadith")


@bot.command(name="book")
async def book(ctx: commands.Context):
    """Affiche une liste de livres islamiques en français."""
    books = get_books_fr()

    if not books:
        await ctx.send("❌ Aucun livre trouvé dans **book_fr.txt**")
        return

    description = ""
    # Création de la description avec les liens formatés
    for i, (title, link) in enumerate(books, start=1):
        description += f"**{i}.** [{title}]({link})\n\n"

    embed = discord.Embed(
        title="📚 Bibliothèque Islamique - Livres en Français",
        description=description,
        color=discord.Color.gold()
    )

    embed.set_footer(text="HadithSahih • @n9rs9")
    await ctx.send(embed=embed)


# --- Fonction Principale ---

def main():
    """Fonction principale pour démarrer le bot."""
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        logger.error(
            "DISCORD_BOT_TOKEN non trouvé dans les variables d'environnement!")
        return
    logger.info("Starting the bot...")
    bot.run(token)


if __name__ == "__main__":
    main()

# owner : @n9rs9
# github : https://github.com/n9rs9
