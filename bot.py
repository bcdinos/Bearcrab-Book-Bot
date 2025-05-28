import discord
from discord.ext import commands
import requests
import os
import asyncio
from flask import Flask
from threading import Thread

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

currently_reading = {}
reviews = {}  # user_id -> list of reviews

def search_google_books(query, max_results=3):
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults={max_results}&key={GOOGLE_API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()
    if "items" not in data or len(data["items"]) == 0:
        return None
    books = []
    for item in data["items"]:
        v = item["volumeInfo"]
        books.append({
            "title": v.get("title", "Unknown Title"),
            "authors": ", ".join(v.get("authors", ["Unknown Author"])),
            "description": v.get("description", "No description available."),
            "thumbnail": v.get("imageLinks", {}).get("thumbnail"),
            "infoLink": v.get("infoLink", None),
        })
    return books

async def prompt_for_choice(ctx, prompt_message, num_choices):
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    try:
        while True:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
            content = msg.content.strip().lower()
            if content == "cancel":
                await ctx.send("Cancelled.")
                return None
            if content.isdigit():
                choice = int(content)
                if 1 <= choice <= num_choices:
                    return choice - 1
            await ctx.send(f"Please enter a number between 1 and {num_choices}, or type `cancel` to abort.")
    except asyncio.TimeoutError:
        await ctx.send("Timeout. Please try again.")
        return None

@bot.command(name='reading')
async def reading_command(ctx, *, arg=None):
    if arg is None:
        book = currently_reading.get(ctx.author.id)
        if book:
            embed = discord.Embed(
                title=book["title"],
                url=book.get("infoLink"),
                description=book["description"][:2048],
                color=discord.Color.blue()
            )
            embed.set_author(name=book["authors"])
            if book.get("thumbnail"):
                embed.set_thumbnail(url=book["thumbnail"])
            await ctx.send(f"{ctx.author.display_name} is currently reading:", embed=embed)
        else:
            await ctx.send("You have not set a currently reading book. Use `!reading [book name]` to set one.")
    else:
        if len(ctx.message.mentions) > 0:
            user = ctx.message.mentions[0]
            book = currently_reading.get(user.id)
            if book:
                embed = discord.Embed(
                    title=book["title"],
                    url=book.get("infoLink"),
                    description=book["description"][:2048],
                    color=discord.Color.green()
                )
                embed.set_author(name=book["authors"])
                if book.get("thumbnail"):
                    embed.set_thumbnail(url=book["thumbnail"])
                await ctx.send(f"{user.display_name} is currently reading:", embed=embed)
            else:
                await ctx.send(f"{user.display_name} has not set a currently reading book.")
            return

        books = search_google_books(arg)
        if not books:
            await ctx.send(f"Could not find any books matching '{arg}'.")
            return

        description_lines = []
        for i, book in enumerate(books, start=1):
            line = f"**{i}.** [{book['title']}]({book['infoLink']}) by {book['authors']}"
            description_lines.append(line)
        description = "\n".join(description_lines)
        prompt = await ctx.send(
            f"{ctx.author.mention}, pick the number of the book you want to set as currently reading (1-{len(books)}), or type `cancel`:\n{description}",
            suppress_embeds=True
        )

        choice = await prompt_for_choice(ctx, prompt, len(books))
        if choice is None:
            return

        selected = books[choice]
        currently_reading[ctx.author.id] = selected

        embed = discord.Embed(
            title=selected["title"],
            url=selected.get("infoLink"),
            description=selected["description"][:2048],
            color=discord.Color.blue()
        )
        embed.set_author(name=selected["authors"])
        if selected.get("thumbnail"):
            embed.set_thumbnail(url=selected["thumbnail"])
        await ctx.send(f"{ctx.author.display_name} is now reading:", embed=embed)

@bot.command(name='clearreading')
async def clear_reading_command(ctx):
    if ctx.author.id in currently_reading:
        del currently_reading[ctx.author.id]
        await ctx.send("Your currently reading book has been cleared.")
    else:
        await ctx.send("You don't have a currently reading book set.")

@bot.command(name='review')
async def review_command(ctx, *, arg=None):
    if not arg:
        await ctx.send("Usage: `!review Book Title`")
        return

    books = search_google_books(arg)
    if not books:
        await ctx.send(f"No results found for '{arg}'.")
        return

    lines = []
    for i, b in enumerate(books, 1):
        lines.append(f"**{i}.** [{b['title']}]({b['infoLink']}) by {b['authors']}")
    await ctx.send(
        f"{ctx.author.mention}, pick a number to review (1-{len(books)}) or type `cancel`:\n" + "\n".join(lines),
        suppress_embeds=True
    )

    choice = await prompt_for_choice(ctx, ctx.message, len(books))
    if choice is None:
        return

    selected = books[choice]

    await ctx.send(f"{ctx.author.mention}, enter a rating from 1–5:")

    def check_rating(m): return m.author == ctx.author and m.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", timeout=60, check=check_rating)
        rating = int(msg.content)
        if rating < 1 or rating > 5:
            raise ValueError
    except:
        await ctx.send("Invalid rating or timeout. Review cancelled.")
        return

    await ctx.send("Add a text review? Type it now or `skip` to skip.")

    try:
        msg = await bot.wait_for("message", timeout=90, check=check_rating)
        review_text = None if msg.content.lower() == "skip" else msg.content
    except:
        review_text = None

    user_reviews = reviews.get(ctx.author.id, [])
    user_reviews.append({
        "title": selected["title"],
        "authors": selected["authors"],
        "description": selected["description"],
        "thumbnail": selected["thumbnail"],
        "infoLink": selected["infoLink"],
        "rating": rating,
        "review_text": review_text,
    })
    reviews[ctx.author.id] = user_reviews

    embed = discord.Embed(
        title=f"Review Submitted: {selected['title']}",
        url=selected["infoLink"],
        description=selected["description"][:2048],
        color=discord.Color.purple()
    )
    embed.add_field(name="Author(s)", value=selected["authors"], inline=True)
    embed.add_field(name="Rating", value=f"{rating}/5", inline=True)
    if review_text:
        embed.add_field(name="Review", value=review_text, inline=False)
    if selected.get("thumbnail"):
        embed.set_thumbnail(url=selected["thumbnail"])
    await ctx.send(embed=embed)

@bot.command(name='myreviews')
async def my_reviews_command(ctx):
    user_reviews = reviews.get(ctx.author.id, [])
    if not user_reviews:
        await ctx.send("You haven’t submitted any reviews yet.")
        return
    for r in user_reviews[-5:]:
        embed = discord.Embed(
            title=r["title"],
            url=r["infoLink"],
            description=r["description"][:2048],
            color=discord.Color.orange()
        )
        embed.add_field(name="Author(s)", value=r["authors"], inline=True)
        embed.add_field(name="Rating", value=f"{r['rating']}/5", inline=True)
        if r["review_text"]:
            embed.add_field(name="Review", value=r["review_text"], inline=False)
        if r.get("thumbnail"):
            embed.set_thumbnail(url=r["thumbnail"])
        await ctx.send(embed=embed)

@bot.command(name='reviews')
async def all_reviews_command(ctx, user: discord.User = None):
    if user is None:
        user = ctx.author
    user_reviews = reviews.get(user.id, [])
    if not user_reviews:
        await ctx.send(f"{user.display_name} has not submitted any reviews yet.")
        return
    for r in user_reviews[-5:]:
        embed = discord.Embed(
            title=r["title"],
            url=r["infoLink"],
            description=r["description"][:2048],
            color=discord.Color.teal()
        )
        embed.add_field(name="Author(s)", value=r["authors"], inline=True)
        embed.add_field(name="Rating", value=f"{r['rating']}/5", inline=True)
        if r["review_text"]:
            embed.add_field(name="Review", value=r["review_text"], inline=False)
        if r.get("thumbnail"):
            embed.set_thumbnail(url=r["thumbnail"])
        await ctx.send(embed=embed)

@bot.command(name='bookhelp')
async def book_help(ctx):
    await ctx.send("""\
**Book Bot Commands**
`!reading` – Show your current book  
`!reading [title]` – Set book  
`!reading @user` – See someone else's book  
`!clearreading` – Clear it  
`!review [title]` – Review a book  
`!myreviews` – Show your reviews  
`!reviews @user` – See others' reviews  
""")

# --- Flask web server for uptime (optional, remove if not using uptime robot) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()
# ------------------------------------------------------------------------------

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
