import discord
import os
import requests
import json
import random
from ping import keep_alive

# === Local JSON "DB" (instead of Replit DB) ===
DB_FILE = "data.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    else:
        return {"responding": True, "encouragements": []} # default values

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

# Load data at startup
db = load_db()

intents = discord.Intents.default()
intents.message_content = True  # Required to read message content

client = discord.Client(intents=intents) #Connection to Discord

# Store last search results for deletion
last_search_results = {}

sad_words = ["sad", "depressed", "unhappy", "angry", "miserable", "depressing", "depression", "depressive", "depress", "depresses"]

starter_encouragements =["Cheer up!", "Hang in there.", "You are a great person.", "You are not alone.", "You are strong.", "You are brave.", "You are kind.", "You are smart.", "You are funny.", "You are beautiful.", "You are amazing.", "You are awesome.", "You are a rockstar.", "You are a superstar.", "You are a hero.", "You are a champion.", "You are a winner.", "You are a legend.", "You are a hero.", "You are a champion."]

def update_encouragements(encouraging_message):
  db["encouragements"].append(encouraging_message) #Add the new encouragement to the list
  save_db() #Save to JSON file

def delete_encouragment(index):
  if 0 <= index < len(db["encouragements"]):
    del db["encouragements"][index] #Delete the encouragement at the given index
    save_db() #Save to JSON file

def delete_encouragment_by_text(text):
  if text in db["encouragements"]:
    db["encouragements"].remove(text) #Remove the encouragement by text
    save_db() #Save to JSON file
    return True
  return False

def get_quote():
  response = requests.get("https://zenquotes.io/api/random") # Get a random quote from the API
  json_data = json.loads(response.text)# Convert the response to JSON
  quote = json_data[0]['q'] + " -" + json_data[0]['a'] # Get the quote and the author
  return(quote)
  
@client.event #Regester an event
async def on_ready(): #When the bot is ready
    print('We have logged in as {0.user}'.format(client))

@client.event #When bot recieves a message
async def on_message(message):#triggers when bot recieves a message
    if message.author == client.user: #If the message is from the bot
      return

    msg = message.content
  
    if message.content.startswith('$hello'): #If the message starts with $hello
      await message.channel.send('Hello!') #Send Hello to Discord!

    if message.content.startswith('$inspire'): #If the message starts with $inspire
      await message.channel.send(get_quote()) #Send a quote to Discord!
  
    if message.content.startswith('$goodbye'): #If the message starts with $goodbye
      await message.channel.send('Goodbye!') #Send Goodbye to Discord!

    if db["responding"]: #If the bot is set to respond to sad words
      options = starter_encouragements + db["encouragements"] #Combine starter + custom encouragements
      if any(word in msg.lower() for word in sad_words):
        await message.channel.send(random.choice(options))#If the message contains any of the sad words

    if msg.startswith("$new"): #If the message starts with $new
      encouraging_message = msg[4:].strip() #Get the message after $new (with or without space)
      if encouraging_message: #Only add if there's actually a message
        update_encouragements(encouraging_message) #Add the message to the database
        await message.channel.send("New encouraging message added.")
      else:
        await message.channel.send("Please provide a message to add. Example: $new You're awesome!")

    if msg.startswith("$list"): #If the message starts with $list
      # Clear search results when showing regular list
      last_search_results.clear()
      
      if db["encouragements"]:
        encouragements = list(db["encouragements"])
        formatted_list = ""
        for i, encouragement in enumerate(encouragements):
          formatted_list += f"{i}: {encouragement}\n"
        await message.channel.send(f"Your custom encouragements:\n```{formatted_list}```")
      else:
        await message.channel.send("No custom encouragements added yet. Use $new to add some!")

    if msg.startswith("$search"): #If the message starts with $search
      search_term = msg[7:].strip() #Get the search term after $search (with or without space)
      if search_term:
        # Clear previous search results
        last_search_results.clear()
        
        # Find matches in starter encouragements (not deletable)
        starter_matches = []
        for encouragement in starter_encouragements:
          if search_term.lower() in encouragement.lower():
            starter_matches.append(encouragement)
        
        # Find matches in custom encouragements (deletable)
        custom_matches = []
        custom_indices = []
        for i, encouragement in enumerate(db["encouragements"]):
          if search_term.lower() in encouragement.lower():
            custom_matches.append(encouragement)
            custom_indices.append(i)
        
        # Combine all matches
        all_matches = starter_matches + custom_matches
        
        if all_matches:
          formatted_results = ""
          for i, match in enumerate(all_matches, 1):
            # Store search result info for deletion
            if i <= len(starter_matches):
              last_search_results[i] = {'text': match, 'deletable': False}
              formatted_results += f"{i}. {match} (built-in)\n"
            else:
              custom_index = custom_indices[i - len(starter_matches) - 1]
              last_search_results[i] = {'text': match, 'deletable': True, 'db_index': custom_index}
              formatted_results += f"{i}. {match} (custom - deletable)\n"
          
          await message.channel.send(f"Encouragements containing '{search_term}':\n```{formatted_results}```Use $del <number> to delete custom encouragements.")
        else:
          await message.channel.send(f"No encouragements found containing '{search_term}'. Try a different word!")
      else:
        await message.channel.send("Please provide a word to search for. Example: $search jit")

    if msg.startswith("$del"): #If the message starts with $del
      delete_input = msg[4:].strip() #Get the input after $del (with or without space)
      if delete_input:
        if delete_input.isdigit(): #If it's a number
          index = int(delete_input)
          
          # Check if this is a search result index
          if index in last_search_results:
            search_item = last_search_results[index]
            if search_item['deletable']:
              delete_encouragment(search_item['db_index'])
              await message.channel.send(f"Deleted '{search_item['text']}' from search results.")
              # Clear search results after deletion
              last_search_results.clear()
            else:
              await message.channel.send(f"Cannot delete '{search_item['text']}' - it's a built-in encouragement.")
          
          # Otherwise try to delete from regular custom list
          elif index < len(db["encouragements"]):
            delete_encouragment(index) #Delete the encouragement at the given index
            encouragements = db["encouragements"] #Get the updated list
            await message.channel.send(f"Deleted encouragement at index {index}. Updated list: {list(encouragements)}")
          else:
            await message.channel.send(f"Index {index} doesn't exist. Use $list to see all encouragements or $search to find specific ones.")
        
        else: #If it's text, delete by matching text
          if delete_encouragment_by_text(delete_input):
            encouragements = db["encouragements"] #Get the updated list
            await message.channel.send(f"Deleted '{delete_input}'. Updated list: {list(encouragements)}")
          else:
            await message.channel.send(f"'{delete_input}' not found. Use $list to see all encouragements.")
      else:
        await message.channel.send("Please provide a number or text to delete. Examples: $del 0 or $del You're awesome!")

    if msg.startswith("$responding"): #If the message starts with $responding
      value = msg[11:].strip() #Get the value after $responding (with or without space)
      
      if value: #Only proceed if there's actually a value
        if value.lower() == "true":
          db["responding"] = True #Set the bot to respond to sad words
          save_db() #Save to JSON file
          await message.channel.send("Responding is on.")
        else:
          db["responding"] = False #Set the bot to not respond to sad words
          save_db() #Save to JSON file
          await message.channel.send("Responding is off.")
      else:
        await message.channel.send("Please specify true or false. Examples: $responding true or $responding false")

keep_alive()
token = os.getenv('TOKEN')
if token is None:
    print("Error: TOKEN environment variable not set!")
    exit(1)
client.run(token)
