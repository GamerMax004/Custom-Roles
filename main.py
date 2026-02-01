import discord
from discord import app_commands
from discord.ext import commands
import json
import logging
from datetime import datetime
from typing import Optional, List
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# Flask-App für Render Keep-Alive
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
    
# Lade Umgebungsvariablen
load_dotenv()

# Logging-Konfiguration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('RoleBot')

class RoleBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True

        super().__init__(command_prefix='!', intents=intents)

        self.config_file = 'config.json'

        # Standard-Rollen die IMMER alle Befehle ausführen können (nach Rollen-ID)
        # Füge hier die IDs deiner beiden Standard-Rollen ein
        self.default_admin_roles = [1399855053283528735, 1399855033931137137]

        self.config = self.load_config()

    def load_config(self):
        """Lädt die Konfiguration aus der JSON-Datei"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

                # Stelle sicher, dass alle benötigten Keys existieren
                if 'role_connections' not in config:
                    config['role_connections'] = {}
                if 'log_channels' not in config:
                    config['log_channels'] = {}
                if 'command_permissions' not in config:
                    config['command_permissions'] = {}

                # Speichere aktualisierte Config
                self.save_config(config)
                return config

        except FileNotFoundError:
            default_config = {
                'role_connections': {},  # guild_id: {parent_role_id: [child_role_ids]}
                'log_channels': {},  # guild_id: channel_id
                'command_permissions': {}  # guild_id: {command_name: [role_ids]}
            }
            self.save_config(default_config)
            return default_config

    def save_config(self, config=None):
        """Speichert die Konfiguration in die JSON-Datei"""
        if config is None:
            config = self.config
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        logger.info("Konfiguration gespeichert")

    def has_default_permission(self, member: discord.Member) -> bool:
        """Prüft ob ein User Standard-Berechtigungen hat (Administrator, Manage Roles oder Standard-Admin-Rollen)"""
        # Prüfe Discord-Berechtigungen
        if member.guild_permissions.administrator or member.guild_permissions.manage_roles:
            return True

        # Prüfe ob User eine der Standard-Admin-Rollen hat
        user_role_ids = [role.id for role in member.roles]
        if any(role_id in self.default_admin_roles for role_id in user_role_ids):
            return True

        return False

    def check_command_permission(self, guild_id: str, command_name: str, user_roles: List[int]) -> bool:
        """Prüft ob ein User die Berechtigung für einen Command hat"""
        # Wenn keine Berechtigungen für diesen Command konfiguriert sind, return False
        if guild_id not in self.config['command_permissions']:
            return False
        if command_name not in self.config['command_permissions'][guild_id]:
            return False

        # Prüfe ob User eine der erlaubten Rollen hat
        allowed_roles = self.config['command_permissions'][guild_id][command_name]
        return any(role_id in allowed_roles for role_id in user_roles)

    async def log_action(self, guild: discord.Guild, action_type: str, user: discord.Member, 
                        details: str, moderator: Optional[discord.Member] = None, 
                        roles: List[discord.Role] = None):
        """Protokolliert Aktionen mit schönen Embeds im Log-Channel"""
        logger.info(f"[{guild.name}] {action_type}: {details}")

        guild_id = str(guild.id)
        if guild_id in self.config['log_channels']:
            channel_id = self.config['log_channels'][guild_id]
            channel = guild.get_channel(channel_id)

            if channel:
                # Bestimme Farbe und Style basierend auf Aktion
                if action_type == "Rolle bekommen":
                    color = discord.Color.from_str("#1eff00")
                    title = "Rolle vergeben"
                elif action_type == "Rolle entfernt":
                    color = discord.Color.from_str("#ff0000")
                    title = "Rolle entfernt"
                elif action_type == "Automatisch zugewiesen":
                    color = discord.Color.from_str("#1eff00")
                    title = "Automatisch zugewiesen"
                elif action_type == "Automatisch entfernt":
                    color = discord.Color.from_str("#ff0000")
                    title = "Automatisch entfernt"
                else:
                    color = discord.Color.from_str("#647be0")
                    title = f"{action_type}"

                embed = discord.Embed(
                    title=title,
                    color=color,
                    timestamp=datetime.utcnow(),
                )
                
                # User Information
                user_info = f"> User: {user.mention}\n> Username: `{user.name}`\n> User-ID: `{user.id}`"
                embed.add_field(
                    name="<:7549member:1467278105616973997> Benutzer",
                    value=user_info,
                    inline=True
                )

                #Aktionsinformation Rollenverbildungen
                if action_type == "Rollenverbindung erstellt":
                    embed.add_field(
                        name="<:1198link:1467278050436710500> Verbindung(en)",
                        value="> <:3518checkmark:1467278064340832513> Aktiviert",
                        inline=False
                    )
                elif action_type == "Rollenverbindung gelöscht":
                    embed.add_field(
                        name="<:1198link:1467278050436710500> Verbindung(en)",
                        value="> <:3518crossmark:1467278065729146900> Deaktiviert",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="<:4549activity:1467278075778699344> Aktion",
                        value=f"> Aktion: `{action_type}`",
                        inline=False
                    )
                
                # Rolleninformationen
                if action_type in ["Rolle bekommen", "Rolle entfernt"]:
                    embed.add_field(
                        name="<:4748ticket:1467278078672633967> Rolle",
                        value=f"> Rolle: {roles[0].mention}\n> Rollen-ID: `{roles[0].id}`",
                        inline=False)
                
                else:
                    embed.add_field(
                        name="<:4748ticket:1467278078672633967> Rolle",
                        value=f"> Rolle: {', '.join([r.mention for r in roles])}",
                        inline=False)
                
                # Details
                if details:
                    embed.add_field(
                        name="Details",
                        value=f"```{details}```",
                        inline=False
                    )

                # Footer
                embed.set_footer(
                    text=f"{guild.name}",
                    icon_url=guild.icon.url if guild.icon else None
                )

                embed.set_image(url="https://media.discordapp.net/attachments/1451317020418117724/1467474183863668778/image.png?ex=69808355&is=697f31d5&hm=6afff69c87b5034878535c9212796fff168b1d3388950cc2aa6039e7736140c4&=&format=webp&quality=lossless&width=1128&height=254")
                # Thumbnail (User Avatar)
                embed.set_thumbnail(url=user.display_avatar.url)

                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    logger.error(f"Fehler beim Senden der Log-Nachricht: {e}")

    async def setup_hook(self):
        """Wird beim Start des Bots ausgeführt"""
        await self.tree.sync()
        logger.info("Slash-Commands synchronisiert")

bot = RoleBot()

@bot.event
async def on_ready():
    logger.info(f'Bot eingeloggt als {bot.user.name} (ID: {bot.user.id})')
    logger.info(f'Verbunden mit {len(bot.guilds)} Server(n)')

    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="Rollenverwaltung | /help"
    )
    await bot.change_presence(activity=activity)

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    """Überwacht Rollenänderungen und verwaltet verbundene Rollen"""
    guild_id = str(after.guild.id)

    added_roles = set(after.roles) - set(before.roles)
    removed_roles = set(before.roles) - set(after.roles)

    if guild_id in bot.config['role_connections']:
        connections = bot.config['role_connections'][guild_id]

        # Wenn eine Parent-Rolle hinzugefügt wurde, füge Child-Rollen hinzu
        for role in added_roles:
            role_id = str(role.id)
            if role_id in connections:
                child_role_ids = connections[role_id]
                child_roles = []

                for child_id in child_role_ids:
                    child_role = after.guild.get_role(child_id)
                    if child_role and child_role not in after.roles:
                        child_roles.append(child_role)

                if child_roles:
                    try:
                        await after.add_roles(*child_roles, reason="Verbundene Rollen automatisch hinzugefügt")
                        role_names = ", ".join([r.name for r in child_roles])
                        await bot.log_action(
                            after.guild,
                            "Automatisch zugewiesen",
                            after,
                            f"Durch Rolle '{role.name}' wurden automatisch zugewiesen: {role_names}",
                            roles=child_roles
                        )
                    except Exception as e:
                        logger.error(f"Fehler beim Hinzufügen verbundener Rollen: {e}")

        # Wenn eine Parent-Rolle entfernt wird, prüfe ob Child-Rollen wieder hinzugefügt werden müssen
        for role in removed_roles:
            role_id = str(role.id)
            if role_id in connections:
                child_role_ids = connections[role_id]
                roles_to_remove = []

                for child_id in child_role_ids:
                    child_role = after.guild.get_role(child_id)
                    if child_role and child_role in after.roles:
                        # Prüfe, ob der User eine andere Parent-Rolle hat, die diese Child-Rolle benötigt
                        should_keep_role = False
                        for other_parent_id, other_child_ids in connections.items():
                            if child_id in other_child_ids and other_parent_id != role_id:
                                other_parent_role = after.guild.get_role(int(other_parent_id))
                                if other_parent_role and other_parent_role in after.roles:
                                    should_keep_role = True
                                    break

                        if not should_keep_role:
                            roles_to_remove.append(child_role)

                if roles_to_remove:
                    try:
                        await after.remove_roles(*roles_to_remove, reason="Verbundene Rollen automatisch entfernt")
                        role_names = ", ".join([r.name for r in roles_to_remove])
                        await bot.log_action(
                            after.guild,
                            "Automatisch entfernt",
                            after,
                            f"Durch Entfernung von '{role.name}' wurden entfernt: {role_names}",
                            roles=roles_to_remove
                        )
                    except Exception as e:
                        logger.error(f"Fehler beim Entfernen verbundener Rollen: {e}")

# ========== SLASH COMMANDS ==========
@bot.tree.command(name="config", description="Zeigt die komplette Bot-Konfiguration")
async def show_config(interaction: discord.Interaction):
    """Zeigt eine detaillierte Übersicht der Konfiguration"""
    # Prüfe Berechtigung
    if not bot.has_default_permission(interaction.user):
        await interaction.response.send_message(
            "<:3518crossmark:1467278065729146900> Du hast keine Berechtigung für diesen Command!",
            ephemeral=True
        )
        return

    guild_id = str(interaction.guild_id)

    embed = discord.Embed(
        title="Bot-Konfiguration",
        description=f"Konfiguration für **{interaction.guild.name}**",
        color=discord.Color.from_str("#647be0"),
        timestamp=datetime.utcnow()
    )

    # 1. Log-Channel
    if guild_id in bot.config['log_channels']:
        channel = interaction.guild.get_channel(bot.config['log_channels'][guild_id])
        if channel:
            embed.add_field(
                name="<:1041searchthreads:1467278040915771596> Log-Kanal",
                value=f"<:3518checkmark:1467278064340832513> Aktiviert\n> Kanal: {channel.mention}\n> Kanal-ID:  `{channel.id}`",
                inline=False
            )
        else:
            embed.add_field(
                name="<:1041searchthreads:1467278040915771596> Log-Kanal",
                value="<:2533warning:1467278063002845184> Kanal nicht gefunden!",
                inline=False
            )
    else:
        embed.add_field(
            name="<:1041searchthreads:1467278040915771596> Log-Channel",
            value="<:3518crossmark:1467278065729146900> Nicht konfiguriert!`",
            inline=False
        )

    # 2. Rollenverbindungen
    connection_count = 0
    if guild_id in bot.config['role_connections'] and bot.config['role_connections'][guild_id]:
        connections_text = []
        for parent_id, child_ids in bot.config['role_connections'][guild_id].items():
            parent_role = interaction.guild.get_role(int(parent_id))
            if parent_role:
                connection_count += 1
                child_count = len(child_ids)
                if child_count > 0:
                    connections_text.append(f"**{parent_role.mention}** → {child_count} weitere Rolle{'n' if child_count > 1 else ''}")

        if connections_text:
            # Nur die ersten 100 anzeigen
            connections_display = "\n".join(connections_text[:100])
            if len(connections_text) > 100:
                connections_display += f"\n*... und {len(connections_text)-100} weitere*"

            embed.add_field(
                name=f"<:1198link:1467278050436710500> Rollenverbindungen ({connection_count})",
                value=connections_display,
                inline=False
            )
        else:
            embed.add_field(
                name="<:1198link:1467278050436710500> Rollenverbindungen",
                value="<:3518crossmark:1467278065729146900> Keine aktiven Verbindungen!",
                inline=False
            )
    else:
        embed.add_field(
            name="<:1198link:1467278050436710500> Rollenverbindungen",
            value="<:3518crossmark:1467278065729146900> Keine Verbindungen konfiguriert!",
            inline=False
        )

    # 3. Command-Berechtigungen
    permission_count = 0
    if guild_id in bot.config['command_permissions'] and bot.config['command_permissions'][guild_id]:
        perms_text = []
        for cmd_name, role_ids in bot.config['command_permissions'][guild_id].items():
            permission_count += 1
            roles = [interaction.guild.get_role(rid) for rid in role_ids]
            roles = [r for r in roles if r]
            if roles:
                role_mentions = ", ".join([r.mention for r in roles[:2]])
                if len(roles) > 2:
                    role_mentions += f" *(+{len(roles)-2})*"
                perms_text.append(f"`/{cmd_name}` → {role_mentions}")

        if perms_text:
            perms_display = "\n".join(perms_text[:5])
            if len(perms_text) > 5:
                perms_display += f"\n*... und {len(perms_text)-5} weitere*"

            embed.add_field(
                name=f"<:8586slashcommand:1467278119814692934> Command-Berechtigungen ({permission_count})",
                value=perms_display,
                inline=False
            )
        else:
            embed.add_field(
                name="<:8586slashcommand:1467278119814692934> Command-Berechtigungen",
                value="<:3518crossmark:1467278065729146900> Keine Berechtigungen gesetzt!",
                inline=False
            )
    else:
        embed.add_field(
            name="<:8586slashcommand:1467278119814692934> Command-Berechtigungen",
            value="<:3518crossmark:1467278065729146900> Keine Berechtigungen konfiguriert!",
            inline=False
        )

    # Statistiken
    total_roles = len(interaction.guild.roles) - 1
    total_members = interaction.guild.member_count

    stats = f"> Rollen: `{total_roles}`\n> Mitglieder: `{total_members}`\n> Verbindungen:  `{connection_count}`\n> Berechtigungen: `{permission_count}`"
    embed.add_field(
        name="<:4549activity:1467278075778699344> Statistiken",
        value=stats,
        inline=False
    )
    embed.set_image(url="https://media.discordapp.net/attachments/1451317020418117724/1467292124071596368/image.png?ex=697fd9c7&is=697e8847&hm=1d0d8fa95827221fe5cfc85de1d5bb90e5b704cd3f005fea087d7c81792b0113&=&format=webp&quality=lossless&width=1128&height=254")
    embed.set_footer(
        text="Custum Roles by Custom Discord Development",
        icon_url=bot.user.display_avatar.url
    )

    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="set_log_channel", description="Setzt den Log-Channel für Rollenaktionen")
@app_commands.describe(channel="Der Channel für Logs")
async def set_log_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    # Prüfe Berechtigung
    if not bot.has_default_permission(interaction.user):
        await interaction.response.send_message(
            "<:3518crossmark:1467278065729146900> Du hast keine Berechtigung für diesen Command!",
            ephemeral=True
        )
        return

    guild_id = str(interaction.guild_id)
    bot.config['log_channels'][guild_id] = channel.id
    bot.save_config()

    embed = discord.Embed(
        title="Log-Channel konfiguriert!",
        description=f"Alle Rollenaktionen werden nun in {channel.mention} geloggt.",
        color=discord.Color.from_str("#647be0")
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

    # Sende Test-Nachricht
    test_embed = discord.Embed(
        title="Log-System aktiviert!",
        description="Dieser Channel wird nun für Rollenlogs verwendet.",
        color=discord.Color.from_str("#647be0"),
        timestamp=datetime.utcnow()
    )
    test_embed.set_image(url="https://media.discordapp.net/attachments/1451317020418117724/1467295842628272401/image.png?ex=697fdd3d&is=697e8bbd&hm=826749579b2f4f8d5b96b815e2405c6e3a306edae1778798810cf284b92aeb8b&=&format=webp&quality=lossless&width=1128&height=254")
    test_embed.set_footer(
        text=f"Konfiguriert von {interaction.user.name}",
        icon_url=interaction.user.display_avatar.url
    )

    try:
        await channel.send(embed=test_embed)
    except:
        pass

@bot.tree.command(name="connect_roles", description="Verbindet bis zu 15 Rollen mit einer Parent-Rolle")
@app_commands.describe(
    parent="Die Parent-Rolle",
    child1="Child-Rolle 1",
    child2="Child-Rolle 2 (optional)",
    child3="Child-Rolle 3 (optional)",
    child4="Child-Rolle 4 (optional)",
    child5="Child-Rolle 5 (optional)",
    child6="Child-Rolle 6 (optional)",
    child7="Child-Rolle 7 (optional)",
    child8="Child-Rolle 8 (optional)",
    child9="Child-Rolle 9 (optional)",
    child10="Child-Rolle 10 (optional)",
    child11="Child-Rolle 11 (optional)",
    child12="Child-Rolle 12 (optional)",
    child13="Child-Rolle 13 (optional)",
    child14="Child-Rolle 14 (optional)",
    child15="Child-Rolle 15 (optional)"
)
async def connect_roles(
    interaction: discord.Interaction,
    parent: discord.Role,
    child1: discord.Role,
    child2: Optional[discord.Role] = None,
    child3: Optional[discord.Role] = None,
    child4: Optional[discord.Role] = None,
    child5: Optional[discord.Role] = None,
    child6: Optional[discord.Role] = None,
    child7: Optional[discord.Role] = None,
    child8: Optional[discord.Role] = None,
    child9: Optional[discord.Role] = None,
    child10: Optional[discord.Role] = None,
    child11: Optional[discord.Role] = None,
    child12: Optional[discord.Role] = None,
    child13: Optional[discord.Role] = None,
    child14: Optional[discord.Role] = None,
    child15: Optional[discord.Role] = None
):
    """Verbindet eine Parent-Rolle mit bis zu 15 Child-Rollen"""

    # Prüfe Berechtigung
    if not bot.has_default_permission(interaction.user):
        await interaction.response.send_message(
            "<:3518crossmark:1467278065729146900> Du hast keine Berechtigung für diesen Command!",
            ephemeral=True
        )
        return

    # Sammle alle Child-Rollen
    child_roles = [child1, child2, child3, child4, child5, child6, child7, child8, 
                   child9, child10, child11, child12, child13, child14, child15]
    child_roles = [r for r in child_roles if r is not None]

    # Entferne Duplikate
    unique_children = []
    seen_ids = set()
    for role in child_roles:
        if role.id not in seen_ids:
            unique_children.append(role)
            seen_ids.add(role.id)

    guild_id = str(interaction.guild_id)
    parent_id = str(parent.id)

    if guild_id not in bot.config['role_connections']:
        bot.config['role_connections'][guild_id] = {}

    # Speichere die Verbindungen
    bot.config['role_connections'][guild_id][parent_id] = [r.id for r in unique_children]
    bot.save_config()

    # Erstelle Response-Embed
    embed = discord.Embed(
        title="Rollenverbindungen erstellt!",
        description=f"**Hauptrolle:** {parent.mention}\n\n**Verbundene Rollen ({len(unique_children)}):**",
        color=discord.Color.from_str("#647be0")
    )

    roles_text = "\n".join([f"<:3518checkmark:1467278064340832513> {role.mention}" for role in unique_children])
    embed.add_field(
        name="Verbundene Rolle(n)",
        value=roles_text,
        inline=False
    )

    embed.add_field(
        name="Information",
        value="Wenn jemand die Hauptrolle erhält, bekommt er automatisch die `verbundene Rolle(n)`.",
        inline=False
    )
    embed.set_image(url="https://media.discordapp.net/attachments/1451317020418117724/1467472069330604187/image.png?ex=6980815d&is=697f2fdd&hm=3e2dcbd395cc5f56304d40ad75acbd4508082e75d6af5f06564c138db3604357&=&format=webp&quality=lossless&width=1125&height=256")

    await interaction.response.send_message(embed=embed, ephemeral=True)

    # Logge die Aktion
    await bot.log_action(
        interaction.guild,
        "Rollenverbindung erstellt",
        interaction.user,
        f"Parent: {parent.name} → {len(unique_children)} Child-Rolle(n)",
        moderator=interaction.user,
        roles=[parent] + unique_children
    )

@bot.tree.command(name="disconnect_roles", description="Entfernt eine Rollenverbindung")
@app_commands.describe(parent="Die Parent-Rolle deren Verbindungen entfernt werden sollen")
async def disconnect_roles(interaction: discord.Interaction, parent: discord.Role):
    """Entfernt alle Verbindungen einer Parent-Rolle"""

    # Prüfe Berechtigung
    if not bot.has_default_permission(interaction.user):
        await interaction.response.send_message(
            "<:3518crossmark:1467278065729146900> Du hast keine Berechtigung für diesen Command!",
            ephemeral=True
        )
        return

    guild_id = str(interaction.guild_id)
    parent_id = str(parent.id)

    if (guild_id in bot.config['role_connections'] and 
        parent_id in bot.config['role_connections'][guild_id]):

        child_ids = bot.config['role_connections'][guild_id][parent_id]
        child_roles = [interaction.guild.get_role(cid) for cid in child_ids]
        child_roles = [r for r in child_roles if r]

        del bot.config['role_connections'][guild_id][parent_id]
        bot.save_config()

        embed = discord.Embed(
            title="Rollenverbindungen entfernt!",
            description=f"Alle Verbindungen von {parent.mention} wurden entfernt.",
            color=discord.Color.from_str("#ff0000")
        )

        if child_roles:
            removed_text = "\n".join([f"<:3518crossmark:1467278065729146900> {r.mention}" for r in child_roles])
            embed.add_field(
                name=f"Entfernte Verbindungen ({len(child_roles)})",
                value=removed_text,
                inline=False
            )
        embed.set_image(url="https://media.discordapp.net/attachments/1451317020418117724/1467472069330604187/image.png?ex=6980815d&is=697f2fdd&hm=3e2dcbd395cc5f56304d40ad75acbd4508082e75d6af5f06564c138db3604357&=&format=webp&quality=lossless&width=1125&height=256")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

        await bot.log_action(
            interaction.guild,
            "Rollenverbindung gelöscht",
            interaction.user,
            f"Alle Verbindungen von '{parent.name}' wurden entfernt",
            moderator=interaction.user,
            roles=[parent]
        )
    else:
        await interaction.response.send_message(
            f"<:3518crossmark:1467278065729146900> {parent.mention} hat keine Verbindungen!",
            ephemeral=True
        )

@bot.tree.command(name="list_connections", description="Zeigt alle Rollenverbindungen")
async def list_connections(interaction: discord.Interaction):
    """Zeigt alle Rollenverbindungen"""
    # Prüfe Berechtigung
    if not bot.has_default_permission(interaction.user):
        await interaction.response.send_message(
            "<:3518crossmark:1467278065729146900> Du hast keine Berechtigung für diesen Command!",
            ephemeral=True
        )
        return

    guild_id = str(interaction.guild_id)

    if guild_id not in bot.config['role_connections'] or not bot.config['role_connections'][guild_id]:
        await interaction.response.send_message(
            "<:2533warning:1467278063002845184> Keine Rollenverbindungen konfiguriert!",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="Rollenverbindungen",
        description="Übersicht aller Parent → Child Verbindungen",
        color=discord.Color.from_str("#647be0"),
        timestamp=datetime.utcnow()
    )

    for parent_id, child_ids in bot.config['role_connections'][guild_id].items():
        parent_role = interaction.guild.get_role(int(parent_id))
        if parent_role:
            child_roles = [interaction.guild.get_role(cid) for cid in child_ids]
            child_roles = [r for r in child_roles if r]

            if child_roles:
                value_text = "\n".join([f"└─ {r.mention}" for r in child_roles])
                embed.add_field(
                    name=f"{parent_role.name} ({len(child_roles)})",
                    value=value_text,
                    inline=False
                )

    embed.set_footer(
        text=f"{len(bot.config['role_connections'][guild_id])} Verbindung(en)",
        icon_url=interaction.guild.icon.url if interaction.guild.icon else None
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="set_command_permission", description="Gibt einer Rolle Zugriff auf einen Command")
@app_commands.describe(
    command_name="Der Name des Commands (z.B. give_role)",
    role="Die Rolle die Zugriff bekommen soll"
)
async def set_command_permission(interaction: discord.Interaction, command_name: str, role: discord.Role):
    """Erlaubt einer Rolle die Nutzung eines Commands"""

    # Prüfe Berechtigung
    if not bot.has_default_permission(interaction.user):
        await interaction.response.send_message(
            "<:3518crossmark:1467278065729146900> Du hast keine Berechtigung für diesen Command!",
            ephemeral=True
        )
        return

    guild_id = str(interaction.guild_id)

    if guild_id not in bot.config['command_permissions']:
        bot.config['command_permissions'][guild_id] = {}

    if command_name not in bot.config['command_permissions'][guild_id]:
        bot.config['command_permissions'][guild_id][command_name] = []

    if role.id not in bot.config['command_permissions'][guild_id][command_name]:
        bot.config['command_permissions'][guild_id][command_name].append(role.id)
        bot.save_config()

        embed = discord.Embed(
            title="Berechtigung hinzugefügt!",
            description=f"{role.mention} kann nun `/{command_name}` verwenden.",
            color=discord.Color.from_str("#1eff00")
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(
            f"<:2533warning:1467278063002845184> {role.mention} hat bereits Zugriff auf `/{command_name}`!",
            ephemeral=True
        )

@bot.tree.command(name="remove_command_permission", description="Entfernt Command-Zugriff von einer Rolle")
@app_commands.describe(
    command_name="Der Name des Commands",
    role="Die Rolle"
)
async def remove_command_permission(interaction: discord.Interaction, command_name: str, role: discord.Role):
    """Entfernt Command-Berechtigung von einer Rolle"""

    # Prüfe Berechtigung
    if not bot.has_default_permission(interaction.user):
        await interaction.response.send_message(
            "<:3518crossmark:1467278065729146900> Du hast keine Berechtigung für diesen Command!",
            ephemeral=True
        )
        return

    guild_id = str(interaction.guild_id)

    if (guild_id in bot.config['command_permissions'] and
        command_name in bot.config['command_permissions'][guild_id] and
        role.id in bot.config['command_permissions'][guild_id][command_name]):

        bot.config['command_permissions'][guild_id][command_name].remove(role.id)
        bot.save_config()

        embed = discord.Embed(
            title="Berechtigung entfernt!",
            description=f"{role.mention} kann `/{command_name}` nicht mehr verwenden.",
            color=discord.Color.from_str("#ff0000")
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(
            f"<:3518crossmark:1467278065729146900> {role.mention} hat keinen Zugriff auf `/{command_name}`!",
            ephemeral=True
        )

@bot.tree.command(name="list_command_permissions", description="Zeigt alle Command-Berechtigungen")
async def list_command_permissions(interaction: discord.Interaction):
    """Zeigt alle Command-Berechtigungen"""

    # Prüfe Berechtigung
    if not bot.has_default_permission(interaction.user):
        await interaction.response.send_message(
            "<:3518crossmark:1467278065729146900> Du hast keine Berechtigung für diesen Command!",
            ephemeral=True
        )
        return

    guild_id = str(interaction.guild_id)

    if guild_id not in bot.config['command_permissions'] or not bot.config['command_permissions'][guild_id]:
        await interaction.response.send_message(
            "<:2533warning:1467278063002845184> Keine Command-Berechtigungen konfiguriert!",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="Command-Berechtigungen",
        description="Übersicht aller Rollen-basierten Berechtigungen",
        color=discord.Color.from_str("#647be0"),
        timestamp=datetime.utcnow()
    )

    for cmd_name, role_ids in bot.config['command_permissions'][guild_id].items():
        roles = [interaction.guild.get_role(rid) for rid in role_ids]
        roles = [r for r in roles if r]

        if roles:
            role_mentions = "\n".join([f"└─ {r.mention}" for r in roles])
            embed.add_field(
                name=f"/{cmd_name}",
                value=role_mentions,
                inline=False
            )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="give_role", description="Vergibt eine Rolle an einen Benutzer")
@app_commands.describe(member="Der Benutzer", role="Die Rolle")
async def give_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    # Prüfe Standard-Berechtigungen (Administrator oder Manage Roles)
    has_default = bot.has_default_permission(interaction.user)

    if not has_default:
        # Nur wenn keine Standard-Berechtigungen, prüfe spezielle Berechtigungen
        guild_id = str(interaction.guild_id)
        user_role_ids = [r.id for r in interaction.user.roles]
        has_permission = bot.check_command_permission(guild_id, "give_role", user_role_ids)

        if not has_permission:
            await interaction.response.send_message(
                "<:3518crossmark:1467278065729146900> Du hast keine Berechtigung für diesen Command!",
                ephemeral=True
            )
            return

    try:
        await member.add_roles(role, reason=f"Vergeben von {interaction.user.name}")

        embed = discord.Embed(
            title="Rolle vergeben!",
            description=f"{role.mention} wurde {member.mention} gegeben!",
            color=discord.Color.from_str("#1eff00")
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

        await bot.log_action(
            interaction.guild,
            "Rolle bekommen",
            member,
            f"Manuell vergeben",
            moderator=interaction.user,
            roles=[role]
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Fehler: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="remove_role", description="Entfernt eine Rolle von einem Benutzer")
@app_commands.describe(member="Der Benutzer", role="Die Rolle")
async def remove_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    # Prüfe Standard-Berechtigungen (Administrator oder Manage Roles)
    has_default = bot.has_default_permission(interaction.user)

    if not has_default:
        # Nur wenn keine Standard-Berechtigungen, prüfe spezielle Berechtigungen
        guild_id = str(interaction.guild_id)
        user_role_ids = [r.id for r in interaction.user.roles]
        has_permission = bot.check_command_permission(guild_id, "remove_role", user_role_ids)

        if not has_permission:
            await interaction.response.send_message(
                "<:3518crossmark:1467278065729146900> Du hast keine Berechtigung für diesen Command!",
                ephemeral=True
            )
            return

    try:
        await member.remove_roles(role, reason=f"Entfernt von {interaction.user.name}")

        embed = discord.Embed(
            title="Rolle entfernt!",
            description=f"{role.mention} wurde von {member.mention} entfernt!",
            color=discord.Color.from_str("#ff0000")
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

        await bot.log_action(
            interaction.guild,
            "Rolle entfernt",
            member,
            f"Manuell entfernt",
            moderator=interaction.user,
            roles=[role]
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Fehler: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="roleinfo", description="Zeigt Informationen über eine Rolle")
@app_commands.describe(role="Die Rolle")
async def role_info(interaction: discord.Interaction, role: discord.Role):
    # Prüfe Berechtigung
    if not bot.has_default_permission(interaction.user):
        await interaction.response.send_message(
            "<:3518crossmark:1467278065729146900> Du hast keine Berechtigung für diesen Command!",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="Rolleninformation",
        color=role.color if role.color != discord.Color.default() else discord.Color.from_str("#647be0"),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Rolle", value=f"{role.mention}", inline=True)
    embed.add_field(name="Rollen-ID", value=f"`{role.id}`", inline=True)
    embed.add_field(name="Farbe", value=f"`{role.color}`", inline=True)
    embed.add_field(name="Erwähnbar", value="<:3518checkmark:1467278064340832513> Aktiviert" if role.mentionable else "<:3518crossmark:1467278065729146900> Deaktiviert", inline=True)
    embed.add_field(name="Angeheftet", value="<:3518checkmark:1467278064340832513> Aktiviert" if role.hoist else "<:3518crossmark:1467278065729146900> Deaktiviert", inline=True)
    embed.add_field(name="Automatische Verwaltung", value="<:3518checkmark:1467278064340832513> Aktiviert" if role.is_bot_managed() else "<:3518crossmark:1467278065729146900> Deaktiviert", inline=True)
    embed.add_field(name="Position", value=f"`{role.position}`", inline=True)
    embed.add_field(name="Mitglieder", value=f"`{len(role.members)}`", inline=True)
    embed.add_field(name="Erstellt", value=f"<t:{int(role.created_at.timestamp())}:F>", inline=False)

    # Verbindungen prüfen
    guild_id = str(interaction.guild_id)
    if guild_id in bot.config['role_connections']:
        role_id = str(role.id)

        # Als Parent
        if role_id in bot.config['role_connections'][guild_id]:
            child_ids = bot.config['role_connections'][guild_id][role_id]
            child_roles = [interaction.guild.get_role(cid) for cid in child_ids]
            child_roles = [r for r in child_roles if r]
            if child_roles:
                embed.add_field(
                    name="Verbundene Rolle(n)",
                    value="\n".join([f"<:3518checkmark:1467278064340832513> {r.mention}" for r in child_roles[:10]]),
                    inline=False
                )

        # Als Child
        parent_roles = []
        for parent_id, child_ids in bot.config['role_connections'][guild_id].items():
            if role.id in child_ids:
                parent = interaction.guild.get_role(int(parent_id))
                if parent:
                    parent_roles.append(parent)

        if parent_roles:
            embed.add_field(
                name="Verbundene Rolle(n)",
                value="\n".join([f"<:3518checkmark:1467278064340832513> {r.mention}" for r in parent_roles]),
                inline=False
            )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="help", description="Zeigt alle Commands")
async def help_command(interaction: discord.Interaction):
    # Prüfe Berechtigung
    if not bot.has_default_permission(interaction.user):
        await interaction.response.send_message(
            "<:3518crossmark:1467278065729146900> Du hast keine Berechtigung für diesen Command!",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="Bot-Hilfe",
        description="> Hier sind alle Commands des Bots aufgelistet mit einer kleinen Beschreibung. Bitte beachte, dass der Bot sich noch in der Version `V1.1 Beta` befindet. Mögliche Probleme können jederzeit an <@1211683189186105434> gemeldet werden.",
        color=discord.Color.from_str("#647be0"),
        timestamp=datetime.utcnow()
    )

    commands_info = {
        "<:1041searchthreads:1467278040915771596> Konfiguration": [
            "`/config` - Zeigt die komplette Konfiguration",
            "`/set_log_channel` - Setzt den Log-Channel"
        ],
        "<:1198link:1467278050436710500> Rollenverbindungen": [
            "`/connect_roles` - Verbindet bis zu 15 Rollen",
            "`/disconnect_roles` - Entfernt Verbindungen",
            "`/list_connections` - Zeigt alle Verbindungen"
        ],
        "<:8586slashcommand:1467278119814692934> Berechtigungen": [
            "`/set_command_permission` - Gibt Rolle Command-Zugriff",
            "`/remove_command_permission` - Entfernt Command-Zugriff",
            "`/list_command_permissions` - Zeigt alle Berechtigungen"
        ],
        "<:4748ticket:1467278078672633967> Rollenverwaltung": [
            "`/give_role` - Vergibt eine Rolle",
            "`/remove_role` - Entfernt eine Rolle",
            "`/role_info` - Zeigt Rollendetails"
        ]
    }
    embed.set_image(url="https://media.discordapp.net/attachments/1451317020418117724/1467292284323369093/image.png?ex=697fd9ed&is=697e886d&hm=82f7142fc2c87850ca4cbca9debc4497fc6a37edf21276baee43caf09f1aac7b&=&format=webp&quality=lossless&width=1128&height=255")
    
    for category, commands in commands_info.items():
        embed.add_field(
            name=category,
            value="\n".join(commands),
            inline=False
        )

    embed.set_footer(
        text="Custum Roles by Custom Discord Development",
        icon_url=bot.user.display_avatar.url
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

if __name__ == "__main__":
    import sys

    token = os.getenv('DISCORD_TOKEN')

    if not token:
        print("Custum Roles ist online.")
        print("=" * 40)
        token = input("Bot-Token: ").strip()

    if not token:
        print("❌ Kein Token!")
        sys.exit(1)

    try:
        print("🚀 Starte Bot...")
        keep_alive()  # <-- DIESE ZEILE HINZUFÜGEN
        bot.run(token)
    except Exception as e:
        logger.error(f"❌ Fehler: {e}")
