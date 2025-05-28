import discord
from discord.ext import commands
from discord import app_commands
import requests
import os

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
currently_reading = {}
reviews = {}

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

async def prompt_user_choice(interaction, books):
    view = discord.ui.View(timeout=60)
    options = []
    for i, book in enumerate(books, 1):
        label = f"{book['title']} by {book['authors']}"
        options.append(discord.SelectOption(label=label[:100], value=str(i-1)))

    choice = {"index": None}

    async def select_callback(interact):
        choice["index"] = int(select.values[0])
        await interact.response.edit_message(content=f"Selected: {books[choice['index']]['title']} by {books[choice['index']]['authors']}", view=None)
        view.stop()

    select = discord.ui.Select(placeholder="Pick a book...", options=options[:25])
    select.callback = select_callback
    view.add_item(select)

    await interaction.response.send_message("Select your book:", view=view, ephemeral=True)
    await view.wait()
    return choice["index"]

class RatingView(discord.ui.View):
    def __init__(self, interaction, book):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.book = book
        self.rating = None
        self.value = None

    async def send_review_modal(self, interaction, rating):
        modal = ReviewModal(book=self.book, rating=rating)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="1", style=discord.ButtonStyle.red)
    async def one(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.rating = 1
        await self.send_review_modal(interaction, 1)
        self.stop()

    @discord.ui.button(label="2", style=discord.ButtonStyle.red)
    async def two(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.rating = 2
        await self.send_review_modal(interaction, 2)
        self.stop()

    @discord.ui.button(label="3", style=discord.ButtonStyle.grey)
    async def three(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.rating = 3
        await self.send_review_modal(interaction, 3)
        self.stop()

    @discord.ui.button(label="4", style=discord.ButtonStyle.green)
    async def four(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.rating = 4
        await self.send_review_modal(interaction, 4)
        self.stop()

    @discord.ui.button(label="5", style=discord.ButtonStyle.green)
    async def five(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.rating = 5
        await self.send_review_modal(interaction, 5)
        self.stop()

class ReviewModal(discord.ui.Modal, title="Write your review"):
    def __init__(self, book, rating):
        super().__init__()
        self.book = book
        self.rating = rating
        self.review = discord.ui.TextInput(label="Your review (optional)", style=discord.TextStyle.paragraph, required=False, max_length=1024)
        self.add_item(self.review)

    async def on_submit(self, interaction: discord.Interaction):
        review_text = self.review.value or None
        user_reviews = reviews.get(interaction.user.id, [])
        user_reviews.append({
            "title": self.book["title"],
            "authors": self.book["authors"],
            "description": self.book["description"],
            "thumbnail": self.book["thumbnail"],
            "infoLink": self.book["infoLink"],
            "rating": self.rating,
            "review_text": review_text,
        })
        reviews[interaction.user.id] = user_reviews

        embed = discord.Embed(
            title=self.book["title"],
            url=self.book["infoLink"],
            description=self.book["description"][:2048],
            color=discord.Color.purple()
        )
        embed.add_field(name="Author(s)", value=self.book["authors"], inline=True)
        embed.add_field(name="Rating", value=f"{self.rating}/5", inline=True)
        if review_text:
            embed.add_field(name="Review", value=review_text, inline=False)
        if self.book["thumbnail"]:
            embed.set_thumbnail(url=self.book["thumbnail"])

        await interaction.response.send_message(f"{interaction.user.display_name} submitted a review!", embed=embed)

@tree.command(name="review", description="Review a book")
@app_commands.describe(title="The title of the book you want to review")
async def review(interaction: discord.Interaction, title: str):
    books = search_google_books(title)
    if not books:
        await interaction.response.send_message("No results found.", ephemeral=True)
        return

    choice = await prompt_user_choice(interaction, books)
    if choice is None:
        return

    selected = books[choice]
    view = RatingView(interaction, selected)
    await interaction.followup.send("Select a rating from 1–5:", view=view, ephemeral=True)

@tree.command(name="reading", description="Show or set your currently reading book")
@app_commands.describe(title="The title of the book you are reading (or leave blank to show)")
async def reading(interaction: discord.Interaction, title: str = None):
    user_id = interaction.user.id
    if title is None:
        book = currently_reading.get(user_id)
        if not book:
            await interaction.response.send_message("No book set. Use `/reading [title]` to set one.", ephemeral=True)
            return
        embed = discord.Embed(title=book["title"], url=book["infoLink"], description=book["description"][:2048], color=discord.Color.blue())
        embed.set_author(name=book["authors"])
        if book["thumbnail"]:
            embed.set_thumbnail(url=book["thumbnail"])
        await interaction.response.send_message(f"{interaction.user.display_name} is currently reading:", embed=embed)
        return

    books = search_google_books(title)
    if not books:
        await interaction.response.send_message("No books found.", ephemeral=True)
        return

    choice = await prompt_user_choice(interaction, books)
    if choice is None:
        return

    selected = books[choice]
    currently_reading[user_id] = selected

    embed = discord.Embed(title=selected["title"], url=selected["infoLink"], description=selected["description"][:2048], color=discord.Color.blue())
    embed.set_author(name=selected["authors"])
    if selected["thumbnail"]:
        embed.set_thumbnail(url=selected["thumbnail"])
    await interaction.followup.send(f"{interaction.user.display_name} is now reading:", embed=embed)

@tree.command(name="clearreading", description="Clear your currently reading book")
async def clearreading(interaction: discord.Interaction):
    if interaction.user.id in currently_reading:
        del currently_reading[interaction.user.id]
        await interaction.response.send_message("Cleared your currently reading book.")
    else:
        await interaction.response.send_message("You don't have one set.", ephemeral=True)

@tree.command(name="myreviews", description="Show your submitted book reviews")
async def myreviews(interaction: discord.Interaction):
    user_reviews = reviews.get(interaction.user.id, [])
    if not user_reviews:
        await interaction.response.send_message("You haven’t submitted any reviews.", ephemeral=True)
        return
    for r in user_reviews[-5:]:
        embed = discord.Embed(title=r["title"], url=r["infoLink"], description=r["description"][:2048], color=discord.Color.orange())
        embed.add_field(name="Author(s)", value=r["authors"], inline=True)
        embed.add_field(name="Rating", value=f"{r['rating']}/5", inline=True)
        if r["review_text"]:
            embed.add_field(name="Review", value=r["review_text"], inline=False)
        if r["thumbnail"]:
            embed.set_thumbnail(url=r["thumbnail"])
        await interaction.followup.send(embed=embed)

@tree.command(name="reviews", description="Show another user's reviews")
@app_commands.describe(user="User to look up")
async def reviews_of_user(interaction: discord.Interaction, user: discord.User = None):
    if user is None:
        user = interaction.user
    user_reviews = reviews.get(user.id, [])
    if not user_reviews:
        await interaction.response.send_message(f"{user.display_name} has not submitted any reviews.")
        return
    for r in user_reviews[-5:]:
        embed = discord.Embed(title=r["title"], url=r["infoLink"], description=r["description"][:2048], color=discord.Color.teal())
        embed.add_field(name="Author(s)", value=r["authors"], inline=True)
        embed.add_field(name="Rating", value=f"{r['rating']}/5", inline=True)
        if r["review_text"]:
            embed.add_field(name="Review", value=r["review_text"], inline=False)
        if r["thumbnail"]:
            embed.set_thumbnail(url=r["thumbnail"])
        await interaction.followup.send(embed=embed)

@tree.command(name="bookhelp", description="List available book bot commands")
async def bookhelp(interaction: discord.Interaction):
    await interaction.response.send_message("""\
**Book Bot Slash Commands**
/reading [title] – Set or show your book  
/clearreading – Clear your book  
/review [title] – Review a book  
/myreviews – Show your reviews  
/reviews [user] – See others' reviews  
""", ephemeral=True)

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}")

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
