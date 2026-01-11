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
import json

# ---------- ENVIRONMENT ----------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "!")
COMBAT_DB_NAME = os.getenv("DB_PATH", "medieval_combat_enhanced.db")

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

# ---------- ENHANCED COMBAT SYSTEMS ----------
WEATHER_EFFECTS = {
    "Clear Skies": {"morale": 1.1, "visibility": 1.2, "movement": 1.1, "archery": 1.1, "description": "Perfect conditions for battle"},
    "Heavy Rain": {"morale": 0.9, "visibility": 0.7, "movement": 0.8, "archery": 0.6, "description": "Rain hampers movement and archery"},
    "Foggy": {"morale": 0.95, "visibility": 0.5, "movement": 0.9, "archery": 0.7, "description": "Low visibility favors ambushes"},
    "Stormy": {"morale": 0.8, "visibility": 0.6, "movement": 0.7, "archery": 0.5, "description": "Thunderstorms disrupt formations"},
    "Snowstorm": {"morale": 0.7, "visibility": 0.4, "movement": 0.6, "archery": 0.4, "description": "Snow slows everything to a crawl"},
    "Light Rain": {"morale": 1.0, "visibility": 0.9, "movement": 0.95, "archery": 0.8, "description": "Light rain slightly hampers combat"},
    "Overcast": {"morale": 1.0, "visibility": 1.0, "movement": 1.0, "archery": 1.0, "description": "Standard battle conditions"},
}

TERRAIN_EFFECTS = {
    "Open Plains": {"defense": 1.0, "cavalry": 1.3, "archery": 1.2, "ambush": 0.5, "infantry": 1.0, "siege": 1.1, "description": "Flat terrain ideal for cavalry"},
    "Dense Forest": {"defense": 1.2, "cavalry": 0.6, "archery": 0.7, "ambush": 1.5, "infantry": 1.1, "siege": 0.5, "description": "Wooded terrain hampers movement"},
    "Rocky Mountains": {"defense": 1.4, "cavalry": 0.4, "archery": 0.8, "ambush": 1.3, "infantry": 1.2, "siege": 0.4, "description": "Mountainous defensive terrain"},
    "Swampy Marshlands": {"defense": 1.1, "cavalry": 0.3, "archery": 0.6, "ambush": 1.4, "infantry": 0.9, "siege": 0.3, "description": "Difficult terrain slows all"},
    "Desert Wastes": {"defense": 0.9, "cavalry": 0.8, "archery": 0.9, "ambush": 0.7, "infantry": 0.8, "siege": 1.0, "description": "Harsh desert conditions"},
    "Frozen Tundra": {"defense": 1.0, "cavalry": 0.7, "archery": 0.8, "ambush": 0.8, "infantry": 0.9, "siege": 0.9, "description": "Cold slows movement"},
    "Hilly Highlands": {"defense": 1.3, "cavalry": 0.9, "archery": 1.1, "ambush": 1.2, "infantry": 1.1, "siege": 0.8, "description": "Elevated defensive positions"},
    "River Crossing": {"defense": 1.5, "cavalry": 0.5, "archery": 1.0, "ambush": 1.1, "infantry": 1.0, "siege": 0.6, "description": "River provides natural barrier"},
    "Forest Hills": {"defense": 1.2, "cavalry": 0.7, "archery": 0.9, "ambush": 1.4, "infantry": 1.1, "siege": 0.7, "description": "Mixed forested hills"},
    "Coastal Cliffs": {"defense": 1.6, "cavalry": 0.2, "archery": 1.3, "ambush": 1.0, "infantry": 1.0, "siege": 0.5, "description": "Cliffs provide strong defense"},
}

# Army types with different strengths
ARMY_TYPES = {
    "Infantry Heavy": {"infantry": 1.3, "cavalry": 0.8, "archers": 1.0, "siege": 0.9, "description": "Strong infantry forces"},
    "Cavalry Heavy": {"infantry": 0.8, "cavalry": 1.4, "archers": 0.9, "siege": 0.7, "description": "Mobile cavalry focus"},
    "Archer Heavy": {"infantry": 0.9, "cavalry": 0.9, "archers": 1.3, "siege": 1.0, "description": "Ranged superiority"},
    "Balanced": {"infantry": 1.1, "cavalry": 1.1, "archers": 1.1, "siege": 1.1, "description": "Well-rounded army"},
    "Siege Specialized": {"infantry": 1.0, "cavalry": 0.7, "archers": 1.0, "siege": 1.5, "description": "Expert siege warfare"},
    "Defensive": {"infantry": 1.4, "cavalry": 0.6, "archers": 1.2, "siege": 0.8, "description": "Defensive fortification focus"},
}

# Battle tactics with different effects
BATTLE_TACTICS = {
    "Flank Attack": {"damage": 1.3, "risk": 1.2, "morale": 1.1, "description": "Attack enemy flanks"},
    "Frontal Assault": {"damage": 1.1, "risk": 1.4, "morale": 1.0, "description": "Direct frontal attack"},
    "Defensive Position": {"damage": 0.9, "risk": 0.7, "morale": 1.2, "description": "Hold defensive line"},
    "Skirmish Tactics": {"damage": 1.0, "risk": 0.9, "morale": 1.0, "description": "Hit and run tactics"},
    "Full Retreat": {"damage": 0.0, "risk": 0.3, "morale": 0.5, "description": "Strategic withdrawal"},
    "Ambush": {"damage": 1.5, "risk": 1.3, "morale": 1.3, "description": "Surprise attack"},
    "Siege Warfare": {"damage": 1.2, "risk": 1.1, "morale": 1.0, "description": "Systematic siege"},
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

# ---------- UTILITY FUNCTIONS ----------
def generate_random_recruits():
    """Generate random number of recruits with variation"""
    base = random.randint(50, 150)
    variation = random.randint(-20, 20)
    return max(10, base + variation)

def get_random_terrain():
    """Get random terrain for battles"""
    terrains = list(TERRAIN_EFFECTS.keys())
    return random.choice(terrains)

def get_random_weather():
    """Get random weather for battles"""
    weathers = list(WEATHER_EFFECTS.keys())
    return random.choice(weathers)

def get_random_tactic():
    """Get random battle tactic"""
    tactics = list(BATTLE_TACTICS.keys())
    return random.choice(tactics)

def calculate_desertion_rate(morale, supplies, army_size):
    """Calculate desertion rate based on conditions"""
    base_rate = 0.01
    morale_effect = (100 - morale) / 500  # Up to 0.2
    supply_effect = 0.0 if supplies >= 50 else (50 - supplies) / 250  # Up to 0.2
    size_effect = army_size / 10000  # Larger armies harder to control
    return min(0.3, base_rate + morale_effect + supply_effect + size_effect)

def calculate_supply_consumption(army_size, days=1):
    """Calculate daily supply consumption for army"""
    base_consumption = army_size * 0.01  # 1% of army size per day
    return int(base_consumption * days)

def calculate_knight_chance(training_size, commander_level):
    """Calculate chance to get a knight from training"""
    base_chance = 0.07  # 7% base chance
    size_bonus = min(0.05, training_size / 1000)  # Up to 5% bonus for large training
    level_bonus = commander_level * 0.001  # 0.1% per level
    return min(0.15, base_chance + size_bonus + level_bonus)  # Max 15% chance

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
                total_recruits_trained INTEGER DEFAULT 0,
                total_soldiers_lost INTEGER DEFAULT 0,
                total_battles INTEGER DEFAULT 0,
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
                daily_actions INTEGER DEFAULT 3,
                last_daily_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                round_timeout INTEGER DEFAULT 60,
                terrain TEXT DEFAULT 'Open Plains',
                weather TEXT DEFAULT 'Clear Skies'
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
                team_a_members TEXT DEFAULT '[]',
                team_b_members TEXT DEFAULT '[]',
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
                victory_conditions TEXT DEFAULT '{"type": "annihilation", "rounds": 10}',
                current_tactic_a TEXT DEFAULT 'Frontal Assault',
                current_tactic_b TEXT DEFAULT 'Frontal Assault'
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

            # XP history table
            db.execute("""
            CREATE TABLE IF NOT EXISTS xp_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                amount INTEGER,
                source TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")

            # Fortification history table
            db.execute("""
            CREATE TABLE IF NOT EXISTS fortification_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                fortifications_built INTEGER,
                supplies_used INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")

            # Daily actions table
            db.execute("""
            CREATE TABLE IF NOT EXISTS daily_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                action_type TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

# ---------- CHARACTER SYSTEM ----------
def get_enhanced_combatant(user_id, guild_id):
    """Get combatant character with enhanced army data"""
    try:
        with get_combat_db_connection() as db:
            result = db.execute("""
            SELECT c.*, a.army_type, a.current_soldiers, a.current_recruits, a.max_soldiers,
                   a.max_recruits, a.tactical_points, a.morale, a.supplies,
                   a.total_knights, a.total_archers, a.total_cavalry, a.total_siege,
                   a.fortifications, a.weekly_recruitment_used, a.daily_actions,
                   a.battle_formation, a.last_daily_reset
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

        # Apply formation bonus
        formation_bonus = get_formation_bonus(combatant.get('battle_formation', 'Line'))
        total_power = int(total_power * morale_multiplier * formation_bonus)

        return {
            'total': total_power,
            'infantry': int(infantry_power * bonuses['infantry']),
            'knights': int(knight_power * bonuses['infantry']),
            'archers': int(archer_power * bonuses['archers']),
            'cavalry': int(cavalry_power * bonuses['cavalry']),
            'siege': int(siege_power * bonuses['siege']),
            'morale_multiplier': morale_multiplier,
            'formation_bonus': formation_bonus
        }

    except Exception as e:
        print(f"Error calculating army power: {e}")
        return {'total': 0, 'infantry': 0, 'knights': 0, 'archers': 0, 'cavalry': 0, 'siege': 0, 'morale_multiplier': 1.0, 'formation_bonus': 1.0}

def get_formation_bonus(formation_name):
    """Get bonus from formation"""
    try:
        with get_combat_db_connection() as db:
            formation = db.execute("""
            SELECT infantry_bonus, cavalry_bonus, archer_bonus, defense_bonus
            FROM battle_formations WHERE formation_name=?
            """, (formation_name,)).fetchone()

            if formation:
                # Average of bonuses
                return (formation['infantry_bonus'] + formation['cavalry_bonus'] +
                       formation['archer_bonus'] + formation['defense_bonus']) / 4
            return 1.0
    except:
        return 1.0

def can_perform_daily_action(user_id, guild_id):
    """Check if user can perform a daily action"""
    try:
        combatant = get_enhanced_combatant(user_id, guild_id)
        if not combatant:
            return False, "Not registered"

        # Check if daily reset is needed
        last_reset = dt.fromisoformat(combatant['last_daily_reset']) if combatant['last_daily_reset'] else utcnow()
        if (utcnow() - last_reset).days >= 1:
            # Reset daily actions
            with get_combat_db_connection() as db:
                db.execute("""
                UPDATE armies SET daily_actions=3, last_daily_reset=?
                WHERE user_id=? AND guild_id=?
                """, (utcnow().isoformat(), user_id, guild_id))
                db.commit()
            return True, "Actions reset"

        if combatant['daily_actions'] <= 0:
            return False, "No daily actions remaining"

        return True, f"{combatant['daily_actions']} actions remaining"
    except Exception as e:
        return False, f"Error: {str(e)}"

def use_daily_action(user_id, guild_id, action_type):
    """Use a daily action"""
    try:
        with get_combat_db_connection() as db:
            # Record action
            db.execute("""
            INSERT INTO daily_actions (user_id, guild_id, action_type)
            VALUES (?, ?, ?)
            """, (user_id, guild_id, action_type))

            # Decrement action count
            db.execute("""
            UPDATE armies SET daily_actions=daily_actions-1
            WHERE user_id=? AND guild_id=?
            """, (user_id, guild_id))
            db.commit()
            return True
    except Exception as e:
        print(f"Error using daily action: {e}")
        return False

# ---------- RECRUITMENT & TRAINING ----------
def can_recruit_army(user_id, guild_id):
    """Recruitment eligibility check"""
    try:
        with get_combat_db_connection() as db:
            army = db.execute("""
            SELECT weekly_recruitment_used, recruitment_cooldown, morale, supplies, daily_actions
            FROM armies WHERE user_id=? AND guild_id=?
            """, (user_id, guild_id)).fetchone()

            if not army:
                return False, "No army found"

            # Check daily actions
            can_action, action_msg = can_perform_daily_action(user_id, guild_id)
            if not can_action:
                return False, action_msg

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

def recruit_soldiers(user_id, guild_id):
    """Randomized recruitment system with supply costs"""
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

def train_soldiers(user_id, guild_id, train_amount):
    """Enhanced training system with multiple unit types and desertions"""
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

            # Get commander level for knight chance
            combatant = get_enhanced_combatant(user_id, guild_id)
            commander_level = combatant['level'] if combatant else 1

            # Calculate desertions based on morale and supplies
            desertion_rate = calculate_desertion_rate(army['morale'], army['supplies'], train_amount)
            soldiers_deserted = 0
            for _ in range(train_amount):
                if random.random() < desertion_rate:
                    soldiers_deserted += 1

            # Calculate knight chance (7% base + bonuses)
            knight_chance = calculate_knight_chance(train_amount, commander_level)

            # Calculate unit type distribution
            unit_types = distribute_unit_types(train_amount - soldiers_deserted, army_type, knight_chance)

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

            # Update combatant stats
            if combatant:
                update_combatant_stats(
                    user_id, guild_id,
                    total_recruits_trained=combatant['total_recruits_trained'] + soldiers_trained
                )

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
            message = f"⚔️ **Training Complete** ⚔️\n\n"
            message += f"**{train_amount}** recruits underwent rigorous training.\n"
            message += f"**Desertion Rate:** {desertion_rate*100:.1f}%\n\n"

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
            message += f"**Knight Chance:** {knight_chance*100:.1f}%\n"

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

def distribute_unit_types(total_recruits, army_type, knight_chance):
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
        'knights': 0.02,  # 2% knights base (will be adjusted)
        'archers': 0.15,  # 15% archers
        'cavalry': 0.10,  # 10% cavalry
        'siege': 0.03     # 3% siege equipment
    }

    # Adjust knight chance
    base_distribution['knights'] = knight_chance

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

# ---------- COMBAT SYSTEM ----------
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

def calculate_war_damage(attacker_power, defender_power, terrain, weather, attacker_tactic, defender_tactic):
    """Calculate war damage with all modifiers"""
    try:
        # Base damage
        base_damage = (attacker_power * 0.1) + random.randint(-50, 50)

        # Get modifiers
        terrain_mod = TERRAIN_EFFECTS.get(terrain, TERRAIN_EFFECTS["Open Plains"])
        weather_mod = WEATHER_EFFECTS.get(weather, WEATHER_EFFECTS["Clear Skies"])
        attacker_tactic_mod = BATTLE_TACTICS.get(attacker_tactic, BATTLE_TACTICS["Frontal Assault"])
        defender_tactic_mod = BATTLE_TACTICS.get(defender_tactic, BATTLE_TACTICS["Frontal Assault"])

        # Calculate total modifier
        total_modifier = (
            (terrain_mod.get('infantry', 1.0) * 0.3 + terrain_mod.get('cavalry', 1.0) * 0.3 +
             terrain_mod.get('archery', 1.0) * 0.2 + terrain_mod.get('defense', 1.0) * 0.2) *
            (weather_mod.get('morale', 1.0) * weather_mod.get('archery', 1.0)) *
            attacker_tactic_mod['damage'] *
            (1.0 / defender_tactic_mod['damage'])
        )

        damage = int(base_damage * total_modifier)

        # Ensure minimum damage
        damage = max(10, damage)

        # Chance for critical/surprise based on terrain
        surprise_chance = terrain_mod.get('ambush', 1.0) * 0.1
        if random.random() < surprise_chance:
            damage = int(damage * random.uniform(1.3, 1.8))
            return damage, True, "surprise"

        return damage, False, "normal"

    except Exception as e:
        print(f"Error calculating war damage: {e}")
        return int(attacker_power * 0.05), False, "normal"

def calculate_casualties(army_power, damage_received, terrain, weather):
    """Calculate casualties from battle"""
    try:
        # Base casualty rate
        casualty_rate = damage_received / (army_power + 1000)  # Relative to army power

        # Apply terrain and weather modifiers
        terrain_mod = TERRAIN_EFFECTS.get(terrain, TERRAIN_EFFECTS["Open Plains"])
        weather_mod = WEATHER_EFFECTS.get(weather, WEATHER_EFFECTS["Clear Skies"])

        defense_modifier = terrain_mod.get('defense', 1.0) * weather_mod.get('morale', 1.0)
        casualty_rate *= (1.0 / defense_modifier)

        # Cap casualty rate
        casualty_rate = min(0.5, max(0.05, casualty_rate))

        return casualty_rate

    except Exception as e:
        print(f"Error calculating casualties: {e}")
        return 0.1

# ---------- REGISTRATION SYSTEM ----------
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

        await interaction.response.send_modal(CharacterModal(self))

    @discord.ui.button(label="🏰 Army Details", style=discord.ButtonStyle.blurple, emoji="🏰")
    async def set_army_name(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This registration is not for thee!", ephemeral=True)

        await interaction.response.send_modal(ArmyModal(self))

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
                          value="Use `/recruit` to gain recruits\n`/train` to build your army\n`/stats` to view your progress",
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

class CharacterModal(discord.ui.Modal, title="Character Details"):
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

class ArmyModal(discord.ui.Modal, title="Army Details"):
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

# ---------- COMMANDS ----------
# Slash Commands
@tree.command(name="register", description="Register as a combatant in the realm")
async def register(interaction: discord.Interaction):
    """Slash command for registration"""
    await enhanced_register_cmd(interaction)

@tree.command(name="stats", description="View your combat statistics")
@app_commands.describe(member="Optional: View another member's stats")
async def stats(interaction: discord.Interaction, member: discord.Member = None):
    """Slash command for stats"""
    await enhanced_stats_cmd(interaction, member)

@tree.command(name="recruit", description="Recruit new soldiers for your army")
async def recruit(interaction: discord.Interaction):
    """Slash command for recruitment"""
    await enhanced_recruit_cmd(interaction)

@tree.command(name="train", description="Train recruits into soldiers")
@app_commands.describe(amount="Number of recruits to train")
async def train(interaction: discord.Interaction, amount: int):
    """Slash command for training"""
    await enhanced_train_cmd(interaction, amount)

@tree.command(name="duel", description="Challenge another player to a duel")
@app_commands.describe(opponent="The player to duel", wager="Optional prestige wager")
async def duel(interaction: discord.Interaction, opponent: discord.Member, wager: int = 0):
    """Slash command for duels"""
    await enhanced_duel_cmd(interaction, opponent, wager)

@tree.command(name="war", description="Declare war on another player or faction")
@app_commands.describe(opponent="The opponent to fight", war_name="Name of the war")
async def war(interaction: discord.Interaction, opponent: discord.Member, war_name: str):
    """Slash command for war"""
    await enhanced_war_cmd(interaction, opponent, war_name)

@tree.command(name="armymanage", description="Open army management interface")
async def armymanage(interaction: discord.Interaction):
    """Slash command for army management"""
    await army_manage_cmd(interaction)

@tree.command(name="formation", description="Change or view battle formations")
@app_commands.describe(formation_name="Name of the formation to use")
async def formation(interaction: discord.Interaction, formation_name: str = None):
    """Slash command for formations"""
    await formation_cmd(interaction, formation_name)

@tree.command(name="allocate", description="Allocate stat points")
@app_commands.describe(stat="Stat to allocate to", amount="Number of points to allocate")
async def allocate(interaction: discord.Interaction, stat: str, amount: int):
    """Slash command for stat allocation"""
    await allocate_cmd(interaction, stat, amount)

@tree.command(name="help", description="Display comprehensive help guide")
async def help_command(interaction: discord.Interaction):
    """Slash command for help"""
    await enhanced_help_cmd(interaction)

# Prefix Commands
@bot.command(name="register")
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
            title="🎖️ Combatant Registration",
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
        await ctx.send(embed=medieval_response(f"Error in registration: {str(e)}", success=False))

@bot.command(name="stats")
@commands.guild_only()
async def enhanced_stats_cmd(ctx, member: discord.Member = None):
    """View enhanced combatant statistics"""
    try:
        member = member or ctx.author
        combatant = get_enhanced_combatant(member.id, ctx.guild.id)

        if not combatant:
            return await ctx.send(embed=medieval_response(
                f"{member.display_name} is not registered as a combatant! Use `!register` to begin.",
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

        # Daily Actions
        embed.add_field(name="📅 Daily Actions", value=f"{combatant['daily_actions']}/3 remaining", inline=False)

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error viewing stats: {str(e)}", success=False))

@bot.command(name="recruit")
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

        # Check daily actions
        can_action, action_msg = can_perform_daily_action(ctx.author.id, ctx.guild.id)
        if not can_action:
            return await ctx.send(embed=medieval_response(action_msg, success=False))

        # Check recruitment eligibility
        can_recruit, message = can_recruit_army(ctx.author.id, ctx.guild.id)
        if not can_recruit:
            return await ctx.send(embed=medieval_response(message, success=False))

        # Attempt enhanced recruitment
        success, message = recruit_soldiers(ctx.author.id, ctx.guild.id)
        if success:
            use_daily_action(ctx.author.id, ctx.guild.id, "recruit")
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
        await ctx.send(embed=medieval_response(f"Error in recruitment: {str(e)}", success=False))

@bot.command(name="train")
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

        # Check daily actions
        can_action, action_msg = can_perform_daily_action(ctx.author.id, ctx.guild.id)
        if not can_action:
            return await ctx.send(embed=medieval_response(action_msg, success=False))

        # Validate training amount
        if amount <= 0:
            return await ctx.send(embed=medieval_response(
                "Must train a positive number of recruits!",
                success=False
            ))

        # Attempt enhanced training
        success, message = train_soldiers(ctx.author.id, ctx.guild.id, amount)
        if success:
            use_daily_action(ctx.author.id, ctx.guild.id, "train")
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
        await ctx.send(embed=medieval_response(f"Error in training: {str(e)}", success=False))

# ---------- DUEL SYSTEM ----------
class DuelChallengeView(discord.ui.View):
    def __init__(self, challenger_id, defender_id, terrain, weather, wager):
        super().__init__(timeout=300.0)
        self.challenger_id = challenger_id
        self.defender_id = defender_id
        self.terrain = terrain
        self.weather = weather
        self.wager = wager
        self.accepted = False

    @discord.ui.button(label="⚔️ Accept Duel", style=discord.ButtonStyle.green, emoji="⚔️")
    async def accept_duel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.defender_id:
            return await interaction.response.send_message("This duel is not for thee!", ephemeral=True)

        self.accepted = True

        # Start the duel
        try:
            with get_combat_db_connection() as db:
                db.execute("""
                INSERT INTO active_duels (guild_id, challenger_id, defender_id,
                                        current_turn_user, duel_type, wager, terrain, weather)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (interaction.guild.id, self.challenger_id, self.defender_id,
                      self.challenger_id, "Enhanced Duel", self.wager, self.terrain, self.weather))
                db.commit()

            await interaction.response.send_message(
                embed=medieval_embed(
                    title="⚔️ Duel Accepted!",
                    description="The duel begins! Use `/turn` to take your action.",
                    color_name="green"
                )
            )
            self.stop()

        except Exception as e:
            await interaction.response.send_message(
                embed=medieval_response(f"Error starting duel: {str(e)}", success=False)
            )

    @discord.ui.button(label="❌ Decline Duel", style=discord.ButtonStyle.red, emoji="❌")
    async def decline_duel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.defender_id:
            return await interaction.response.send_message("This duel is not for thee!", ephemeral=True)

        await interaction.response.send_message(
            embed=medieval_response("Duel declined!", success=False)
        )
        self.stop()

@bot.command(name="duel")
@commands.guild_only()
async def enhanced_duel_cmd(ctx, opponent: discord.Member = None, wager: int = 0):
    """Enhanced duel with terrain and weather effects"""
    try:
        if opponent is None:
            return await ctx.send(embed=medieval_response(
                "Thou must specify an opponent! Use `!duel @opponent`",
                success=False
            ))

        if opponent.id == ctx.author.id:
            return await ctx.send(embed=medieval_response(
                "Thou cannot duel thyself!",
                success=False
            ))

        # Check if both are registered
        challenger = get_enhanced_combatant(ctx.author.id, ctx.guild.id)
        defender = get_enhanced_combatant(opponent.id, ctx.guild.id)

        if not challenger:
            return await ctx.send(embed=medieval_response(
                f"{ctx.author.display_name} must first register!",
                success=False
            ))

        if not defender:
            return await ctx.send(embed=medieval_response(
                f"{opponent.display_name} must first register!",
                success=False
            ))

        # Check for existing duel
        with get_combat_db_connection() as db:
            existing_duel = db.execute("""
            SELECT * FROM active_duels
            WHERE guild_id=? AND (
                (challenger_id=? AND defender_id=?) OR
                (challenger_id=? AND defender_id=?)
            ) AND status='active'
            """, (ctx.guild.id, ctx.author.id, opponent.id, opponent.id, ctx.author.id)).fetchone()

            if existing_duel:
                return await ctx.send(embed=medieval_response(
                    f"A duel between {ctx.author.display_name} and {opponent.display_name} is already in progress!",
                    success=False
                ))

        # Generate terrain and weather
        terrain = get_random_terrain()
        weather = get_random_weather()

        # Create duel challenge embed
        embed = medieval_embed(
            title="⚔️ Duel Challenge!",
            description=f"**{challenger['title']} {challenger['character_name']}** challenges **{defender['title']} {defender['character_name']}** to a duel!",
            color_name="gold"
        )

        embed.add_field(name="🏞️ Terrain", value=terrain, inline=True)
        embed.add_field(name="🌤️ Weather", value=weather, inline=True)
        embed.add_field(name="🎯 Wager", value=f"{wager} prestige" if wager > 0 else "None", inline=True)

        embed.add_field(
            name="Terrain Effects",
            value=TERRAIN_EFFECTS[terrain]['description'],
            inline=True
        )

        embed.add_field(
            name="Weather Effects",
            value=WEATHER_EFFECTS[weather]['description'],
            inline=True
        )

        view = DuelChallengeView(ctx.author.id, opponent.id, terrain, weather, wager)
        await ctx.send(embed=embed, view=view)

    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error creating duel: {str(e)}", success=False))

@bot.command(name="turn")
@commands.guild_only()
async def enhanced_turn_cmd(ctx, action: str = None):
    """Take your turn in an enhanced duel"""
    try:
        # Get active duel
        with get_combat_db_connection() as db:
            duel = db.execute("""
            SELECT * FROM active_duels
            WHERE guild_id=? AND (
                challenger_id=? OR defender_id=?
            ) AND status='active'
            """, (ctx.guild.id, ctx.author.id, ctx.author.id)).fetchone()

            if not duel:
                return await ctx.send(embed=medieval_response(
                    "Thou hast no active duels!",
                    success=False
                ))

            if duel['current_turn_user'] != ctx.author.id:
                opponent = duel['defender_id'] if duel['challenger_id'] == ctx.author.id else duel['challenger_id']
                opponent_name = ctx.guild.get_member(opponent)
                return await ctx.send(embed=medieval_response(
                    f"It is {opponent_name.display_name if opponent_name else 'your opponent'}'s turn!",
                    success=False
                ))

            if not action:
                # Show available actions
                embed = medieval_embed(
                    title="⚔️ Your Turn - Choose Action",
                    description="Available actions:",
                    color_name="gold"
                )

                actions = [
                    ("power_strike", "Heavy melee attack (Strength-based)"),
                    ("quick_strike", "Fast attack (Agility-based)"),
                    ("magic_bolt", "Magical attack (Intelligence-based)"),
                    ("cavalry_charge", "Cavalry charge (Strength-based)"),
                    ("archer_volley", "Ranged attack (Agility-based)"),
                    ("shield_wall", "Defensive stance (Vitality-based)"),
                    ("flanking_maneuver", "Tactical attack (Agility-based)")
                ]

                for action_name, description in actions:
                    embed.add_field(name=action_name.replace("_", " ").title(), value=description, inline=False)

                return await ctx.send(embed=embed)

            # Process action
            challenger = get_enhanced_combatant(duel['challenger_id'], ctx.guild.id)
            defender = get_enhanced_combatant(duel['defender_id'], ctx.guild.id)

            is_challenger = ctx.author.id == duel['challenger_id']
            attacker = challenger if is_challenger else defender
            target = defender if is_challenger else challenger

            # Calculate damage
            damage, critical = calculate_enhanced_damage(
                attacker, target, action,
                duel.get('terrain', 'Open Plains'),
                duel.get('weather', 'Clear Skies')
            )

            # Update HP
            if is_challenger:
                new_defender_hp = max(0, duel['defender_hp'] - damage)
                db.execute("""
                UPDATE active_duels
                SET defender_hp=?, current_turn_user=?, turn=turn+1,
                    last_action=?
                WHERE id=?
                """, (new_defender_hp, duel['defender_id'], utcnow().isoformat(), duel['id']))
            else:
                new_challenger_hp = max(0, duel['challenger_hp'] - damage)
                db.execute("""
                UPDATE active_duels
                SET challenger_hp=?, current_turn_user=?, turn=turn+1,
                    last_action=?
                WHERE id=?
                """, (new_challenger_hp, duel['challenger_id'], utcnow().isoformat(), duel['id']))

            # Record action
            actions_field = 'challenger_actions' if is_challenger else 'defender_actions'
            current_actions = eval(duel[actions_field])
            current_actions.append({
                'turn': duel['turn'],
                'action': action,
                'damage': damage,
                'critical': critical
            })

            db.execute(f"""
            UPDATE active_duels
            SET {actions_field}=?
            WHERE id=?
            """, (str(current_actions), duel['id']))

            db.commit()

            # Check for winner
            winner = None
            if new_defender_hp <= 0:
                winner = duel['challenger_id']
            elif new_challenger_hp <= 0:
                winner = duel['defender_id']

            if winner:
                # End duel
                db.execute("""
                UPDATE active_duels
                SET status='ended', last_action=?
                WHERE id=?
                """, (utcnow().isoformat(), duel['id']))

                # Update combatant stats
                winner_data = challenger if winner == duel['challenger_id'] else defender
                loser_data = defender if winner == duel['challenger_id'] else challenger

                update_combatant_stats(winner, ctx.guild.id, wins=winner_data['wins'] + 1)
                update_combatant_stats(
                    loser_data['user_id'], ctx.guild.id,
                    losses=loser_data['losses'] + 1
                )

                # Award XP
                add_experience(winner, ctx.guild.id, 50, "duel_win")
                add_experience(loser_data['user_id'], ctx.guild.id, 15, "duel_loss")

                # Handle wager
                if duel['wager'] > 0:
                    update_combatant_stats(winner, ctx.guild.id, prestige=winner_data['prestige'] + duel['wager'])
                    update_combatant_stats(
                        loser_data['user_id'], ctx.guild.id,
                        prestige=max(0, loser_data['prestige'] - duel['wager'])
                    )

                db.commit()

                winner_member = ctx.guild.get_member(winner)
                await ctx.send(embed=medieval_embed(
                    title="🏆 Duel Victory!",
                    description=f"**{winner_member.display_name if winner_member else 'The victor'}** wins the duel!",
                    color_name="green"
                ))
            else:
                # Send turn result
                opponent_id = duel['defender_id'] if is_challenger else duel['challenger_id']
                opponent_member = ctx.guild.get_member(opponent_id)

                embed = medieval_embed(
                    title="⚔️ Action Executed!",
                    description=f"**{ctx.author.display_name}** used **{action.replace('_', ' ').title()}**!",
                    color_name="blue"
                )

                embed.add_field(name="Damage", value=f"{damage} HP", inline=True)
                if critical:
                    embed.add_field(name="Critical Hit!", value="⭐", inline=True)
                embed.add_field(name="Next Turn", value=opponent_member.display_name if opponent_member else "Opponent", inline=True)
                embed.add_field(name="Challenger HP", value=new_challenger_hp if not is_challenger else duel['challenger_hp'], inline=True)
                embed.add_field(name="Defender HP", value=new_defender_hp if is_challenger else duel['defender_hp'], inline=True)

                await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error taking turn: {str(e)}", success=False))

# ---------- WAR SYSTEM ----------
class WarChallengeView(discord.ui.View):
    def __init__(self, challenger_id, defender_id, war_name, terrain, weather):
        super().__init__(timeout=300.0)
        self.challenger_id = challenger_id
        self.defender_id = defender_id
        self.war_name = war_name
        self.terrain = terrain
        self.weather = weather
        self.accepted = False

    @discord.ui.button(label="⚔️ Accept War", style=discord.ButtonStyle.green, emoji="⚔️")
    async def accept_war(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.defender_id:
            return await interaction.response.send_message("This war declaration is not for thee!", ephemeral=True)

        self.accepted = True

        # Create war in database
        try:
            with get_combat_db_connection() as db:
                # Get army powers
                challenger = get_enhanced_combatant(self.challenger_id, interaction.guild.id)
                defender = get_enhanced_combatant(self.defender_id, interaction.guild.id)

                challenger_power = calculate_army_power(challenger)
                defender_power = calculate_army_power(defender)

                db.execute("""
                INSERT INTO faction_wars (guild_id, war_name, war_type, team_a_leader,
                                        team_b_leader, terrain, weather, status,
                                        team_a_army_size, team_b_army_size,
                                        team_a_members, team_b_members)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (interaction.guild.id, self.war_name, "Field Battle",
                      self.challenger_id, self.defender_id, self.terrain,
                      self.weather, "active",
                      challenger_power['total'], defender_power['total'],
                      str([self.challenger_id]), str([self.defender_id])))
                db.commit()

            await interaction.response.send_message(
                embed=medieval_embed(
                    title="⚔️ War Accepted!",
                    description=f"**{self.war_name}** begins! Use `/warturn` to take actions.",
                    color_name="green"
                )
            )
            self.stop()

        except Exception as e:
            await interaction.response.send_message(
                embed=medieval_response(f"Error starting war: {str(e)}", success=False)
            )

    @discord.ui.button(label="🕊️ Refuse War", style=discord.ButtonStyle.red, emoji="🕊️")
    async def refuse_war(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.defender_id:
            return await interaction.response.send_message("This war declaration is not for thee!", ephemeral=True)

        await interaction.response.send_message(
            embed=medieval_embed(
                title="🕊️ Peace Preserved",
                description="The war has been refused. Peace reigns... for now.",
                color_name="blue"
            )
        )
        self.stop()

@bot.command(name="war")
@commands.guild_only()
async def enhanced_war_cmd(ctx, opponent: discord.Member = None, war_name: str = None):
    """Start an enhanced war with terrain and weather effects"""
    try:
        if not war_name or not opponent:
            return await ctx.send(embed=medieval_response(
                "Usage: `!war <war_name> @opponent`",
                success=False
            ))

        if opponent.id == ctx.author.id:
            return await ctx.send(embed=medieval_response(
                "Thou cannot wage war against thyself!",
                success=False
            ))

        # Check if both are registered
        challenger = get_enhanced_combatant(ctx.author.id, ctx.guild.id)
        defender = get_enhanced_combatant(opponent.id, ctx.guild.id)

        if not challenger:
            return await ctx.send(embed=medieval_response(
                f"{ctx.author.display_name} must first register!",
                success=False
            ))

        if not defender:
            return await ctx.send(embed=medieval_response(
                f"{opponent.display_name} must first register!",
                success=False
            ))

        # Generate terrain and weather
        terrain = get_random_terrain()
        weather = get_random_weather()

        # Calculate army powers
        challenger_power = calculate_army_power(challenger)
        defender_power = calculate_army_power(defender)

        # Create war challenge
        embed = medieval_embed(
            title="⚔️ War Declaration!",
            description=f"**{challenger['army_name']}** declares war on **{defender['army_name']}**!",
            color_name="red"
        )

        embed.add_field(name="War Name", value=war_name, inline=True)
        embed.add_field(name="Terrain", value=terrain, inline=True)
        embed.add_field(name="Weather", value=weather, inline=True)

        embed.add_field(
            name=f"{challenger['army_name']} Power",
            value=f"**Total:** {challenger_power['total']:,}\n"
                  f"Infantry: {challenger_power['infantry']:,}\n"
                  f"Cavalry: {challenger_power['cavalry']:,}",
            inline=True
        )

        embed.add_field(
            name=f"{defender['army_name']} Power",
            value=f"**Total:** {defender_power['total']:,}\n"
                  f"Infantry: {defender_power['infantry']:,}\n"
                  f"Cavalry: {defender_power['cavalry']:,}",
            inline=True
        )

        embed.add_field(name="Terrain Effects", value=TERRAIN_EFFECTS[terrain]['description'], inline=False)
        embed.add_field(name="Weather Effects", value=WEATHER_EFFECTS[weather]['description'], inline=False)

        view = WarChallengeView(ctx.author.id, opponent.id, war_name, terrain, weather)
        await ctx.send(embed=embed, view=view)

    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error declaring war: {str(e)}", success=False))

@bot.command(name="warturn")
@commands.guild_only()
async def war_turn_cmd(ctx, tactic: str = None):
    """Take your turn in a war"""
    try:
        # Get active war involving user
        with get_combat_db_connection() as db:
            war = db.execute("""
            SELECT * FROM faction_wars
            WHERE guild_id=? AND status='active' AND
                  (team_a_leader=? OR team_b_leader=?)
            """, (ctx.guild.id, ctx.author.id, ctx.author.id)).fetchone()

            if not war:
                return await ctx.send(embed=medieval_response(
                    "Thou art not in an active war!",
                    success=False
                ))

            # Determine which team user is on
            is_team_a = war['team_a_leader'] == ctx.author.id
            current_team = 'A' if is_team_a else 'B'

            if war['current_team'] != current_team:
                other_team = 'B' if current_team == 'A' else 'A'
                return await ctx.send(embed=medieval_response(
                    f"It is Team {other_team}'s turn!",
                    success=False
                ))

            if not tactic:
                # Show available tactics
                embed = medieval_embed(
                    title="⚔️ War Turn - Choose Tactic",
                    description="Available battle tactics:",
                    color_name="gold"
                )

                for tactic_name, tactic_info in BATTLE_TACTICS.items():
                    embed.add_field(
                        name=tactic_name,
                        value=f"{tactic_info['description']}\nDamage: {tactic_info['damage']}x | Risk: {tactic_info['risk']}x",
                        inline=False
                    )

                return await ctx.send(embed=embed)

            if tactic not in BATTLE_TACTICS:
                return await ctx.send(embed=medieval_response(
                    f"Invalid tactic! Choose from: {', '.join(BATTLE_TACTICS.keys())}",
                    success=False
                ))

            # Get combatants
            team_a_leader = get_enhanced_combatant(war['team_a_leader'], ctx.guild.id)
            team_b_leader = get_enhanced_combatant(war['team_b_leader'], ctx.guild.id)

            if not team_a_leader or not team_b_leader:
                return await ctx.send(embed=medieval_response(
                    "War participants not found!",
                    success=False
                ))

            # Calculate army powers
            team_a_power = calculate_army_power(team_a_leader)
            team_b_power = calculate_army_power(team_b_leader)

            # Get current tactics
            attacker_tactic = tactic
            defender_tactic = war['current_tactic_b'] if is_team_a else war['current_tactic_a']

            # Calculate damage
            if is_team_a:
                damage, surprise, surprise_type = calculate_war_damage(
                    team_a_power['total'], team_b_power['total'],
                    war['terrain'], war['weather'], attacker_tactic, defender_tactic
                )
            else:
                damage, surprise, surprise_type = calculate_war_damage(
                    team_b_power['total'], team_a_power['total'],
                    war['terrain'], war['weather'], attacker_tactic, defender_tactic
                )

            # Calculate casualties
            if is_team_a:
                casualty_rate = calculate_casualties(
                    team_b_power['total'], damage, war['terrain'], war['weather']
                )
                team_b_casualties = int(team_b_power['total'] * casualty_rate)
                team_a_casualties = int(team_a_power['total'] * (casualty_rate * 0.5))
            else:
                casualty_rate = calculate_casualties(
                    team_a_power['total'], damage, war['terrain'], war['weather']
                )
                team_a_casualties = int(team_a_power['total'] * casualty_rate)
                team_b_casualties = int(team_b_power['total'] * (casualty_rate * 0.5))

            # Update war stats
            if is_team_a:
                new_score_a = war['war_score_a'] + damage
                new_score_b = war['war_score_b'] - damage
                db.execute("""
                UPDATE faction_wars
                SET war_score_a=?, war_score_b=?, current_team='B',
                    current_tactic_a=?, turn=turn+1
                WHERE id=?
                """, (new_score_a, new_score_b, tactic, war['id']))
            else:
                new_score_b = war['war_score_b'] + damage
                new_score_a = war['war_score_a'] - damage
                db.execute("""
                UPDATE faction_wars
                SET war_score_b=?, war_score_a=?, current_team='A',
                    current_tactic_b=?, turn=turn+1
                WHERE id=?
                """, (new_score_b, new_score_a, tactic, war['id']))

            # Record casualties
            if is_team_a:
                db.execute("""
                INSERT INTO war_casualties (war_id, user_id, guild_id, soldiers_lost,
                                          casualty_type, description)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (war['id'], war['team_b_leader'], ctx.guild.id, team_b_casualties,
                      "battle", f"Team B suffered {team_b_casualties:,} casualties from Team A's {tactic}"))

                if team_a_casualties > 0:
                    db.execute("""
                    INSERT INTO war_casualties (war_id, user_id, guild_id, soldiers_lost,
                                              casualty_type, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (war['id'], war['team_a_leader'], ctx.guild.id, team_a_casualties,
                          "counterattack", f"Team A suffered {team_a_casualties:,} return casualties"))
            else:
                db.execute("""
                INSERT INTO war_casualties (war_id, user_id, guild_id, soldiers_lost,
                                          casualty_type, description)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (war['id'], war['team_a_leader'], ctx.guild.id, team_a_casualties,
                      "battle", f"Team A suffered {team_a_casualties:,} casualties from Team B's {tactic}"))

                if team_b_casualties > 0:
                    db.execute("""
                    INSERT INTO war_casualties (war_id, user_id, guild_id, soldiers_lost,
                                              casualty_type, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (war['id'], war['team_b_leader'], ctx.guild.id, team_b_casualties,
                          "counterattack", f"Team B suffered {team_b_casualties:,} return casualties"))

            # Record war action
            db.execute("""
            INSERT INTO war_actions (war_id, user_id, guild_id, action_type,
                                   target_team, army_size_used, soldiers_lost,
                                   total_damage, description, critical_success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (war['id'], ctx.author.id, ctx.guild.id, tactic,
                  'B' if is_team_a else 'A',
                  team_a_power['total'] if is_team_a else team_b_power['total'],
                  team_b_casualties if is_team_a else team_a_casualties,
                  damage, f"Used {tactic} tactic", surprise))

            db.commit()

            # Check for war end
            if war['turn'] >= 10:  # 10 rounds max
                winner = 'A' if new_score_a > new_score_b else 'B' if new_score_b > new_score_a else 'draw'

                db.execute("""
                UPDATE faction_wars SET status='ended', ended_at=?
                WHERE id=?
                """, (utcnow().isoformat(), war['id']))

                # Award XP to winner
                if winner != 'draw':
                    winner_id = war['team_a_leader'] if winner == 'A' else war['team_b_leader']
                    add_experience(winner_id, ctx.guild.id, 200, "war_victory")

                    loser_id = war['team_b_leader'] if winner == 'A' else war['team_a_leader']
                    add_experience(loser_id, ctx.guild.id, 50, "war_participation")

                db.commit()

                winner_name = team_a_leader['character_name'] if winner == 'A' else team_b_leader['character_name'] if winner == 'B' else "None"
                embed = medieval_embed(
                    title="🏆 War Concluded!",
                    description=f"**{war['war_name']}** has ended after {war['turn']} rounds!\n"
                              f"**Winner:** {winner_name if winner != 'draw' else 'Draw!'}\n"
                              f"Final Score - Team A: {new_score_a:,} | Team B: {new_score_b:,}",
                    color_name="gold" if winner == 'draw' else "green"
                )

                return await ctx.send(embed=embed)

            # Send turn result
            embed = medieval_embed(
                title="⚔️ War Turn Executed!",
                description=f"**{ctx.author.display_name}** used **{tactic}**!",
                color_name="blue"
            )

            embed.add_field(name="Damage Inflicted", value=f"{damage:,}", inline=True)
            embed.add_field(name="Enemy Casualties", value=f"{team_b_casualties if is_team_a else team_a_casualties:,}", inline=True)
            embed.add_field(name="Friendly Casualties", value=f"{team_a_casualties if is_team_a else team_b_casualties:,}", inline=True)

            if surprise:
                embed.add_field(name="Surprise!", value=f"{surprise_type.capitalize()} attack successful!", inline=False)

            embed.add_field(name="Current Score",
                          value=f"Team A: {new_score_a if is_team_a else war['war_score_a']:,} | Team B: {new_score_b if not is_team_a else war['war_score_b']:,}",
                          inline=False)

            next_team = 'B' if current_team == 'A' else 'A'
            next_leader = war['team_b_leader'] if next_team == 'B' else war['team_a_leader']
            next_member = ctx.guild.get_member(next_leader)

            embed.add_field(name="Next Turn", value=f"Team {next_team} - {next_member.display_name if next_member else 'Unknown'}", inline=False)

            await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error taking war turn: {str(e)}", success=False))

# ---------- ARMY MANAGEMENT ----------
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

        await interaction.response.send_message(embed=embed, ephemeral=True)

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

# ---------- FORMATION COMMAND ----------
@bot.command(name="formation")
@commands.guild_only()
async def formation_cmd(ctx, formation_name: str = None):
    """Change or view battle formations"""
    try:
        combatant = get_enhanced_combatant(ctx.author.id, ctx.guild.id)
        if not combatant:
            return await ctx.send(embed=medieval_response(
                "Thou must first register as a combatant!",
                success=False
            ))

        if not formation_name:
            # Show available formations
            with get_combat_db_connection() as db:
                formations = db.execute("""
                SELECT formation_name, infantry_bonus, cavalry_bonus, archer_bonus,
                       defense_bonus, movement_penalty, description
                FROM battle_formations
                """).fetchall()

                embed = medieval_embed(
                    title="⚔️ Available Formations",
                    description="Choose a formation with `!formation <name>`",
                    color_name="gold"
                )

                for formation in formations:
                    embed.add_field(
                        name=f"**{formation['formation_name']}**",
                        value=f"{formation['description']}\n"
                              f"Infantry: {formation['infantry_bonus']}x | "
                              f"Cavalry: {formation['cavalry_bonus']}x | "
                              f"Archers: {formation['archer_bonus']}x | "
                              f"Defense: {formation['defense_bonus']}x",
                        inline=False
                    )

                await ctx.send(embed=embed)
                return

        # Change formation
        with get_combat_db_connection() as db:
            # Get formation details
            formation = db.execute("""
            SELECT * FROM battle_formations WHERE formation_name=?
            """, (formation_name,)).fetchone()

            if not formation:
                return await ctx.send(embed=medieval_response(
                    "Formation not found!",
                    success=False
                ))

            # Update army formation
            db.execute("""
            UPDATE armies SET battle_formation=? WHERE user_id=? AND guild_id=?
            """, (formation_name, ctx.author.id, ctx.guild.id))
            db.commit()

            embed = medieval_embed(
                title="✅ Formation Changed!",
                description=f"Thy army now uses the **{formation_name}** formation!\n*{formation['description']}*",
                color_name="green"
            )

            await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error changing formation: {str(e)}", success=False))

# ---------- ALLOCATE COMMAND ----------
@bot.command(name="allocate")
@commands.guild_only()
async def allocate_cmd(ctx, stat: str = None, amount: int = None):
    """Allocate stat points"""
    try:
        combatant = get_enhanced_combatant(ctx.author.id, ctx.guild.id)
        if not combatant:
            return await ctx.send(embed=medieval_response(
                "Thou must first register as a combatant!",
                success=False
            ))

        if combatant['stat_points'] <= 0:
            return await ctx.send(embed=medieval_response(
                "Thou hast no stat points to allocate!",
                success=False
            ))

        if not stat or not amount:
            # Show current stats and available points
            embed = medieval_embed(
                title="📊 Stat Allocation",
                description=f"**Available Stat Points:** {combatant['stat_points']}",
                color_name="gold"
            )

            embed.add_field(name="⚔️ Strength", value=combatant['strength'], inline=True)
            embed.add_field(name="🏃 Agility", value=combatant['agility'], inline=True)
            embed.add_field(name="🧠 Intelligence", value=combatant['intelligence'], inline=True)
            embed.add_field(name="❤️ Vitality", value=combatant['vitality'], inline=True)
            embed.add_field(name="💬 Charisma", value=combatant['charisma'], inline=True)
            embed.add_field(name="🍀 Luck", value=combatant['luck'], inline=True)

            embed.add_field(
                name="Usage",
                value="Use `!allocate <stat> <amount>`\nExample: `!allocate strength 2`",
                inline=False
            )

            await ctx.send(embed=embed)
            return

        # Validate stat name
        valid_stats = ['strength', 'agility', 'intelligence', 'vitality', 'charisma', 'luck']
        if stat.lower() not in valid_stats:
            return await ctx.send(embed=medieval_response(
                f"Invalid stat! Choose from: {', '.join(valid_stats)}",
                success=False
            ))

        # Validate amount
        if amount <= 0:
            return await ctx.send(embed=medieval_response(
                "Must allocate a positive number of points!",
                success=False
            ))

        if amount > combatant['stat_points']:
            return await ctx.send(embed=medieval_response(
                f"Thou only hast {combatant['stat_points']} points available!",
                success=False
            ))

        # Allocate points
        current_value = combatant[stat.lower()]
        new_value = current_value + amount
        new_stat_points = combatant['stat_points'] - amount

        update_combatant_stats(
            ctx.author.id, ctx.guild.id,
            **{stat.lower(): new_value, 'stat_points': new_stat_points}
        )

        embed = medieval_embed(
            title="✅ Stats Allocated!",
            description=f"**{amount}** points allocated to **{stat.title()}**",
            color_name="green"
        )

        embed.add_field(name="New Value", value=new_value, inline=True)
        embed.add_field(name="Remaining Points", value=new_stat_points, inline=True)

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error allocating stats: {str(e)}", success=False))

# ---------- HELP COMMAND ----------
@bot.command(name="help")
@commands.guild_only()
async def enhanced_help_cmd(ctx):
    """Display comprehensive help guide"""
    embed = medieval_embed(
        title="🎖️ Medieval Combat System - Complete Guide",
        description="*Hark! A comprehensive guide to strategic warfare and command!*",
        color_name="gold"
    )

    embed.add_field(
        name="📝 Registration & Setup",
        value="`!register` - Registration with titles/factions\n"
              "`!stats [@user]` - View statistics\n"
              "`!allocate <stat> <amount>` - Assign stat points",
        inline=False
    )

    embed.add_field(
        name="🏰 Army Management",
        value="`!armymanage` - Open army management interface\n"
              "`!recruit` - Recruitment with supply costs\n"
              "`!train <amount>` - Train multiple unit types\n"
              "`!formation [name]` - Change/view battle formations",
        inline=False
    )

    embed.add_field(
        name="⚔️ Army Composition",
        value="**Infantry:** Basic soldiers\n"
              "**Knights:** Elite warriors (10x power) - 7% chance when training\n"
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
        name="⚔️ Combat Systems",
        value="`!duel @opponent [wager]` - Duel with terrain/weather effects\n"
              "`!turn <action>` - Take your turn in a duel\n"
              "`!war <name> @opponent` - Declare war\n"
              "`!warturn <tactic>` - Take war turn",
        inline=False
    )

    embed.add_field(
        name="🌤️ Environmental Effects",
        value="**Terrain:** Affects unit effectiveness\n"
              "**Weather:** Impacts morale and visibility\n"
              "**Surprises:** Ambush chances based on terrain\n"
              "**Casualties:** Realistic casualty calculations",
        inline=False
    )

    embed.add_field(
        name="📊 Resource Management",
        value="**Morale:** Affects effectiveness (50-150%)\n"
              "**Supplies:** Required for actions (consumed daily)\n"
              "**Daily Actions:** 3 actions per day\n"
              "**Desertion:** Recruits desert based on morale/supplies",
        inline=False
    )

    embed.add_field(
        name="⚡ Enhanced Features",
        value="• Multiple unit types with specialties\n"
              "• Terrain and weather effects on combat\n"
              "• Morale and supply systems\n"
              "• Battle formations with bonuses\n"
              "• Army type specializations\n"
              "• Realistic casualty calculations\n"
              "• Surprise attacks and ambushes\n"
              "• Knight recruitment system (7% chance)",
        inline=False
    )

    embed.add_field(
        name="🎮 Slash Commands",
        value="All commands also available as slash commands!\n"
              "Just type `/` to see available commands",
        inline=False
    )

    await ctx.send(embed=embed)

# ---------- ACHIEVEMENTS SYSTEM ----------
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
                    combatant = get_enhanced_combatant(army['user_id'], army['guild_id'])
                    if not combatant:
                        continue

                    # Calculate total army size
                    total_army = (
                        combatant['current_soldiers'] +
                        combatant['total_knights'] * 10 +
                        combatant['total_archers'] * 3 +
                        combatant['total_cavalry'] * 8 +
                        combatant['total_siege'] * 15
                    )

                    # Calculate days since last check
                    last_check = dt.fromisoformat(combatant['last_supply_check']) if combatant['last_supply_check'] else utcnow()
                    hours_passed = max(1, (utcnow() - last_check).seconds // 3600)

                    # Calculate supply consumption
                    consumption = calculate_supply_consumption(total_army, hours_passed / 24)
                    new_supplies = max(0, combatant['supplies'] - consumption)

                    # Update supplies
                    db.execute("""
                    UPDATE armies
                    SET supplies=?, last_supply_check=?
                    WHERE user_id=? AND guild_id=?
                    """, (new_supplies, utcnow().isoformat(), army['user_id'], army['guild_id']))

                    # If supplies are very low, apply morale penalty
                    if new_supplies <= 10:
                        db.execute("""
                        UPDATE armies
                        SET morale=GREATEST(1, morale - 5)
                        WHERE user_id=? AND guild_id=?
                        """, (army['user_id'], army['guild_id']))

                except Exception as e:
                    print(f"Error updating supplies for army {army['user_id']}: {e}")

            db.commit()

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

@tasks.loop(hours=24)
async def reset_daily_actions():
    """Reset daily actions for all players"""
    try:
        print("⚙️ Resetting daily actions...")
        with get_combat_db_connection() as db:
            db.execute("""
            UPDATE armies
            SET daily_actions=3, last_daily_reset=?
            WHERE datetime(last_daily_reset) <= datetime('now', '-1 day')
            """, (utcnow().isoformat(),))
            db.commit()

        print("✅ Daily actions reset")
    except Exception as e:
        print(f"Error resetting daily actions: {e}")

# ---------- ON READY ----------
@bot.event
async def on_ready():
    try:
        print(f'🎖️ Medieval Combat Bot hath awakened as {bot.user}')
        print('⚔️ Enhanced duel system with terrain/weather effects!')
        print('🏰 Comprehensive army management with multiple unit types!')
        print('📊 Morale and supply systems activated!')
        print('🎯 Army type specializations and formations!')
        print('⚡ 7% knight chance in training!')
        print('🌤️ Terrain and weather effects on combat!')
        print('💀 Realistic casualty calculations!')
        print('🔗 Prefix and slash commands synchronized!')

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
        reset_daily_actions.start()

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

# ---------- KEEP-ALIVE SERVER ----------
app = flask.Flask(__name__)

@app.route('/')
def home():
    return "Medieval Combat Bot is alive! ⚔️ Strategic warfare & army management running."

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

# ---------- RUN ----------
if __name__ == "__main__":
    try:
        print("🎖️ Starting Medieval Combat Bot...")
        print("⚔️ Preparing duel, army & war systems...")
        print("🏰 Initializing comprehensive combat database...")
        print("🌤️ Terrain & weather effects ready!")
        print("⚡ Knight recruitment system activated!")
        print("💀 Casualty calculations online!")
        print("🎮 Prefix and slash commands loaded!")

        # Start Flask keep-alive server in background thread
        Thread(target=run_flask, daemon=True).start()

        # Initialize database and start the bot
        init_combat_db()
        bot.run(TOKEN)
    except Exception as e:
        print(f"Failed to start combat bot: {e}")
        traceback.print_exc()
