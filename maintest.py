import discord
from discord.ext import commands
from discord import ui
import os
import logging
import random
from typing import List, Tuple, Optional, Dict
import math
from flask import Flask
from threading import Thread

# --- Logger ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger('HadithSahih')

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='hs!', intents=intents)

# --- Constantes ---
BOOKS_PER_PAGE = 10
BIBLIO_SOURCES = {
    "FR": "• Site officiel de la mosquée de Médine\n• Site officiel du gouvernement Saoudien",
    "ENG": "• Official website of the Prophet's Mosque\n• Official website of the Saudi Government"
}

# --- Lecture Fichiers ---

def get_random_hadith(file_path: str = "hadiths_eng.txt") -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            hadiths = [h.strip() for h in f.readlines() if h.strip()]
            return random.choice(hadiths) if hadiths else "Empty file."
    except Exception: return "Error reading file."

def get_books(file_path: str) -> List[Tuple[str, str]] | None:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            books = []
            for line in f:
                if not line.startswith('['): continue
                try:
                    link_end = line.find(']')
                    link = line[1:link_end].strip()
                    title_start = line.find('[', link_end + 1)
                    title_end = line.find(']', title_start + 1)
                    if link and title_start != -1:
                        title = line[title_start + 1:title_end].strip()
                        books.append((title, link))
                except: continue
            return books
    except: return None

# NOUVEAU : Lecture du Quiz (Question, BonneReponse, Mauvaise1, Mauvaise2)
def get_quiz_data(file_path: str) -> List[Dict]:
    questions = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or not line.startswith('['): continue
                
                # On découpe par les crochets ']'
                parts = line.split(']')
                # On nettoie les '[' restants et les espaces
                cleaned_parts = [p.replace('[', '').strip() for p in parts if p.strip()]
                
                # Il nous faut au moins 4 parties : Q, Bonne, Mauvaise1, Mauvaise2
                if len(cleaned_parts) >= 4:
                    questions.append({
                        "question": cleaned_parts[0],
                        "correct": cleaned_parts[1],
                        "wrongs": [cleaned_parts[2], cleaned_parts[3]]
                    })
    except Exception as e:
        logger.error(f"Erreur quiz: {e}")
    return questions

# --- Moteur du Jeu Quiz ---

class QuizButton(ui.Button):
    """Bouton individuel pour une réponse."""
    def __init__(self, label: str, is_correct: bool):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.is_correct = is_correct

    async def callback(self, interaction: discord.Interaction):
        # On délègue la logique à la Vue principale
        view: QuizGame = self.view
        if interaction.user != view.ctx.author:
            return await interaction.response.send_message("Ce n'est pas votre partie !", ephemeral=True)
        
        await view.handle_answer(interaction, self.is_correct)

class QuizGame(ui.View):
    """Vue principale qui gère le déroulement du jeu."""
    def __init__(self, ctx, questions: List[Dict], lang: str):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.questions = questions
        self.lang = lang
        self.score = 0
        self.index = 0
        self.total = len(questions)
        
        # Mélanger l'ordre des questions au début
        random.shuffle(self.questions)
        
        # Charger la première question
        self.setup_question()

    def setup_question(self):
        """Prépare les boutons pour la question actuelle."""
        self.clear_items() # Enlever les anciens boutons
        
        current_q = self.questions[self.index]
        correct_answer = current_q["correct"]
        wrong_answers = current_q["wrongs"]
        
        # Créer la liste des options (1 bonne + 2 mauvaises)
        options = [{"label": correct_answer, "correct": True}]
        for wa in wrong_answers:
            options.append({"label": wa, "correct": False})
        
        # Mélanger l'ordre des boutons pour que la bonne réponse ne soit pas toujours la 1ère
        random.shuffle(options)
        
        # Créer les boutons
        for opt in options:
            self.add_item(QuizButton(label=opt["label"], is_correct=opt["correct"]))

    def get_embed(self, finished=False):
        """Génère l'embed d'affichage."""
        if finished:
            title = "🏆 Quiz Terminé !" if self.lang == "FR" else "🏆 Quiz Finished!"
            desc = f"Score final : **{self.score}/{self.total}**"
            color = discord.Color.gold()
            return discord.Embed(title=title, description=desc, color=color)
        
        current_q = self.questions[self.index]
        title = "❓ Quiz Islam"
        
        # Compteur de score en temps réel
        score_text = f"Score: {self.score}/{self.index}"
        progress_text = f"Question: {self.index + 1}/{self.total}"
        
        embed = discord.Embed(title=title, description=f"**{current_q['question']}**", color=discord.Color.blue())
        embed.set_footer(text=f"{progress_text} | {score_text}")
        return embed

    async def handle_answer(self, interaction: discord.Interaction, is_correct: bool):
        if is_correct:
            self.score += 1
        
        self.index += 1
        
        if self.index < self.total:
            # S'il reste des questions
            self.setup_question()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            # Fin du jeu
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(embed=self.get_embed(finished=True), view=None)

# --- Classes Affichage Classiques ---

def get_book_page_embed(books, page_num, total_pages, lang):
    global BOOKS_PER_PAGE 
    start = page_num * BOOKS_PER_PAGE
    end = start + BOOKS_PER_PAGE
    page_books = books[start:end]
    desc = ""
    for i, (t, l) in enumerate(page_books, start=start + 1): desc += f"**{i}.** [{t}]({l})\n"
    
    sources = BIBLIO_SOURCES["FR"] if lang == "FR" else BIBLIO_SOURCES["ENG"]
    instr = "*Copiez le lien...*" if lang == "FR" else "*Copy the link...*"
    title = "📚 Bibliographie" if lang == "FR" else "📚 Bibliography"
    header = f"**{sources}**\n\n{instr}\n\n" if page_num == 0 else f"{instr}\n\n"
    full = header + (desc if desc else ("Fin." if lang=="FR" else "End."))
    
    embed = discord.Embed(title=title, description=full, color=discord.Color.gold())
    embed.set_footer(text=f"Page {page_num + 1}/{total_pages}")
    return embed

class BookBrowser(ui.View):
    def __init__(self, ctx, books, lang):
        super().__init__(timeout=180)
        self.ctx = ctx; self.books = books; self.lang = lang
        self.total_pages = math.ceil(len(books) / 10)
        if self.total_pages < 2 and len(books) > 0: self.total_pages = 2
        self.current_page = 0; self.message = None
        self.update_buttons()

    async def on_timeout(self):
        for c in self.children: c.disabled = True
        try: await self.message.edit(view=self) 
        except: pass
    
    def check(self, i): return i.user == self.ctx.author

    def update_buttons(self):
        self.children[0].disabled = (self.current_page == 0)
        self.children[1].disabled = (self.current_page >= self.total_pages - 1)

    @ui.button(emoji="⬅️", style=discord.ButtonStyle.primary)
    async def prev(self, i: discord.Interaction, b: ui.Button):
        if not self.check(i): return
        self.current_page -= 1; self.update_buttons()
        await i.response.edit_message(embed=get_book_page_embed(self.books, self.current_page, self.total_pages, self.lang), view=self)

    @ui.button(emoji="➡️", style=discord.ButtonStyle.primary)
    async def next(self, i: discord.Interaction, b: ui.Button):
        if not self.check(i): return
        self.current_page += 1; self.update_buttons()
        await i.response.edit_message(embed=get_book_page_embed(self.books, self.current_page, self.total_pages, self.lang), view=self)

# --- Sélecteur Langue Principal ---

class LanguageSelect(ui.View):
    def __init__(self, command_name: str, ctx: commands.Context):
        super().__init__(timeout=60)
        self.command_name = command_name
        self.ctx = ctx
        self.language = None

    async def send_initial_message(self):
        embed = discord.Embed(title=":abcd: Langue / Language", description="🇫🇷 FR | 🇬🇧 ENG", color=discord.Color.red())
        self.message = await self.ctx.send(embed=embed, view=self)

    @ui.button(label="FR", style=discord.ButtonStyle.primary, emoji="🇫🇷")
    async def fr(self, i: discord.Interaction, b: ui.Button):
        self.language = "FR"; await self.handle(i)

    @ui.button(label="ENG", style=discord.ButtonStyle.secondary, emoji="🇬🇧")
    async def en(self, i: discord.Interaction, b: ui.Button):
        self.language = "ENG"; await self.handle(i)

    async def handle(self, i: discord.Interaction):
        if i.user != self.ctx.author: return
        
        if self.command_name == "book":
            fname = "book_fr.txt" if self.language == "FR" else "book_eng.txt"
            books = get_books(fname)
            if not books: return await i.response.edit_message(content="Erreur fichier book.", embed=None, view=None)
            for c in self.children: c.disabled = True
            view = BookBrowser(self.ctx, books, self.language)
            view.message = self.message
            await i.response.edit_message(embed=get_book_page_embed(books, 0, view.total_pages, self.language), view=view)
        
        elif self.command_name == "quiz":
            fname = "quiz_fr.txt" if self.language == "FR" else "quiz_eng.txt"
            questions = get_quiz_data(fname)
            if not questions: return await i.response.edit_message(content="Erreur fichier quiz.", embed=None, view=None)
            
            # Lancer le jeu
            for c in self.children: c.disabled = True
            game_view = QuizGame(self.ctx, questions, self.language)
            await i.response.edit_message(embed=game_view.get_embed(), view=game_view)
            
        else:
            # Autres commandes (hadith, info, commands)
            for c in self.children: c.disabled = True
            embed = None
            if self.command_name == "hadith":
                fname = "hadiths_fr.txt" if self.language == "FR" else "hadiths_eng.txt"
                text = get_random_hadith(fname)
                embed = discord.Embed(title="Hadith", description=text, color=discord.Color.blue())
            elif self.command_name == "commands":
                desc = "hs!hadith, hs!book, hs!quiz, hs!info"
                embed = discord.Embed(title="Commandes", description=desc, color=discord.Color.purple())
            
            if embed: await i.response.edit_message(embed=embed, view=self)

# --- Commandes ---

@bot.event
async def on_ready():
    logger.info(f'{bot.user} ready!')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="hs!commands"))

async def send_lang(ctx, cmd):
    await LanguageSelect(cmd, ctx).send_initial_message()

@bot.command()
async def commands(ctx): await send_lang(ctx, "commands")
@bot.command()
async def hadith(ctx): await send_lang(ctx, "hadith")
@bot.command()
async def book(ctx): await send_lang(ctx, "book")
@bot.command()
async def quiz(ctx): await send_lang(ctx, "quiz")
@bot.command()
async def info(ctx): 
    embed = discord.Embed(title="HadithSahih", description="Bot Islamique", color=discord.Color.pink())
    embed.add_field(name="Servers", value=str(len(bot.guilds)))
    await ctx.send(embed=embed)
@bot.command()
async def ping(ctx): await ctx.send(f"Pong! {round(bot.latency*1000)}ms")

# --- Web Server ---
def run_web():
    app = Flask('')
    @app.route('/')
    def home(): return "Online"
    app.run(host='0.0.0.0', port=8080)

def main():
    Thread(target=run_web).start()
    bot.run(os.environ.get('DISCORD_BOT_TOKEN'))

if __name__ == "__main__":
    main()
