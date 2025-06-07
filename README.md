BearCrabs Book Bot

BearCrabs Book Bot is a Discord bot designed to let users track and review books using the Google Books API. It utilizes modern Discord UI elements like slash commands, dropdowns, buttons, and modals for a smooth, user-friendly experience.

Features

/reading [title]

Sets the book a user is currently reading.

If no title is provided, it shows the user's current book.

Book details include title, author, short description, thumbnail, and a link to Google Books.

/clearreading

Clears the user's currently reading book.

/review [title]

Multi-step book review workflow:

User selects a book from a dropdown list (based on Google Books search).

User selects a rating (1–5) using interactive buttons.

A modal prompts the user to enter an optional text review.

The final review is posted as a public embed, including:

Title (linked to Google Books)

Author

Rating (1–5)

Optional user-written review

Thumbnail image

/myreviews

Displays the last 5 reviews submitted by the user.

/reviews [user]

Displays the last 5 reviews submitted by the specified user.

/bookhelp

Shows a list of available commands.

UI/UX Enhancements

Dropdown menus for book selection.

Buttons for rating input.

Modals for text input.

Truncation of long descriptions and reviews with a "Read more..." link.

All steps are ephemeral (private), except the final posted review.

Tech Stack

Discord.py (with app_commands)

Google Books API

Python 3.12

To-Do / Ideas for the Future

Add persistent storage (e.g., database or file system) for review history.

Add pagination to /myreviews and /reviews for longer review histories.

Allow users to edit or delete reviews.

Setup

Clone the repository.

Set the following environment variables:

DISCORD_BOT_TOKEN

GOOGLE_API_KEY

Run the bot:

python bot.py

Built with ❤️ by the BearCrabs community
