import asyncio
import os
import random  # keeps random.choice from crashing her
import threading  # handles the background web server thread
from http.server import SimpleHTTPRequestHandler, HTTPServer  # basic server classes
import discord
from discord import app_commands
from discord.ext import commands, tasks
import wavelink  # this powers her speakers

# make bot can read the word "misoyan"
intents = discord.Intents.default()
intents.message_content = True 
intents.voice_states = True     # spy on vc

# blasie's id
creator_id = int(os.environ.get("CREATOR_ID", 0))

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

# lavalink stuff
lava_host = os.getenv("LAVALINK_HOST", "lava.link")
lava_port = os.getenv("LAVALINK_PORT", "80")
lava_pass = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")
lava_secure_env = os.getenv("LAVALINK_SECURE", "false").lower() == "true"

# settings panel (pls no touch)
# oke -kam
misoyan_settings = {
    "all_features": True,           # "nah, i'm going offline for a bit"
    "vc_joining": True,             # "cant join vc im busy"
    "vc_leaving": True,             # yeah i can hold the vc for a bit
    "status_changes": True,         # maybe i wont make a note rn...
    "status_change_delay": False,   # "wait i should do this... NO WAIT THIS IS-"
    "fih_replies": True,            # fih :3
    "need_reconnection": False,     # "i dont need to connect rn, im alr connected :sob:"
    "is_connecting": False,         # "yo im alr connecting"
    "blacklist": set()              # "i hate you, dont talk to me >:("
}

# asyncio lock to prevent the loop and events from connecting at the same time
vc_connection_lock = asyncio.Lock()

# clanker has emotions | format: (status, discord note)
status_pool = [
    (discord.Status.online, discord.CustomActivity(name="hanging out in the vc :3")),
    (discord.Status.idle, discord.CustomActivity(name="waiting for someone to join :c")),
    (discord.Status.dnd, discord.CustomActivity(name="learning new stuff...")),
    (discord.Status.invisible, discord.CustomActivity(name="lurking...")),
    (discord.Status.online, discord.CustomActivity(name="yapping in yappanese bleh")),
    (discord.Status.idle, discord.CustomActivity(name="waiting for someone to call my name :c")),
    (discord.Status.dnd, discord.CustomActivity(name="please do the fih")),
    (discord.Status.invisible, discord.CustomActivity(name="sleeping... zzz")),
    (discord.Status.dnd, discord.CustomActivity(name="planning next stream")),
    (discord.Status.idle, discord.CustomActivity(name="bored as hell")),
    (discord.Status.online, discord.CustomActivity(name="hanging out on stream")),
    (discord.Status.dnd, discord.CustomActivity(name="i'm lurking in your walls :3"))
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
    "the fih gods are watching us",
    "https://tenor.com/view/spinning-fish-gif-11746948154213447163",
    "https://tenor.com/view/upside-down-spinning-fish-long-sticker-gif-14191013706827067344",
    "https://tenor.com/view/pog-gif-14149886028736974766",
    "https://tenor.com/view/silly-cat-doodle-fish-nibble-cat-eating-fish-gif-15126373179558858541",
    "https://tenor.com/view/screaming-fish-fish-fish-finger-gif-9883040399517041611",
    "https://tenor.com/view/kiracord-fish-gif-22855500",
    "https://tenor.com/view/cat-cat-pufferfish-pufferfish-cat-fish-catfish-gif-9997139051265883971",
    "praise fih",
    "killer fish from san diego",
    "fih party",
    "spinning fish",
    "me and fih :3",
    "🐟",  # fixed: added missing comma separator here so string literals don't merge!
    "im in your walls :D"
]

class FullSystemControlPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.update_panel_layout()

    def update_panel_layout(self):
        """paints the visual styles across both button rows based on your boolean settings"""
        self.children[0].label = f"all: {'on' if misoyan_settings['all_features'] else 'off'}"
        self.children[0].style = discord.ButtonStyle.blurple if misoyan_settings["all_features"] else discord.ButtonStyle.grey

        self.children[1].label = f"voicelines: {'on' if misoyan_settings['fih_replies'] else 'off'}"
        self.children[1].style = discord.ButtonStyle.blurple if misoyan_settings["fih_replies"] else discord.ButtonStyle.gray

        self.children[2].label = f"vc join: {'on' if misoyan_settings['vc_joining'] else 'off'}"
        self.children[2].style = discord.ButtonStyle.blurple if misoyan_settings["vc_joining"] else discord.ButtonStyle.grey

        self.children[3].label = f"vc leave: {'on' if misoyan_settings['vc_leaving'] else 'off'}"
        self.children[3].style = discord.ButtonStyle.blurple if misoyan_settings["vc_leaving"] else discord.ButtonStyle.grey

        self.children[4].label = f"statuses: {'on' if misoyan_settings['status_changes'] else 'off'}"
        self.children[4].style = discord.ButtonStyle.blurple if misoyan_settings["status_changes"] else discord.ButtonStyle.gray

        self.children[5].label = f"cycle rate: {'fast (1m)' if misoyan_settings['status_change_delay'] else 'normal (2.5m)'}"
        self.children[5].style = discord.ButtonStyle.blurple if misoyan_settings["status_change_delay"] else discord.ButtonStyle.grey

    def generate_dashboard_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="the command block",
            description="my internal organs :3",
            color=0xffcc80
        )
        embed.set_thumbnail(url=bot.user.display_avatar.url)
        
        embed.add_field(name="all features: ", value=f"state: `{'on' if misoyan_settings['all_features'] else 'off'}`", inline=False)
        embed.add_field(name="vc joining", value=f"state: `{'active' if misoyan_settings['vc_joining'] else 'disabled'}`", inline=True)
        embed.add_field(name="vc leaving", value=f"state: `{'active' if misoyan_settings['vc_leaving'] else 'disabled'}`", inline=True)
        embed.add_field(name="voicelines", value=f"state: `{'listening' if misoyan_settings['fih_replies'] else 'muted'}`", inline=True)
        embed.add_field(name="status changes", value=f"state: `{'cycling' if misoyan_settings['status_changes'] else 'frozen'}`", inline=True)
        embed.add_field(name="cycle frequency", value=f"state: `{'fast layout mode (1m)' if misoyan_settings['status_change_delay'] else 'normal engine rate (2.5m)'}`", inline=True)
        
        blacklist_mentions = ", ".join([f"<@{uid}>" for uid in misoyan_settings["blacklist"]]) if misoyan_settings["blacklist"] else "none"
        embed.add_field(name="blacklisted people", value=blacklist_mentions, inline=False)
        return embed

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

async def connect_external_audio_node():
    """establishes a persistent socket tunnel to the public web server cluster"""
    await bot.wait_until_ready()

    is_secure = lava_secure_env or lava_port == "443"
    protocol = "https" if is_secure else "http"
    
    nodes = [
        wavelink.Node(
            identifier="misoyan",
            uri=f"{protocol}://{lava_host}:{lava_port}",
            password=lava_pass,
        )
    ]
    
    try:
        await wavelink.Pool.connect(nodes=nodes, client=bot)
    except Exception as e:
        print(f"[!] wait my mic broke: {e}")

@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    print(f"\n[+] yay my mic works and im connected")

@tasks.loop(seconds=15)
async def native_voice_sentinel_loop():
    """automatically monitors, isolates, and heals crashes silently without spamming dead transport pipes"""
    if not misoyan_settings["all_features"] or not misoyan_settings["vc_joining"]:
        return

    if misoyan_settings["is_connecting"] or vc_connection_lock.locked():
        return

    global target_voice_channel_id
    home_channel = bot.get_channel(target_voice_channel_id)
    if not home_channel or not isinstance(home_channel, discord.VoiceChannel):
        return

    try:
        player: wavelink.Player = wavelink.Pool.get_node().get_player(home_channel.guild.id)
    except Exception:
        player = None

    is_disconnected = not player or not player.connected

    if is_disconnected or misoyan_settings["need_reconnection"]:
        async with vc_connection_lock:
            print("wait im reconnecting pls wait for me")
            misoyan_settings["is_connecting"] = True
            
            try:
                if home_channel.guild.voice_client:
                    try:
                        await home_channel.guild.voice_client.disconnect(force=True)
                        await asyncio.sleep(1.5)
                    except Exception:
                        pass

                await home_channel.connect(cls=wavelink.Player)
                print("im back :3")
                misoyan_settings["need_reconnection"] = False
                
            except Exception as e:
                print(f"so uhh, my wifi broke: {e}")
                # if it throws a closing transport error, force lower the flag so it backs off completely
                if "closing transport" in str(e).lower() or "timeout" in str(e).lower():
                    misoyan_settings["need_reconnection"] = False
                await asyncio.sleep(8.0)
            finally:
                misoyan_settings["is_connecting"] = False

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
        print(f"yeah i couldnt change my discord status: {e}")

@bot.event
async def on_ready():
    print(f"ah, time to go on discord | {bot.user.name}")
    
    try:
        synced = await bot.tree.sync()
        print(f"i got {len(synced)} commands ready :o")
    except Exception as e:
        print(f"wait where did my commands go- | {e}")
        
    if not cycle_status_loop.is_running():
        cycle_status_loop.start()
        print("time to pick a status i guess.")
        
    if not native_voice_sentinel_loop.is_running():
        native_voice_sentinel_loop.start()
        print("time to set up my speakers for music")
        
    bot.loop.create_task(connect_external_audio_node())

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if member.id != bot.user.id:
        return

    if after.channel is None or after.channel.id != target_voice_channel_id:
        print("wait im not in my vc anymore give me a sec")
        
        if misoyan_settings["all_features"] and misoyan_settings["vc_joining"]:
            # only trigger if we aren't already locking the engine state
            if not misoyan_settings["is_connecting"] and not vc_connection_lock.locked():
                misoyan_settings["need_reconnection"] = True

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
            print(f"my chat broke: {e}")

# slash commands
@bot.tree.command(name="ping", description="check misoyan's reflexes")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"i'm not playing ping pong. (`{latency}ms`)")

@bot.tree.command(name="join", description="i wanna join the vc :3")
async def join(interaction: discord.Interaction):
    if not misoyan_settings["all_features"] or not misoyan_settings["vc_joining"]:
        await interaction.response.send_message("nah, too busy rn (disabled)", ephemeral=True)
        return

    global target_voice_channel_id
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("get in a voice channel you dummy!", ephemeral=True)
        return
    
    user_channel = interaction.user.voice.channel
    await interaction.response.defer() 
    target_voice_channel_id = user_channel.id
    
    if vc_connection_lock.locked():
        await interaction.followup.send("wait, i'm already trying to adjust my voice cords... hold on!", ephemeral=True)
        return

    async with vc_connection_lock:
        try:
            misoyan_settings["is_connecting"] = True
            print(f"connecting to vc: {user_channel.name}")
            await user_channel.connect(cls=wavelink.Player)
            misoyan_settings["need_reconnection"] = False
            await interaction.followup.send(f"im in your vc now :D")
        except Exception as e:
            print(f"shit i failed to join: {e}")
            await interaction.followup.send(f"so i may have failed to connect...: {e}", ephemeral=True)
        finally:
            misoyan_settings["is_connecting"] = False

@bot.tree.command(name="leave", description="pls let me go :c")
async def leave(interaction: discord.Interaction):
    if not misoyan_settings["all_features"] or not misoyan_settings["vc_leaving"]:
        await interaction.response.send_message("you are not making me leave lmaooo (disabled)", ephemeral=True)
        return
    
    try:
        player: wavelink.Player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        if player and player.connected:
            async with vc_connection_lock:
                misoyan_settings["need_reconnection"] = False
                await player.disconnect()
                await interaction.response.send_message("i am free!! (yay :3)", ephemeral=True)
        else:
            await interaction.response.send_message("you want me to leave...? im not connected to a vc", ephemeral=True)
    except Exception:
        await interaction.response.send_message("i think my speakers malfunctioned", ephemeral=True)

@bot.tree.command(name="play", description="what song do you want?")
@app_commands.describe(search="the song name, artist, or direct url you want to play")
async def play(interaction: discord.Interaction, search: str):
    if not misoyan_settings["all_features"]:
        await interaction.response.send_message("my speakers are off rn (disabled)", ephemeral=True)
        return

    if interaction.user.id in misoyan_settings["blacklist"]:
        await interaction.response.send_message("hey, don't touch that.", ephemeral=True)
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
            async with vc_connection_lock:
                misoyan_settings["is_connecting"] = True
                print(f"[/play] connecting to vc: {user_channel.name}")
                player = await user_channel.connect(cls=wavelink.Player)
                global target_voice_channel_id
                target_voice_channel_id = user_channel.id
                misoyan_settings["need_reconnection"] = False
                await asyncio.sleep(1.5)

        cleaned_search = search
        for automated_prefix in ["ytsearch:", "ytmsearch:", "scsearch:", "youtube_music:"]:
            if cleaned_search.lower().startswith(automated_prefix):
                cleaned_search = cleaned_search[len(automated_prefix):].strip()

        print(f"wait, im searching for '{cleaned_search}' rn gimme a sec")
        search_results = await wavelink.Playable.search(cleaned_search)
        
        if not search_results:
            await interaction.followup.send(f"so... there's no song named *{search}*. you sure that exists?")
            return

        if hasattr(search_results, "tracks"):
            tracks = search_results.tracks
        elif isinstance(search_results, list):
            tracks = search_results
        else:
            tracks = [search_results]

        if not tracks:
            await interaction.followup.send(f"so i searched for *{search}*, but it has no songs... D:")
            return

        track = tracks[0]
        
        if player.playing:
            # if she's already singing, put it in the waiting line
            player.queue.put(track)
            
            embed = discord.Embed(
                title="added to queue!",
                description=f"**[{track.title}]({track.uri})**",
                color=0xffcc80
            )
            embed.add_field(name="position", value=f"`#{len(player.queue)}`", inline=True)
            if track.author:
                embed.add_field(name="artist", value=f"`{track.author}`", inline=True)
            embed.set_footer(text=f"requested by {interaction.user.name} :3")
            await interaction.followup.send(embed=embed)
            print(f"[queue] added '{track.title}' to the server line")
            
        else:
            # if the speakers are silent, just play it right away
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
            print(f"[music - play] playing '{track.title} - {track.author}'")

    except Exception as e:
        print(f"[!] my speakers nooo- | {e}")
        await interaction.followup.send(f"so my speakers... uhh: `{e}`", ephemeral=True)
    finally:
        misoyan_settings["is_connecting"] = False

@bot.tree.command(name="skip", description="skip this track if it's bad bleh")
async def skip(interaction: discord.Interaction):
    if not misoyan_settings["all_features"]:
        await interaction.response.send_message("my speakers are off rn (disabled)", ephemeral=True)
        return

    if interaction.user.id in misoyan_settings["blacklist"]:
        await interaction.response.send_message("hey, don't touch that.", ephemeral=True)
        return

    try:
        node = wavelink.Pool.get_node()
        player: wavelink.Player = node.get_player(interaction.guild.id)

        if not player or not player.connected:
            await interaction.response.send_message("i'm not even in a vc to skip anything?", ephemeral=True)
            return

        if not player.playing:
            await interaction.response.send_message("there's nothing playing right now anyway!", ephemeral=True)
            return

        # skip the current song
        await player.skip()
        await interaction.response.send_message("track skipped! next track coming up...")
        print(f"[music] skip command triggered by {interaction.user.name}")

    except Exception as e:
        print(f"[!] failed to skip: {e}")
        await interaction.response.send_message(f"uhh my controls jammed: `{e}`", ephemeral=True)

@bot.tree.command(name="previous", description="go back to the last song!")
async def previous(interaction: discord.Interaction):
    if not misoyan_settings["all_features"]:
        await interaction.response.send_message("my speakers are off rn (disabled)", ephemeral=True)
        return

    if interaction.user.id in misoyan_settings["blacklist"]:
        await interaction.response.send_message("hey, don't touch that.", ephemeral=True)
        return

    try:
        node = wavelink.Pool.get_node()
        player: wavelink.Player = node.get_player(interaction.guild.id)

        if not player or not player.connected:
            await interaction.response.send_message("i'm not in a vc!", ephemeral=True)
            return

        # check if there's even a past track recorded in the memory bank
        if not player.queue.history:
            await interaction.response.send_message("hmph, there isn't even any previous songs played.", ephemeral=True)
            return

        # grab the absolute last track that played
        # history keeps growing, so the last item is at index -1
        last_track = player.queue.history[-1]
        
        # if a song is playing, clear it out so we can backtrack immediately
        await player.play(last_track)
        await interaction.response.send_message(f"rewinding back to: **{last_track.title}**")
        print(f"[music] rewound to previous track via {interaction.user.name}")

    except Exception as e:
        print(f"[!] failed to backtrack: {e}")
        await interaction.response.send_message(f"couldn't go back: `{e}`", ephemeral=True)

@bot.tree.command(name="queue", description="see what songs are lined up next")
async def view_queue(interaction: discord.Interaction):
    try:
        node = wavelink.Pool.get_node()
        player: wavelink.Player = node.get_player(interaction.guild.id)

        if not player or not player.connected:
            await interaction.response.send_message("i'm not in a vc, no queue here!", ephemeral=True)
            return

        embed = discord.Embed(title="misoyan's waiting line", color=0xffcc80)
        
        # display current song
        if player.current:
            embed.description = f"**now playing:** [{player.current.title}]({player.current.uri})\n\n__up next:__"
        else:
            embed.description = "nothing is playing right now.\n\n__up next:__"

        # parse the next 5 upcoming tracks cleanly
        if player.queue.is_empty:
            embed.description += "\nqueue is completely empty. add some tracks! :3"
        else:
            # slice the queue to just show the top items so the embed doesn't smash the limit size
            for index, upcoming_track in enumerate(list(player.queue)[:5], start=1):
                embed.description += f"\n`{index}.` [{upcoming_track.title}]({upcoming_track.uri})"
            
            if len(player.queue) > 5:
                embed.description += f"\n*...and {len(player.queue) - 5} more tracks in line!*"

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"couldn't read the waiting list: `{e}`", ephemeral=True)

@bot.tree.command(name="play-file", description="give me your audio file :)")
@app_commands.describe(attachment="drag and drop or select an audio file (.mp3, .wav, .ogg, etc.) from your device")
async def play_file(interaction: discord.Interaction, attachment: discord.Attachment):
    if not misoyan_settings["all_features"]:
        await interaction.response.send_message("my speakers are off, mb (disabled)", ephemeral=True)
        return

    if interaction.user.id in misoyan_settings["blacklist"]:
        await interaction.response.send_message("no, i'm not playing that for you.", ephemeral=True)
        return

    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("join a voice channel first, you dummy! i need an audience. :c", ephemeral=True)
        return

    valid_extensions = [".mp3", ".wav", ".ogg", ".flac", ".m4a"]
    if not any(attachment.filename.lower().endswith(ext) for ext in valid_extensions):
        await interaction.response.send_message("you sure this is an audio file? doesnt look like it", ephemeral=True)
        return

    user_channel = interaction.user.voice.channel
    await interaction.response.defer()

    try:
        node = wavelink.Pool.get_node()
        player: wavelink.Player = node.get_player(interaction.guild.id)

        if not player or not player.connected:
            async with vc_connection_lock:
                misoyan_settings["is_connecting"] = True
                print(f"[play-file] connecting to vc: {user_channel.name}")
                player = await user_channel.connect(cls=wavelink.Player)
                global target_voice_channel_id
                target_voice_channel_id =
