import asyncio
import os
import random  # keeps random.choice from crashing her
import threading  # handles the background web server thread
from http.server import SimpleHTTPRequestHandler, HTTPServer  # basic server classes
import discord
from discord import app_commands
from discord.ext import commands, tasks
import wavelink  # 🚀 THE NEW IMMORTAL AUDIO BACKEND BRIDGE

# make bot can read the word "misoyan"
intents = discord.Intents.default()
intents.message_content = True 
intents.voice_states = True     # spy on vc

# blasie's id
creator_id = 891917254789320714

# compiler needs this
bot = commands.Bot(
    command_prefix="!", 
    intents=intents,
    heartbeat_timeout=60.0,    # gives her a full minute to recover if discord drops a gateway packet
    ws_close_timeout=10.0      # cleans up dead sockets fast so she can immediately re-handshake
)

# global settings
target_voice_channel_id = 123456789012345678  # default home channel
bot_token = os.environ.get("DISCORD_BOT_TOKEN")
render_port = os.environ.get("PORT")      # reads render's network port variable

# --- 🔒 CENTRALIZED RECONNECT CONCURRENCY LOCK ---
# prevents system layers from fighting each other over the connection pipeline
reconnect_lock = asyncio.Lock()

# settings panel (pls no touch)
# oke -kam
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

class FullSystemControlPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.update_panel_layout()

    def update_panel_layout(self):
        """paints the visual styles across both button rows based on your boolean settings"""
        # row 0: the voicelines and every damn festure 
        # holy dramatic nicknaming -kam
        self.children[0].label = f"all: {'on' if misoyan_settings['all_features'] else 'off'}"
        self.children[0].style = discord.ButtonStyle.blurple if misoyan_settings["all_features"] else discord.ButtonStyle.grey

        self.children[1].label = f"voicelines: {'on' if misoyan_settings['fih_replies'] else 'off'}"
        self.children[1].style = discord.ButtonStyle.blurple if misoyan_settings["fih_replies"] else discord.ButtonStyle.gray

        # row 1: vc shit
        # son -kam
        self.children[2].label = f"vc join: {'on' if misoyan_settings['vc_joining'] else 'off'}"
        self.children[2].style = discord.ButtonStyle.blurple if misoyan_settings["vc_joining"] else discord.ButtonStyle.grey

        self.children[3].label = f"vc leave: {'on' if misoyan_settings['vc_leaving'] else 'off'}"
        self.children[3].style = discord.ButtonStyle.blurple if misoyan_settings["vc_leaving"] else discord.ButtonStyle.grey

        # row 2: discord notes blah blah blah
        # sonion -kam
        self.children[4].label = f"statuses: {'on' if misoyan_settings['status_changes'] else 'off'}"
        self.children[4].style = discord.ButtonStyle.blurple if misoyan_settings["status_changes"] else discord.ButtonStyle.gray

        self.children[5].label = f"cycle rate: {'fast (1m)' if misoyan_settings['status_change_delay'] else 'normal (2.5m)'}"
        self.children[5].style = discord.ButtonStyle.blurple if misoyan_settings["status_change_delay"] else discord.ButtonStyle.grey

    def generate_dashboard_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="the command block",
            description="my internal organs :3", # why the fuck did i do this - blasie
            color=0xffcc80
        )

        embed.set_thumbnail(url=bot.user.display_avatar.url)
        
        # just display if on or off
        # sonbreto -kam
        embed.add_field(name="all features: ", value=f"state: `{'on' if misoyan_settings['all_features'] else 'off'}`", inline=False)
        embed.add_field(name="vc joining", value=f"state: `{'active' if misoyan_settings['vc_joining'] else 'disabled'}`", inline=True)
        embed.add_field(name="vc leaving", value=f"state: `{'active' if misoyan_settings['vc_leaving'] else 'disabled'}`", inline=True)
        embed.add_field(name="voicelines", value=f"state: `{'listening' if misoyan_settings['fih_replies'] else 'muted'}`", inline=True)
        embed.add_field(name="status changes", value=f"state: `{'cycling' if misoyan_settings['status_changes'] else 'frozen'}`", inline=True)
        embed.add_field(name="cycle frequency", value=f"state: `{'fast layout mode (1m)' if misoyan_settings['status_change_delay'] else 'normal engine rate (2.5m)'}`", inline=True)
        
        blacklist_mentions = ", ".join([f"<@{uid}>" for uid in misoyan_settings["blacklist"]]) if misoyan_settings["blacklist"] else "none"
        embed.add_field(name="blacklisted people", value=blacklist_mentions, inline=False)
        return embed

    # buttons
    # SONIONNNNN 😭 -kam
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

# --- 🌐 IMMORTAL BACKEND NODE POOL COUPLING ---
async def connect_external_audio_node():
    """establishes a persistent socket tunnel to the public web server cluster"""
    await bot.wait_until_ready()

    lava_host = os.getenv("LAVALINK_HOST", "lava.link")
    lava_port = os.getenv("LAVALINK_PORT", "80")
    lava_pass = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")

    is_secure = True if lava_port == "443" else False
    protocol = "https" if is_secure else "http"
    
    nodes = [
        wavelink.Node(
            identifier="misoyan_immortal_v4",
            uri=f"{protocol}://{lava_host}:{lava_port}",
            password=lava_pass,
        )
    ]
    
    try:
        await wavelink.Pool.connect(nodes=nodes, client=bot)
    except Exception as e:
        print(f"[!] audio node pipeline crash on startup: {e}")

@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    print(f"\n[+] network pipeline active! audio node '{payload.node.identifier}' is holding her voice core.")

# --- 🛡️ THE NATIVE VOICE SENTINEL GUARD ---
@tasks.loop(seconds=15)
async def native_voice_sentinel_loop():
    """discord.ext.tasks automatically monitors, isolates, and heals crashes silently!"""
    if not misoyan_settings["all_features"] or not misoyan_settings["vc_joining"]:
        return

    # skip check execution if the listener layer is currently re-handshaking the gateway
    if reconnect_lock.locked():
        return

    async with reconnect_lock:
        try:
            global target_voice_channel_id
            home_channel = bot.get_channel(target_voice_channel_id)
            if home_channel and isinstance(home_channel, discord.VoiceChannel):
                
                try:
                    player: wavelink.Player = wavelink.Pool.get_node().get_player(home_channel.guild.id)
                except Exception:
                    player = None
                
                if not player or not player.connected:
                    print("damn im gone from the vc. lemme reconnect via web node injector...")
                    
                    # force clean up lying internal engine cache states before firing
                    if home_channel.guild.voice_client:
                        try:
                            await home_channel.guild.voice_client.disconnect(force=True)
                            await asyncio.sleep(1.5)
                        except Exception:
                            pass

                    await home_channel.connect(cls=wavelink.Player)
                    
                elif player.channel.id != target_voice_channel_id:
                    print("im in the wrong channel. reconnecting back...")
                    await player.move_to(home_channel)
                    
        except Exception as e:
            print(f"sentinel loop encounter flaw: {e}")
            await asyncio.sleep(5.0)  # injection protection backoff buffer

# "feeling diffrent today"
@tasks.loop(minutes=2.5)
async def cycle_status_loop():
    await bot.wait_until_ready()
    if not misoyan_settings["all_features"] or not misoyan_settings["status_changes"]:
        return

    current_interval = cycle_status_loop.minutes
    if misoyan_settings["status_change_delay"] and current_interval != 1.0:
        cycle_status_loop.change_interval(minutes=1.0)
    elif not misoyan_settings["status_change_delay"] and current_interval != 2.5:
        cycle_status_loop.change_interval(minutes=2.5)

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
        
    if not cycle_status_loop.is_running():
        cycle_status_loop.start()
        print("misoyan's status note rotation schedule has officially started.")
        
    if not native_voice_sentinel_loop.is_running():
        native_voice_sentinel_loop.start()
        print("[sentinel] persistent voice monitor initialized.")
        
    bot.loop.create_task(connect_external_audio_node())

# intercept system to make sure nobody boots her out of paradise
@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if member.id == bot.user.id:
        if after.channel is None or after.channel.id != target_voice_channel_id:
            print("oh shit, i think its time to reconnect")
            
            if misoyan_settings["all_features"] and misoyan_settings["vc_joining"]:
                # skip immediately if the sentinel task is already managing a network handshake loop
                if reconnect_lock.locked():
                    print("[lock] reconnect task already running elsewhere. dropping event bubble hook.")
                    return

                async with reconnect_lock:
                    try:
                        player: wavelink.Player = wavelink.Pool.get_node().get_player(member.guild.id)
                        if player:
                            await player.disconnect()
                            await asyncio.sleep(1.0)
                    except Exception as e:
                        print(f"couldn't wipe dead voice handle: {e}")
                    
                    home_channel = bot.get_channel(target_voice_channel_id)
                    if home_channel and isinstance(home_channel, discord.VoiceChannel):
                        try:
                            print(f"snapping back to home vc -> {home_channel.name}")
                            
                            # check if core library container state is out of sync with discord's gateway
                            if member.guild.voice_client:
                                try:
                                    await member.guild.voice_client.disconnect(force=True)
                                    await asyncio.sleep(1.5)
                                except Exception:
                                    pass

                            await home_channel.connect(cls=wavelink.Player)
                        except Exception as e:
                            print(f"instant intercept recovery failed: {e}. backup loop will catch it.")
                            await asyncio.sleep(5.0)  # ⚠️ crucial machine-gun security backoff lock delay!

# "misoyan what you like?"
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if not misoyan_settings["all_features"] or message.author.id in misoyan_settings["blacklist"]:
        return
        
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
    await interaction.response.defer() 
    target_voice_channel_id = user_channel.id
    
    try:
        print(f"establishing client connection to web node for: {user_channel.name}")
        await user_channel.connect(cls=wavelink.Player)
        await interaction.followup.send(f"i joined **{user_channel.name}**")
    except Exception as e:
        print(f"fatal crash inside slash join command execution: {e}")
        await interaction.followup.send(f"failed to join voice channel: {e}", ephemeral=True)

@bot.tree.command(name="leave", description="pls let me go :c")
async def leave(interaction: discord.Interaction):
    if not misoyan_settings["all_features"] or not misoyan_settings["vc_leaving"]:
        await interaction.response.send_message("sorry, but blasie disabled this feature.", ephemeral=True)
        return
    
    try:
        player: wavelink.Player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        if player and player.connected:
            await player.disconnect()
            await interaction.response.send_message("i am free!! (yay :3)", ephemeral=True)
        else:
            await interaction.response.send_message("you are asking me to leave discord? im not connected to vc..", ephemeral=True)
    except Exception:
        await interaction.response.send_message("im not connected to any voice node...", ephemeral=True)

@bot.tree.command(name="play", description="blast some tracks through misoyan's powerful speakers!")
@app_commands.describe(search="the song name, artist, or direct video url you want to play")
async def play(interaction: discord.Interaction, search: str):
    if not misoyan_settings["all_features"]:
        await interaction.response.send_message("sorry, but blasie has disabled this feature.", ephemeral=True)
        return

    if interaction.user.id in misoyan_settings["blacklist"]:
        await interaction.response.send_message("you are on my blacklist. no speakers for you.", ephemeral=True)
        return

    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("join a voice channel first, you dummy! i need an audience. :c", ephemeral=True)
        return

    user_channel = interaction.user.voice.channel
    await interaction.response.defer()

    try:
        node = wavelink.Pool.get_node()
        player: wavelink.Player = node.get_player(interaction.guild.id)

        if not player or not player.connected:
            print(f"[play] connecting voice client node injector to: {user_channel.name}")
            player = await user_channel.connect(cls=wavelink.Player)
            global target_voice_channel_id
            target_voice_channel_id = user_channel.id

        tracks = await wavelink.Playable.search(search)
        
        if not tracks:
            await interaction.followup.send(f"i couldn't find anything for `{search}`... are you sure that exists? :c")
            return

        track = tracks[0]
        await player.play(track)
        
        embed = discord.Embed(
            title="now playing!",
            description=f"**[{track.title}]({track.uri})**",
            color=0xffcc80
        )
        if track.author:
            embed.add_field(name="artist/creator", value=f"`{track.author}`", inline=True)
        if track.length:
            minutes = int((track.length // 1000) // 60)
            seconds = int((track.length // 1000) % 60)
            embed.add_field(name="duration", value=f"`{minutes}:{seconds:02d}`", inline=True)
            
        embed.set_footer(text=f"requested by {interaction.user.name} :3")
        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(f"[!] play command architecture threw a flaw: {e}")
        await interaction.followup.send(f"uh oh, my speakers failed: `{e}`", ephemeral=True)

@bot.tree.command(name="status", description="check out my internal self :D")
async def systemstatus(interaction: discord.Interaction):
    total_guilds = len(bot.guilds)
    latency = round(bot.latency * 1000)
    
    try:
        current_vc_connections = 1 if wavelink.Pool.get_node().get_player(interaction.guild.id) else 0
    except Exception:
        current_vc_connections = 0
        
    bot_thumbnail = bot.user.display_avatar.url
    
    embed = discord.Embed(
        title="misoyan's internal brain :3",
        description="very simple stuff",
        color=0x2b2d31
    )

    embed.set_thumbnail(url=bot_thumbnail)
    embed.add_field(name="reflex times: ", value=f"`{latency}ms`", inline=False)
    embed.add_field(name="servers i'm in: ", value=f"`{total_guilds} servers`", inline=False)
    embed.add_field(name="vcs i'm in right now: ", value=f"`{current_vc_connections} active vcs`", inline=False)
    
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
    if interaction.user.id != creator_id:
        await interaction.response.send_message("whoops, blasie didnt gave u access D:", ephemeral=True)
        return
        
    await interaction.response.send_message("fih", ephemeral=True)
    
    try:
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
# SONNNNNNNNNNNNNNNNNNNNNN😭😭😭 -kam
def run_dummy_server(port):
    try:
        server_address = ('0.0.0.0', int(port))
        httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
        print(f"dummy network port verification listener active on port: {port}")
        httpd.serve_forever()
    except Exception as e:
        print(f"dummy listener server error trace: {e}")

if __name__ == "__main__":
    if render_port:
        threading.Thread(target=run_dummy_server, args=(render_port,), daemon=True).start()

    if bot_token:
        bot.run(bot_token)
    else:
        print("you forgot my token you dummy!")
