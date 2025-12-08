import discord
from discord.ext import commands
from discord import ui
import os
import logging
import random
from typing import List, Tuple, Optional, Dict, Any
import math # Importation nécessaire pour le calcul des pages

# --- Configuration du Logger ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('HadithSahih')

# --- Configuration du Bot et des Intents ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Initialisation du bot avec le préfixe 'hs!'
bot = commands.Bot(command_prefix='hs!', intents=intents)

# --- Constantes de Pagination ---
BOOKS_PER_PAGE = 5 # Nombre de livres à afficher par page

# --- Classe View pour la Sélection de Langue (inchangée) ---

class LanguageSelect(ui.View):
    """Vue interactive pour permettre à l'utilisateur de sélectionner une langue (FR/ENG)."""

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
            # Édite le message pour désactiver les boutons après le timeout
            await self.ctx.message.edit(view=self)
        except discord.NotFound:
            pass # Le message a peut-être été supprimé

    def check_author(self, interaction: discord.Interaction) -> bool:
        """Vérifie si l'utilisateur qui clique est l'auteur de la commande."""
        if interaction.user != self.ctx.author:
            error_message = "This is not your command! / Ce n'est pas ta commande!"
            # Envoi du message d'erreur éphémère à l'utilisateur non autorisé
            # Note: Si le message original a été envoyé par `ctx.send`, il faut utiliser `interaction.response.send_message`
            # avec `ephemeral=True` pour éviter un échec d'interaction si une réponse/édition a déjà été faite.
            if not interaction.response.is_done():
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
        # Désactive tous les boutons après le premier clic
        for item in self.children:
            item.disabled = True

        # Mapping des commandes aux fonctions de génération d'embed
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

# --- Fonctions Utilitaires de Fichier ---

# (get_random_hadith est inchangée)
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
                    # Le format est [Lien] [Titre]
                    # On cherche la première occurrence de ']' et on sépare
                    try:
                        link_end = line.find(']')
                        link_full = line[:link_end+1].strip() # Ex: [lien.com]
                        title_full = line[link_end+1:].strip() # Ex: [Titre]

                        # Extraction du lien (sans les crochets)
                        link = link_full[1:-1]
                        
                        # Extraction du titre (sans les crochets)
                        title = title_full[1:-1]

                        if link and title:
                             books.append((title, link))
                    except IndexError:
                        # Gère les lignes mal formatées (par exemple, un seul crochet)
                        logger.warning(f"Ligne de livre mal formatée ignorée: {line}")
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
    # ... (inchangée)
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
    # ... (inchangée)
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
    # ... (inchangée)
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
# --- Classes et Fonctions pour la Pagination du Livre ---
# ----------------------------------------------------

def get_book_page_embed(books: List[Tuple[str, str]], page_num: int, total_pages: int) -> discord.Embed:
    """Génère l'embed pour une page spécifique de la liste de livres."""
    
    # Calcul des indices de début et de fin pour la page
    start_index = page_num * BOOKS_PER_PAGE
    end_index = start_index + BOOKS_PER_PAGE
    
    # Extraction des livres pour la page actuelle
    page_books = books[start_index:end_index]

    description = ""
    # Création de la description avec les liens formatés
    for i, (title, link) in enumerate(page_books, start=start_index + 1):
        # Utilisation du format Markdown pour le lien: [Titre](Lien)
        description += f"**{i}.** [{title}]({link})\n\n"

    embed = discord.Embed(
        title="📚 Bibliothèque Islamique - Livres en Français",
        description=description or "Aucun livre trouvé sur cette page.",
        color=discord.Color.gold()
    )

    # Ajout du numéro de page dans le footer
    embed.set_footer(text=f"Page {page_num + 1}/{total_pages} • HadithSahih • @n9rs9")
    return embed


class BookBrowser(ui.View):
    """Vue interactive pour naviguer entre les pages de la liste de livres."""

    def __init__(self, ctx: commands.Context, books: List[Tuple[str, str]]):
        super().__init__(timeout=180) # Timeout plus long pour la lecture
        self.ctx = ctx
        self.books = books
        self.total_books = len(books)
        # Calcul du nombre total de pages
        self.total_pages = math.ceil(self.total_books / BOOKS_PER_PAGE)
        self.current_page = 0 # La page commence à l'index 0
        
        # Désactiver les boutons de navigation initiaux
        self.update_buttons()

    async def on_timeout(self):
        """Désactive les boutons si le temps d'attente est écoulé."""
        for item in self.children:
            item.disabled = True
        try:
            # Édite le message pour désactiver les boutons après le timeout
            # Le message initial est stocké dans `self.message` après l'envoi
            await self.message.edit(view=self)
        except (discord.NotFound, AttributeError):
            pass

    def check_author(self, interaction: discord.Interaction) -> bool:
        """Vérifie si l'utilisateur qui clique est l'auteur de la commande."""
        if interaction.user != self.ctx.author:
            error_message = "This is not your command! / Ce n'est pas ta commande!"
            interaction.response.send_message(error_message, ephemeral=True)
            return False
        return True

    def update_buttons(self):
        """Met à jour l'état (disabled/emoji) des boutons de navigation."""
        # Récupération des boutons par leur ID (car ils n'ont pas de nom d'attribut direct ici)
        
        # Le premier enfant est le bouton de gauche
        left_button = self.children[0] 
        # Le deuxième enfant est le bouton de droite
        right_button = self.children[1] 

        # Bouton Gauche (Précédent)
        if self.current_page == 0:
            left_button.disabled = True
            left_button.style = discord.ButtonStyle.red # Utiliser un style différent pour 'X'
            left_button.emoji = "❌"
        else:
            left_button.disabled = False
            left_button.style = discord.ButtonStyle.primary
            left_button.emoji = "⬅️"

        # Bouton Droit (Suivant)
        if self.current_page == self.total_pages - 1:
            right_button.disabled = True
            right_button.style = discord.ButtonStyle.red # Utiliser un style différent pour 'X'
            right_button.emoji = "❌"
        else:
            right_button.disabled = False
            right_button.style = discord.ButtonStyle.primary
            right_button.emoji = "➡️"

    @ui.button(style=discord.ButtonStyle.primary, emoji="⬅️")
    async def previous_page(self, interaction: discord.Interaction, button: ui.Button):
        if not self.check_author(interaction):
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = get_book_page_embed(self.books, self.current_page, self.total_pages)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            # Ne devrait pas arriver si le bouton est désactivé, mais bonne pratique
            await interaction.response.edit_message(embed=get_book_page_embed(self.books, self.current_page, self.total_pages), view=self)


    @ui.button(style=discord.ButtonStyle.primary, emoji="➡️")
    async def next_page(self, interaction: discord.Interaction, button: ui.Button):
        if not self.check_author(interaction):
            return
        
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = get_book_page_embed(self.books, self.current_page, self.total_pages)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            # Ne devrait pas arriver si le bouton est désactivé, mais bonne pratique
            await interaction.response.edit_message(embed=get_book_page_embed(self.books, self.current_page, self.total_pages), view=self)

# ----------------------------------------------------
# --- Événements et Commandes du Bot (Mise à Jour) ---
# ----------------------------------------------------

@bot.event
async def on_ready():
    # ... (inchangée)
    """Se déclenche lorsque le bot est prêt."""
    logger.info(f'{bot.user} is connected to Discord!')
    logger.info(f'Bot ID: {bot.user.id}')
    logger.info(f'Connected servers: {len(bot.guilds)}')
    logger.info(f'Prefix: hs!')


@bot.event
async def on_message(message):
    # ... (inchangée)
    """
    Gestionnaire de messages. Il est important de laisser uniquement 
    bot.process_commands(message) pour éviter la double réponse,
    sauf si vous avez une logique de message personnalisée.
    """
    if message.author == bot.user:
        return
    await bot.process_commands(message) # Nécessaire pour traiter les commandes

# (send_language_select inchangée)
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
    # ... (inchangée)
    """Affiche la liste des commandes avec sélection de langue."""
    await send_language_select(ctx, "commands")


@bot.command(name='ping')
async def ping(ctx: commands.Context):
    # ... (inchangée)
    """
    Affiche la latence du bot sans sélecteur de langue.
    Format : @nomutilisateur :small_blue_diamond: Latence : **Xms**
    """
    latency_ms = round(bot.latency * 1000)
    
    response = f"{ctx.author.mention} :small_blue_diamond: Latence : **{latency_ms}ms**"
    
    await ctx.send(response)


@bot.command(name='info')
async def info(ctx: commands.Context):
    # ... (inchangée)
    """Affiche les informations du bot avec sélection de langue."""
    await send_language_select(ctx, "info")


@bot.command(name='hadith')
async def hadith(ctx: commands.Context):
    # ... (inchangée)
    """Affiche un Hadith aléatoire avec sélection de langue."""
    await send_language_select(ctx, "hadith")


@bot.command(name="book")
async def book(ctx: commands.Context):
    """Affiche une liste de livres islamiques en français avec pagination."""
    books = get_books_fr()

    if not books:
        await ctx.send("❌ Aucun livre trouvé dans **book_fr.txt**")
        return

    total_pages = math.ceil(len(books) / BOOKS_PER_PAGE)
    
    if total_pages == 0:
        await ctx.send("❌ Le fichier **book_fr.txt** est vide ou mal formaté.")
        return

    # 1. Générer la première page de l'embed
    first_page_embed = get_book_page_embed(books, 0, total_pages)
    
    # 2. Créer la vue du navigateur
    view = BookBrowser(ctx, books)
    
    # 3. Envoyer le message avec la vue et stocker le message
    message = await ctx.send(embed=first_page_embed, view=view)
    view.message = message # Stocker le message pour l'édition future (on_timeout)


# --- Fonction Principale ---

def main():
    # ... (inchangée)
    """Fonction principale pour démarrer le bot."""
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        # Erreur pour indiquer que le token n'est pas trouvé
        logger.error(
            "DISCORD_BOT_TOKEN non trouvé dans les variables d'environnement!")
        return
    logger.info("Starting the bot...")
    # Lancement du bot
    bot.run(token)


if __name__ == "__main__":
    main()
# owner : @n9rs9
# github : https://github.com/n9rs9
