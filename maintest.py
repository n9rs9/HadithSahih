import discord
from discord.ext import commands
from discord import ui
import os
import logging
import random
from threading import Thread
from flask import Flask

# --- CONFIGURATION INITIALE ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('HadithSahih')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='hs!', intents=intents)

# --- FONCTIONS D'HÉBERGEMENT 24/7 ---
def run_web_server():
    app = Flask('')
    @app.route('/')
    def home():
        return "Bot est en ligne !"
    
    # IMPORTANT : Utilise le port attribué par Render (ou 8080 par défaut)
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    """Lance le serveur Flask dans un thread séparé pour ne pas bloquer le bot."""
    t = Thread(target=run_web_server)
    t.start()

# --- CLASSES DE VUES DISCORD (Aucun changement nécessaire) ---
class LanguageSelect(ui.View):

    def __init__(self, command_name, ctx):
        super().__init__(timeout=60)
        self.command_name = command_name
        self.ctx = ctx
        self.language = None

    @ui.button(label="FR", style=discord.ButtonStyle.primary, emoji="🇫🇷")
    async def french_button(self, interaction: discord.Interaction,
                             button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                "Ce n'est pas ta commande!", ephemeral=True)
            return
        self.language = "FR"
        await self.show_command_result(interaction)

    @ui.button(label="ENG", style=discord.ButtonStyle.secondary, emoji="🇬🇧")
    async def english_button(self, interaction: discord.Interaction,
                             button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                "This is not your command!", ephemeral=True)
            return
        self.language = "ENG"
        await self.show_command_result(interaction)

    async def show_command_result(self, interaction: discord.Interaction):
        for item in self.children:
            item.disabled = True

        if self.command_name == "commands":
            embed = get_commands_embed(self.language)
        elif self.command_name == "ping":
            embed = get_ping_embed(self.language, bot.latency)
        elif self.command_name == "info":
            embed = get_info_embed(self.language, len(bot.guilds))
        elif self.command_name == "hadith":
            embed = get_hadith_embed(self.language)
        else:
            embed = discord.Embed(title="Error", description="Unknown command")

        await interaction.response.edit_message(embed=embed, view=self)


# --- FONCTIONS D'EMBEDS (Aucun changement nécessaire) ---
def get_commands_embed(lang):
    if lang == "FR":
        embed = discord.Embed(
            title="Commandes de HadithSahih",
            description="Toutes les commandes de ce bot :satellite:",
            color=discord.Color.purple())
        embed.add_field(name="    ", value="", inline=False)
        embed.add_field(name=" • hs!hadith",
                        value="*Affiche un hadith sahih aléatoire*",
                        inline=False)
        embed.add_field(name=" • hs!commands",
                        value="*Toutes les commandes du bot*",
                        inline=False)
        embed.add_field(name=" • hs!ping",
                        value="*Vérifie la latence du bot*",
                        inline=False)
        embed.add_field(name=" • hs!info",
                        value="*Informations sur le bot*",
                        inline=False)
        embed.add_field(name="    ", value="", inline=False)
        embed.set_footer(text="-             @n9rs9")
    else:
        embed = discord.Embed(
            title="HadithSahih's Commands",
            description="All commands for this bot :satellite:",
            color=discord.Color.purple())
        embed.add_field(name="    ", value="", inline=False)
        embed.add_field(name=" • hs!hadith",
                        value="*Displays a random Sahih hadith*",
                        inline=False)
        embed.add_field(name=" • hs!commands",
                        value="*All commands for this bot*",
                        inline=False)
        embed.add_field(name=" • hs!ping",
                        value="*Check the bot's latency*",
                        inline=False)
        embed.add_field(name=" • hs!info",
                        value="*Bot information*",
                        inline=False)
        embed.add_field(name="    ", value="", inline=False)
        embed.set_footer(text="-             @n9rs9")
    return embed


def get_ping_embed(lang, latency):
    latency_ms = round(latency * 1000)
    if lang == "FR":
        embed = discord.Embed(title=":ping_pong: Pong!",
                              description=f"*Latence: {latency_ms}ms*",
                              color=discord.Color.green())
    else:
        embed = discord.Embed(title=":ping_pong: Pong!",
                              description=f"*Latency: {latency_ms}ms*",
                              color=discord.Color.green())
    return embed


def get_info_embed(lang, server_count):
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


def get_hadith_embed(lang):
    if lang == "FR":
        hadith_text = get_random_hadith("hadiths_fr.txt")
        embed = discord.Embed(title="✨ Hadith Sahih Aléatoire",
                              description=hadith_text,
                              color=discord.Color.blue())
        embed.add_field(name="    ", value="", inline=False)
        embed.set_footer(
            text=
            "رَبِّ زِدْنِي عِلْمًا - Rabbi zidnī 'ilman - Mon Seigneur, augmente ma connaissance"
        )
    else:
        hadith_text = get_random_hadith("hadiths_eng.txt")
        embed = discord.Embed(title="✨ Random Sahih Hadith",
                              description=hadith_text,
                              color=discord.Color.blue())
        embed.add_field(name="    ", value="", inline=False)
        embed.set_footer(
            text=
            "رَبِّ زِدْنِي عِلْمًا - Rabbi zidnī 'ilman - My Lord, increase me in knowledge"
        )
    return embed


def get_random_hadith(file_path="hadiths_eng.txt"):
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
        return "Erreur: Fichier hadiths_eng.txt introuvable / Error: hadiths_eng.txt not found."
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier: {e}")
        return "Une erreur est survenue / An error occurred."


# --- ÉVÉNEMENTS DU BOT ---
@bot.event
async def on_ready():
    # Définition du statut personnalisé pour le bot
    activity_name = "hs!help · github.com/n9rs9/HadithSahih"
    activity = discord.Game(name=activity_name)
    await bot.change_presence(status=discord.Status.online, activity=activity)
    
    logger.info(f'{bot.user} is connected to Discord!')
    logger.info(f'Bot ID: {bot.user.id}')
    logger.info(f'Connected servers: {len(bot.guilds)}')
    logger.info(f'Prefix: hs!')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)


# --- COMMANDES DU BOT (Ping MODIFIÉ) ---
@bot.command(name='commands')
async def liste_commandes(ctx):
    embed = discord.Embed(
        title=":abcd: Choisissez votre langue / Choose your language",
        description=
        "*Cliquez sur un bouton ci-dessous*\n*Click a button below*",
        color=discord.Color.red())
    view = LanguageSelect("commands", ctx)
    await ctx.send(embed=embed, view=view)


@bot.command(name='ping')
async def ping(ctx):
    # Calcule la latence en millisecondes
    latency_ms = round(bot.latency * 1000)
    
    # Répond directement avec le format spécifié, sans sélection de langue/embed
    await ctx.send(
        f'{ctx.author.mention} *:small_blue_diamond: Latence : {latency_ms}ms*'
    )


@bot.command(name='info')
async def info(ctx):
    embed = discord.Embed(
        title=":abcd: Choisissez votre langue / Choose your language",
        description=
        "*Cliquez sur un bouton ci-dessous*\n*Click a button below*",
        color=discord.Color.red())
    view = LanguageSelect("info", ctx)
    await ctx.send(embed=embed, view=view)


@bot.command(name='hadith')
async def hadith(ctx):
    embed = discord.Embed(
        title=":abcd: Choisissez votre langue / Choose your language",
        description=
        "*Cliquez sur un bouton ci-dessous*\n*Click a button below*",
        color=discord.Color.red())
    view = LanguageSelect("hadith", ctx)
    await ctx.send(embed=embed, view=view)


# --- FONCTION DE LANCEMENT PRINCIPALE ---
def main():
    token = os.environ.get('DISCORD_TOKEN') 
    if not token:
        logger.error(
            "DISCORD_TOKEN non trouvé dans les variables d'environnement!")
        return
    
    # 1. Lance le serveur Flask en arrière-plan
    keep_alive() 
    
    # 2. Lance le bot Discord sur le thread principal (bloquant)
    logger.info("Starting the bot...")
    bot.run(token)


if __name__ == "__main__":
    main()
