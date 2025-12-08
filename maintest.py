import discord
from discord.ext import commands
from discord import ui
import os
import logging
import random
from typing import List, Tuple, Optional, Dict, Any
import math
# --- Ajouts pour le serveur web ---
from flask import Flask
from threading import Thread
# ---------------------------------

# --- Configuration du Logger ---
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger('HadithSahih')

# --- Configuration du Bot et des Intents ---
# Nécessaire pour les commandes et pour certaines informations sur les membres
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Initialisation du bot avec le préfixe 'hs!'
bot = commands.Bot(command_prefix='hs!', intents=intents)

# --- Constantes de Pagination ---
BOOKS_PER_PAGE = 10 # 10 éléments par page

# --- Sources de la Bibliographie ---
BIBLIO_SOURCES = "• Site officiel de la mosquée de Médine\n• Site officiel du gouvernement Saoudien"

# --- Classe View pour la Sélection de Langue (inchangée) ---

class LanguageSelect(ui.View):
    """Vue interactive pour permettre à l'utilisateur de sélectionner une langue (FR/ENG)."""

    def __init__(self, command_name: str, ctx: commands.Context):
        super().__init__(timeout=60)
        self.command_name = command_name
        self.ctx = ctx
        self.language = None

    async def on_timeout(self):
        """Désactive les boutons et édite le message après le timeout."""
        for item in self.children:
            item.disabled = True
        
        try:
            await self.message.edit(view=self)
        except (discord.NotFound, AttributeError, discord.HTTPException):
            pass 

    # Ajoutez cette méthode pour stocker le message d'interaction initial
    async def start_interaction(self, ctx: commands.Context):
        """Envoie le message initial et stocke l'objet Message."""
        embed = discord.Embed(
            title=":abcd: Choisissez votre langue / Choose your language",
            description="*Cliquez sur un bouton ci-dessous*\n*Click a button below*",
            color=discord.Color.red())
        self.message = await ctx.send(embed=embed, view=self)


    def check_author(self, interaction: discord.Interaction) -> bool:
        """Vérifie si l'utilisateur qui clique est l'auteur de la commande."""
        if interaction.user != self.ctx.author:
            error_message = "This is not your command! / Ce n'est pas ta commande!"
            if not interaction.response.is_done():
                interaction.response.send_message(error_message, ephemeral=True)
            return False
        return True

    @ui.button(label="FR", style=discord.ButtonStyle.primary, emoji="🇫🇷")
    async def french_button(self, interaction: discord.Interaction, button: ui.Button):
        self.language = "FR"
        if not self.check_author(interaction): return
        await self.show_command_result(interaction)

    @ui.button(label="ENG", style=discord.ButtonStyle.secondary, emoji="🇬🇧")
    async def english_button(self, interaction: discord.Interaction, button: ui.Button):
        self.language = "ENG"
        if not self.check_author(interaction): return
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

        # Édition du message original
        await interaction.response.edit_message(embed=result_embed, view=self)

# --- Fonctions Utilitaires de Fichier (inchangées) ---

def get_random_hadith(file_path: str = "hadiths_eng.txt") -> str:
    """Lit un fichier et renvoie une ligne aléatoire."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            hadiths = [h.strip() for h in f.readlines() if h.strip()]
            return random.choice(hadiths) if hadiths else "Le fichier de hadiths est vide / The hadiths file is empty."
    except FileNotFoundError:
        logger.error(f"Fichier non trouvé: {file_path}")
        return f"Erreur: Fichier {file_path} introuvable / Error: {file_path} not found."
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier: {e}")
        return "Une erreur est survenue / An error occurred."


def get_books_fr(file_path: str = "book_fr.txt") -> List[Tuple[str, str]] | None:
    """
    Lit le fichier des livres. 
    Format attendu des lignes : [LIEN] [TITRE]
    Renvoie une liste de (titre, lien).
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            books = []
            for line in f:
                line = line.strip()
                if not line or not line.startswith('[') or ']' not in line:
                    continue

                try:
                    # Trouver la fin du premier crochet (qui contient le lien)
                    link_end = line.find(']')
                    
                    # Extraire le lien (entre les premiers crochets)
                    link = line[1:link_end].strip()
                    
                    # Le reste de la ligne devrait commencer par un autre crochet (le titre)
                    title_start = line.find('[', link_end + 1)
                    title_end = line.find(']', title_start + 1)

                    if link and title_start != -1 and title_end != -1:
                        # Extraire le titre (entre les deuxièmes crochets)
                        title = line[title_start + 1:title_end].strip()
                        
                        if title:
                            books.append((title, link))

                except Exception as e:
                    logger.warning(f"Ligne de livre mal formatée ignorée: {line}. Erreur: {e}")
                    continue

            return books

    except FileNotFoundError:
        logger.error(f"Fichier non trouvé: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier {file_path}: {e}")
        return None

# --- Fonctions de Génération d'Embeds (inchangées) ---

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

# ----------------------------------------------------
# --- Classes et Fonctions pour la Pagination du Livre (MODIFIÉES) ---
# ----------------------------------------------------

def get_book_page_embed(books: List[Tuple[str, str]], page_num: int, total_pages: int) -> discord.Embed:
    """Génère l'embed pour une page spécifique de la liste de livres."""
    global BOOKS_PER_PAGE 
    
    start_index = page_num * BOOKS_PER_PAGE
    end_index = start_index + BOOKS_PER_PAGE
    
    page_books = books[start_index:end_index]

    description_list = ""
    # Création de la description avec les liens formatés
    for i, (title, link) in enumerate(page_books, start=start_index + 1):
        # Format: [i. Titre](Lien)
        description_list += f"**{i}.** [{title}]({link})\n"

    # Message d'instruction + sources
    # L'instruction est en ITALIQUE
    instruction_text = "*Copiez le lien et collez-le si cela ne fonctionne pas*"
    
    if page_num == 0:
        # Ajout de la description des sources en premier
        header_text = f"**{BIBLIO_SOURCES}**\n\n{instruction_text}\n\n"
    else:
        # Pour les pages suivantes, seulement l'instruction
        header_text = f"{instruction_text}\n\n"


    if description_list:
        full_description = f"{header_text}{description_list}"
    else:
        # Pour les pages vides
        if page_num == 0:
             full_description = f"{header_text}**Aucun livre trouvé dans le fichier book_fr.txt.**"
        else:
             full_description = f"{header_text}**Fin de la bibliographie.**"
    
    embed = discord.Embed(
        title="📚 Bibliographie", 
        description=full_description,
        color=discord.Color.gold()
    )

    # Pied de page affiche uniquement la pagination
    embed.set_footer(text=f"Page {page_num + 1}/{total_pages}")
    return embed


class BookBrowser(ui.View):
    """Vue interactive pour naviguer entre les pages de la liste de livres."""

    def __init__(self, ctx: commands.Context, books: List[Tuple[str, str]]):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.books = books
        self.total_books = len(books)
        self.total_pages = math.ceil(self.total_books / BOOKS_PER_PAGE)
        self.current_page = 0
        self.message: Optional[discord.Message] = None 
        
        # Pour forcer une 2e page vide si la liste n'est pas remplie
        if self.total_pages < 2 and self.total_books > 0:
            self.total_pages = 2 
        
        self.update_buttons()

    async def on_timeout(self):
        """Désactive les boutons si le temps d'attente est écoulé."""
        for item in self.children:
            item.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except (discord.NotFound, discord.HTTPException):
            pass

    def check_author(self, interaction: discord.Interaction) -> bool:
        """Vérifie si l'utilisateur qui clique est l'auteur de la commande."""
        if interaction.user != self.ctx.author:
            error_message = "This is not your command! / Ce n'est pas ta commande!"
            if not interaction.response.is_done():
                   interaction.response.send_message(error_message, ephemeral=True)
            return False
        return True

    def update_buttons(self):
        """Met à jour l'état (disabled/emoji) des boutons de navigation."""
        
        # Le premier enfant est le bouton de gauche, le deuxième est le bouton de droite
        left_button = self.children[0]
        right_button = self.children[1]

        # Bouton Gauche (Précédent)
        if self.current_page == 0:
            left_button.disabled = True
            left_button.style = discord.ButtonStyle.red
            left_button.emoji = "❌"
        else:
            left_button.disabled = False
            left_button.style = discord.ButtonStyle.primary
            left_button.emoji = "⬅️"

        # Bouton Droit (Suivant)
        if self.current_page >= self.total_pages - 1:
            right_button.disabled = True
            right_button.style = discord.ButtonStyle.red
            right_button.emoji = "❌"
        else:
            right_button.disabled = False
            right_button.style = discord.ButtonStyle.primary
            right_button.emoji = "➡️"

    @ui.button(style=discord.ButtonStyle.primary, emoji="⬅️")
    async def previous_page(self, interaction: discord.Interaction, button: ui.Button):
        if not self.check_author(interaction): return
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = get_book_page_embed(self.books, self.current_page, self.total_pages)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.edit_message(view=self) 


    @ui.button(style=discord.ButtonStyle.primary, emoji="➡️")
    async def next_page(self, interaction: discord.Interaction, button: ui.Button):
        if not self.check_author(interaction): return
        
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = get_book_page_embed(self.books, self.current_page, self.total_pages)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.edit_message(view=self) 

# ----------------------------------------------------
# --- Événements et Commandes du Bot (MODIFIÉ) ---
# ----------------------------------------------------

@bot.event
async def on_ready():
    """Se déclenche lorsque le bot est prêt."""
    logger.info(f'{bot.user} is connected to Discord!')
    logger.info(f'Bot ID: {bot.user.id}')
    logger.info(f'Connected servers: {len(bot.guilds)}')
    logger.info(f'Prefix: hs!')


# NOTE : La fonction on_message a été supprimée pour éviter le double dispatch.

async def send_language_select(ctx: commands.Context, command_name: str):
    """Fonction utilitaire pour démarrer la vue de sélection de langue."""
    view = LanguageSelect(command_name, ctx)
    await view.start_interaction(ctx)


@bot.command(name='commands')
async def list_commands(ctx: commands.Context):
    """Affiche la liste des commandes avec sélection de langue."""
    await send_language_select(ctx, "commands")


@bot.command(name='ping')
async def ping(ctx: commands.Context):
    """
    Affiche la latence du bot sans sélecteur de langue.
    """
    latency_ms = round(bot.latency * 1000)
    response = f"{ctx.author.mention} :small_blue_diamond: Latence : **{latency_ms}ms**"
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
    """
    Affiche une liste de livres islamiques en français avec pagination.
    """
    books = get_books_fr()

    if not books:
        await ctx.send("❌ Aucun livre trouvé ou le fichier **book_fr.txt** est vide/mal formaté.")
        return

    # 1. Créer la vue du navigateur (gère total_pages > 1 si total_books > 0)
    view = BookBrowser(ctx, books)
    
    # 2. Générer la première page de l'embed
    first_page_embed = get_book_page_embed(books, 0, view.total_pages)
    
    # 3. Envoyer le message et stocker le message dans l'objet View
    view.message = await ctx.send(embed=first_page_embed, view=view)

# ----------------------------------------------------
# --- Fonctions pour le Serveur Web (Keep-Alive) (inchangées) ---
# ----------------------------------------------------

def run_web_server():
    """Démarre une application Flask pour maintenir le bot en vie."""
    app = Flask('')
    
    @app.route('/')
    def home():
        return "Bot est en ligne !"
    
    # IMPORTANT : Utilise le port attribué par Render (ou 8080 par défaut)
    port = int(os.environ.get('PORT', 8080))
    # Flask s'exécute ici. Le mode debug=False est crucial en production.
    app.run(host='0.0.0.0', port=port, debug=False)


# --- Fonction Principale (inchangée) ---

def main():
    """Fonction principale pour démarrer le bot et le serveur web."""
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        logger.error(
            "DISCORD_BOT_TOKEN non trouvé dans les variables d'environnement! Arrêt du bot.")
        return
        
    # 1. Démarrer le serveur web dans un thread séparé (en arrière-plan)
    logger.info("Démarrage du serveur web Keep-Alive...")
    t = Thread(target=run_web_server)
    t.start()
    
    # 2. Lancer le bot Discord (cela doit être la fonction principale)
    logger.info("Démarrage du bot Discord...")
    try:
        bot.run(token)
    except discord.LoginFailure:
        logger.critical("Échec de la connexion: Jeton invalide.")
    except Exception as e:
        logger.critical(f"Erreur inattendue au lancement du bot: {e}")


if __name__ == "__main__":
    main()
