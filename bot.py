import asyncio
import os
import discord
from discord import app_commands
from discord.ext import commands

intents = discord.Intents.default()
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
    if vc and vc.is_connected() and not vc.is_playing():
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
                
                # if completely disconnected, connect back to target channel
                if not vc or not vc.is_connected():
                    print(f"auto-connecting/reconnecting to target channel: {channel.name}")
                    vc = await channel.connect(reconnect=True, timeout=20.0)
                    start_silence_loop(vc)
                # if connected but in the WRONG channel (e.g. pulled away by force or glitch), move back
                elif vc.channel.id != target_voice_channel_id:
                    print(f"correcting position: moving back to target channel: {channel.name}")
                    await vc.move_to(channel)
                    start_silence_loop(vc)
                else:
                    # ensure it's actively streaming silence even if it got interrupted
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
        
    # ignite the background persistent manager safely inside the loop
    bot.loop.create_task(auto_join_loop())

# --- SLASH COMMANDS REGISTRATION ---

@bot.tree.command(name="join", description="summons the bot to your current voice channel.")
async def join(interaction: discord.Interaction):
    global target_voice_channel_id
    
    # check if the user is in a vc
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("❌ you need to be inside a voice channel first!", ephemeral=True)
        return
        
    user_channel = interaction.user.voice.channel
    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    
    await interaction.response.defer() # keeps discord from timing out
    
    # CRITICAL: update the global tracking id so the auto_join_loop doesn't immediately drag it back
    target_voice_channel_id = user_channel.id
    
    if vc and vc.is_connected():
        # if already in a channel, move it smoothly
        await vc.move_to(user_channel)
    else:
        # otherwise make a fresh connection
        vc = await user_channel.connect(reconnect=True)
        
    start_silence_loop(vc)
    await interaction.followup.send(f"joined and locked into **{user_channel.name}**! 🔊")

@bot.tree.command(name="leave", description="forces the bot to disconnect from the voice channel.")
async def leave(interaction: discord.Interaction):
    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    
    if vc and vc.is_connected():
        await vc.disconnect()
        await interaction.response.send_message("👋 successfully disconnected from the voice channel.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ i'm not currently connected to any voice channels in this server.", ephemeral=True)

if __name__ == "__main__":
    if bot_token:
        bot.run(bot_token)
    else:
        print("error: DISCORD_BOT_TOKEN environment variable not found.")
