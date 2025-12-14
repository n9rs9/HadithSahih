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
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='hs!', intents=intents)

# --- Constantes de Pagination ---
BOOKS_PER_PAGE = 10 

# --- Sources de la Bibliographie (Dictionnaire par langue) ---
BIBLIO_SOURCES = {
    "FR": "• Site officiel de la mosquée de Médine\n• Site officiel du gouvernement Saoudien",
    "ENG": "• Official website of the Prophet's Mosque (Medina)\n• Official website of the Saudi Government"
}

# --- Fonctions Utilitaires de Fichier ---

def get_random_hadith(file_path: str = "hadiths_eng.txt") -> str:
    """Lit un fichier et renvoie une ligne aléatoire."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            hadiths = [h.strip() for h in f.readlines() if h.strip()]
            return random.choice(hadiths) if hadiths else "Empty file."
    except FileNotFoundError:
        return f"Error: {file_path} not found."
    except Exception as e:
        return "An error occurred."

# MODIFIÉ : Fonction générique pour lire n'importe quel fichier de livres
def get_books(file_path: str) -> List[Tuple[str, str]] | None:
    """
    Lit le fichier des livres. 
    Format attendu : [LIEN] [TITRE]
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            books = []
            for line in f:
                line = line.strip()
                if not line or not line.startswith('[') or ']' not in line:
                    continue
                try:
                    # Trouver le lien (premier crochet)
                    link_end = line.find(']')
                    link = line[1:link_end].strip()
                    
                    # Trouver le titre (deuxième crochet)
                    title_start = line.find('[', link_end + 1)
                    title_end = line.find(']', title_start + 1)

                    if link and title_start != -1 and title_end != -1:
                        title = line[title_start + 1:title_end].strip()
                        if title:
                            books.append((title, link))
                except Exception as e:
                    logger.warning(f"Ligne ignorée : {line}. Erreur: {e}")
                    continue
            return books
    except FileNotFoundError:
        logger.error(f"Fichier non trouvé: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Erreur lecture {file_path}: {e}")
        return None

def get_quiz_questions(file_path: str) -> List[Dict[str, Any]] | None:
    """
    Lit le fichier de quiz et retourne une liste de questions.
    Format attendu : [Question] [Bonne réponse] [Mauvaise 1] [Mauvaise 2]
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            questions = []
            for line in f:
                line = line.strip()
                if not line or not line.startswith('['):
                    continue
                
                parts = []
                current_pos = 0
                
                # Parser tous les crochets
                while True:
                    start = line.find('[', current_pos)
                    if start == -1:
                        break
                    end = line.find(']', start + 1)
                    if end == -1:
                        break
                    parts.append(line[start + 1:end].strip())
                    current_pos = end + 1
                
                # Vérifier qu'on a bien 4 parties (question + 3 réponses)
                if len(parts) == 4:
                    question_data = {
                        "question": parts[0],
                        "correct": parts[1],
                        "wrong1": parts[2],
                        "wrong2": parts[3]
                    }
                    questions.append(question_data)
            
            return questions if questions else None
    except FileNotFoundError:
        logger.error(f"Fichier non trouvé: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Erreur lecture quiz {file_path}: {e}")
        return None

# --- Fonctions de Génération d'Embeds ---

def get_commands_embed(lang: str) -> discord.Embed:
    if lang == "FR":
        embed = discord.Embed(
            title="Commandes de HadithSahih",
            description="Toutes les commandes de ce bot :satellite:",
            color=discord.Color.purple()
        )
        commands_list = [
            (" • hs!hadith", "*Affiche un hadith sahih aléatoire*"),
            (" • hs!book", "*Affiche une liste de livres islamiques*"),
            (" • hs!quiz", "*Lance un quiz sur l'Islam*"),
            (" • hs!commands", "*Toutes les commandes du bot*"),
            (" • hs!ping", "*Vérifie la latence du bot*"),
            (" • hs!info", "*Informations sur le bot*")
        ]
    else:
        embed = discord.Embed(
            title="HadithSahih's Commands",
            description="All commands for this bot :satellite:",
            color=discord.Color.purple()
        )
        commands_list = [
            (" • hs!hadith", "*Displays a random Sahih hadith*"),
            (" • hs!book", "*Displays a list of Islamic books*"),
            (" • hs!quiz", "*Start a quiz about Islam*"),
            (" • hs!commands", "*All commands for this bot*"),
            (" • hs!ping", "*Check the bot's latency*"),
            (" • hs!info", "*Bot information*")
        ]

    for name, value in commands_list:
        embed.add_field(name=name, value=value, inline=False)
    return embed

def get_info_embed(lang: str, server_count: int) -> discord.Embed:
    # Toujours description FR et champs ENG comme demandé
    embed = discord.Embed(
        title=" • HadithSahih",
        description="Des Hadiths Sahih pour vous chaque jour ! :books:", 
        color=discord.Color.pink())
    embed.add_field(name="Owner", value="@n9rs9", inline=True)
    embed.add_field(name="Servers", value=str(server_count), inline=True)
    return embed

def get_hadith_embed(lang: str) -> discord.Embed:
    if lang == "FR":
        hadith_text = get_random_hadith("hadiths_fr.txt")
        embed = discord.Embed(title="✨ Hadith Sahih Aléatoire", description=hadith_text, color=discord.Color.blue())
        footer_text = "رَبِّ زِدْنِي عِلْمًا - Rabbi zidnī ʿilman - Mon Seigneur, augmente ma connaissance"
    else:
        hadith_text = get_random_hadith("hadiths_eng.txt")
        embed = discord.Embed(title="✨ Random Sahih Hadith", description=hadith_text, color=discord.Color.blue())
        footer_text = "رَبِّ زِدْنِي عِلْمًا - Rabbi zidnī ʿilman - My Lord, increase me in knowledge"
    
    embed.set_footer(text=footer_text)
    return embed

# --- Pagination des Livres (MODIFIÉ pour la langue) ---

def get_book_page_embed(books: List[Tuple[str, str]], page_num: int, total_pages: int, lang: str) -> discord.Embed:
    """Génère l'embed pour une page de livres avec gestion de langue."""
    global BOOKS_PER_PAGE 
    
    start_index = page_num * BOOKS_PER_PAGE
    end_index = start_index + BOOKS_PER_PAGE
    page_books = books[start_index:end_index]

    description_list = ""
    for i, (title, link) in enumerate(page_books, start=start_index + 1):
        description_list += f"**{i}.** [{title}]({link})\n"

    # Textes traduits
    if lang == "FR":
        title_text = "📚 Bibliographie"
        instruction = "*Copiez le lien et collez-le si cela ne fonctionne pas*"
        sources = BIBLIO_SOURCES["FR"]
        empty_msg = "**Fin de la bibliographie.**" if page_num > 0 else "**Aucun livre trouvé.**"
        footer_pg = f"Page {page_num + 1}/{total_pages}"
    else:
        title_text = "📚 Bibliography"
        instruction = "*Copy the link and paste it if it doesn't work*"
        sources = BIBLIO_SOURCES["ENG"]
        empty_msg = "**End of bibliography.**" if page_num > 0 else "**No books found.**"
        footer_pg = f"Page {page_num + 1}/{total_pages}"

    if page_num == 0:
        header_text = f"**{sources}**\n\n{instruction}\n\n"
    else:
        header_text = f"{instruction}\n\n"

    full_description = f"{header_text}{description_list}" if description_list else f"{header_text}{empty_msg}"
    
    embed = discord.Embed(title=title_text, description=full_description, color=discord.Color.gold())
    embed.set_footer(text=footer_pg)
    return embed


class BookBrowser(ui.View):
    """Vue interactive pour naviguer entre les pages."""

    def __init__(self, ctx: commands.Context, books: List[Tuple[str, str]], lang: str):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.books = books
        self.lang = lang  # On stocke la langue
        self.total_books = len(books)
        self.total_pages = math.ceil(self.total_books / BOOKS_PER_PAGE)
        self.current_page = 0
        self.message: Optional[discord.Message] = None 
        
        # FORCE 2 PAGES MINIMUM (même si vide) comme demandé
        if self.total_pages < 2 and self.total_books > 0:
            self.total_pages = 2 
        
        self.update_buttons()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            if self.message: await self.message.edit(view=self)
        except: pass

    def check_author(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            msg = "Ce n'est pas ta commande!" if self.lang == "FR" else "This is not your command!"
            if not interaction.response.is_done():
                interaction.response.send_message(msg, ephemeral=True)
            return False
        return True

    def update_buttons(self):
        left_button = self.children[0]
        right_button = self.children[1]

        # Bouton Précédent
        if self.current_page == 0:
            left_button.disabled = True
            left_button.style = discord.ButtonStyle.red
            left_button.emoji = "❌"
        else:
            left_button.disabled = False
            left_button.style = discord.ButtonStyle.primary
            left_button.emoji = "⬅️"

        # Bouton Suivant
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
            # On passe self.lang ici
            embed = get_book_page_embed(self.books, self.current_page, self.total_pages, self.lang)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.edit_message(view=self) 

    @ui.button(style=discord.ButtonStyle.primary, emoji="➡️")
    async def next_page(self, interaction: discord.Interaction, button: ui.Button):
        if not self.check_author(interaction): return
        
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            # On passe self.lang ici
            embed = get_book_page_embed(self.books, self.current_page, self.total_pages, self.lang)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.edit_message(view=self)

# --- Vue Quiz ---

class QuizView(ui.View):
    """Vue interactive pour le quiz avec 3 questions."""

    def __init__(self, ctx: commands.Context, questions: List[Dict[str, Any]], lang: str):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.questions = questions
        self.lang = lang
        self.current_question = 0
        self.score = 0
        self.message: Optional[discord.Message] = None
        
        # Mélanger les réponses pour la première question
        self.shuffle_answers()
        self.create_buttons()

    def shuffle_answers(self):
        """Mélange les réponses pour la question actuelle."""
        q = self.questions[self.current_question]
        self.answers = [q["correct"], q["wrong1"], q["wrong2"]]
        random.shuffle(self.answers)
        self.correct_answer = q["correct"]

    def create_buttons(self):
        """Crée les boutons de réponse."""
        self.clear_items()
        
        for i, answer in enumerate(self.answers):
            button = ui.Button(
                label=answer,
                style=discord.ButtonStyle.primary,
                custom_id=f"answer_{i}"
            )
            button.callback = self.create_answer_callback(answer)
            self.add_item(button)

    def create_answer_callback(self, answer: str):
        """Crée un callback pour un bouton de réponse."""
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                msg = "Ce n'est pas ton quiz!" if self.lang == "FR" else "This is not your quiz!"
                await interaction.response.send_message(msg, ephemeral=True)
                return
            
            # Vérifier la réponse
            if answer == self.correct_answer:
                self.score += 1
            
            # Passer à la question suivante
            self.current_question += 1
            
            if self.current_question < len(self.questions):
                # Encore des questions
                self.shuffle_answers()
                self.create_buttons()
                embed = self.get_question_embed()
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                # Fin du quiz
                embed = self.get_result_embed()
                self.clear_items()
                await interaction.response.edit_message(embed=embed, view=self)
        
        return callback

    def get_question_embed(self) -> discord.Embed:
        """Génère l'embed pour la question actuelle."""
        q = self.questions[self.current_question]
        
        if self.lang == "FR":
            title = f"📝 Quiz - Question {self.current_question + 1}/3"
            color = discord.Color.green()
        else:
            title = f"📝 Quiz - Question {self.current_question + 1}/3"
            color = discord.Color.green()
        
        embed = discord.Embed(
            title=title,
            description=f"**{q['question']}**",
            color=color
        )
        return embed

    def get_result_embed(self) -> discord.Embed:
        """Génère l'embed du résultat final."""
        if self.lang == "FR":
            title = "🏆 Résultat du Quiz"
            description = f"**Score : {self.score}/3**"
            
            if self.score == 3:
                message = "Parfait ! Macha Allah ! 🌟"
            elif self.score == 2:
                message = "Très bien ! Continue comme ça ! 👍"
            elif self.score == 1:
                message = "Pas mal ! Tu peux faire mieux ! 💪"
            else:
                message = "Continue d'apprendre ! 📚"
        else:
            title = "🏆 Quiz Result"
            description = f"**Score: {self.score}/3**"
            
            if self.score == 3:
                message = "Perfect! Masha Allah! 🌟"
            elif self.score == 2:
                message = "Very good! Keep it up! 👍"
            elif self.score == 1:
                message = "Not bad! You can do better! 💪"
            else:
                message = "Keep learning! 📚"
        
        embed = discord.Embed(
            title=title,
            description=f"{description}\n\n{message}",
            color=discord.Color.gold()
        )
        return embed

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except:
            pass

# --- Vue Sélection de Langue (MODIFIÉE pour gérer Book et Quiz) ---

class LanguageSelect(ui.View):
    def __init__(self, command_name: str, ctx: commands.Context):
        super().__init__(timeout=60)
        self.command_name = command_name
        self.ctx = ctx
        self.language = None

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except: pass

    async def send_initial_message(self):
        embed = discord.Embed(
            title=":abcd: Choisissez votre langue / Choose your language",
            description="*Cliquez sur un bouton ci-dessous*\n*Click a button below*",
            color=discord.Color.red())
        self.message = await self.ctx.send(embed=embed, view=self)

    def check_author(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            interaction.response.send_message("This is not your command! / Ce n'est pas ta commande!", ephemeral=True)
            return False
        return True

    @ui.button(label="FR", style=discord.ButtonStyle.primary, emoji="🇫🇷")
    async def french_button(self, interaction: discord.Interaction, button: ui.Button):
        self.language = "FR"
        if not self.check_author(interaction): return
        await self.handle_selection(interaction)

    @ui.button(label="ENG", style=discord.ButtonStyle.secondary, emoji="🇬🇧")
    async def english_button(self, interaction: discord.Interaction, button: ui.Button):
        self.language = "ENG"
        if not self.check_author(interaction): return
        await self.handle_selection(interaction)

    async def handle_selection(self, interaction: discord.Interaction):
        """Gère le choix de la langue et lance la bonne action."""
        
        # Cas spécial pour BOOK : on doit lancer une nouvelle Vue (BookBrowser)
        if self.command_name == "book":
            # 1. Charger le bon fichier
            filename = "book_fr.txt" if self.language == "FR" else "book_eng.txt"
            books = get_books(filename)
            
            if not books:
                err_msg = "Erreur: Fichier introuvable." if self.language == "FR" else "Error: File not found."
                await interaction.response.edit_message(content=err_msg, embed=None, view=None)
                return

            # 2. Créer le BookBrowser
            # On désactive les boutons de langue avant de changer de vue (optionnel mais propre)
            for item in self.children: item.disabled = True
            
            browser_view = BookBrowser(self.ctx, books, self.language)
            first_page_embed = get_book_page_embed(books, 0, browser_view.total_pages, self.language)
            
            # 3. Mettre à jour le message existant avec la nouvelle vue
            browser_view.message = self.message # Lier le message à la vue
            await interaction.response.edit_message(embed=first_page_embed, view=browser_view)
            return

        # Cas spécial pour QUIZ
        if self.command_name == "quiz":
            filename = "quiz_fr.txt" if self.language == "FR" else "quiz_eng.txt"
            all_questions = get_quiz_questions(filename)
            
            if not all_questions or len(all_questions) < 3:
                err_msg = "Erreur: Pas assez de questions disponibles." if self.language == "FR" else "Error: Not enough questions available."
                await interaction.response.edit_message(content=err_msg, embed=None, view=None)
                return
            
            # Sélectionner 3 questions aléatoires
            selected_questions = random.sample(all_questions, 3)
            
            # Désactiver les boutons de langue
            for item in self.children: item.disabled = True
            
            # Créer la vue du quiz
            quiz_view = QuizView(self.ctx, selected_questions, self.language)
            first_question_embed = quiz_view.get_question_embed()
            
            quiz_view.message = self.message
            await interaction.response.edit_message(embed=first_question_embed, view=quiz_view)
            return

        # Pour les autres commandes (Info, Hadith, Commands), on génère juste un Embed
        for item in self.children: item.disabled = True
        
        embed_generators = {
            "commands": lambda lang: get_commands_embed(lang),
            "hadith": lambda lang: get_hadith_embed(lang),
            # Info n'est plus ici car hs!info est direct, mais au cas où :
            "info": lambda lang: get_info_embed(lang, len(bot.guilds))
        }

        embed_func = embed_generators.get(self.command_name)
        if embed_func:
            result_embed = embed_func(self.language)
            await interaction.response.edit_message(embed=result_embed, view=self)
        else:
            await interaction.response.edit_message(content="Error", view=None)


# --- Commandes ---

@bot.event
async def on_ready():
    logger.info(f'{bot.user} is connected to Discord!')
    activity = discord.Activity(type=discord.ActivityType.listening, name="hs!commands")
    await bot.change_presence(status=discord.Status.online, activity=activity)

async def send_language_select(ctx: commands.Context, command_name: str):
    view = LanguageSelect(command_name, ctx)
    await view.send_initial_message()

@bot.command(name='commands')
async def list_commands(ctx: commands.Context):
    await send_language_select(ctx, "commands")

@bot.command(name='ping')
async def ping(ctx: commands.Context):
    latency_ms = round(bot.latency * 1000)
    await ctx.send(f"{ctx.author.mention} :small_blue_diamond: Latence : **{latency_ms}ms**")

@bot.command(name='info')
async def info(ctx: commands.Context):
    # Directement en Anglais pour l'interface, mais description FR
    embed = get_info_embed("ENG", len(bot.guilds))
    await ctx.send(embed=embed)

@bot.command(name='hadith')
async def hadith(ctx: commands.Context):
    await send_language_select(ctx, "hadith")

@bot.command(name="book")
async def book(ctx: commands.Context):
    # Lance maintenant le sélecteur de langue au lieu de charger directement le FR
    await send_language_select(ctx, "book")

@bot.command(name="quiz")
async def quiz(ctx: commands.Context):
    """Lance un quiz de 3 questions aléatoires."""
    await send_language_select(ctx, "quiz")

# --- Serveur Web ---

def run_web_server():
    app = Flask('')
    @app.route('/')
    def home(): return "Bot est en ligne !"
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

def main():
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("Token introuvable.")
        return
    Thread(target=run_web_server).start()
    bot.run(token)

if __name__ == "__main__":
    main()
