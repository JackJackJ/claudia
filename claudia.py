import discord
from discord.ext import commands
from anthropic import Anthropic
from collections import defaultdict
import time
import json

# Initialize the Discord client and Anthropic client
DISCORD_TOKEN = 'YOUR DISCORD TOKEN'
ANTHROPIC_API_KEY = 'YOUR ANTHROPIC API KEY'


# Create Discord bot instance with command prefix '!'
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Enhanced data structures for user and conversation tracking
conversation_history = defaultdict(list)
user_memories = defaultdict(lambda: {
    'first_seen': None,
    'total_messages': 0,
    'topics_discussed': set(),
    'last_interaction': None,
    'message_history': []
})
last_interaction = defaultdict(float)

# Constants
MAX_HISTORY_LENGTH = 50 #Maximum number of messages to store 
MAX_HISTORY_AGE = 172800 #Time in seconds before memory reset due to inactivity
MAX_USER_HISTORY = 50  # Maximum number of messages to store per user

def clear_old_conversations():
    current_time = time.time()
    for channel_id in list(conversation_history.keys()):
        if current_time - last_interaction[channel_id] > MAX_HISTORY_AGE:
            del conversation_history[channel_id]
            del last_interaction[channel_id]

def update_user_memory(user_id, username, message_content, timestamp):
    """Update the memory database for a user"""
    if user_memories[user_id]['first_seen'] is None:
        user_memories[user_id]['first_seen'] = timestamp
    
    user_memories[user_id].update({
        'last_interaction': timestamp,
        'total_messages': user_memories[user_id]['total_messages'] + 1,
    })
    
    # Add message to user's history, maintaining maximum length
    message_entry = {
        'content': message_content,
        'timestamp': timestamp,
    }
    user_memories[user_id]['message_history'].append(message_entry)
    if len(user_memories[user_id]['message_history']) > MAX_USER_HISTORY:
        user_memories[user_id]['message_history'] = user_memories[user_id]['message_history'][-MAX_USER_HISTORY:]

def format_conversation_history(channel_id):
    """Format conversation history with user context"""
    formatted_messages = []
    
    for msg in conversation_history[channel_id]:
        if msg['role'] == 'user':
            user_id = msg['user_id']
            user_info = user_memories[user_id]
            context = f"[User: {msg['username']}, Messages: {user_info['total_messages']}, " \
                     f"First seen: {time.strftime('%Y-%m-%d', time.localtime(user_info['first_seen']))}] "
            formatted_messages.append({
                "role": "user",
                "content": context + msg['content']
            })
        else:
            formatted_messages.append({
                "role": "assistant",
                "content": msg['content']
            })
    
    return formatted_messages

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(name='ask')
async def ask_claude(ctx, *, question):
    """
    Command to ask Claude a question with shared channel conversation memory
    Usage: !ask <your question>
    """
    try:
        channel_id = ctx.channel.id
        current_time = time.time()
        user_id = ctx.author.id
        username = ctx.author.name
        
        clear_old_conversations()
        last_interaction[channel_id] = current_time
        
        # Update user memory
        update_user_memory(user_id, username, question, current_time)
        
        # Store message with user details
        conversation_history[channel_id].append({
            "role": "user",
            "content": question,
            "user_id": user_id,
            "username": username,
            "timestamp": current_time
        })
        
        if len(conversation_history[channel_id]) > MAX_HISTORY_LENGTH:
            conversation_history[channel_id] = conversation_history[channel_id][-MAX_HISTORY_LENGTH:]
        
        async with ctx.typing():
            response = anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022", #Claude model used
                max_tokens=1024, #Max response length
                system = """ ENTER ANY CONTEXT HERE
                    """,
                messages=format_conversation_history(channel_id)
            )
            
            claude_response = response.content[0].text
            
            conversation_history[channel_id].append({
                "role": "assistant",
                "content": claude_response,
                "timestamp": time.time()
            })
            
            if len(claude_response) > 2000:
                chunks = [claude_response[i:i+2000] for i in range(0, len(claude_response), 2000)]
                for chunk in chunks:
                    await ctx.send(chunk)
            else:
                await ctx.send(claude_response)

    except Exception as e:
        error_message = f"An error occurred while processing your request: {str(e)}"
        await ctx.send(error_message)
        print(f"Error details: {str(e)}")

@bot.command(name='userinfo')
async def show_user_info(ctx, member: discord.Member = None):
    """
    Show information about a user's interaction history
    Usage: !userinfo or !userinfo @username
    """
    if member is None:
        member = ctx.author
    
    user_id = member.id
    if user_id in user_memories:
        memory = user_memories[user_id]
        
        info = f"User Information for {member.name}:\n"
        info += f"First seen: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(memory['first_seen']))}\n"
        info += f"Total messages: {memory['total_messages']}\n"
        info += f"Last interaction: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(memory['last_interaction']))}\n"
        
        # Show recent messages
        info += "\nRecent messages:\n"
        recent_messages = memory['message_history'][-5:]  # Last 5 messages
        for msg in recent_messages:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg['timestamp']))
            content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
            info += f"{timestamp}: {content}\n"
        
        await ctx.send(f"```{info}```")
    else:
        await ctx.send(f"No information found for {member.name}")

@bot.command(name='clear')
async def clear_history(ctx):
    """Clear channel conversation history"""
    channel_id = ctx.channel.id
    if channel_id in conversation_history:
        del conversation_history[channel_id]
        del last_interaction[channel_id]
        await ctx.send("Channel conversation history has been cleared.")
    else:
        await ctx.send("No conversation history found for this channel.")

@bot.command(name='history')
async def show_history(ctx):
    """Show current channel conversation history"""
    channel_id = ctx.channel.id
    if channel_id in conversation_history and conversation_history[channel_id]:
        history_text = "Channel Conversation History:\n\n"
        for msg in conversation_history[channel_id]:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg['timestamp']))
            if msg['role'] == 'user':
                history_text += f"{timestamp} - {msg['username']}: {msg['content']}\n"
            else:
                history_text += f"{timestamp} - Claude: {msg['content']}\n"
            history_text += "-" * 50 + "\n"
        
        if len(history_text) > 2000:
            chunks = [history_text[i:i+1900] for i in range(0, len(history_text), 1900)]
            for chunk in chunks:
                await ctx.send(f"```{chunk}```")
        else:
            await ctx.send(f"```{history_text}```")
    else:
        await ctx.send("No conversation history found for this channel.")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please provide a question after the !ask command.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found. Available commands: !ask, !clear, !history, !userinfo")
    else:
        await ctx.send(f"An error occurred: {str(error)}")

# Run the bot
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
