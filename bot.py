import discord
from discord.ext import commands
import requests
from flask import Flask
import os
import threading

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Flask app setup (optional, for uptime)
app = Flask(__name__)

# Store currently reading books by user ID
currently_reading = {}

# Google Books API key from environment
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Helper function to search Google Books
def search_google_books(query):
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&key={GOOGLE_API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        print("Error fetching from Google Books API")
        return None
    data = response.json()
    if "items" not in data or len(data["items"]) == 0:
        return None
    book = data["items"][0]
    info = book["volumeInfo"]
    return {
        "title": info.get("title", "Unknown Title"),
        "authors": ", ".join(info.get("authors", ["Unknown Author"])),
        "description": info.get("description", "No description available."),
        "thumbnail": info.get("imageLinks", {}).get("thumbnail"),
        "link": info.get("infoLink")
    }

# Commands

@bot.command(name='reading')
async def reading_command(ctx, *, arg=None):
    """Set or get currently reading book. If arg is empty, shows your current book.
       If arg is a username mention, shows their current book."""
    if arg is None:
        # Show user's own current book
        book = currently_reading.get(ctx.author.id)
        if book:
            embed = discord.Embed(title=book["title"], url=book["link"], description=book["description"])
            embed.set_author(name=f"{ctx.author.display_name} is currently reading")
            embed.add_field(name="Author(s)", value=book["authors"], inline=False)
            if book.get("thumbnail"):
                embed.set_thumbnail(url=book["thumbnail"])
            await ctx.send(embed=embed)
        else:
            await ctx.send("You have not set a currently reading book. Use `!reading [book name]` to set one.")
    else:
        # Check if arg is a user mention
        if len(ctx.message.mentions) > 0:
            user = ctx.message.mentions[0]
            book = currently_reading.get(user.id)
            if book:
                embed = discord.Embed(title=book["title"], url=book["link"], description=book["description"])
                embed.set_author(name=f"{user.display_name} is currently reading")
                embed.add_field(name="Author(s)", value=book["authors"], inline=False)
                if book.get("thumbnail"):
                    embed.set_thumbnail(url=book["thumbnail"])
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"{user.display_name} has not set a currently reading book.")
        else:
            # Set user's current book
            book_info = search_google_books(arg)
            if book_info is None:
                await ctx.send(f"Could not find the book '{arg}' in Google Books.")
                return
            currently_reading[ctx.author.id] = book_info
            embed = discord.Embed(title=book_info["title"], url=book_info["link"], description=book_info["description"])
            embed.set_author(name=f"{ctx.author.display_name} is now reading")
            embed.add_field(name="Author(s)", value=book_info["authors"], inline=False)
            if book_info.get("thumbnail"):
                embed.set_thumbnail(url=book_info["thumbnail"])
            await ctx.send(embed=embed)

@bot.command(name='clearreading')
async def clear_reading_command(ctx):
    if ctx.author.id in currently_reading:
        del currently_reading[ctx.author.id]
        await ctx.send(f"{ctx.author.display_name}, your currently reading book has been cleared.")
    else:
        await ctx.send("You don't have a currently reading book set.")

@bot.command(name='bookhelp')
async def book_help(ctx):
    help_message = """
**📚 BearCrabs Book Bot Commands**

`!reading [book name]` – Set the book you're currently reading  
`!reading [@username]` – Check what someone else is reading  
`!clearreading` – Clear your currently reading status  
`!bookhelp` – Show this help message
"""
    await ctx.send(help_message)

@app.route('/')
def home():
    return "I'm alive!"

if __name__ == '__main__':
    def run_flask():
        app.run(host='0.0.0.0', port=8080)

    threading.Thread(target=run_flask).start()

    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN environment variable not set.")
    else:
        bot.run(DISCORD_TOKEN)
