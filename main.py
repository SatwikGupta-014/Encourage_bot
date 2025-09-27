import discord
from pymongo import MongoClient
import os
import requests
import json
import random
from ping import keep_alive  # Make sure keep_alive.py is present

# ===========================
# DATABASE SETUP
# ===========================
class EncouragementDB:
    def __init__(self, uri=None, db_name="encouragebot", collection_name="encouragements"):
        self.client = MongoClient(uri or os.getenv("MONGO_URL"))
        self.collection = self.client[db_name][collection_name]

    def add(self, message: str):
        """Add a new encouragement message to the database."""
        if message:
            self.collection.insert_one({"text": message})

    def all(self) -> list[str]:
        """Retrieve all encouragement messages from the database."""
        return [doc["text"] for doc in self.collection.find({}, {"_id": 0, "text": 1})]

    def delete_by_index(self, index: int):
        """Delete encouragement by its index in the database list."""
        docs = list(self.collection.find())
        if 0 <= index < len(docs):
            self.collection.delete_one({"_id": docs[index]["_id"]})
            return True
        return False

    def delete_by_text(self, text: str):
        """Delete encouragement by matching its text."""
        result = self.collection.delete_one({"text": text})
        return result.deleted_count > 0

# Initialize database
db = EncouragementDB()

# ===========================
# DISCORD CLIENT SETUP
# ===========================
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content
client = discord.Client(intents=intents)  # Connect to Discord

# ===========================
# GLOBAL VARIABLES
# ===========================
last_search_results = {}  # Store last search results for deletion
responding = True  # Default bot responding setting

sad_words = [
    "sad", "depressed", "unhappy", "angry", "miserable",
    "depressing", "depression", "depressive", "depress", "depresses"
]

starter_encouragements = [
    "Cheer up!", "Hang in there.", "You are a great person.", "You are not alone.", "You are strong.",
    "You are brave.", "You are kind.", "You are smart.", "You are funny.", "You are beautiful.",
    "You are amazing.", "You are awesome.", "You are a rockstar.", "You are a superstar.",
    "You are a hero.", "You are a champion.", "You are a winner.", "You are a legend."
]

# ===========================
# HELPER FUNCTIONS
# ===========================
def get_quote():
    """Get a random inspirational quote from ZenQuotes API."""
    try:
        response = requests.get("https://zenquotes.io/api/random")
        json_data = response.json()
        quote = json_data[0]['q'] + " -" + json_data[0]['a']
        return quote
    except Exception:
        return "Keep going, you're doing great!"

# ===========================
# DISCORD EVENT HANDLERS
# ===========================
@client.event
async def on_ready():  # When the bot is ready
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):  # Triggered when bot receives a message
    global responding
    if message.author == client.user:  # Ignore messages from the bot itself
        return

    msg = message.content

    # ---------------------------
    # BASIC COMMANDS
    # ---------------------------
    if msg.startswith("$hello"):
        await message.channel.send("Hello!")

    elif msg.startswith("$goodbye"):
        await message.channel.send("Goodbye!")

    elif msg.startswith("$inspire"):
        await message.channel.send(get_quote())

    # ---------------------------
    # SAD WORD RESPONSE
    # ---------------------------
    elif responding and any(word in msg.lower() for word in sad_words):
        options = starter_encouragements + db.all()
        await message.channel.send(random.choice(options))

    # ---------------------------
    # ADD NEW ENCOURAGEMENT
    # ---------------------------
    elif msg.startswith("$new"):
        encouraging_message = msg[4:].strip()
        if encouraging_message:
            db.add(encouraging_message)
            await message.channel.send("New encouraging message added.")
        else:
            await message.channel.send("Please provide a message to add. Example: $new You're awesome!")

    # ---------------------------
    # LIST ALL CUSTOM ENCOURAGEMENTS
    # ---------------------------
    elif msg.startswith("$list"):
        last_search_results.clear()
        encouragements = db.all()
        if encouragements:
            formatted_list = "\n".join(f"{i}: {e}" for i, e in enumerate(encouragements))
            await message.channel.send(f"Your custom encouragements:\n```{formatted_list}```")
        else:
            await message.channel.send("No custom encouragements added yet. Use $new to add some!")

    # ---------------------------
    # SEARCH ENCOURAGEMENTS
    # ---------------------------
    elif msg.startswith("$search"):
        search_term = msg[7:].strip()
        if search_term:
            last_search_results.clear()

            # Search starter encouragements (built-in, not deletable)
            starter_matches = [e for e in starter_encouragements if search_term.lower() in e.lower()]

            # Search custom encouragements (deletable)
            custom_docs = db.all()
            custom_matches = []
            custom_indices = []
            for i, e in enumerate(custom_docs):
                if search_term.lower() in e.lower():
                    custom_matches.append(e)
                    custom_indices.append(i)

            all_matches = starter_matches + custom_matches

            if all_matches:
                formatted_results = ""
                for i, match in enumerate(all_matches, 1):
                    if i <= len(starter_matches):
                        last_search_results[i] = {'text': match, 'deletable': False}
                        formatted_results += f"{i}. {match} (built-in)\n"
                    else:
                        custom_index = custom_indices[i - len(starter_matches) - 1]
                        last_search_results[i] = {'text': match, 'deletable': True, 'db_index': custom_index}
                        formatted_results += f"{i}. {match} (custom - deletable)\n"

                await message.channel.send(
                    f"Encouragements containing '{search_term}':\n```{formatted_results}```Use $del <number> to delete custom encouragements."
                )
            else:
                await message.channel.send(f"No encouragements found containing '{search_term}'. Try a different word!")
        else:
            await message.channel.send("Please provide a word to search for. Example: $search happy")

    # ---------------------------
    # DELETE ENCOURAGEMENT
    # ---------------------------
    elif msg.startswith("$del"):
        delete_input = msg[4:].strip()
        if delete_input:
            if delete_input.isdigit():
                index = int(delete_input)
                if index in last_search_results:
                    search_item = last_search_results[index]
                    if search_item['deletable']:
                        db.delete_by_index(search_item['db_index'])
                        await message.channel.send(f"Deleted '{search_item['text']}' from search results.")
                        last_search_results.clear()
                    else:
                        await message.channel.send(f"Cannot delete '{search_item['text']}' - it's a built-in encouragement.")
                else:
                    await message.channel.send(f"Index {index} not found in last search results.")
            else:
                if db.delete_by_text(delete_input):
                    await message.channel.send(f"Deleted '{delete_input}'.")
                else:
                    await message.channel.send(f"'{delete_input}' not found.")
        else:
            await message.channel.send("Provide a number or text to delete. Example: $del 0 or $del You're awesome!")

    # ---------------------------
    # TOGGLE RESPONDING SETTING
    # ---------------------------
    elif msg.startswith("$responding"):
        value = msg[11:].strip().lower()
        if value == "true":
            responding = True
            await message.channel.send("Responding is on.")
        elif value == "false":
            responding = False
            await message.channel.send("Responding is off.")
        else:
            await message.channel.send("Specify true or false. Example: $responding true")

# ===========================
# BOT STARTUP
# ===========================
keep_alive()
TOKEN = os.getenv("DISCORD_TOKEN")  # Make sure .env uses DISCORD_TOKEN
if not TOKEN:
    print("Error: DISCORD_TOKEN environment variable not set!")
    exit(1)

client.run(TOKEN)
