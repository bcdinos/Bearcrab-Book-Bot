import discord
from discord.ext import commands, tasks
import aiohttp
import os

# Get tokens from environment variables for security
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GOOGLE_BOOKS_API_KEY = os.getenv('GOOGLE_BOOKS_API_KEY')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# In-memory storage for user reviews and currently reading (you can later move to DB)
user_reviews = {}
currently_reading = {}

# Helper to fetch book info from Google Books API
async def fetch_book_info(book_title):
    url = f'https://www.googleapis.com/books/v1/volumes?q={book_title}&key={GOOGLE_BOOKS_API_KEY}&maxResults=1'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            if 'items' not in data or len(data['items']) == 0:
                return None
            book = data['items'][0]['volumeInfo']
            title = book.get('title', 'Unknown Title')
            authors = ", ".join(book.get('authors', ['Unknown Author']))
            description = book.get('description', 'No description available.')
            return {
                'title': title,
                'authors': authors,
                'description': description
            }

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.command(name='review')
async def review(ctx, rating: int, *, book_title):
    """Leave a review and rating for a book."""
    if rating < 1 or rating > 5:
        await ctx.send("Please provide a rating between 1 and 5.")
        return

    info = await fetch_book_info(book_title)
    if not info:
        await ctx.send(f"Sorry, I couldn't find the book titled '{book_title}'.")
        return

    # Save review in-memory (replace with DB if you want persistent storage)
    user_reviews[(ctx.author.id, info['title'])] = {
        'rating': rating,
        'review': f"{ctx.author.name}'s review on {info['title']}",
    }

    await ctx.send(f"Thanks for your review of **{info['title']}** by {info['authors']}! You gave it a {rating}/5.")

@bot.command(name='currentlyreading')
async def currently_reading_cmd(ctx, *, book_title):
    """Set what book you are currently reading."""
    info = await fetch_book_info(book_title)
    if not info:
        await ctx.send(f"Couldn't find the book titled '{book_title}'.")
        return

    currently_reading[ctx.author.id] = info['title']
    await ctx.send(f"{ctx.author.name} is now reading **{info['title']}**.")

@bot.command(name='showreading')
async def show_reading(ctx, member: discord.Member = None):
    """Show what book a user is currently reading."""
    member = member or ctx.author
    book = currently_reading.get(member.id, None)
    if not book:
        await ctx.send(f"{member.name} hasn't set a currently reading book.")
        return
    await ctx.send(f"{member.name} is currently reading **{book}**.")

@bot.command(name='helpme')
async def help_command(ctx):
    help_text = """
**BearCrabs Book Bot Commands:**
`!review <rating 1-5> <book title>` - Leave a rating and review for a book.
`!currentlyreading <book title>` - Set what you’re currently reading.
`!showreading [@user]` - Show what book a user is reading. If no user mentioned, shows yours.
`!helpme` - Show this help message.
"""
    await ctx.send(help_text)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)

from flask import Flask
from threading import Thread

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
