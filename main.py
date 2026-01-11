import os
import random
import sqlite3
import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
from datetime import timedelta, datetime as dt, timezone
from discord.utils import utcnow
import asyncio
import re
from io import BytesIO
import aiohttp
import ast
import sys
import traceback
from contextlib import contextmanager
import math
from typing import Dict, List, Optional, Tuple, Any
from threading import Thread
import flask

# ---------- ENVIRONMENT ----------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "!")
COMBAT_DB_NAME = os.getenv("DB_PATH", "medieval_combat_enhanced.db")  # Configurable for Render persistent disk

# ---------- ROYAL SEAL IMAGE ----------
ROYAL_SEAL_URL = "https://imgs.search.brave.com/ybyUdUFEw0dNXKCLGu2FuNAlJpvCTxkjXZUxOSFKcMM/rs:fit:500:0:1:0/g:ce/aHR0cHM6Ly90aHVt/YnMuZHJlYW1zdGlt/ZS5jb20vYi9yb3lh/bC1kZWNyZWUtdW52/ZWlsZWQtZXhxdWlz/aXRlLWdvbGQtc2Vh/bC12aW50YWdlLXN0/YXRpb25lcnktaGFu/ZHdyaXR0ZW4tbGV0/dGVyLWV4cGxvcmUt/b3B1bGVuY2UtcmVn/YWwtc3RlcC1iYWNr/LTM1MTI2NjUwOC5q/cGc"

# ---------- BOT INITIALIZATION ----------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.moderation = True
intents.guilds = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None, case_insensitive=True)
tree = bot.tree

# ---------- DATABASE CONNECTION MANAGER ----------
@contextmanager
def get_combat_db_connection():
    """Context manager for combat database connections"""
    conn = None
    try:
        conn = sqlite3.connect(COMBAT_DB_NAME, timeout=10.0, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        print(f"Combat database error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

# ---------- ENHANCED MEDIEVAL FLAIR ----------
MEDIEVAL_COLORS = {
    "gold": discord.Colour.gold(),
    "silver": discord.Colour.light_grey(),
    "bronze": discord.Colour.dark_orange(),
    "red": discord.Colour.dark_red(),
    "green": discord.Colour.dark_green(),
    "blue": discord.Colour.dark_blue(),
    "purple": discord.Colour.purple(),
    "orange": discord.Colour.dark_orange(),
    "teal": discord.Colour.teal(),
    "blurple": discord.Colour.blurple(),
    "yellow": discord.Colour.yellow(),
    "dark_gray": discord.Colour.dark_gray(),
}

MEDIEVAL_PREFIXES = [
    "Hark!", "Verily,", "By mine honour,", "Prithee,", "Forsooth,", "Hear ye, hear ye!",
    "Lo and behold,", "By mine troth,", "Marry,", "Gadzooks!", "Zounds!", "By the saints,",
    "By my halidom,", "In faith,", "By my beard,", "By the rood,", "Alack,", "Alas,", "Fie!",
    "Good my lord,", "Noble sir,", "Fair lady,", "By the mass,", "Gramercy,", "Well met,",
    "God ye good den,", "What ho!", "Avaunt!", "By cock and pie,", "Odds bodikins!",
    "Methinks,", "Veritably,", "I prithee,", "By the gods!", "In sooth,",
]

# Enhanced descriptions with more variety
TRAINING_DESCRIPTIONS = [
    "The raw recruits endure rigorous sword drills beneath the watchful eye of veteran sergeants.",
    "In the training yards, recruits practice formation marching while sergeants bark orders.",
    "The clang of steel rings out as recruits learn the art of blade work from master-at-arms.",
    "Archery butts fill with arrows as recruits learn to draw the longbow with steady hands.",
    "Shield walls form and dissolve as soldiers learn to fight as one cohesive unit.",
    "The stench of sweat fills the barracks as recruits endure endless combat drills.",
    "Morning mist shrouds the parade ground where formations take shape with precision.",
    "Veteran knights share battle wisdom while recruits hang on every word of experience.",
    "Recruits stumble through mud and mire, learning the harsh realities of battlefield survival.",
    "The rhythm of marching feet echoes across the courtyard as new formations take shape.",
    "Weapon masters demonstrate lethal techniques to wide-eyed recruits.",
    "Tireless sergeants push recruits beyond their limits, forging warriors from common folk.",
]

WAR_CASUALTY_DESCRIPTIONS = [
    "The battlefield runs red with blood as arrows find their marks.",
    "Thunderous cavalry charges trample the fallen beneath iron-shod hooves.",
    "The screams of the dying mingle with the clash of steel as formations collapse.",
    "Smoke from burning siege towers chokes those who yet breathe on the blood-soaked field.",
    "The wounded crawl among the corpses, calling for mothers who shall never come.",
    "Carrion birds circle overhead as the ground becomes a feast for crows.",
    "The setting sun illuminates a field strewn with broken bodies and shattered shields.",
    "Even the victors weep at the cost, counting their dead among the heaps of fallen foes.",
    "Arrows fall like rain, finding gaps in armor and ending lives in an instant.",
    "The stench of death hangs heavy in the air as the battle rages on.",
    "Broken lances and shattered swords litter the ground where brave men fell.",
    "The lamentation of widows will be heard in villages across the land this night.",
]

BATTLE_VICTORY_DESCRIPTIONS = [
    "The enemy's banners fall as your forces claim the field in glorious victory!",
    "With a mighty roar, your army breaks the enemy lines and drives them from the field!",
    "The enemy commander surrenders his sword, acknowledging your superior tactics!",
    "Your knights charge through the enemy ranks, scattering them like leaves in a storm!",
    "The enemy retreats in disarray, leaving their dead and wounded upon the field!",
    "Your archers rain death upon the enemy until they can bear no more and flee!",
    "With a final push, your infantry breaks through and secures a hard-fought victory!",
]

BATTLE_DEFEAT_DESCRIPTIONS = [
    "The line breaks! Your forces retreat in disarray from the field of battle!",
    "Outmaneuvered and outflanked, your army suffers a crushing defeat!",
    "Your standard falls, and with it, the hopes of victory on this day!",
    "The enemy cavalry charges through your lines, scattering your forces!",
    "Your army breaks and runs, leaving honor and comrades upon the field!",
    "Overwhelmed by superior numbers, your forces are forced to withdraw!",
]

SIEGE_DESCRIPTIONS = [
    "The siege engines groan as they launch their deadly payloads against the walls.",
    "Mining operations proceed beneath the castle, seeking to undermine the foundations.",
    "Trebuchets launch massive stones that shatter against the castle's thick walls.",
    "Archers on the battlements exchange volleys with those on the ground below.",
    "Boiling oil pours from murder holes, creating a deadly barrier for attackers.",
    "The battering ram pounds against the gate, shaking the very foundations.",
    "Scaling ladders are raised against the walls as brave men risk everything.",
]

RAID_DESCRIPTIONS = [
    "Fast-moving raiders strike supply lines and disappear into the wilderness.",
    "Villages burn as raiders plunder and retreat before reinforcements arrive.",
    "Scouts report enemy movements, allowing for lightning strikes on vulnerable points.",
    "Supply wagons are ambushed, depriving the enemy of vital resources.",
    "Foragers are attacked, starving the enemy army of food and water.",
]

WEATHER_EFFECTS = {
    "Clear Skies": {"morale": 1.1, "visibility": 1.2, "movement": 1.1, "archery": 1.1},
    "Heavy Rain": {"morale": 0.9, "visibility": 0.7, "movement": 0.8, "archery": 0.6},
    "Foggy": {"morale": 0.95, "visibility": 0.5, "movement": 0.9, "archery": 0.7},
    "Stormy": {"morale": 0.8, "visibility": 0.6, "movement": 0.7, "archery": 0.5},
    "Snowstorm": {"morale": 0.7, "visibility": 0.4, "movement": 0.6, "archery": 0.4},
    "Light Rain": {"morale": 1.0, "visibility": 0.9, "movement": 0.95, "archery": 0.8},
    "Overcast": {"morale": 1.0, "visibility": 1.0, "movement": 1.0, "archery": 1.0},
}

TERRAIN_EFFECTS = {
    "Open Plains": {"defense": 1.0, "cavalry": 1.3, "archery": 1.2, "ambush": 0.5},
    "Dense Forest": {"defense": 1.2, "cavalry": 0.6, "archery": 0.7, "ambush": 1.5},
    "Rocky Mountains": {"defense": 1.4, "cavalry": 0.4, "archery": 0.8, "ambush": 1.3},
    "Swampy Marshlands": {"defense": 1.1, "cavalry": 0.3, "archery": 0.6, "ambush": 1.4},
    "Desert Wastes": {"defense": 0.9, "cavalry": 0.8, "archery": 0.9, "ambush": 0.7},
    "Frozen Tundra": {"defense": 1.0, "cavalry": 0.7, "archery": 0.8, "ambush": 0.8},
    "Hilly Highlands": {"defense": 1.3, "cavalry": 0.9, "archery": 1.1, "ambush": 1.2},
    "River Crossing": {"defense": 1.5, "cavalry": 0.5, "archery": 1.0, "ambush": 1.1},
    "Forest Hills": {"defense": 1.2, "cavalry": 0.7, "archery": 0.9, "ambush": 1.4},
    "Coastal Cliffs": {"defense": 1.6, "cavalry": 0.2, "archery": 1.3, "ambush": 1.0},
}

# Army types with different strengths
ARMY_TYPES = {
    "Infantry Heavy": {"infantry": 1.3, "cavalry": 0.8, "archers": 1.0, "siege": 0.9},
    "Cavalry Heavy": {"infantry": 0.8, "cavalry": 1.4, "archers": 0.9, "siege": 0.7},
    "Archer Heavy": {"infantry": 0.9, "cavalry": 0.9, "archers": 1.3, "siege": 1.0},
    "Balanced": {"infantry": 1.1, "cavalry": 1.1, "archers": 1.1, "siege": 1.1},
    "Siege Specialized": {"infantry": 1.0, "cavalry": 0.7, "archers": 1.0, "siege": 1.5},
    "Defensive": {"infantry": 1.4, "cavalry": 0.6, "archers": 1.2, "siege": 0.8},
}

def get_medieval_prefix():
    return random.choice(MEDIEVAL_PREFIXES)

def medieval_embed(title="", description="", color_name="gold", thumbnail_url=None, image_url=None):
    color = MEDIEVAL_COLORS.get(color_name, MEDIEVAL_COLORS["gold"])
    embed = discord.Embed(
        title=f"⚔️ {title}" if "⚔️" not in title else title,
        description=description,
        colour=color,
        timestamp=utcnow()
    )
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    else:
        embed.set_thumbnail(url=ROYAL_SEAL_URL)
    if image_url:
        embed.set_image(url=image_url)
    embed.set_footer(text="By royal decree of the combat arena")
    return embed

def medieval_response(message, success=True, extra="", title=""):
    prefix = get_medieval_prefix()
    color = "green" if success else "red"
    full_message = f"{prefix} {message}".strip().capitalize()
    if extra:
        full_message += f"\n\n{extra}"
    embed_title = "✅ Success!" if success and not title else "❌ Failure!" if not success and not title else title
    return medieval_embed(title=embed_title, description=full_message, color_name=color)

# ---------- ENHANCED COMBAT DATABASE ----------
def init_combat_db():
    """Initialize enhanced combat database with comprehensive systems"""
    try:
        with get_combat_db_connection() as db:
            # Combat roles registration
            db.execute("""
            CREATE TABLE IF NOT EXISTS combat_roles (
                guild_id INTEGER,
                role_id INTEGER,
                role_name TEXT,
                PRIMARY KEY (guild_id, role_id)
            )""")

            # Character stats and progression with expanded attributes
            db.execute("""
            CREATE TABLE IF NOT EXISTS combatants (
                user_id INTEGER,
                guild_id INTEGER,
                character_name TEXT,
                army_name TEXT,
                title TEXT DEFAULT 'Commander',
                faction TEXT DEFAULT 'Independent',
                level INTEGER DEFAULT 1,
                experience INTEGER DEFAULT 0,
                experience_needed INTEGER DEFAULT 100,
                stat_points INTEGER DEFAULT 5,
                strength INTEGER DEFAULT 5,
                agility INTEGER DEFAULT 5,
                intelligence INTEGER DEFAULT 5,
                vitality INTEGER DEFAULT 5,
                charisma INTEGER DEFAULT 5,
                luck INTEGER DEFAULT 5,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                total_kills INTEGER DEFAULT 0,
                total_deaths INTEGER DEFAULT 0,
                total_damage INTEGER DEFAULT 0,
                last_duel TIMESTAMP,
                last_recruitment TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                prestige INTEGER DEFAULT 0,
                achievements TEXT DEFAULT '[]',
                PRIMARY KEY (user_id, guild_id)
            )""")

            # Enhanced Army management system
            db.execute("""
            CREATE TABLE IF NOT EXISTS armies (
                user_id INTEGER,
                guild_id INTEGER,
                army_type TEXT DEFAULT 'Balanced',
                current_soldiers INTEGER DEFAULT 0,
                current_recruits INTEGER DEFAULT 0,
                max_soldiers INTEGER DEFAULT 500,
                max_recruits INTEGER DEFAULT 1000,
                tactical_points INTEGER DEFAULT 5,
                morale INTEGER DEFAULT 100,
                supplies INTEGER DEFAULT 100,
                terrain_advantage TEXT,
                weekly_recruitment_used INTEGER DEFAULT 0,
                total_knights INTEGER DEFAULT 0,
                total_archers INTEGER DEFAULT 0,
                total_cavalry INTEGER DEFAULT 0,
                total_siege INTEGER DEFAULT 0,
                recruitment_cooldown TIMESTAMP,
                last_supply_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                battle_formation TEXT DEFAULT 'Line',
                fortifications INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )""")

            # Training history with more detail
            db.execute("""
            CREATE TABLE IF NOT EXISTS training_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                soldiers_trained INTEGER,
                soldiers_deserted INTEGER,
                knights_gained INTEGER,
                archers_gained INTEGER,
                cavalry_gained INTEGER,
                siege_gained INTEGER,
                training_type TEXT,
                training_quality TEXT DEFAULT 'Normal',
                success_rate REAL,
                morale_change INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")

            # Comprehensive War casualties tracking
            db.execute("""
            CREATE TABLE IF NOT EXISTS war_casualties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                war_id INTEGER,
                user_id INTEGER,
                guild_id INTEGER,
                soldiers_lost INTEGER DEFAULT 0,
                knights_lost INTEGER DEFAULT 0,
                archers_lost INTEGER DEFAULT 0,
                cavalry_lost INTEGER DEFAULT 0,
                siege_lost INTEGER DEFAULT 0,
                deserters INTEGER DEFAULT 0,
                prisoners_taken INTEGER DEFAULT 0,
                supplies_lost INTEGER DEFAULT 0,
                morale_loss INTEGER DEFAULT 0,
                casualty_type TEXT,
                description TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")

            # Active duels with expanded tracking
            db.execute("""
            CREATE TABLE IF NOT EXISTS active_duels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                challenger_id INTEGER,
                defender_id INTEGER,
                turn INTEGER DEFAULT 1,
                current_turn_user INTEGER,
                challenger_hp INTEGER DEFAULT 100,
                defender_hp INTEGER DEFAULT 100,
                challenger_actions TEXT DEFAULT '[]',
                defender_actions TEXT DEFAULT '[]',
                status TEXT DEFAULT 'active',
                duel_type TEXT DEFAULT 'Honorable Duel',
                wager INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_action TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                round_timeout INTEGER DEFAULT 60
            )""")

            # Enhanced Faction wars with more details
            db.execute("""
            CREATE TABLE IF NOT EXISTS faction_wars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                war_name TEXT,
                war_type TEXT DEFAULT 'Field Battle',
                team_a_leader INTEGER,
                team_b_leader INTEGER,
                team_a_members TEXT,
                team_b_members TEXT,
                team_a_army_size INTEGER DEFAULT 0,
                team_b_army_size INTEGER DEFAULT 0,
                team_a_morale INTEGER DEFAULT 100,
                team_b_morale INTEGER DEFAULT 100,
                team_a_supplies INTEGER DEFAULT 100,
                team_b_supplies INTEGER DEFAULT 100,
                team_a_tactics INTEGER DEFAULT 0,
                team_b_tactics INTEGER DEFAULT 0,
                terrain TEXT,
                weather TEXT,
                turn INTEGER DEFAULT 1,
                current_team TEXT DEFAULT 'A',
                status TEXT DEFAULT 'preparing',
                war_score_a INTEGER DEFAULT 0,
                war_score_b INTEGER DEFAULT 0,
                objectives TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                ended_at TIMESTAMP,
                victory_conditions TEXT DEFAULT '{"type": "annihilation", "rounds": 10}'
            )""")

            # Comprehensive War actions
            db.execute("""
            CREATE TABLE IF NOT EXISTS war_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                war_id INTEGER,
                user_id INTEGER,
                guild_id INTEGER,
                action_type TEXT,
                target_team TEXT,
                army_size_used INTEGER,
                soldiers_lost INTEGER DEFAULT 0,
                knights_lost INTEGER DEFAULT 0,
                archers_lost INTEGER DEFAULT 0,
                cavalry_lost INTEGER DEFAULT 0,
                siege_lost INTEGER DEFAULT 0,
                deserters INTEGER DEFAULT 0,
                prisoners_taken INTEGER DEFAULT 0,
                supplies_captured INTEGER DEFAULT 0,
                tactical_bonus INTEGER,
                terrain_bonus INTEGER,
                weather_bonus INTEGER,
                morale_bonus INTEGER,
                total_damage INTEGER,
                description TEXT,
                critical_success BOOLEAN DEFAULT FALSE,
                critical_failure BOOLEAN DEFAULT FALSE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")

            # Battle formations table
            db.execute("""
            CREATE TABLE IF NOT EXISTS battle_formations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                formation_name TEXT,
                infantry_bonus REAL,
                cavalry_bonus REAL,
                archer_bonus REAL,
                defense_bonus REAL,
                movement_penalty REAL,
                description TEXT
            )""")

            # Siege equipment table
            db.execute("""
            CREATE TABLE IF NOT EXISTS siege_equipment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_name TEXT,
                cost INTEGER,
                attack_power INTEGER,
                defense_bonus INTEGER,
                siege_bonus REAL,
                description TEXT
            )""")

            # Achievements table
            db.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                achievement_name TEXT,
                description TEXT,
                requirement TEXT,
                reward INTEGER,
                category TEXT
            )""")

            # Insert default battle formations
            default_formations = [
                ("Line", 1.0, 0.8, 1.2, 0.9, 0.0, "Standard infantry line with archer support"),
                ("Phalanx", 1.3, 0.5, 0.7, 1.4, -0.2, "Dense spear formation, strong defense"),
                ("Wedge", 0.9, 1.4, 0.6, 0.8, 0.1, "Cavalry wedge formation for breaking lines"),
                ("Square", 1.1, 0.6, 1.0, 1.3, -0.3, "Defensive square against cavalry"),
                ("Skirmish", 0.8, 0.9, 1.3, 0.7, 0.2, "Loose formation for archers and skirmishers"),
                ("Column", 1.0, 1.1, 0.8, 0.8, 0.3, "Fast marching column"),
                ("Echelon", 1.1, 1.2, 0.9, 0.9, 0.0, "Staggered formation for flanking"),
                ("Tortoise", 1.2, 0.4, 0.5, 1.5, -0.4, "Testudo formation with overlapping shields"),
            ]
            
            db.executemany("""
            INSERT OR IGNORE INTO battle_formations 
            (formation_name, infantry_bonus, cavalry_bonus, archer_bonus, defense_bonus, movement_penalty, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, default_formations)

            # Insert default siege equipment
            default_siege = [
                ("Battering Ram", 500, 75, 10, 2.0, "Heavy wooden ram for breaking gates"),
                ("Trebuchet", 1500, 150, 5, 3.5, "Massive siege engine for wall destruction"),
                ("Catapult", 800, 100, 5, 2.5, "Medium siege engine for wall damage"),
                ("Siege Tower", 1200, 50, 20, 2.0, "Mobile tower for wall assault"),
                ("Mantlet", 300, 0, 30, 0.0, "Mobile shields for archer protection"),
                ("Ballista", 600, 80, 10, 1.5, "Giant crossbow for anti-personnel"),
                ("Petrary", 400, 60, 5, 1.8, "Small stone-throwing engine"),
            ]
            
            db.executemany("""
            INSERT OR IGNORE INTO siege_equipment 
            (equipment_name, cost, attack_power, defense_bonus, siege_bonus, description)
            VALUES (?, ?, ?, ?, ?, ?)
            """, default_siege)

            # Insert default achievements
            default_achievements = [
                ("First Blood", "Win your first duel", '{"wins": 1}', 100, "combat"),
                ("Battle-Hardened", "Win 10 duels", '{"wins": 10}', 500, "combat"),
                ("War Veteran", "Win 50 duels", '{"wins": 50}', 2000, "combat"),
                ("Army Builder", "Reach 1000 soldiers", '{"soldiers": 1000}', 800, "army"),
                ("Knight Commander", "Have 50 knights", '{"knights": 50}', 1500, "army"),
                ("Master Strategist", "Win 5 wars", '{"war_wins": 5}', 3000, "war"),
                ("Undefeated", "Win 10 duels without loss", '{"streak": 10}', 2500, "combat"),
                ("Recruitment King", "Recruit 5000 total soldiers", '{"total_recruits": 5000}', 1200, "army"),
                ("Fortress Builder", "Build 100 fortifications", '{"fortifications": 100}', 1800, "defense"),
                ("Hero of the Realm", "Reach level 50", '{"level": 50}', 5000, "progression"),
            ]
            
            db.executemany("""
            INSERT OR IGNORE INTO achievements 
            (achievement_name, description, requirement, reward, category)
            VALUES (?, ?, ?, ?, ?)
            """, default_achievements)

            db.commit()
            print("✅ Enhanced combat database with comprehensive systems initialized")
    except sqlite3.Error as e:
        print(f"❌ Enhanced combat database initialization error: {e}")
        traceback.print_exc()
        raise

# ---------- ENHANCED CHARACTER REGISTRATION ----------
class EnhancedRegistrationView(discord.ui.View):
    def __init__(self, user_id, guild_id):
        super().__init__(timeout=300.0)
        self.user_id = user_id
        self.guild_id = guild_id
        self.character_name = None
        self.army_name = None
        self.faction = None
        self.title = "Commander"

    @discord.ui.button(label="🗡️ Character Details", style=discord.ButtonStyle.blurple, emoji="⚔️")
    async def set_character_name(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This registration is not for thee!", ephemeral=True)

        await interaction.response.send_modal(EnhancedCharacterModal(self))

    @discord.ui.button(label="🏰 Army Details", style=discord.ButtonStyle.blurple, emoji="🏰")
    async def set_army_name(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This registration is not for thee!", ephemeral=True)

        await interaction.response.send_modal(EnhancedArmyModal(self))

    @discord.ui.button(label="✅ Complete", style=discord.ButtonStyle.green, emoji="✅")
    async def complete_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This registration is not for thee!", ephemeral=True)

        if not self.character_name or not self.army_name:
            return await interaction.response.send_message(
                "Thou must set both character and army details first!",
                ephemeral=True
            )

        # Create character and army
        try:
            with get_combat_db_connection() as db:
                # Create combatant with enhanced stats
                db.execute("""
                INSERT INTO combatants (user_id, guild_id, character_name, army_name, 
                faction, title, level, experience, experience_needed, stat_points, 
                strength, agility, intelligence, vitality, charisma, luck, wins, losses)
                VALUES (?, ?, ?, ?, ?, ?, 1, 0, 100, 5, 5, 5, 5, 5, 5, 5, 0, 0)
                """, (self.user_id, self.guild_id, self.character_name, self.army_name, 
                     self.faction or "Independent", self.title))

                # Create enhanced army
                db.execute("""
                INSERT INTO armies (user_id, guild_id, army_type, current_soldiers, current_recruits,
                max_soldiers, max_recruits, tactical_points, morale, supplies)
                VALUES (?, ?, 'Balanced', 0, 0, 500, 1000, 5, 100, 100)
                """, (self.user_id, self.guild_id))

                db.commit()

            embed = medieval_embed(
                title="🎖️ Registration Complete!",
                description=f"**{self.title} {self.character_name}** of the **{self.army_name}** has been registered!",
                color_name="green"
            )
            embed.add_field(name="Character", value=self.character_name, inline=True)
            embed.add_field(name="Title", value=self.title, inline=True)
            embed.add_field(name="Army", value=self.army_name, inline=True)
            if self.faction:
                embed.add_field(name="Faction", value=self.faction, inline=True)
            embed.add_field(name="Starting Status", 
                          value="⚔️ 0 Soldiers, 0 Recruits\n⚡ 5 Tactical Points\n❤️ 100 Morale\n📦 100 Supplies", 
                          inline=False)
            embed.add_field(name="Next Steps", 
                          value="Use `!recruit` to gain recruits\n`!train` to build your army\n`!stats` to view your progress",
                          inline=False)

            await interaction.response.send_message(embed=embed)
            self.stop()

        except sqlite3.IntegrityError:
            await interaction.response.send_message(
                "Thou art already registered in this realm!",
                ephemeral=True
            )
        except Exception as e:
            print(f"Registration error: {e}")
            traceback.print_exc()
            await interaction.response.send_message(
                "Error completing registration!", ephemeral=True
            )

class EnhancedCharacterModal(discord.ui.Modal, title="Character Details"):
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    name = discord.ui.TextInput(
        label="Character Name",
        placeholder="Enter your character's name...",
        min_length=2,
        max_length=30,
        required=True
    )

    title = discord.ui.TextInput(
        label="Title (Optional)",
        placeholder="e.g., Sir, Lord, Captain...",
        max_length=20,
        required=False
    )

    faction = discord.ui.TextInput(
        label="Faction (Optional)",
        placeholder="e.g., Kingdom of Valoria, Free Cities...",
        max_length=30,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        self.parent_view.character_name = str(self.name)
        self.parent_view.title = str(self.title) if self.title else "Commander"
        self.parent_view.faction = str(self.faction) if self.faction else None
        
        response = f"✅ Character details set:\n**Name:** {self.name}"
        if self.title:
            response += f"\n**Title:** {self.title}"
        if self.faction:
            response += f"\n**Faction:** {self.faction}"
            
        await interaction.response.send_message(response, ephemeral=True)

class EnhancedArmyModal(discord.ui.Modal, title="Army Details"):
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    name = discord.ui.TextInput(
        label="Army Name",
        placeholder="Enter your army's name...",
        min_length=2,
        max_length=40,
        required=True
    )

    motto = discord.ui.TextInput(
        label="Army Motto (Optional)",
        placeholder="e.g., For Glory! For Honor!",
        max_length=50,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        self.parent_view.army_name = str(self.name)
        
        response = f"✅ Army details set:\n**Name:** {self.name}"
        if self.motto:
            response += f"\n**Motto:** *{self.motto}*"
            
        await interaction.response.send_message(response, ephemeral=True)

# ---------- ENHANCED CHARACTER SYSTEM ----------
def get_enhanced_combatant(user_id, guild_id):
    """Get combatant character with enhanced army data"""
    try:
        with get_combat_db_connection() as db:
            result = db.execute("""
            SELECT c.*, a.army_type, a.current_soldiers, a.current_recruits, a.max_soldiers,
                   a.max_recruits, a.tactical_points, a.morale, a.supplies,
                   a.total_knights, a.total_archers, a.total_cavalry, a.total_siege,
                   a.fortifications, a.weekly_recruitment_used
            FROM combatants c
            LEFT JOIN armies a ON c.user_id = a.user_id AND c.guild_id = a.guild_id
            WHERE c.user_id=? AND c.guild_id=?
            """, (user_id, guild_id)).fetchone()

            return dict(result) if result else None
    except sqlite3.Error as e:
        print(f"Error getting enhanced combatant: {e}")
        return None

def update_combatant_stats(user_id, guild_id, **stats):
    """Update combatant stats with timestamp"""
    try:
        with get_combat_db_connection() as db:
            set_clause = ", ".join([f"{key}=?" for key in stats.keys()])
            values = list(stats.values()) + [user_id, guild_id]

            db.execute(f"""
            UPDATE combatants SET {set_clause}, last_active=? WHERE user_id=? AND guild_id=?
            """, values + [utcnow().isoformat()])
            db.commit()
    except Exception as e:
        print(f"Error updating combatant stats: {e}")

def add_experience(user_id, guild_id, exp, source="unknown"):
    """Add experience with scaling requirements and achievements"""
    try:
        combatant = get_enhanced_combatant(user_id, guild_id)
        if not combatant:
            return False, 0

        new_exp = combatant['experience'] + exp
        new_level = combatant['level']
        new_stat_points = combatant['stat_points']
        levels_gained = 0

        # Calculate XP needed for next level (scaling)
        while new_exp >= combatant['experience_needed']:
            new_exp -= combatant['experience_needed']
            new_level += 1
            levels_gained += 1
            new_stat_points += 3  # 3 stat points per level
            # Increase XP needed for next level
            new_xp_needed = int(100 * (1.7 ** (new_level - 1)))
            
            # Update XP needed
            update_combatant_stats(user_id, guild_id,
                                  level=new_level,
                                  stat_points=new_stat_points,
                                  experience_needed=new_xp_needed)
            
            # Check for level-based achievements
            check_achievements(user_id, guild_id)

        update_combatant_stats(user_id, guild_id,
                              experience=new_exp,
                              level=new_level,
                              stat_points=new_stat_points)

        # Record XP gain for tracking
        with get_combat_db_connection() as db:
            db.execute("""
            INSERT INTO xp_history (user_id, guild_id, amount, source, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """, (user_id, guild_id, exp, source, utcnow().isoformat()))
            db.commit()

        return levels_gained > 0, levels_gained

    except Exception as e:
        print(f"Error adding experience: {e}")
        return False, 0

# ---------- ENHANCED ARMY MANAGEMENT ----------
class ArmyManagementView(discord.ui.View):
    def __init__(self, user_id, guild_id):
        super().__init__(timeout=180.0)
        self.user_id = user_id
        self.guild_id = guild_id

    @discord.ui.button(label="📊 Army Status", style=discord.ButtonStyle.blurple, emoji="📊")
    async def army_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This menu is not for thee!", ephemeral=True)

        combatant = get_enhanced_combatant(self.user_id, self.guild_id)
        if not combatant:
            return await interaction.response.send_message("Thou art not registered!", ephemeral=True)

        embed = medieval_embed(
            title=f"🏰 {combatant['army_name']} Status",
            description=f"*Led by {combatant['title']} {combatant['character_name']}*",
            color_name="blue"
        )

        # Army composition
        embed.add_field(
            name="⚔️ Army Composition",
            value=f"**Soldiers:** {combatant['current_soldiers']:,}/{combatant['max_soldiers']:,}\n"
                  f"**Recruits:** {combatant['current_recruits']:,}/{combatant['max_recruits']:,}\n"
                  f"**Knights:** {combatant['total_knights']:,}\n"
                  f"**Archers:** {combatant['total_archers']:,}\n"
                  f"**Cavalry:** {combatant['total_cavalry']:,}\n"
                  f"**Siege:** {combatant['total_siege']:,}",
            inline=True
        )

        # Army stats
        embed.add_field(
            name="📈 Army Statistics",
            value=f"**Type:** {combatant['army_type']}\n"
                  f"**Morale:** {combatant['morale']}/100\n"
                  f"**Supplies:** {combatant['supplies']}/100\n"
                  f"**Tactical Points:** {combatant['tactical_points']}\n"
                  f"**Fortifications:** {combatant['fortifications']}",
            inline=True
        )

        # Army capabilities
        army_power = calculate_army_power(combatant)
        embed.add_field(
            name="⚡ Army Power",
            value=f"**Total Power:** {army_power['total']:,}\n"
                  f"**Infantry:** {army_power['infantry']:,}\n"
                  f"**Cavalry:** {army_power['cavalry']:,}\n"
                  f"**Archers:** {army_power['archers']:,}\n"
                  f"**Siege:** {army_power['siege']:,}",
            inline=False
        )

        # Current status effects
        status_effects = get_army_status_effects(self.user_id, self.guild_id)
        if status_effects:
            status_text = "\n".join([f"• {effect}" for effect in status_effects])
            embed.add_field(name="📋 Status Effects", value=status_text, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="⚔️ Change Formation", style=discord.ButtonStyle.blurple, emoji="⚔️")
    async def change_formation(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This menu is not for thee!", ephemeral=True)

        formations = get_available_formations()
        
        select = discord.ui.Select(
            placeholder="Choose a formation...",
            options=[
                discord.SelectOption(
                    label=form['name'],
                    value=form['name'],
                    description=form['description'][:50]
                ) for form in formations
            ]
        )
        
        async def formation_callback(interaction: discord.Interaction):
            await change_battle_formation(self.user_id, self.guild_id, select.values[0])
            await interaction.response.send_message(
                f"✅ Formation changed to **{select.values[0]}**!",
                ephemeral=True
            )
        
        select.callback = formation_callback
        view = discord.ui.View(timeout=60.0)
        view.add_item(select)
        
        await interaction.response.send_message(
            "Select a battle formation:", view=view, ephemeral=True
        )

    @discord.ui.button(label="🏗️ Build Fortifications", style=discord.ButtonStyle.green, emoji="🏗️")
    async def build_fortifications(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This menu is not for thee!", ephemeral=True)

        combatant = get_enhanced_combatant(self.user_id, self.guild_id)
        if not combatant:
            return await interaction.response.send_message("Thou art not registered!", ephemeral=True)

        # Check supplies
        if combatant['supplies'] < 20:
            return await interaction.response.send_message(
                "Thou needest at least 20 supplies to build fortifications!",
                ephemeral=True
            )

        success, message = build_fortification(self.user_id, self.guild_id)
        if success:
            await interaction.response.send_message(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    @discord.ui.button(label="🔄 Change Army Type", style=discord.ButtonStyle.blurple, emoji="🔄")
    async def change_army_type(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This menu is not for thee!", ephemeral=True)

        army_types = list(ARMY_TYPES.keys())
        
        select = discord.ui.Select(
            placeholder="Choose an army type...",
            options=[
                discord.SelectOption(
                    label=army_type,
                    value=army_type,
                    description=f"Specialization: {ARMY_TYPES[army_type]}"
                ) for army_type in army_types
            ]
        )
        
        async def type_callback(interaction: discord.Interaction):
            success, message = change_army_type(self.user_id, self.guild_id, select.values[0])
            await interaction.response.send_message(message, ephemeral=True)
        
        select.callback = type_callback
        view = discord.ui.View(timeout=60.0)
        view.add_item(select)
        
        await interaction.response.send_message(
            "Select an army type (costs 1 Tactical Point):", view=view, ephemeral=True
        )

def calculate_army_power(combatant):
    """Calculate comprehensive army power"""
    try:
        # Base calculations
        infantry_power = combatant['current_soldiers']
        knight_power = combatant['total_knights'] * 10  # Knights are worth 10 soldiers
        archer_power = combatant['total_archers'] * 3   # Archers have range advantage
        cavalry_power = combatant['total_cavalry'] * 8  # Cavalry has mobility advantage
        siege_power = combatant['total_siege'] * 15     # Siege equipment is powerful but slow
        
        # Apply army type bonuses
        army_type = combatant.get('army_type', 'Balanced')
        bonuses = ARMY_TYPES.get(army_type, ARMY_TYPES['Balanced'])
        
        total_power = (
            infantry_power * bonuses['infantry'] +
            knight_power * bonuses['infantry'] +  # Knights count as infantry for type bonuses
            archer_power * bonuses['archers'] +
            cavalry_power * bonuses['cavalry'] +
            siege_power * bonuses['siege']
        )
        
        # Apply morale bonus/penalty
        morale = combatant.get('morale', 100)
        morale_multiplier = 0.5 + (morale / 100) * 0.5  # 0.75x to 1.25x
        
        total_power = int(total_power * morale_multiplier)
        
        return {
            'total': total_power,
            'infantry': int(infantry_power * bonuses['infantry']),
            'knights': int(knight_power * bonuses['infantry']),
            'archers': int(archer_power * bonuses['archers']),
            'cavalry': int(cavalry_power * bonuses['cavalry']),
            'siege': int(siege_power * bonuses['siege']),
            'morale_multiplier': morale_multiplier
        }
        
    except Exception as e:
        print(f"Error calculating army power: {e}")
        return {'total': 0, 'infantry': 0, 'knights': 0, 'archers': 0, 'cavalry': 0, 'siege': 0, 'morale_multiplier': 1.0}

def get_available_formations():
    """Get list of available battle formations"""
    try:
        with get_combat_db_connection() as db:
            formations = db.execute("""
            SELECT formation_name, infantry_bonus, cavalry_bonus, archer_bonus, 
                   defense_bonus, movement_penalty, description 
            FROM battle_formations
            """).fetchall()
            
            return [
                {
                    'name': row['formation_name'],
                    'infantry_bonus': row['infantry_bonus'],
                    'cavalry_bonus': row['cavalry_bonus'],
                    'archer_bonus': row['archer_bonus'],
                    'defense_bonus': row['defense_bonus'],
                    'movement_penalty': row['movement_penalty'],
                    'description': row['description']
                }
                for row in formations
            ]
    except Exception as e:
        print(f"Error getting formations: {e}")
        return []

def change_battle_formation(user_id, guild_id, formation_name):
    """Change army battle formation"""
    try:
        with get_combat_db_connection() as db:
            # Get formation details
            formation = db.execute("""
            SELECT * FROM battle_formations WHERE formation_name=?
            """, (formation_name,)).fetchone()
            
            if not formation:
                return False, "Formation not found!"
            
            # Update army formation
            db.execute("""
            UPDATE armies SET battle_formation=? WHERE user_id=? AND guild_id=?
            """, (formation_name, user_id, guild_id))
            db.commit()
            
            return True, f"Formation changed to **{formation_name}**!\n*{formation['description']}*"
            
    except Exception as e:
        print(f"Error changing formation: {e}")
        return False, "Error changing formation!"

def build_fortification(user_id, guild_id):
    """Build fortifications for defense"""
    try:
        with get_combat_db_connection() as db:
            # Get current army status
            army = db.execute("""
            SELECT supplies, fortifications FROM armies WHERE user_id=? AND guild_id=?
            """, (user_id, guild_id)).fetchone()
            
            if not army:
                return False, "Army not found!"
            
            # Check supplies
            if army['supplies'] < 20:
                return False, "Insufficient supplies! Need at least 20."
            
            # Calculate fortification cost and benefit
            fortification_cost = 20
            fortification_bonus = random.randint(3, 7)
            new_fortifications = army['fortifications'] + fortification_bonus
            new_supplies = army['supplies'] - fortification_cost
            
            # Update army
            db.execute("""
            UPDATE armies 
            SET fortifications=?, supplies=?
            WHERE user_id=? AND guild_id=?
            """, (new_fortifications, new_supplies, user_id, guild_id))
            
            # Record fortification building
            db.execute("""
            INSERT INTO fortification_history (user_id, guild_id, fortifications_built, supplies_used)
            VALUES (?, ?, ?, ?)
            """, (user_id, guild_id, fortification_bonus, fortification_cost))
            
            db.commit()
            
            return True, (
                f"🏗️ **Fortifications Built!** 🏗️\n\n"
                f"Thy engineers have constructed new defenses!\n"
                f"**+{fortification_bonus}** fortifications built\n"
                f"**-{fortification_cost}** supplies used\n\n"
                f"**Total Fortifications:** {new_fortifications}\n"
                f"**Remaining Supplies:** {new_supplies}"
            )
            
    except Exception as e:
        print(f"Error building fortifications: {e}")
        return False, "Error building fortifications!"

def change_army_type(user_id, guild_id, new_type):
    """Change army type specialization"""
    try:
        with get_combat_db_connection() as db:
            # Get current army
            army = db.execute("""
            SELECT tactical_points FROM armies WHERE user_id=? AND guild_id=?
            """, (user_id, guild_id)).fetchone()
            
            if not army:
                return False, "Army not found!"
            
            # Check tactical points
            if army['tactical_points'] < 1:
                return False, "Insufficient tactical points! Need at least 1."
            
            # Validate army type
            if new_type not in ARMY_TYPES:
                return False, f"Invalid army type! Choose from: {', '.join(ARMY_TYPES.keys())}"
            
            # Update army
            new_tactical_points = army['tactical_points'] - 1
            db.execute("""
            UPDATE armies 
            SET army_type=?, tactical_points=?
            WHERE user_id=? AND guild_id=?
            """, (new_type, new_tactical_points, user_id, guild_id))
            
            db.commit()
            
            bonuses = ARMY_TYPES[new_type]
            return True, (
                f"🔄 **Army Type Changed!** 🔄\n\n"
                f"Thy army is now specialized as **{new_type}**!\n"
                f"**Bonuses:**\n"
                f"• Infantry: {bonuses['infantry']}x\n"
                f"• Cavalry: {bonuses['cavalry']}x\n"
                f"• Archers: {bonuses['archers']}x\n"
                f"• Siege: {bonuses['siege']}x\n\n"
                f"**Remaining Tactical Points:** {new_tactical_points}"
            )
            
    except Exception as e:
        print(f"Error changing army type: {e}")
        return False, "Error changing army type!"

def get_army_status_effects(user_id, guild_id):
    """Get current status effects on army"""
    try:
        combatant = get_enhanced_combatant(user_id, guild_id)
        if not combatant:
            return []
        
        status_effects = []
        
        # Check morale effects
        morale = combatant['morale']
        if morale >= 90:
            status_effects.append("🎖️ **High Morale**: +15% effectiveness")
        elif morale >= 70:
            status_effects.append("✅ **Good Morale**: +5% effectiveness")
        elif morale <= 30:
            status_effects.append("⚠️ **Low Morale**: -20% effectiveness")
        elif morale <= 50:
            status_effects.append("⚠️ **Poor Morale**: -10% effectiveness")
        
        # Check supplies effects
        supplies = combatant['supplies']
        if supplies <= 20:
            status_effects.append("⚠️ **Low Supplies**: -15% effectiveness, desertion risk")
        elif supplies <= 50:
            status_effects.append("⚠️ **Limited Supplies**: -5% effectiveness")
        
        # Check fortifications
        fortifications = combatant['fortifications']
        if fortifications >= 50:
            status_effects.append(f"🛡️ **Strong Fortifications**: +{fortifications//10}% defense")
        elif fortifications >= 20:
            status_effects.append(f"🛡️ **Fortified**: +{fortifications//20}% defense")
        
        # Check army type bonuses
        army_type = combatant['army_type']
        bonuses = ARMY_TYPES.get(army_type, ARMY_TYPES['Balanced'])
        if army_type != 'Balanced':
            strongest = max(bonuses, key=bonuses.get)
            status_effects.append(f"⚡ **{army_type}**: {bonuses[strongest]}x {strongest}")
        
        return status_effects
        
    except Exception as e:
        print(f"Error getting status effects: {e}")
        return []

# ---------- ENHANCED RECRUITMENT & TRAINING ----------
def enhanced_can_recruit_army(user_id, guild_id):
    """Enhanced recruitment eligibility check"""
    try:
        with get_combat_db_connection() as db:
            army = db.execute("""
            SELECT weekly_recruitment_used, recruitment_cooldown, morale, supplies
            FROM armies WHERE user_id=? AND guild_id=?
            """, (user_id, guild_id)).fetchone()

            if not army:
                return False, "No army found"

            # Check weekly recruitment limit
            if army['weekly_recruitment_used'] >= 700:
                return False, "Weekly recruitment limit reached"

            # Check morale for recruitment
            if army['morale'] < 30:
                return False, "Morale too low for recruitment (need at least 30)"

            # Check supplies for recruitment
            if army['supplies'] < 10:
                return False, "Insufficient supplies for recruitment (need at least 10)"

            # Check if new week has started
            if army['recruitment_cooldown']:
                cooldown_time = dt.fromisoformat(army['recruitment_cooldown'])
                if utcnow() >= cooldown_time:
                    # Reset weekly recruitment
                    db.execute("""
                    UPDATE armies SET weekly_recruitment_used=0, recruitment_cooldown=NULL
                    WHERE user_id=? AND guild_id=?
                    """, (user_id, guild_id))
                    db.commit()
                    return True, "New week started - recruitment reset!"

            return True, "Ready to recruit"
    except Exception as e:
        print(f"Error checking enhanced recruitment: {e}")
        return False, "Error checking recruitment"

def enhanced_recruit_soldiers(user_id, guild_id):
    """Enhanced randomized recruitment system with supply costs"""
    try:
        with get_combat_db_connection() as db:
            army = db.execute("""
            SELECT current_recruits, max_recruits, weekly_recruitment_used, morale, supplies
            FROM armies WHERE user_id=? AND guild_id=?
            """, (user_id, guild_id)).fetchone()

            if not army:
                return False, "No army found"

            # Generate random recruitment amount with morale modifier
            base_recruit_amount = generate_random_recruits()
            morale_modifier = army['morale'] / 100  # 0.3 to 1.0 range
            recruit_amount = int(base_recruit_amount * morale_modifier)
            
            # Calculate supply cost (1 supply per 10 recruits)
            supply_cost = max(1, recruit_amount // 10)

            # Check limits
            current_used = army['weekly_recruitment_used']
            current_recruits = army['current_recruits']
            max_recruits = army['max_recruits']
            current_supplies = army['supplies']

            if current_used + recruit_amount > 700:
                remaining_quota = 700 - current_used
                return False, f"Can only recruit {remaining_quota} more this week!"

            if current_recruits + recruit_amount > max_recruits:
                available_space = max_recruits - current_recruits
                return False, f"Recruit capacity full! Can only recruit {available_space} more!"

            if current_supplies < supply_cost:
                return False, f"Insufficient supplies! Need {supply_cost}, have {current_supplies}"

            # Update army with new recruits
            new_recruits = current_recruits + recruit_amount
            new_weekly_used = current_used + recruit_amount
            new_supplies = current_supplies - supply_cost

            db.execute("""
            UPDATE armies
            SET current_recruits=?, weekly_recruitment_used=?, supplies=?,
                recruitment_cooldown=?, morale=GREATEST(1, morale - 1)
            WHERE user_id=? AND guild_id=?
            """, (new_recruits, new_weekly_used, new_supplies,
                  (utcnow() + timedelta(days=7)).isoformat(), user_id, guild_id))
            db.commit()

            return True, (
                f"✅ **Recruitment Successful!** ✅\n\n"
                f"**{recruit_amount}** raw recruits have joined thy ranks!\n"
                f"*(Base: {base_recruit_amount}, Morale modifier: {morale_modifier:.2f}x)*\n\n"
                f"**Cost:** {supply_cost} supplies\n"
                f"**New Total:** {new_recruits} recruits awaiting training\n"
                f"**Remaining Supplies:** {new_supplies}\n"
                f"**Weekly Quota Used:** {new_weekly_used}/700"
            )
    except Exception as e:
        print(f"Error in enhanced recruitment: {e}")
        return False, "Error recruiting soldiers"

def enhanced_train_soldiers(user_id, guild_id, train_amount):
    """Enhanced training system with multiple unit types"""
    try:
        with get_combat_db_connection() as db:
            army = db.execute("""
            SELECT current_recruits, current_soldiers, max_soldiers, total_knights,
                   total_archers, total_cavalry, total_siege, morale, supplies,
                   army_type
            FROM armies WHERE user_id=? AND guild_id=?
            """, (user_id, guild_id)).fetchone()

            if not army:
                return False, "No army found"

            current_recruits = army['current_recruits']
            current_soldiers = army['current_soldiers']
            max_soldiers = army['max_soldiers']
            current_supplies = army['supplies']
            army_type = army['army_type']

            # Validate training amount
            if train_amount <= 0:
                return False, "Must train a positive number of recruits!"

            if train_amount > current_recruits:
                return False, f"Thou only hast {current_recruits} recruits to train!"

            # Calculate supply cost (1 supply per 5 recruits trained)
            supply_cost = max(1, train_amount // 5)
            if current_supplies < supply_cost:
                return False, f"Insufficient supplies! Need {supply_cost}, have {current_supplies}"

            # Enhanced desertion calculation with morale effect
            base_desertion_rate = 0.01  # 1% base desertion
            morale_modifier = (100 - army['morale']) / 200  # Up to 0.35 extra desertion
            total_desertion_chance = min(0.3, base_desertion_rate + morale_modifier)
            
            soldiers_deserted = 0
            for _ in range(train_amount):
                if random.random() < total_desertion_chance:
                    soldiers_deserted += 1

            # Calculate unit type distribution based on army type
            unit_types = distribute_unit_types(train_amount - soldiers_deserted, army_type)
            
            # Calculate final trained soldiers
            soldiers_trained = max(0, train_amount - soldiers_deserted)

            # Check soldier capacity
            if current_soldiers + soldiers_trained > max_soldiers:
                available_space = max_soldiers - current_soldiers
                if available_space <= 0:
                    return False, "Soldier capacity full! Cannot train more soldiers!"

                # Adjust training to fit capacity
                soldiers_trained = available_space
                soldiers_deserted = train_amount - soldiers_trained

            # Update army with new units
            new_recruits = current_recruits - train_amount
            new_soldiers = current_soldiers + unit_types['infantry']
            new_knights = army['total_knights'] + unit_types['knights']
            new_archers = army['total_archers'] + unit_types['archers']
            new_cavalry = army['total_cavalry'] + unit_types['cavalry']
            new_siege = army['total_siege'] + unit_types['siege']
            new_supplies = current_supplies - supply_cost
            
            # Morale change from training
            morale_change = 2  # Training boosts morale
            new_morale = min(100, army['morale'] + morale_change)

            db.execute("""
            UPDATE armies
            SET current_recruits=?, current_soldiers=?, total_knights=?,
                total_archers=?, total_cavalry=?, total_siege=?,
                supplies=?, morale=?
            WHERE user_id=? AND guild_id=?
            """, (new_recruits, new_soldiers, new_knights, new_archers, 
                  new_cavalry, new_siege, new_supplies, new_morale, user_id, guild_id))

            # Record training history
            db.execute("""
            INSERT INTO training_history (user_id, guild_id, soldiers_trained, 
                                        soldiers_deserted, knights_gained, archers_gained,
                                        cavalry_gained, siege_gained, training_type,
                                        training_quality, success_rate, morale_change)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, guild_id, soldiers_trained, soldiers_deserted,
                  unit_types['knights'], unit_types['archers'], unit_types['cavalry'],
                  unit_types['siege'], "enhanced", "Normal",
                  ((soldiers_trained)/train_amount)*100 if train_amount > 0 else 0,
                  morale_change))

            db.commit()

            # Build response message
            message = f"⚔️ **Enhanced Training Complete** ⚔️\n\n"
            message += f"**{train_amount}** recruits underwent rigorous training.\n\n"
            
            if soldiers_deserted > 0:
                message += f"⚠️ **{soldiers_deserted}** recruits deserted during training.\n"
            
            message += f"\n**New Units Trained:**\n"
            if unit_types['infantry'] > 0:
                message += f"• **{unit_types['infantry']}** infantry soldiers\n"
            if unit_types['knights'] > 0:
                message += f"• **{unit_types['knights']}** knights 🛡️\n"
            if unit_types['archers'] > 0:
                message += f"• **{unit_types['archers']}** archers 🏹\n"
            if unit_types['cavalry'] > 0:
                message += f"• **{unit_types['cavalry']}** cavalry 🐎\n"
            if unit_types['siege'] > 0:
                message += f"• **{unit_types['siege']}** siege equipment 🏗️\n"
            
            message += f"\n**Cost:** {supply_cost} supplies\n"
            message += f"**Morale:** +{morale_change} (now {new_morale}/100)\n"
            
            message += f"\n**Current Status:**\n"
            message += f"Recruits: **{new_recruits}**\n"
            message += f"Soldiers: **{new_soldiers}**\n"
            message += f"Knights: **{new_knights}**\n"
            message += f"Archers: **{new_archers}**\n"
            message += f"Cavalry: **{new_cavalry}**\n"
            message += f"Siege: **{new_siege}**\n"
            message += f"Supplies: **{new_supplies}**"

            return True, message

    except Exception as e:
        print(f"Error in enhanced training: {e}")
        traceback.print_exc()
        return False, "Error during training!"

def distribute_unit_types(total_recruits, army_type):
    """Distribute recruits into different unit types based on army specialization"""
    unit_types = {
        'infantry': 0,
        'knights': 0,
        'archers': 0,
        'cavalry': 0,
        'siege': 0
    }
    
    if total_recruits <= 0:
        return unit_types
    
    # Get army type bonuses
    bonuses = ARMY_TYPES.get(army_type, ARMY_TYPES['Balanced'])
    
    # Calculate distribution probabilities based on army type
    base_distribution = {
        'infantry': 0.7,  # 70% infantry by default
        'knights': 0.02,  # 2% knights (rare)
        'archers': 0.15,  # 15% archers
        'cavalry': 0.10,  # 10% cavalry
        'siege': 0.03     # 3% siege equipment
    }
    
    # Adjust based on army type bonuses
    for unit_type in base_distribution:
        if unit_type in bonuses:
            # Increase probability for specialized units
            base_distribution[unit_type] *= bonuses[unit_type]
    
    # Normalize probabilities
    total_prob = sum(base_distribution.values())
    for unit_type in base_distribution:
        base_distribution[unit_type] /= total_prob
    
    # Distribute recruits
    remaining = total_recruits
    for unit_type, probability in base_distribution.items():
        if remaining <= 0:
            break
            
        # Calculate number for this unit type
        count = int(remaining * probability)
        if count < 0:
            count = 0
            
        # Ensure we don't exceed remaining
        count = min(count, remaining)
        unit_types[unit_type] = count
        remaining -= count
    
    # Distribute any remaining recruits to infantry
    if remaining > 0:
        unit_types['infantry'] += remaining
    
    return unit_types

def check_achievements(user_id, guild_id):
    """Check and award achievements"""
    try:
        combatant = get_enhanced_combatant(user_id, guild_id)
        if not combatant:
            return []
        
        with get_combat_db_connection() as db:
            # Get all achievements
            achievements = db.execute("""
            SELECT * FROM achievements
            """).fetchall()
            
            # Get current achievements
            current_achievements = eval(combatant['achievements'])
            
            new_achievements = []
            for achievement in achievements:
                if achievement['achievement_name'] in current_achievements:
                    continue
                
                # Check requirements
                requirements = eval(achievement['requirement'])
                meets_requirements = True
                
                for req_key, req_value in requirements.items():
                    if req_key == 'wins':
                        if combatant['wins'] < req_value:
                            meets_requirements = False
                            break
                    elif req_key == 'soldiers':
                        if combatant['current_soldiers'] < req_value:
                            meets_requirements = False
                            break
                    elif req_key == 'knights':
                        if combatant['total_knights'] < req_value:
                            meets_requirements = False
                            break
                    elif req_key == 'level':
                        if combatant['level'] < req_value:
                            meets_requirements = False
                            break
                    elif req_key == 'streak':
                        # This would need streak tracking
                        pass
                    elif req_key == 'war_wins':
                        # This would need war win tracking
                        pass
                    elif req_key == 'total_recruits':
                        # This would need total recruit tracking
                        pass
                    elif req_key == 'fortifications':
                        if combatant['fortifications'] < req_value:
                            meets_requirements = False
                            break
                
                if meets_requirements:
                    # Award achievement
                    current_achievements.append(achievement['achievement_name'])
                    
                    # Add reward to prestige
                    new_prestige = combatant['prestige'] + achievement['reward']
                    update_combatant_stats(user_id, guild_id,
                                         achievements=str(current_achievements),
                                         prestige=new_prestige)
                    
                    new_achievements.append({
                        'name': achievement['achievement_name'],
                        'description': achievement['description'],
                        'reward': achievement['reward']
                    })
            
            return new_achievements
            
    except Exception as e:
        print(f"Error checking achievements: {e}")
        return []

# ---------- ENHANCED COMBAT CALCULATIONS ----------
def calculate_enhanced_damage(attacker, defender, action_type, terrain="Open Plains", weather="Clear Skies"):
    """Calculate enhanced combat damage with terrain and weather effects"""
    try:
        # Get terrain and weather effects
        terrain_effects = TERRAIN_EFFECTS.get(terrain, TERRAIN_EFFECTS["Open Plains"])
        weather_effects = WEATHER_EFFECTS.get(weather, WEATHER_EFFECTS["Clear Skies"])
        
        # Include all unit types in combat calculations
        knight_bonus = attacker.get('total_knights', 0) * 3  # Knights are elite
        archer_bonus = attacker.get('total_archers', 0) * 2  # Archers provide ranged support
        cavalry_bonus = attacker.get('total_cavalry', 0) * 2.5  # Cavalry are fast and powerful
        siege_bonus = attacker.get('total_siege', 0) * 4  # Siege equipment is devastating
        
        # Base damage calculation
        base_damage = random.randint(15, 35)
        
        # Action type modifiers
        action_modifiers = {
            "power_strike": {"stat": 'strength', "multiplier": 2.2, "terrain": 'infantry'},
            "magic_bolt": {"stat": 'intelligence', "multiplier": 2.8, "terrain": 'archery'},
            "quick_strike": {"stat": 'agility', "multiplier": 2.0, "terrain": 'cavalry'},
            "cavalry_charge": {"stat": 'strength', "multiplier": 2.5, "terrain": 'cavalry'},
            "archer_volley": {"stat": 'agility', "multiplier": 2.3, "terrain": 'archery'},
            "shield_wall": {"stat": 'vitality', "multiplier": 1.5, "terrain": 'defense'},
            "flanking_maneuver": {"stat": 'agility', "multiplier": 2.1, "terrain": 'cavalry'},
        }
        
        action_info = action_modifiers.get(action_type, action_modifiers["power_strike"])
        
        # Calculate stat bonus with unit contributions
        if action_info['terrain'] == 'infantry':
            unit_bonus = knight_bonus
        elif action_info['terrain'] == 'archery':
            unit_bonus = archer_bonus
        elif action_info['terrain'] == 'cavalry':
            unit_bonus = cavalry_bonus
        else:
            unit_bonus = knight_bonus + archer_bonus
        
        stat_bonus = (attacker[action_info['stat']] + unit_bonus) * action_info['multiplier']
        
        # Calculate defense
        defense_stat = 'vitality' if action_type != "magic_bolt" else 'intelligence'
        defense_bonus = defender[defense_stat] * 1.8
        
        # Apply terrain bonus to attack/defense
        terrain_bonus = terrain_effects.get(action_info['terrain'], 1.0)
        stat_bonus *= terrain_bonus
        
        # Apply weather effects
        weather_multiplier = weather_effects.get('morale', 1.0) * weather_effects.get('archery', 1.0)
        stat_bonus *= weather_multiplier
        
        # Calculate final damage
        damage = max(5, int((base_damage + stat_bonus - defense_bonus) * random.uniform(0.7, 1.3)))
        
        # Critical hit chance (based on luck + agility + knights)
        total_crit_chance = (attacker['agility'] + attacker['luck'] + (attacker.get('total_knights', 0) // 10)) * 0.005
        if random.random() < total_crit_chance:
            damage = int(damage * random.uniform(1.5, 2.5))
            return damage, True  # Return damage and critical flag
        
        return damage, False
        
    except Exception as e:
        print(f"Error calculating enhanced damage: {e}")
        return random.randint(10, 25), False

def calculate_supply_consumption(army_size, days=1):
    """Calculate daily supply consumption for army"""
    base_consumption = army_size * 0.01  # 1% of army size per day
    return int(base_consumption * days)

def update_army_supplies(user_id, guild_id):
    """Update army supplies with consumption"""
    try:
        with get_combat_db_connection() as db:
            army = db.execute("""
            SELECT supplies, current_soldiers, total_knights, total_archers, 
                   total_cavalry, total_siege, last_supply_check
            FROM armies WHERE user_id=? AND guild_id=?
            """, (user_id, guild_id)).fetchone()
            
            if not army:
                return
            
            # Calculate total army size
            total_army = (
                army['current_soldiers'] +
                army['total_knights'] * 10 +
                army['total_archers'] * 3 +
                army['total_cavalry'] * 8 +
                army['total_siege'] * 15
            )
            
            # Calculate days since last check
            last_check = dt.fromisoformat(army['last_supply_check']) if army['last_supply_check'] else utcnow()
            days_passed = max(1, (utcnow() - last_check).days)
            
            # Calculate supply consumption
            consumption = calculate_supply_consumption(total_army, days_passed)
            new_supplies = max(0, army['supplies'] - consumption)
            
            # Update supplies
            db.execute("""
            UPDATE armies 
            SET supplies=?, last_supply_check=?
            WHERE user_id=? AND guild_id=?
            """, (new_supplies, utcnow().isoformat(), user_id, guild_id))
            
            # If supplies are very low, apply morale penalty
            if new_supplies <= 10:
                db.execute("""
                UPDATE armies 
                SET morale=GREATEST(1, morale - 5)
                WHERE user_id=? AND guild_id=?
                """, (user_id, guild_id))
            
            db.commit()
            
    except Exception as e:
        print(f"Error updating army supplies: {e}")

# ---------- ENHANCED COMMANDS ----------
@bot.command(name="eregister")
@commands.guild_only()
async def enhanced_register_cmd(ctx):
    """Enhanced registration with more customization"""
    try:
        # Check if already registered
        combatant = get_enhanced_combatant(ctx.author.id, ctx.guild.id)
        if combatant:
            embed = medieval_embed(
                title="⚔️ Already Registered",
                description=f"**{combatant['title']} {combatant['character_name']}** of the **{combatant['army_name']}**",
                color_name="blue"
            )
            embed.add_field(name="Level", value=combatant['level'], inline=True)
            embed.add_field(name="Prestige", value=combatant['prestige'], inline=True)
            embed.add_field(name="Faction", value=combatant.get('faction', 'Independent'), inline=True)
            embed.add_field(name="Army", value=f"{combatant.get('current_soldiers', 0):,} soldiers", inline=True)
            embed.add_field(name="Morale", value=f"{combatant.get('morale', 0)}/100", inline=True)
            embed.add_field(name="Supplies", value=f"{combatant.get('supplies', 0)}/100", inline=True)
            return await ctx.send(embed=embed)

        # Start enhanced registration process
        embed = medieval_embed(
            title="🎖️ Enhanced Combatant Registration",
            description="Welcome to the realm of strategic warfare!",
            color_name="gold"
        )
        embed.add_field(
            name="📝 Registration Features",
            value="• Custom character name and title\n• Faction alignment\n• Army name and motto\n• Enhanced starting bonuses",
            inline=False
        )
        embed.add_field(
            name="🎖️ Starting Bonuses",
            value="• 5 stat points to allocate\n• 0 soldiers, 0 recruits\n• 100 morale and supplies\n• Balanced army type\n• Tactical training system",
            inline=False
        )

        view = EnhancedRegistrationView(ctx.author.id, ctx.guild.id)
        await ctx.send(embed=embed, view=view)

    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error in enhanced registration: {str(e)}", success=False))

@bot.command(name="estats")
@commands.guild_only()
async def enhanced_stats_cmd(ctx, member: discord.Member = None):
    """View enhanced combatant statistics"""
    try:
        member = member or ctx.author
        combatant = get_enhanced_combatant(member.id, ctx.guild.id)

        if not combatant:
            return await ctx.send(embed=medieval_response(
                f"{member.display_name} is not registered as a combatant! Use `!eregister` to begin.",
                success=False
            ))

        # Calculate XP progress
        xp_progress = (combatant['experience'] / combatant['experience_needed']) * 100

        embed = medieval_embed(
            title=f"🎖️ {combatant['title']} {combatant['character_name']}",
            description=f"*Leader of the {combatant['army_name']}*",
            color_name="gold"
        )

        # Character Info
        embed.add_field(name="🏆 Level", value=combatant['level'], inline=True)
        embed.add_field(name="⭐ Experience", value=f"{combatant['experience']:,}/{combatant['experience_needed']:,}", inline=True)
        embed.add_field(name="📊 Progress", value=f"{xp_progress:.1f}%", inline=True)

        # Enhanced Stats
        embed.add_field(name="⚔️ Strength", value=combatant['strength'], inline=True)
        embed.add_field(name="🏃 Agility", value=combatant['agility'], inline=True)
        embed.add_field(name="🧠 Intelligence", value=combatant['intelligence'], inline=True)
        embed.add_field(name="❤️ Vitality", value=combatant['vitality'], inline=True)
        embed.add_field(name="💬 Charisma", value=combatant['charisma'], inline=True)
        embed.add_field(name="🍀 Luck", value=combatant['luck'], inline=True)

        # Unallocated stats
        embed.add_field(name="🔴 Unallocated Stats", value=combatant['stat_points'], inline=True)
        embed.add_field(name="⭐ Prestige", value=combatant['prestige'], inline=True)
        embed.add_field(name="🎭 Faction", value=combatant.get('faction', 'Independent'), inline=True)

        # Army Info
        army_power = calculate_army_power(combatant)
        embed.add_field(name="🏰 Army Power",
                       value=f"**Total:** {army_power['total']:,}\n"
                             f"**Infantry:** {army_power['infantry']:,}\n"
                             f"**Cavalry:** {army_power['cavalry']:,}",
                       inline=True)
        
        embed.add_field(name="📈 Army Status",
                       value=f"**Type:** {combatant['army_type']}\n"
                             f"**Morale:** {combatant['morale']}/100\n"
                             f"**Supplies:** {combatant['supplies']}/100\n"
                             f"**Formation:** {combatant.get('battle_formation', 'Line')}",
                       inline=True)
        
        embed.add_field(name="⚔️ Army Composition",
                       value=f"**Soldiers:** {combatant['current_soldiers']:,}\n"
                             f"**Knights:** {combatant['total_knights']:,}\n"
                             f"**Archers:** {combatant['total_archers']:,}\n"
                             f"**Cavalry:** {combatant['total_cavalry']:,}\n"
                             f"**Siege:** {combatant['total_siege']:,}",
                       inline=True)

        # Combat Record
        total_fights = combatant['wins'] + combatant['losses'] + combatant['draws']
        win_rate = (combatant['wins'] / total_fights * 100) if total_fights > 0 else 0
        embed.add_field(name="✅ Wins", value=combatant['wins'], inline=True)
        embed.add_field(name="❌ Losses", value=combatant['losses'], inline=True)
        embed.add_field(name="🤝 Draws", value=combatant['draws'], inline=True)
        embed.add_field(name="📈 Win Rate", value=f"{win_rate:.1f}%", inline=True)
        embed.add_field(name="💀 Kills", value=combatant['total_kills'], inline=True)
        embed.add_field(name="☠️ Deaths", value=combatant['total_deaths'], inline=True)

        # Achievements
        achievements = eval(combatant['achievements'])
        if achievements:
            embed.add_field(name="🏅 Achievements", 
                          value=f"{len(achievements)} earned\n*Use `!achievements` to view*",
                          inline=False)

        # Status Effects
        status_effects = get_army_status_effects(member.id, ctx.guild.id)
        if status_effects:
            status_text = "\n".join([effect for effect in status_effects[:3]])  # Show first 3
            if len(status_effects) > 3:
                status_text += f"\n...and {len(status_effects) - 3} more"
            embed.add_field(name="📋 Status Effects", value=status_text, inline=False)

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error viewing enhanced stats: {str(e)}", success=False))

@bot.command(name="armymanage")
@commands.guild_only()
async def army_manage_cmd(ctx):
    """Open army management interface"""
    try:
        combatant = get_enhanced_combatant(ctx.author.id, ctx.guild.id)
        if not combatant:
            return await ctx.send(embed=medieval_response(
                "Thou must first register as a combatant!",
                success=False
            ))

        embed = medieval_embed(
            title=f"🏰 {combatant['army_name']} Management",
            description=f"Manage thy forces, {combatant['title']} {combatant['character_name']}",
            color_name="blue"
        )
        
        embed.add_field(
            name="📊 Quick Status",
            value=f"**Soldiers:** {combatant['current_soldiers']:,}\n"
                  f"**Recruits:** {combatant['current_recruits']:,}\n"
                  f"**Morale:** {combatant['morale']}/100\n"
                  f"**Supplies:** {combatant['supplies']}/100",
            inline=True
        )
        
        embed.add_field(
            name="⚡ Army Power",
            value=f"**Total:** {calculate_army_power(combatant)['total']:,}\n"
                  f"**Type:** {combatant['army_type']}\n"
                  f"**Formation:** {combatant.get('battle_formation', 'Line')}\n"
                  f"**Fortifications:** {combatant['fortifications']}",
            inline=True
        )

        view = ArmyManagementView(ctx.author.id, ctx.guild.id)
        await ctx.send(embed=embed, view=view)

    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error in army management: {str(e)}", success=False))

@bot.command(name="erecruit")
@commands.guild_only()
async def enhanced_recruit_cmd(ctx):
    """Enhanced recruitment with supply costs"""
    try:
        combatant = get_enhanced_combatant(ctx.author.id, ctx.guild.id)
        if not combatant:
            return await ctx.send(embed=medieval_response(
                "Thou must first register as a combatant!",
                success=False
            ))

        # Check recruitment eligibility
        can_recruit, message = enhanced_can_recruit_army(ctx.author.id, ctx.guild.id)
        if not can_recruit:
            return await ctx.send(embed=medieval_response(message, success=False))

        # Attempt enhanced recruitment
        success, message = enhanced_recruit_soldiers(ctx.author.id, ctx.guild.id)
        if success:
            embed = medieval_embed(
                title="✅ Recruitment Successful",
                description=message,
                color_name="green"
            )
        else:
            embed = medieval_embed(
                title="❌ Recruitment Failed",
                description=message,
                color_name="red"
            )
        
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error in enhanced recruitment: {str(e)}", success=False))

@bot.command(name="etrain")
@commands.guild_only()
async def enhanced_train_cmd(ctx, amount: int):
    """Enhanced training system with multiple unit types"""
    try:
        combatant = get_enhanced_combatant(ctx.author.id, ctx.guild.id)
        if not combatant:
            return await ctx.send(embed=medieval_response(
                "Thou must first register as a combatant!",
                success=False
            ))

        # Validate training amount
        if amount <= 0:
            return await ctx.send(embed=medieval_response(
                "Must train a positive number of recruits!",
                success=False
            ))

        # Attempt enhanced training
        success, message = enhanced_train_soldiers(ctx.author.id, ctx.guild.id, amount)
        if success:
            embed = medieval_embed(
                title="⚔️ Training Complete",
                description=message,
                color_name="green"
            )
        else:
            embed = medieval_embed(
                title="❌ Training Failed",
                description=message,
                color_name="red"
            )
        
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error in enhanced training: {str(e)}", success=False))

@bot.command(name="achievements")
@commands.guild_only()
async def achievements_cmd(ctx, member: discord.Member = None):
    """View achievements"""
    try:
        member = member or ctx.author
        combatant = get_enhanced_combatant(member.id, ctx.guild.id)

        if not combatant:
            return await ctx.send(embed=medieval_response(
                f"{member.display_name} is not registered!",
                success=False
            ))

        achievements = eval(combatant['achievements'])
        
        embed = medieval_embed(
            title=f"🏅 {member.display_name}'s Achievements",
            description=f"**Prestige:** {combatant['prestige']}",
            color_name="gold"
        )
        
        if achievements:
            # Get achievement details
            with get_combat_db_connection() as db:
                achievement_details = db.execute("""
                SELECT achievement_name, description, reward 
                FROM achievements 
                WHERE achievement_name IN ({})
                """.format(','.join(['?']*len(achievements))), achievements).fetchall()
                
                for i, achievement in enumerate(achievement_details, 1):
                    embed.add_field(
                        name=f"{i}. {achievement['achievement_name']}",
                        value=f"{achievement['description']}\n**Reward:** {achievement['reward']} prestige",
                        inline=False
                    )
        else:
            embed.add_field(
                name="No Achievements Yet",
                value="Complete challenges and battles to earn achievements!",
                inline=False
            )
        
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error viewing achievements: {str(e)}", success=False))

# ---------- ENHANCED HELP COMMAND ----------
@bot.command(name="ehelp")
@commands.guild_only()
async def enhanced_help_cmd(ctx):
    """Display enhanced combat system help"""
    embed = medieval_embed(
        title="🎖️ Enhanced Medieval Combat System - Complete Guide",
        description="*Hark! A comprehensive guide to strategic warfare and command!*",
        color_name="gold"
    )

    embed.add_field(
        name="📝 Registration & Setup",
        value="`!eregister` - Enhanced registration with titles/factions\n"
              "`!estats [@user]` - View enhanced statistics\n"
              "`!allocate <stat> <amount>` - Assign stat points",
        inline=False
    )

    embed.add_field(
        name="🏰 Army Management",
        value="`!armymanage` - Open army management interface\n"
              "`!erecruit` - Enhanced recruitment with supply costs\n"
              "`!etrain <amount>` - Train multiple unit types\n"
              "`!formation` - Change battle formation",
        inline=False
    )

    embed.add_field(
        name="⚔️ Army Composition",
        value="**Infantry:** Basic soldiers\n"
              "**Knights:** Elite warriors (10x power)\n"
              "**Archers:** Ranged units (3x power)\n"
              "**Cavalry:** Mobile forces (8x power)\n"
              "**Siege:** Heavy equipment (15x power)",
        inline=False
    )

    embed.add_field(
        name="🎯 Army Types",
        value="**Infantry Heavy:** +30% infantry\n"
              "**Cavalry Heavy:** +40% cavalry\n"
              "**Archer Heavy:** +30% archers\n"
              "**Siege Specialized:** +50% siege\n"
              "**Defensive:** +40% infantry, +20% archers\n"
              "**Balanced:** +10% to all",
        inline=False
    )

    embed.add_field(
        name="📊 Resource Management",
        value="**Morale:** Affects effectiveness (50-150%)\n"
              "**Supplies:** Required for actions (consumed daily)\n"
              "**Tactical Points:** For special actions\n"
              "**Fortifications:** Defensive bonuses",
        inline=False
    )

    embed.add_field(
        name="⚡ Enhanced Features",
        value="• Multiple unit types with specialties\n"
              "• Terrain and weather effects\n"
              "• Morale and supply systems\n"
              "• Battle formations with bonuses\n"
              "• Army type specializations\n"
              "• Fortification building\n"
              "• Achievement system with prestige\n"
              "• Enhanced training with unit distribution",
        inline=False
    )

    embed.add_field(
        name="🏅 Progression System",
        value="• Level up with XP from battles\n"
              "• 3 stat points per level\n"
              "• Prestige from achievements\n"
              "• Army capacity increases with level\n"
              "• Unlock new formations and abilities",
        inline=False
    )

    embed.add_field(
        name="⚠️ Important Mechanics",
        value="• Supplies consumed daily based on army size\n"
              "• Low morale reduces effectiveness\n"
              "• Army type affects unit training\n"
              "• Terrain affects combat bonuses\n"
              "• Weather affects visibility and movement\n"
              "• Fortifications provide defensive bonuses",
        inline=False
    )

    await ctx.send(embed=embed)

# ---------- BACKGROUND TASKS ----------
@tasks.loop(minutes=30)
async def update_army_supplies_task():
    """Background task to update army supplies"""
    try:
        print("⚙️ Updating army supplies...")
        with get_combat_db_connection() as db:
            # Get all armies
            armies = db.execute("""
            SELECT user_id, guild_id FROM armies
            """).fetchall()
            
            for army in armies:
                try:
                    update_army_supplies(army['user_id'], army['guild_id'])
                except Exception as e:
                    print(f"Error updating supplies for army {army['user_id']}: {e}")
        
        print("✅ Army supplies updated")
    except Exception as e:
        print(f"Error in supply update task: {e}")

@tasks.loop(hours=24)
async def reset_weekly_limits():
    """Reset weekly recruitment limits"""
    try:
        print("⚙️ Resetting weekly limits...")
        with get_combat_db_connection() as db:
            db.execute("""
            UPDATE armies 
            SET weekly_recruitment_used=0, recruitment_cooldown=NULL
            WHERE recruitment_cooldown IS NOT NULL AND 
                  datetime(recruitment_cooldown) <= datetime('now')
            """)
            db.commit()
        
        print("✅ Weekly limits reset")
    except Exception as e:
        print(f"Error resetting weekly limits: {e}")

# ---------- ON READY ----------
@bot.event
async def on_ready():
    try:
        print(f'🎖️ Enhanced Medieval Combat Bot hath awakened as {bot.user}')
        print('⚔️ Enhanced duel system with terrain/weather effects!')
        print('🏰 Comprehensive army management with multiple unit types!')
        print('📊 Morale and supply systems activated!')
        print('🎯 Army type specializations and formations!')
        print('🏗️ Fortification building system!')
        print('🏅 Achievement and prestige system!')
        print('⚡ Enhanced training with unit distribution!')
        print('🌤️ Terrain and weather effects on combat!')
        print('🔗 Enhanced commands synchronized!')

        # Sync slash commands
        try:
            synced = await tree.sync()
            print(f"✅ Synced {len(synced)} slash commands")
        except Exception as e:
            print(f"❌ Failed to sync slash commands: {e}")

        # Initialize database
        init_combat_db()
        
        # Start background tasks
        update_army_supplies_task.start()
        reset_weekly_limits.start()

    except Exception as e:
        print(f"Error in on_ready: {e}")
        traceback.print_exc()

# ---------- ERROR HANDLING ----------
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=medieval_response(
            "Thou lacketh the royal permissions for this command!",
            success=False
        ))
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=medieval_response(
            f"Thou hast forgotten the '{error.param.name}' argument!",
            success=False
        ))
    elif isinstance(error, commands.BadArgument):
        if "Converting to \"int\"" in str(error):
            await ctx.send(embed=medieval_response(
                "Thou must provide a valid number!",
                success=False
            ))
        else:
            await ctx.send(embed=medieval_response(
                f"Thy argument is flawed: {str(error)}",
                success=False
            ))
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send(embed=medieval_response(
            f"I couldst not find the member '{error.argument}'!",
            success=False
        ))
    else:
        print(f"Command error: {error}")
        traceback.print_exc()
        await ctx.send(embed=medieval_response(
            "An ill omen befell the command!",
            success=False
        ))

# ---------- RUN ----------
app = flask.Flask(__name__)

@app.route('/')
def home():
    return "Enhanced Medieval Combat Bot is alive! ⚔️ Strategic warfare & army management running."

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

if __name__ == "__main__":
    try:
        print("🎖️ Starting Enhanced Medieval Combat Bot...")
        print("⚔️ Preparing enhanced duel, army & war systems...")
        print("🏰 Initializing comprehensive combat database...")
        print("🌤️ Terrain & weather effects ready!")
        print("🏗️ Fortifications & supply systems online!")
        print("🏅 Achievements & prestige tracking activated!")
        print("⚡ Unit specialization & army types loaded!")

        # Start Flask keep-alive server in background thread
        Thread(target=run_flask, daemon=True).start()

        # Initialize database and start the bot
        init_combat_db()
        update_army_supplies_task.start()
        reset_weekly_limits.start()

        bot.run(TOKEN)
    except Exception as e:
        print(f"Failed to start enhanced combat bot: {e}")
        traceback.print_exc()
