import asyncio
import os
import random  # keeps random.choice from crashing her
import threading  # handles the background web server thread
from http.server import SimpleHTTPRequestHandler, HTTPServer  # basic server classes
import discord
from discord import app_commands
from discord.ext import commands, tasks

# make bot can read the word "misoyan"
intents = discord.Intents.default()
intents.message_content = True 
intents.voice_states = True     # spy on vc

# blasie's id
creator_id = 891917254789320714

# compiler needs this
bot = commands.Bot(command_prefix="!", intents=intents)

# global settings
target_voice_channel_id = 123456789012345678  # default home channel
bot_token = os.environ.get("DISCORD_BOT_TOKEN")
render_port = os.environ.get("PORT")          # reads render's network port variable

# settings panel (pls no touch)
misoyan_settings = {
    "all_features": True,          # master toggle switch override
    "vc_joining": True,            # allows her to execute voice connection flows
    "vc_leaving": True,            # allows her to disconnect from vc spaces
    "status_changes": True,        # enables the random presence color updates
    "status_change_delay": True,   # toggles whether the loop clock runs fast or normal
    "fih_replies": True,           # controls the on_message regex string listener
    "blacklist": set()             # absolute snowflake number IDs of restricted humans
}

# clanker has emotions | format: (status, discord note)
status_pool = [
    (discord.Status.online, discord.CustomActivity(name="hanging out in the vc :3")),
    (discord.Status.idle, discord.CustomActivity(name="waiting for someone to join :c")),
    (discord.Status.dnd, discord.CustomActivity(name="learning new stuff...")),
    (discord.Status.invisible, discord.CustomActivity(name="lurking...")),
    (discord.Status.online, discord.CustomActivity(name="yapping in yappanese bleh")),
    (discord.Status.idle, discord.CustomActivity(name="waiting for someone to call my name :c")),
    (discord.Status.dnd, discord.CustomActivity(name="please do the fih")),
    (discord.Status.invisible, discord.CustomActivity(name="sleeping... zzz"))
]

# misoyan can now say more things
reply_list = [
    "fih fih fih",
    "who pinged",
    "you like fih?",
    "did someone call my name?",
    "fih :3",
    "please do the fih",
    "i loveeee fih",
    "hi, my name is misoyan and I AM A FIH",
    "hello :D",
    "the fih gods are watching us"
]

class OpusSilenceSource(discord.AudioSource):
    """streams pre-compiled cryptographic voice frames directly to bypass inactivity drops"""
    def __init__(self):
        # 5 specific hex bytes that signal "legitimate frame silence" to discord's server
        self.silence_packet = b'\xf8\xff\xfe\x00\x00'

    def is_opus(self):
        # skips raw pcm processing entirely.
        return True

    def read(self):
        return self.silence_packet

class FullSystemControlPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.update_panel_layout()

    def update_panel_layout(self):
        """paints the visual styles across both button rows based on your boolean settings"""
        # ROW 0: CORE MASTER ARCHITECTURE
        self.children[0].label = f"all: {'ON' if misoyan_settings['all_features'] else 'OFF'}"
        self.children[0].style = discord.ButtonStyle.green if misoyan_settings["all_features"] else discord.ButtonStyle.red

        self.children[1].label = f"voicelines: {'ON' if misoyan_settings['fih_replies'] else 'OFF'}"
        self.children[1].style = discord.ButtonStyle.blurple if misoyan_settings["fih_replies"] else discord.ButtonStyle.gray

        # ROW 1: VOICE SUB-SYSTEMS
        self.children[2].label = f"vc Join: {'ON' if misoyan_settings['vc_joining'] else 'OFF'}"
        self.children[2].style = discord.ButtonStyle.green if misoyan_settings["vc_joining"] else discord.ButtonStyle.red

        self.children[3].label = f"vc Leave: {'ON' if misoyan_settings['vc_leaving'] else 'OFF'}"
        self.children[3].style = discord.ButtonStyle.green if misoyan_settings["vc_leaving"] else discord.ButtonStyle.red

        # ROW 2: PRESENCE CLOCK PARAMETERS
        self.children[4].label = f"statuses: {'ON' if misoyan_settings['status_changes'] else 'OFF'}"
        self.children[4].style = discord.ButtonStyle.blurple if misoyan_settings["status_changes"] else discord.ButtonStyle.gray

        self.children[5].label = f"cycle rate: {'FAST (1m)' if misoyan_settings['status_change_delay'] else 'SLOW (2.5m)'}"
        self.children[5].style = discord.ButtonStyle.danger if misoyan_settings["status_change_delay"] else discord.ButtonStyle.secondary

    def generate_dashboard_embed(self) -> discord.Embed:
        embed = discord.Embed(title="🔧 misoyan granular engine terminal console", color=0x2b2d31)
        
        # loop parameters status layout matrix mapping
        embed.add_field(name="all features", value=f"`{'on' if misoyan_settings['all_features'] else 'off'}`", inline=False)
        embed.add_field(name="vc joining", value=f"`{'active' if misoyan_settings['vc_joining'] else 'disabled'}`", inline=True)
        embed.add_field(name="vc leaving", value=f"`{'active' if misoyan_settings['vc_leaving'] else 'disabled'}`", inline=True)
        embed.add_field(name="voicelines", value=f"`{'listening' if misoyan_settings['fih_replies'] else 'muted'}`", inline=True)
        embed.add_field(name="status changes", value=f"`{'cycling' if misoyan_settings['status_changes'] else 'frozen'}`", inline=True)
        embed.add_field(name="cycle frequency", value=f"`{'_fast layout mode (1m)' if misoyan_settings['status_change_delay'] else '_normal engine rate (2.5m)'}`", inline=True)
        
        blacklist_mentions = ", ".join([f"<@{uid}>" for uid in misoyan_settings["blacklist"]]) if misoyan_settings["blacklist"] else "none"
        embed.add_field(name="blacklisted people", value=blacklist_mentions, inline=False)
        return embed

    # --- BUTTON DECLARATION MATRIX (MAPPED ACCORDING TO YOUR LIST) ---
    @discord.ui.button(custom_id="m_all", row=0)
    async def m_all(self, interaction: discord.Interaction, btn: discord.ui.Button):
        misoyan_settings["all_features"] = not misoyan_settings["all_features"]
        self.update_panel_layout()
        await interaction.response.edit_message(embed=self.generate_dashboard_embed(), view=self)

    @discord.ui.button(custom_id="m_fih", row=0)
    async def m_fih(self, interaction: discord.Interaction, btn: discord.ui.Button):
        misoyan_settings["fih_replies"] = not misoyan_settings["fih_replies"]
        self.update_panel_layout()
        await interaction.response.edit_message(embed=self.generate_dashboard_embed(), view=self)

    @discord.ui.button(custom_id="m_join", row=1)
    async def m_join(self, interaction: discord.Interaction, btn: discord.ui.Button):
        misoyan_settings["vc_joining"] = not misoyan_settings["vc_joining"]
        self.update_panel_layout()
        await interaction.response.edit_message(embed=self.generate_dashboard_embed(), view=self)

    @discord.ui.button(custom_id="m_leave", row=1)
    async def m_leave(self, interaction: discord.Interaction, btn: discord.ui.Button):
        misoyan_settings["vc_leaving"] = not misoyan_settings["vc_leaving"]
        self.update_panel_layout()
        await interaction.response.edit_message(embed=self.generate_dashboard_embed(), view=self)

    @discord.ui.button(custom_id="m_status", row=2)
    async def m_status(self, interaction: discord.Interaction, btn: discord.ui.Button):
        misoyan_settings["status_changes"] = not misoyan_settings["status_changes"]
        self.update_panel_layout()
        await interaction.response.edit_message(embed=self.generate_dashboard_embed(), view=self)

    @discord.ui.button(custom_id="m_delay", row=2)
    async def m_delay(self, interaction: discord.Interaction, btn: discord.ui.Button):
        misoyan_settings["status_change_delay"] = not misoyan_settings["status_change_delay"]
        self.update_panel_layout()
        await interaction.response.edit_message(embed=self.generate_dashboard_embed(), view=self)

def start_silence_loop(vc: discord.VoiceClient):
    """safely sequences the raw opus keepalive injection stream"""
    if vc and vc.is_connected():
        if vc.is_playing():
            print("misoyan is already actively transmitting frames. skipping.")
            return
            
        async def delayed_play():
            await asyncio.sleep(1.5)  
            if vc.is_connected() and not vc.is_playing():
                print("i exist :3")
                try:
                    vc.play(OpusSilenceSource(), after=lambda e: print(f"voice gateway frame recycling/reset: {e}") if e else None)
                except Exception as e:
                    print(f"internal keepalive playback error trace: {e}")

        bot.loop.create_task(delayed_play())

async def auto_join_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        # if global features or vc joining is dropped, completely freeze the pipeline
        if misoyan_settings["all_features"] and misoyan_settings["vc_joining"]:
            try:
                global target_voice_channel_id
                channel = bot.get_channel(target_voice_channel_id)
                if channel and isinstance(channel, discord.VoiceChannel):
                    vc = discord.utils.get(bot.voice_clients, guild=channel.guild)
                    if not vc or not vc.is_connected():
                        vc = await channel.connect(reconnect=True, timeout=20.0)
                        start_silence_loop(vc)
                    elif vc.channel.id != target_voice_channel_id:
                        await vc.move_to(channel)
                        start_silence_loop(vc)
            except Exception as e:
                print(f"background loop trace failure: {e}")
                
        await asyncio.sleep(15)

# "feeling diffrent today"
@tasks.loop(minutes=2.5)
async def cycle_status_loop():
    await bot.wait_until_ready()
    if not misoyan_settings["all_features"] or not misoyan_settings["status_changes"]:
        return

    # dynamic loop check: adjust the clock speed on the fly depending on boolean state
    current_interval = cycle_status_loop.minutes
    if misoyan_settings["status_change_delay"] and current_interval != 1.0:
        cycle_status_loop.change_interval(minutes=1.0) # speed it up to 1 minute ticks
    elif not misoyan_settings["status_change_delay"] and current_interval != 2.5:
        cycle_status_loop.change_interval(minutes=2.5) # slow it back down to standard duration

    selected_status, selected_note = random.choice(status_pool)
    try:
        await bot.change_presence(status=selected_status, activity=selected_note)
    except Exception as e:
        print(f"failed profile matrix shift: {e}")

@bot.event
async def on_ready():
    print(f"logged in as {bot.user.name}")
    
    try:
        synced = await bot.tree.sync()
        print(f"successfully synced {len(synced)} application slash commands.")
    except Exception as e:
        print(f"failed to sync slash commands: {e}")
        
    # timer goes tick tick yeah :D
    if not cycle_status_loop.is_running():
        cycle_status_loop.start()
        print("misoyan's status note rotation schedule has officially started.")
        
    print("starting main loop (ping)")
    bot.loop.create_task(auto_join_loop())

# "misoyan what you like?"
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # check master firewall switches first
    if not misoyan_settings["all_features"] or message.author.id in misoyan_settings["blacklist"]:
        return
        
    # verify if text parsing is allowed
    if not misoyan_settings["fih_replies"]:
        return

    if "misoyan" in message.content.lower() or bot.user.mentioned_in(message):
        try:
            selected_reply = random.choice(reply_list)
            await message.reply(selected_reply, allowed_mentions=discord.AllowedMentions.none())
        except Exception as e:
            print(f"failed to execute phrase callback: {e}")

    await bot.process_commands(message)

# slash commands
@bot.tree.command(name="ping", description="check misoyan's reflexes")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"no. (`{latency}ms`)")

@bot.tree.command(name="join", description="i wanna join the vc :3")
async def join(interaction: discord.Interaction):
    if not misoyan_settings["all_features"] or not misoyan_settings["vc_joining"]:
        await interaction.response.send_message("sorry, but blasie disabled this feature.", ephemeral=True)
        return

    global target_voice_channel_id
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("jump into a voice channel first you dummy!", ephemeral=True)
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
        start_silence_loop(vc)
    except Exception as e:
        print(f"fatal crash inside slash join command execution: {e}")
        await interaction.followup.send(f"failed to join voice channel: {e}", ephemeral=True)

@bot.tree.command(name="leave", description="pls let me go :c")
async def leave(interaction: discord.Interaction):
    if not misoyan_settings["all_features"] or not misoyan_settings["vc_leaving"]:
        await interaction.response.send_message("sorry, but blasie disabled this feature.", ephemeral=True)
        return
    
    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if vc and vc.is_connected():
        await vc.disconnect()
        await interaction.response.send_message("i am free!! (yay :3)", ephemeral=True)
    else:
        await interaction.response.send_message("you are asking me to leave discord? im not connected to vc..", ephemeral=True)

@bot.tree.command(name="status", description="check out my internal self :D")
async def systemstatus(interaction: discord.Interaction):
    total_guilds = len(bot.guilds)
    latency = round(bot.latency * 1000)
    current_vc_connections = len(bot.voice_clients)
    bot_thumbnail = bot.user.display_avatar.url
    
    embed = discord.Embed(
        title="misoyan's internal brain :3",
        description="very simple stuff",
        color=0x2b2d31
    )

    embed.set_thumbnail(url=bot_thumbnail)
    
    embed.add_field(name="reflex times", value=f"`{latency}ms`", inline=True)
    embed.add_field(name="servers i'm in", value=f"`{total_guilds} servers`", inline=True)
    embed.add_field(name="vcs i'm in right now", value=f"`{current_vc_connections} active streams`", inline=True)
    
    embed.set_footer(text="created by blasie :3")   
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="suicide", description="[blasie-only] completely kills misoyan.")
async def systemshutdown(interaction: discord.Interaction):
    if interaction.user.id != creator_id:
        await interaction.response.send_message("whoops, blasie didnt gave u access D:", ephemeral=True)
        return
        
    await interaction.response.send_message("OUCH D:")
    await bot.close()

@bot.tree.command(name="say", description="[blasie-only] make misoyan speak :D")
@app_commands.describe(message="the exact text you want misoyan to broadcast")
async def systemsay(interaction: discord.Interaction, message: str):
    # "shut up, ur not blasie"
    if interaction.user.id != creator_id:
        await interaction.response.send_message("whoops, blasie didnt gave u access D:", ephemeral=True)
        return
        
    # instantly satisfy discord's interaction loop privately so humans wouldnt see(maybe clankers will see idk)
    await interaction.response.send_message("fih", ephemeral=True)
    
    try:
        # drop the message into the exact text channel where you typed the command
        await interaction.channel.send(message)
        print(f"'{message}'")
    except Exception as e:
        print(f"someone tried to take control over me but couldnt due {e}")

@bot.tree.command(name="settings", description="[blasie-only] change my internal organs (oh god) :3")
async def control_panel(interaction: discord.Interaction):
    if interaction.user.id != creator_id:
        await interaction.response.send_message("whoops, blasie didnt gave u access D:", ephemeral=True)
        return
    view = FullSystemControlPanel()
    await interaction.response.send_message(embed=view.generate_dashboard_embed(), view=view, ephemeral=True)

@bot.tree.command(name="restrict", description="[blasie-only] dont end up in this list.")
@app_commands.describe(target="the specific person you want to modify settings for")
async def restrict_user(interaction: discord.Interaction, target: discord.User):
    if interaction.user.id != creator_id:
        await interaction.response.send_message("whoops, blasie didnt gave u access D:", ephemeral=True)
        return
        
    if target.id in misoyan_settings["blacklist"]:
        misoyan_settings["blacklist"].remove(target.id)
        await interaction.response.send_message(f"unblacklisted. **{target.name}** can now trigger misoyan again.", ephemeral=True)
    else:
        misoyan_settings["blacklist"].add(target.id)
        await interaction.response.send_message(f"blacklisted. **{target.name}** has been restricted.", ephemeral=True)

# --- RENDER NETWORK PROXY SYSTEM CHECK BYPASS ---
def run_dummy_server(port):
    """spins up a dead-simple server on an isolated background thread to keep render awake"""
    try:
        server_address = ('0.0.0.0', int(port))
        httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
        print(f"dummy network port verification listener active on port: {port}")
        httpd.serve_forever()
    except Exception as e:
        print(f"dummy listener server error trace: {e}")

if __name__ == "__main__":
    # if render assigned a network port, spin up the dummy web target layout
    if render_port:
        threading.Thread(target=run_dummy_server, args=(render_port,), daemon=True).start()

    if bot_token:
        bot.run(bot_token)
    else:
        print("you forgot my token you dummy!")
