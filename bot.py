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

class SilenceSource(discord.AudioSource):
    """generates pure pcm silence packets to keep the voice gateway hot"""
    def read(self):
        # 384 bytes is 20ms of 16-bit 48khz stereo pcm data
        return b'\x00' * 384

def start_silence_loop(vc: discord.VoiceClient):
    """safely starts feeding the 24/7 silence stream if not already playing"""
    if vc and vc.is_connected():
        if vc.is_playing():
            print("audio is already actively transmitting. skipping initialization.")
            return
            
        print("initiating silence keepalive transmission...")
        try:
            vc.play(SilenceSource(), after=lambda e: print(f"stream ended/reset: {e}") if e else None)
        except Exception as e:
            print(f"failed to play silence source: {e}")

async def auto_join_loop():
    """background task that ensures the bot stays locked into the current target vc"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            global target_voice_channel_id
            channel = bot.get_channel(target_voice_channel_id)
            
            if channel and isinstance(channel, discord.VoiceChannel):
                vc = discord.utils.get(bot.voice_clients, guild=channel.guild)
                
                if not vc or not vc.is_connected():
                    print(f"auto-connecting/reconnecting to target channel: {channel.name}")
                    vc = await channel.connect(reconnect=True, timeout=20.0)
                    start_silence_loop(vc)
                elif vc.channel.id != target_voice_channel_id:
                    print(f"correcting position: moving back to target channel: {channel.name}")
                    await vc.move_to(channel)
                    start_silence_loop(vc)
                else:
                    start_silence_loop(vc)
        except Exception as e:
            print(f"exception encountered in auto-join loop: {e}")
            
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

@bot.tree.command(name="ping", description="checks the bot's current connection latency.")
async def ping(interaction: discord.Interaction):
    # calculates api gateway response lag in milliseconds
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"pong! 🏓 (`{latency}ms`)")

@bot.tree.command(name="join", description="makes the bot join your voice channel.")
async def join(interaction: discord.Interaction):
    global target_voice_channel_id
    
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("join a voice channel first.", ephemeral=True)
        return
        
    user_channel = interaction.user.voice.channel
    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    
    await interaction.response.defer() 
    target_voice_channel_id = user_channel.id
    
    try:
        if vc and vc.is_connected():
            print(f"moving existing client connection to: {user_channel.name}")
            await vc.move_to(user_channel)
        else:
            print(f"establishing brand new client connection to: {user_channel.name}")
            vc = await user_channel.connect(reconnect=True, timeout=15.0)
        
        await interaction.followup.send(f"i successfully joined **{user_channel.name}**")
        start_silence_loop(vc)
        
    except Exception as e:
        print(f"fatal crash inside slash join command execution: {e}")
        await interaction.followup.send(f"failed to join voice channel: {e}", ephemeral=True)

@bot.tree.command(name="leave", description="makes the bot leave your voice channel.")
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
