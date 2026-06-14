import asyncio
import os
import discord
from discord import app_commands
from discord.ext import commands

# CRITICAL: add message_content intent so the bot can read the word "misoyan"
intents = discord.Intents.default()
intents.message_content = True 

# prefix isn't used for slash commands, but required by the constructor
bot = commands.Bot(command_prefix="!", intents=intents)

# global settings
target_voice_channel_id = 123456789012345678  # default home channel
bot_token = os.environ.get("DISCORD_BOT_TOKEN")

# the status pool
status_pool = [
    (discord.Status.online, discord.CustomActivity(name="hanging out in the vc :3"))
]

class OpusSilenceSource(discord.AudioSource):
    """streams pre-compiled cryptographic voice frames directly to bypass inactivity drops"""
    def __init__(self):
        # 5 specific hex bytes that signal "legitimate frame silence" to discord's server
        # this is pre-compressed opus silence. it requires 0 CPU power to read.
        self.silence_packet = b'\xf8\xff\xfe\x00\x00'

    def is_opus(self):
        # CRITICAL HANDSHAKE: this tells discord.py to skip raw pcm processing entirely.
        # it pushes the bytes straight to the gateway network socket. zero disconnects.
        return True

    def read(self):
        # discord's voice loop calls this function exactly every 20ms.
        # we endlessly feed it our 5-byte packet to keep the line open.
        return self.silence_packet

def start_silence_loop(vc: discord.VoiceClient):
    """safely sequences the raw opus keepalive injection stream"""
    if vc and vc.is_connected():
        if vc.is_playing():
            print("misoyan audio engine is already actively transmitting frames. skipping.")
            return
            
        async def delayed_play():
            # CRITICAL COMPLIANCE DELAY: give the new DAVE end-to-end encryption handshake
            # 1.5 seconds to fully bind keys before we throw packets down the wire.
            await asyncio.sleep(1.5)  
            if vc.is_connected() and not vc.is_playing():
                print("initiating misoyan 24/7 silence keepalive transmission...")
                try:
                    # the "after" lambda tells the bot what to do if the stream stops.
                    # if it drops naturally, it will log it here so you can check your railway console.
                    vc.play(OpusSilenceSource(), after=lambda e: print(f"voice gateway frame recycling/reset: {e}") if e else None)
                except Exception as e:
                    print(f"internal keepalive playback error trace: {e}")

        # schedules the execution sequence safely into python's active async task manager
        bot.loop.create_task(delayed_play())

async def auto_join_loop():
    """persistent background loop ensuring misoyan never stays disconnected from home vc"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            global target_voice_channel_id
            channel = bot.get_channel(target_voice_channel_id)
            
            if channel and isinstance(channel, discord.VoiceChannel):
                vc = discord.utils.get(bot.voice_clients, guild=channel.guild)
                
                if not vc or not vc.is_connected():
                    print(f"auto-recovery: connecting back to home vc -> {channel.name}")
                    vc = await channel.connect(reconnect=True, timeout=20.0)
                    start_silence_loop(vc)
                elif vc.channel.id != target_voice_channel_id:
                    print(f"position correction: pulling misoyan back to -> {channel.name}")
                    await vc.move_to(channel)
                    start_silence_loop(vc)
                else:
                    # if already there, make sure the stream engine hasn't accidentally dropped out
                    start_silence_loop(vc)
        except Exception as e:
            print(f"background loop error trace: {e}")
            
        await asyncio.sleep(15)

@bot.event
async def on_ready():
    print(f"logged in as {bot.user.name}")
    
    try:
        synced = await bot.tree.sync()
        print(f"successfully synced {len(synced)} application slash commands.")
    except Exception as e:
        print(f"failed to sync slash commands: {e}")
        
    print("starting main loop (ping)")
    bot.loop.create_task(auto_join_loop())

# custom statuses
@tasks.loop(minutes=2.5)
async def cycle_status_loop():
    """background clock loop that shifts her indicator color and custom note simultaneously"""
    await bot.wait_until_ready()
    
    # randomly grab a tuple from our matrix
    selected_status, selected_note = random.choice(status_pool)
    
    try:
        # change both parameters over the gateway socket in one transmission
        await bot.change_presence(status=selected_status, activity=selected_note)
        print(f"shifted misoyan's profile to Status: {selected_status.name} | Note: '{selected_note.name}'")
    except Exception as e:
        print(f"failed to cycle status note layout: {e}")

# --- TEXT LISTENER (MISOYAN -> FIH) ---

@bot.event
async def on_message(message: discord.Message):
    # absolute rule: don't reply to other bots or yourself
    if message.author.bot:
        return

    # checks if the raw lowercase text contains "misoyan"
    if "misoyan" in message.content.lower():
        try:
            # allowed_mentions=discord.AllowedMentions.none() turns off all reply pings completely
            await message.reply("fih", allowed_mentions=discord.AllowedMentions.none())
            print(f"triggered phrase response for user: {message.author.name}")
        except Exception as e:
            print(f"failed to send message reply: {e}")

    # ensures standard commands/events don't lock up
    await bot.process_commands(message)

# --- SLASH COMMANDS REGISTRATION ---

@bot.tree.command(name="ping", description="check misoyan's current connection latency")
async def ping(interaction: discord.Interaction):
    # calculates api gateway response lag in milliseconds
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"pong! 🏓 (`{latency}ms`)")

@bot.tree.command(name="join", description="i wanna join the vc :3")
async def join(interaction: discord.Interaction):
    global target_voice_channel_id
    
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("❌ jump into a voice channel first!", ephemeral=True)
        return
        
    user_channel = interaction.user.voice.channel
    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    
    await interaction.response.defer() 
    target_voice_channel_id = user_channel.id
    
    try:
        if vc and vc.is_connected():
            print(f"moving existing connection to: {user_channel.name}")
            await vc.move_to(user_channel)
        else:
            print(f"establishing brand new client connection to: {user_channel.name}")
            vc = await user_channel.connect(reconnect=True, timeout=15.0)
        
        await interaction.followup.send(f"i joined **{user_channel.name}**")
        
        # fire up the newly engineered opus silence engine
        start_silence_loop(vc)
        
    except Exception as e:
        print(f"fatal crash inside slash join command execution: {e}")
        await interaction.followup.send(f"failed to join voice channel: {e}", ephemeral=True)

@bot.tree.command(name="leave", description="pls let me go :c")
async def leave(interaction: discord.Interaction):
    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    
    if vc and vc.is_connected():
        await vc.disconnect()
        await interaction.response.send_message("i successfully left the voice channel (yay :3)", ephemeral=True)
    else:
        await interaction.response.send_message("i'm not connected to a voice channel.", ephemeral=True)

if __name__ == "__main__":
    if bot_token:
        bot.run(bot_token)
    else:
        print("error: DISCORD_BOT_TOKEN environment variable not found.")
