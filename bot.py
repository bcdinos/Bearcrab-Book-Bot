import discord
from discord.ext import commands
import requests
from flask import Flask
import os  # For environment variables

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Flask app setup (if needed for uptime)
app = Flask(__name__)

# Store currently reading books by user ID
currently_reading = {}

# Google Books API key from environment variable
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Helper function to search Google Books
def search_google_books(query):
    if not GOOGLE_API_KEY:
        print("ERROR: GOOGLE_API_KEY not set in environment variables.")
        return None

    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&key={GOOGLE_API_KEY}"
    print(f"DEBUG: Google Books API URL: {url}")
    response = requests.get(url)
    print(f"DEBUG: Google Books API Response Status: {response.status_code}")

    if response.status_code != 200:
        print(f"ERROR: API request failed with status {response.status_code}")
        print(f"Response content: {response.text}")
        return None

    data = response.json()
    if "items" not in data or len(data["items"]) == 0:
        return None

    book = data["items"][0]["volumeInfo"]
    title = book.get("title", "Unknown Title")
    authors = ", ".join(book.get("authors", ["Unknown Author"]))
    description = book.get("description", "No description available.")
    thumbnail = book.get("imageLinks", {}).get("thumbnail", None)
    info_link = book.get("infoLink", None)

    return {
        "title": title,
        "authors": authors,
        "description": description,
        "thumbnail": thumbnail,
        "info_link": info_link
    }

# Commands

@bot.command(name='reading')
async def reading_command(ctx, *, arg=None):
    """Set or get currently reading book. If arg is empty, shows your current book.
       If arg is a username mention, shows their current book."""
    print(f"DEBUG: !reading called with arg: {arg}")
    if arg is None:
        # Show user's own current book
        book = currently_reading.get(ctx.author.id)
        if book:
            await ctx.send(f"{ctx.author.display_name} is currently reading: **{book}**")
        else:
            await ctx.send("You have not set a currently reading book. Use `!reading [book name]` to set one.")
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
            # Search for book info to add hyperlink if possible
            book_info = search_google_books(arg)
            if book_info and book_info.get("info_link"):
                await ctx.send(f"{ctx.author.display_name} is now reading: **[{arg}]({book_info['info_link']})**")
            else:
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

    if " - " not in review_text:
        await ctx.send("Please provide your review in the format: `[book name] - [your review]`")
        return

    book_name, review_body = map(str.strip, review_text.split(" - ", 1))

    book_info = search_google_books(book_name)
    if book_info is None:
        await ctx.send(f"Could not find the book '{book_name}' in Google Books.")
        return

    thumbnail_text = f"\nThumbnail: {book_info['thumbnail']}" if book_info.get("thumbnail") else ""
    info_link_text = f"[More Info]({book_info['info_link']})" if book_info.get("info_link") else ""

    await ctx.send(
        f"**Review Submitted!**\n"
        f"Book: **[{book_info['title']}]({book_info['info_link']})** by {book_info['authors']}\n"
        f"Rating: {rating}/5\n"
        f"Review: {review_body}\n"
        f"{info_link_text}"
    )

@bot.command(name='bookhelp')
async def book_help(ctx):
    """Show help message with commands."""
    help_message = """
**📚 BearCrabs Book Bot Commands**

`!reading [book name]` – Set the book you're currently reading  
`!reading [@username]` – Check what someone else is reading  
`!clearreading` – Clear your currently reading status  
`!review [rating 1-5] [book name] - [your review]` – Leave a book review  
`!bookhelp` – Show this help message
"""
    await ctx.send(help_message)

# Flask route for uptime (optional)
@app.route('/')
def home():
    return "I'm alive!"

# Run the bot
if __name__ == '__main__':
    import threading

    def run_flask():
        app.run(host='0.0.0.0', port=8080)

    threading.Thread(target=run_flask).start()

    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN environment variable not set.")
    else:
        bot.run(DISCORD_TOKEN)
