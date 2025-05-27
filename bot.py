import discord
from discord.ext import commands
import requests
import os
from flask import Flask
from threading import Thread

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Keep-alive server (for Replit)
app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# In-memory databases
reviews = {}
currently_reading = {}

GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")

# COMMAND: !review <book name>
@bot.command(name='review')
async def review_book(ctx, *, book_title):
    search_url = f"https://www.googleapis.com/books/v1/volumes?q={book_title}&key={GOOGLE_BOOKS_API_KEY}"
    response = requests.get(search_url)
    data = response.json()

    if "items" not in data or len(data["items"]) == 0:
        await ctx.send("❌ Book not found.")
        return

    book = data["items"][0]["volumeInfo"]
    title = book.get("title", "Unknown Title")
    authors = ", ".join(book.get("authors", ["Unknown Author"]))
    description = book.get("description", "No description available.")

    await ctx.send(f"**{title}** by {authors}\n\n{description}\n\nPlease rate this book (1-5) and leave a review with `!rate \"{title}\" <1-5> <your review>`")

# COMMAND: !rate "<book title>" <1-5> <review>
@bot.command(name='rate')
async def rate_book(ctx, title: str, rating: int, *, user_review):
    user_id = str(ctx.author.id)

    if title not in reviews:
        reviews[title] = []

    reviews[title].append({
        "user": ctx.author.display_name,
        "rating": rating,
        "review": user_review
    })

    await ctx.send(f"✅ Thanks, {ctx.author.display_name}! Your review for **{title}** has been recorded.")

# COMMAND: !reviews <book title>
@bot.command(name='reviews')
async def show_reviews(ctx, *, title):
    if title not in reviews or not reviews[title]:
        await ctx.send("📭 No reviews yet for this book.")
        return

    msg = f"📚 Reviews for **{title}**:\n\n"
    for entry in reviews[title]:
        msg += f"⭐ {entry['rating']}/5 by {entry['user']}: {entry['review']}\n\n"

    await ctx.send(msg)

# COMMAND: !currentlyreading [<book title> | <username>]
@bot.command(name='currentlyreading')
async def currently_reading_command(ctx, *, arg=None):
    user_id = str(ctx.author.id)

    if arg is None:
        # No argument – show user's current book
        if user_id in currently_reading:
            await ctx.send(f"📖 You are currently reading: **{currently_reading[user_id]}**")
        else:
            await ctx.send("❌ You are not currently reading any book.")
        return

    # Try to find a user by mention or name
    mentioned_user = None
    if ctx.message.mentions:
        mentioned_user = ctx.message.mentions[0]
    else:
        for member in ctx.guild.members:
            if member.name.lower() == arg.lower() or member.display_name.lower() == arg.lower():
                mentioned_user = member
                break

    if mentioned_user:
        target_id = str(mentioned_user.id)
        if target_id in currently_reading:
            await ctx.send(f"📖 {mentioned_user.display_name} is currently reading: **{currently_reading[target_id]}**")
        else:
            await ctx.send(f"❌ {mentioned_user.display_name} is not currently reading any book.")
    else:
        # No matching user – assume it's a book title
        currently_reading[user_id] = arg
        await ctx.send(f"✅ Got it! You're now marked as reading: **{arg}**")

# COMMAND: !clearreading
@bot.command(name='clearreading')
async def clear_reading(ctx):
    user_id = str(ctx.author.id)
    if user_id in currently_reading:
        del currently_reading[user_id]
        await ctx.send("🗑️ Your currently reading book has been cleared.")
    else:
        await ctx.send("❌ You don't have a currently reading book to clear.")

# COMMAND: !help (overriding default)
@bot.command(name='help')
async def help_command(ctx):
    help_text = """
📚 **BearCrabs Book Bot Commands**

`!review <book title>` – Search for a book and start a review  
`!rate "<book title>" <1-5> <review>` – Submit a review  
`!reviews <book title>` – Show all reviews for a book  
`!currentlyreading` – Show your current book  
`!currentlyreading <book title>` – Set your current book  
`!currentlyreading <username>` – See someone else's book  
`!clearreading` – Clear your currently reading status  
"""
    await ctx.send(help_text)

# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))
