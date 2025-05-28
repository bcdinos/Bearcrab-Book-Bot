import discord
from discord.ext import commands
import requests
import os
import threading
from flask import Flask

# Flask setup
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# API key from environment
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# In-memory storage
currently_reading = {}
user_reviews = {}
review_sessions = {}

# Google Books helper
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
    thumbnail = book.get("imageLinks", {}).get("thumbnail", "")
    link = data["items"][0].get("volumeInfo", {}).get("infoLink", "")
    return {
        "title": title,
        "authors": authors,
        "description": description,
        "thumbnail": thumbnail,
        "link": link
    }

# Commands

@bot.command(name='reading')
async def reading_command(ctx, *, arg=None):
    if arg is None:
        book = currently_reading.get(ctx.author.id)
        if book:
            await ctx.send(f"{ctx.author.display_name} is currently reading: {book['title']} by {book['authors']}\n{book['link']}")
        else:
            await ctx.send("You haven't set a currently reading book. Use `!reading [book title]` to set one.")
    elif len(ctx.message.mentions) > 0:
        user = ctx.message.mentions[0]
        book = currently_reading.get(user.id)
        if book:
            await ctx.send(f"{user.display_name} is currently reading: {book['title']} by {book['authors']}\n{book['link']}")
        else:
            await ctx.send(f"{user.display_name} hasn't set a currently reading book.")
    else:
        book_info = search_google_books(arg)
        if book_info:
            currently_reading[ctx.author.id] = book_info
            await ctx.send(f"{ctx.author.display_name} is now reading: {book_info['title']} by {book_info['authors']}\n{book_info['link']}")
        else:
            await ctx.send("Could not find that book.")

@bot.command(name='clearreading')
async def clear_reading_command(ctx):
    if ctx.author.id in currently_reading:
        del currently_reading[ctx.author.id]
        await ctx.send("Your currently reading book has been cleared.")
    else:
        await ctx.send("You don't have a currently reading book set.")

@bot.command(name='review')
async def start_review(ctx, *, book_title: str):
    book_info = search_google_books(book_title)
    if not book_info:
        await ctx.send("Could not find that book.")
        return

    review_sessions[ctx.author.id] = {
        "step": "awaiting_rating",
        "book": book_info
    }

    await ctx.send(f"You selected **{book_info['title']}** by {book_info['authors']}.\nPlease enter a rating from 1 to 5.")

@bot.command(name='reviews')
async def show_reviews(ctx, user: discord.User = None):
    user = user or ctx.author
    reviews = user_reviews.get(user.id)
    if not reviews:
        await ctx.send(f"{user.display_name} has not submitted any reviews.")
        return

    response = f"**Reviews by {user.display_name}:**\n"
    for review in reviews:
        response += f"\n📚 **{review['book']['title']}** by {review['book']['authors']}\n⭐ {review['rating']}/5"
        if review.get("text"):
            response += f"\n💬 {review['text']}"
        response += f"\n🔗 {review['book']['link']}\n"

    await ctx.send(response)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    if user_id in review_sessions:
        session = review_sessions[user_id]
        step = session['step']

        if step == "awaiting_rating":
            try:
                rating = int(message.content)
                if 1 <= rating <= 5:
                    session['rating'] = rating
                    session['step'] = "awaiting_text"
                    await message.channel.send("Optional: Type your review or type `skip` to skip writing a review.")
                else:
                    await message.channel.send("Please enter a number between 1 and 5.")
            except ValueError:
                await message.channel.send("That is not a valid number. Please enter a number between 1 and 5.")
            return

        elif step == "awaiting_text":
            text = None if message.content.lower() == "skip" else message.content
            review_data = {
                "book": session["book"],
                "rating": session["rating"],
                "text": text
            }
            user_reviews.setdefault(user_id, []).append(review_data)
            del review_sessions[user_id]

            book = review_data["book"]
            await message.channel.send(
                f"✅ Review saved!\n"
                f"📖 **{book['title']}** by {book['authors']}\n"
                f"⭐ Rating: {review_data['rating']}/5\n"
                f"{'💬 ' + text if text else ''}\n"
                f"🔗 {book['link']}"
            )
            return

    await bot.process_commands(message)

@bot.command(name='bookhelp')
async def book_help(ctx):
    await ctx.send("""
**📚 BearCrabs Book Bot Commands**

`!reading [book title]` – Set what you’re reading  
`!reading [@user]` – See what someone else is reading  
`!clearreading` – Clear your current book  
`!review [book title]` – Start a review (bot will prompt next steps)  
`!reviews [@user]` – Show reviews by you or someone else  
`!bookhelp` – Show this help message
""")

# Run Flask and Discord bot
if __name__ == '__main__':
    def run_flask():
        app.run(host='0.0.0.0', port=8080)

    threading.Thread(target=run_flask).start()

    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN environment variable not set.")
    else:
        bot.run(DISCORD_TOKEN)
