import asyncio
import os
import discord
from discord.ext import commands

# ensure you have voice intents if required, default covers voice states
intents = discord.Intents.default()
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents)

# global settings
TARGET_VOICE_CHANNEL_ID = 123456789012345678  # replace with your target vc id
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

class SilenceSource(discord.AudioSource):
    """generates pure silence packets to keep the voice gateway connection hot"""
    def read(self):
        # returns 20ms of silence (384 bytes of empty PCM audio data)
        return b'\x00' * 384

async def keep_alive_vc():
    await bot.wait_until_ready()
    channel = bot.get_channel(TARGET_VOICE_CHANNEL_ID)
    
    if not channel or not isinstance(channel, discord.VoiceChannel):
        print("error: invalid voice channel id.")
        return

    while not bot.is_closed():
        try:
            # check if bot is already connected to a voice client
            vc = discord.utils.get(bot.voice_clients, guild=channel.guild)
            
            if not vc or not vc.is_connected():
                print(f"connecting to voice channel: {channel.name}")
                vc = await channel.connect(reconnect=True, timeout=20.0)
            
            # if it's not playing anything, start feeding it the silence loop
            if vc and vc.is_connected() and not vc.is_playing():
                print("initiating 24/7 silence keepalive transmission...")
                vc.play(SilenceSource(), after=lambda e: print(f"stream ended/reset: {e}"))
                
        except Exception as e:
            print(f"exception encountered in voice loop: {e}")
            
        # check status every 10 seconds to ensure it hasn't been disconnected
        await asyncio.sleep(10)

@bot.event
async def on_ready():
    print(f"logged in as {bot.user.name}")
    # spin up the background task to manage the voice connection
    bot.loop.create_task(keep_alive_vc())

if __name__ == "__main__":
    if BOT_TOKEN:
        bot.run(BOT_TOKEN)
    else:
        print("error: DISCORD_BOT_TOKEN environment variable not found.")