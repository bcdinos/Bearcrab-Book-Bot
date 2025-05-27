
import discord
from discord.ext import commands
import requests
from flask import Flask

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Flask app setup (if needed for uptime)
app = Flask(__name__)

# Store currently reading books by user ID
currently_reading = {}

# Google Books API key
GOOGLE_API_KEY = "YOUR_GOOGLE_BOOKS_API_KEY"

# Helper function to search Google Books
def search_google_books(query):
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&key={GOOGLE_API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()
    if "items" not in data or len(data["items"]) == 0:
        return None
    book = data["items"][0]["volumeInfo"]
    title = book.get("title", "Unknown Title")
    authors = ", ".join(book.get("authors", ["Unknown Author"]))
    description = book.get("description", "No description available.")
    return {
        "title": title,
        "authors": authors,
        "description": description
    }

# Commands

@bot.command(name='currentlyreading')
async def currently_reading_command(ctx, *, arg=None):
    """Set or get currently reading book. If arg is empty, shows your current book.
       If arg is a username mention, shows their current book."""
    if arg is None:
        # Show user's own current book
        book = currently_reading.get(ctx.author.id)
        if book:
            await ctx.send(f"{ctx.author.display_name} is currently reading: **{book}**")
        else:
            await ctx.send("You have not set a currently reading book. Use `!currentlyreading [book name]` to set one.")
    else:
        # Check if arg is a user mention
        if len(ctx.message.mentions) > 0:
            user = ctx.message.mentions[0]
            book = currently_reading.get(user.id)
            if book:
                await ctx.send(f"{user.display_name} is currently reading: **{book}**")
            else:
                await ctx.send(f"{user.display_name} has not set a currently reading book.")
        else:
            # Set user's current book
            currently_reading[ctx.author.id] = arg
            await ctx.send(f"{ctx.author.display_name} is now reading: **{arg}**")

@bot.command(name='clearreading')
async def clear_reading_command(ctx):
    """Clear the currently reading book for the user."""
    if ctx.author.id in currently_reading:
        del currently_reading[ctx.author.id]
        await ctx.send(f"{ctx.author.display_name}, your currently reading book has been cleared.")
    else:
        await ctx.send("You don't have a currently reading book set.")

@bot.command(name='review')
async def review_command(ctx, rating: int, *, review_text: str):
    """Leave a review with rating 1-5 and text."""
    if rating < 1 or rating > 5:
        await ctx.send("Please provide a rating between 1 and 5.")
        return

    # Split review_text into book name and review body if format is "[book name] - [review]"
    if " - " not in review_text:
        await ctx.send("Please provide your review in the format: `[book name] - [your review]`")
        return

    book_name, review_body = map(str.strip, review_text.split(" - ", 1))

    # Search Google Books for book info
    book_info = search_google_books(book_name)
    if book_info is None:
        await ctx.send(f"Could not find the book '{book_name}' in Google Books.")
        return

    # Here you can add logic to save the review somewhere if you want (database, file, etc.)

    await ctx.send(
        f"**Review Submitted!**\n"
        f"Book: {book_info['title']} by {book_info['authors']}\n"
        f"Rating: {rating}/5\n"
        f"Review: {review_body}"
    )

@bot.command(name='bookhelp')
async def book_help(ctx):
    """Show help message with commands."""
    help_message = """
**📚 BearCrabs Book Bot Commands**

`!currentlyreading [book name]` – Set the book you're currently reading  
`!currentlyreading [@username]` – Check what someone else is reading  
`!clearreading` – Clear your currently reading status  
`!review [rating 1-5] [book name] - [your review]` – Leave a book review  
`!bookhelp` – Show this help message
"""
    await ctx.send(help_message)

# Flask route for uptime (optional, for hosting platforms)
@app.route('/')
def home():
    return "I'm alive!"

# Run the bot
if __name__ == '__main__':
    import os
    import threading

    # Run Flask app in a thread so bot and webserver run concurrently
    def run_flask():
        app.run(host='0.0.0.0', port=8080)

    threading.Thread(target=run_flask).start()

    # Run Discord bot
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN environment variable not set.")
    else:
        bot.run(DISCORD_TOKEN)
