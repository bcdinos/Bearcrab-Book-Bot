import discord
from discord.ext import commands
import aiohttp
import os
from flask import Flask
from threading import Thread

# ----- Discord Bot Setup -----

intents = discord.Intents.default()
intents.message_content = True  # Needed to read message content

bot = commands.Bot(command_prefix='!', intents=intents)

GOOGLE_BOOKS_API_KEY = os.getenv('GOOGLE_BOOKS_API_KEY')

# Helper function to search Google Books API
async def search_book(title):
    url = f"https://www.googleapis.com/books/v1/volumes?q={title}&key={GOOGLE_BOOKS_API_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data["totalItems"] == 0:
                    return None
                book = data["items"][0]["volumeInfo"]
                return {
                    "title": book.get("title", "No title"),
                    "authors": ", ".join(book.get("authors", ["Unknown author"])),
                    "description": book.get("description", "No description available."),
                    "pageCount": book.get("pageCount", "Unknown"),
                    "averageRating": book.get("averageRating", "No rating"),
                    "thumbnail": book.get("imageLinks", {}).get("thumbnail", "")
                }
            else:
                return None

# Command: !review <book title>
@bot.command(name='review')
async def review(ctx, *, book_title):
    book = await search_book(book_title)
    if not book:
        await ctx.send("Sorry, I couldn't find that book.")
        return
    
    embed = discord.Embed(title=book["title"], description=book["description"][:500] + "...", color=0x00ff00)
    embed.set_thumbnail(url=book["thumbnail"])
    embed.add_field(name="Authors", value=book["authors"], inline=True)
    embed.add_field(name="Pages", value=book["pageCount"], inline=True)
    embed.add_field(name="Average Rating", value=str(book["averageRating"]), inline=True)
    await ctx.send(embed=embed)
    await ctx.send("Please rate this book from 1 to 5 by typing the number (you have 30 seconds).")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit() and 1 <= int(m.content) <= 5
    
    try:
        msg = await bot.wait_for('message', timeout=30.0, check=check)
        rating = int(msg.content)
        await ctx.send(f"Thanks for rating **{book['title']}** with a score of {rating}/5!")
        # Here you could store the rating somewhere (database or file)
    except:
        await ctx.send("No rating received. You can rate later if you want!")

# Command: !currentlyreading
currently_reading = {}

@bot.command(name='currentlyreading')
async def currently_reading_command(ctx, *, book_title=None):
    if book_title:
        currently_reading[ctx.author.id] = book_title
        await ctx.send(f"{ctx.author.display_name} is now reading **{book_title}**.")
    else:
        book = currently_reading.get(ctx.author.id)
        if book:
            await ctx.send(f"{ctx.author.display_name} is currently reading **{book}**.")
        else:
            await ctx.send("You haven't set a book you're currently reading. Use `!currentlyreading <book title>` to set one.")

# Ready event
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")

# ----- Flask Web Server to keep Replit awake -----

app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

# ----- Run Discord Bot -----

bot.run(os.getenv('DISCORD_TOKEN'))
