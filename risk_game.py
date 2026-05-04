#!/usr/bin/env python3
"""
RISK - The Classic Board Game of Global Domination
Full Python/Pygame implementation with:
- Complete world map with all 42 territories
- 1-6 players (human or AI simulation)
- Full RISK rules: reinforcements, attacks, fortification
- Territory cards with set trading
- Continent bonuses
- AI strategy logic
- Animated dice rolling
- Card management UI
"""

import pygame
import sys
import random
import math
import time
import json
import os
import glob
from datetime import datetime

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "risk_saves")
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

pygame.init()
pygame.font.init()

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1400, 900
MAP_W, MAP_H = 1000, 700
MAP_X, MAP_Y = 20, 120

FPS = 60

# Colours
COL_BG         = (15, 20, 35)
COL_OCEAN      = (20, 45, 80)
COL_PANEL      = (25, 32, 50)
COL_PANEL2     = (35, 45, 68)
COL_BORDER     = (60, 80, 120)
COL_TEXT       = (220, 230, 245)
COL_TEXT_DIM   = (130, 150, 180)
COL_GOLD       = (220, 180, 50)
COL_RED        = (200, 60, 60)
COL_GREEN      = (60, 180, 80)
COL_WHITE      = (255, 255, 255)
COL_HIGHLIGHT  = (255, 220, 60)
COL_ATTACK_SRC = (255, 180, 0)
COL_ATTACK_DST = (255, 60, 60)

PLAYER_COLORS = [
    (220, 60,  60),   # Red
    (60,  120, 220),  # Blue
    (60,  180, 80),   # Green
    (220, 180, 50),   # Yellow
    (180, 60,  220),  # Purple
    (220, 130, 50),   # Orange
]
PLAYER_NAMES_DEFAULT = ["Red", "Blue", "Green", "Yellow", "Purple", "Orange"]

CONTINENT_COLORS = {
    "North America": (140, 80,  50),
    "South America": (160, 120, 50),
    "Europe":        (80,  110, 160),
    "Africa":        (160, 140, 60),
    "Asia":          (120, 80,  140),
    "Australia":     (60,  150, 120),
}
CONTINENT_BONUS = {
    "North America": 5,
    "South America": 2,
    "Europe":        5,
    "Africa":        3,
    "Asia":          7,
    "Australia":     2,
}

# Card trade-in values (cumulative sets)
TRADE_VALUES = [4, 6, 8, 10, 12, 15]  # first 6 sets; after that +5 each

# ─── TERRITORY DATA ───────────────────────────────────────────────────────────
# Each entry: name, continent, (x,y) map pixel position (relative to MAP area), neighbours list
TERRITORY_DATA = [
    # NORTH AMERICA
    ("Alaska",           "North America", (65,  95),  ["Northwest Territory", "Alberta", "Kamchatka"]),
    ("Northwest Territory","North America",(165, 80),  ["Alaska","Alberta","Ontario","Greenland"]),
    ("Greenland",        "North America", (310, 55),  ["Northwest Territory","Ontario","Quebec","Iceland"]),
    ("Alberta",          "North America", (130, 145), ["Alaska","Northwest Territory","Ontario","Western US"]),
    ("Ontario",          "North America", (195, 155), ["Northwest Territory","Greenland","Alberta","Quebec","Western US","Eastern US"]),
    ("Quebec",           "North America", (270, 155), ["Greenland","Ontario","Eastern US"]),
    ("Western US",       "North America", (130, 215), ["Alberta","Ontario","Eastern US","Central America"]),
    ("Eastern US",       "North America", (210, 220), ["Ontario","Quebec","Western US","Central America"]),
    ("Central America",  "North America", (165, 285), ["Western US","Eastern US","Venezuela"]),
    # SOUTH AMERICA
    ("Venezuela",        "South America", (230, 330), ["Central America","Peru","Brazil"]),
    ("Peru",             "South America", (240, 405), ["Venezuela","Brazil","Argentina"]),
    ("Brazil",           "South America", (295, 380), ["Venezuela","Peru","Argentina","North Africa"]),
    ("Argentina",        "South America", (255, 460), ["Peru","Brazil"]),
    # EUROPE
    ("Iceland",          "Europe",        (390, 90),  ["Greenland","Great Britain","Scandinavia"]),
    ("Great Britain",    "Europe",        (400, 165), ["Iceland","Scandinavia","Northern Europe","Western Europe"]),
    ("Scandinavia",      "Europe",        (470, 100), ["Iceland","Great Britain","Northern Europe","Ukraine"]),
    ("Northern Europe",  "Europe",        (465, 175), ["Great Britain","Scandinavia","Western Europe","Southern Europe","Ukraine"]),
    ("Western Europe",   "Europe",        (415, 240), ["Great Britain","Northern Europe","Southern Europe","North Africa"]),
    ("Southern Europe",  "Europe",        (480, 240), ["Western Europe","Northern Europe","Ukraine","North Africa","Egypt","Middle East"]),
    ("Ukraine",          "Europe",        (545, 160), ["Scandinavia","Northern Europe","Southern Europe","Ural","Afghanistan","Middle East"]),
    # AFRICA
    ("North Africa",     "Africa",        (430, 340), ["Western Europe","Southern Europe","Egypt","East Africa","Congo","Brazil"]),
    ("Egypt",            "Africa",        (505, 320), ["Southern Europe","North Africa","East Africa","Middle East"]),
    ("Congo",            "Africa",        (485, 405), ["North Africa","East Africa","South Africa"]),
    ("East Africa",      "Africa",        (535, 375), ["Egypt","North Africa","Congo","South Africa","Madagascar","Middle East"]),
    ("South Africa",     "Africa",        (495, 460), ["Congo","East Africa","Madagascar"]),
    ("Madagascar",       "Africa",        (570, 450), ["East Africa","South Africa"]),
    # ASIA
    ("Middle East",      "Asia",          (575, 280), ["Southern Europe","Ukraine","Egypt","East Africa","Afghanistan","India"]),
    ("Afghanistan",      "Asia",          (620, 200), ["Ukraine","Ural","China","India","Middle East"]),
    ("Ural",             "Asia",          (635, 130), ["Ukraine","Afghanistan","Siberia","China"]),
    ("Siberia",          "Asia",          (700, 100), ["Ural","China","Mongolia","Irkutsk","Yakutsk"]),
    ("China",            "Asia",          (695, 195), ["Afghanistan","Ural","Siberia","Mongolia","Southeast Asia","India"]),
    ("India",            "Asia",          (655, 265), ["Middle East","Afghanistan","China","Southeast Asia"]),
    ("Southeast Asia",   "Asia",          (735, 270), ["China","India","Indonesia"]),
    ("Mongolia",         "Asia",          (745, 165), ["Siberia","China","Japan","Irkutsk","Kamchatka"]),
    ("Japan",            "Asia",          (815, 175), ["Mongolia","Kamchatka"]),
    ("Irkutsk",          "Asia",          (760, 125), ["Siberia","Mongolia","Kamchatka","Yakutsk"]),
    ("Yakutsk",          "Asia",          (775, 80),  ["Siberia","Irkutsk","Kamchatka"]),
    ("Kamchatka",        "Asia",          (840, 100), ["Yakutsk","Irkutsk","Mongolia","Japan","Alaska"]),
    # AUSTRALIA
    ("Indonesia",        "Australia",     (760, 355), ["Southeast Asia","New Guinea","Western Australia"]),
    ("New Guinea",       "Australia",     (835, 330), ["Indonesia","Western Australia","Eastern Australia"]),
    ("Western Australia","Australia",     (800, 430), ["Indonesia","New Guinea","Eastern Australia"]),
    ("Eastern Australia","Australia",     (870, 415), ["New Guinea","Western Australia"]),
]

CARD_TYPES = ["Infantry", "Cavalry", "Artillery", "Wild"]

# ─── DATA CLASSES ─────────────────────────────────────────────────────────────

@dataclass
class Territory:
    name: str
    continent: str
    pos: tuple
    neighbours: list
    owner: Optional[int] = None   # player index
    armies: int = 0

@dataclass
class Card:
    territory: str   # "" for wild
    card_type: str   # Infantry / Cavalry / Artillery / Wild

@dataclass
class Player:
    index: int
    name: str
    color: tuple
    is_human: bool
    armies: int = 0
    cards: list = field(default_factory=list)
    alive: bool = True

# ─── GAME STATE ───────────────────────────────────────────────────────────────

class Phase(Enum):
    SETUP_PLAYERS   = 0
    SETUP_PLACE     = 1
    REINFORCE       = 2
    ATTACK          = 3
    FORTIFY         = 4
    GAME_OVER       = 5

class RiskGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("⚔  RISK — Global Domination")
        self.clock = pygame.time.Clock()

        # Fonts
        self.font_title  = pygame.font.SysFont("Georgia", 28, bold=True)
        self.font_large  = pygame.font.SysFont("Georgia", 22, bold=True)
        self.font_med    = pygame.font.SysFont("Verdana", 16)
        self.font_small  = pygame.font.SysFont("Verdana", 13)
        self.font_tiny   = pygame.font.SysFont("Verdana", 11)
        self.font_dice   = pygame.font.SysFont("Courier", 36, bold=True)

        self._build_territories()
        self._build_deck()

        self.players: list[Player] = []
        self.current_player = 0
        self.phase = Phase.SETUP_PLAYERS
        self.trade_count = 0   # how many sets traded globally

        # UI state
        self.selected_territory: Optional[str] = None
        self.attack_source: Optional[str] = None
        self.attack_target: Optional[str] = None
        self.message = "Welcome to RISK! Configure players below."
        self.log: list[str] = []
        self.dice_result: list = []   # [(val, won), ...]
        self.show_dice = False
        self.dice_timer = 0

        # Setup UI
        self.num_players = 2
        self.player_types = [True, False]   # True=human, False=AI
        self.player_name_inputs = list(PLAYER_NAMES_DEFAULT)
        self.active_input = -1
        self.start_btn = pygame.Rect(SCREEN_W//2 - 100, 750, 200, 45)

        # Fortify
        self.fortify_source: Optional[str] = None

        # Show cards overlay
        self.show_cards = False

        # Save / Load menu state
        self.show_save_menu = False
        self.show_load_menu = False
        self.save_slot_input = ""
        self.save_input_active = False
        self._load_saves_cache = []   # list of (path, display_name)
        self._load_selected = -1      # highlighted slot index

        # AI delay
        self.ai_timer = 0
        self.ai_action_pending = False

        # Armies to place this turn
        self.armies_to_place = 0
        self.setup_armies_remaining: list[int] = []

        # Winner
        self.winner = None

    # ── Territory construction ────────────────────────────────────────────────

    def _build_territories(self):
        self.territories: dict[str, Territory] = {}
        for name, cont, pos, nbrs in TERRITORY_DATA:
            px = MAP_X + int(pos[0] * MAP_W / 900)
            py = MAP_Y + int(pos[1] * MAP_H / 520)
            self.territories[name] = Territory(name, cont, (px, py), nbrs)

    def _build_deck(self):
        self.deck: list[Card] = []
        types = ["Infantry", "Cavalry", "Artillery"]
        terr_names = [t for t, _, _, _ in TERRITORY_DATA]
        for i, name in enumerate(terr_names):
            self.deck.append(Card(name, types[i % 3]))
        self.deck.append(Card("", "Wild"))
        self.deck.append(Card("", "Wild"))
        random.shuffle(self.deck)
        self.discard: list[Card] = []

    def draw_card(self) -> Optional[Card]:
        if not self.deck:
            self.deck = self.discard[:]
            self.discard = []
            random.shuffle(self.deck)
        if self.deck:
            return self.deck.pop()
        return None

    # ── Setup ─────────────────────────────────────────────────────────────────

    def start_game(self):
        self.players = []
        for i in range(self.num_players):
            p = Player(
                index=i,
                name=self.player_name_inputs[i],
                color=PLAYER_COLORS[i],
                is_human=self.player_types[i],
            )
            p._earned_card = False   # FIX BUG 4: always initialise flag
            self.players.append(p)

        # Starting armies per player count
        army_map = {2: 40, 3: 35, 4: 30, 5: 25, 6: 20}
        start_armies = army_map.get(self.num_players, 20)
        self.setup_armies_remaining = [start_armies] * self.num_players  # FIX BUG 5: always fresh list

        # Reset territories
        for t in self.territories.values():
            t.owner = None
            t.armies = 0

        self._build_deck()
        self.current_player = 0
        self.phase = Phase.SETUP_PLACE
        self.message = f"{self.players[0].name}: Click an unclaimed territory to place your first army."
        self._log(f"Game started with {self.num_players} players!")

        # If first player is AI, schedule action
        if not self.players[self.current_player].is_human:
            self.ai_action_pending = True
            self.ai_timer = pygame.time.get_ticks() + 600

    def _log(self, msg: str):
        self.log.insert(0, msg)
        if len(self.log) > 25:
            self.log = self.log[:25]

    # ── Core game logic ───────────────────────────────────────────────────────

    def territories_of(self, player_idx: int) -> list[Territory]:
        return [t for t in self.territories.values() if t.owner == player_idx]

    def calculate_reinforcements(self, player_idx: int) -> int:
        terrs = len(self.territories_of(player_idx))
        armies = max(3, terrs // 3)
        for cont, bonus in CONTINENT_BONUS.items():
            if all(t.owner == player_idx for t in self.territories.values() if t.continent == cont):
                armies += bonus
        return armies

    def trade_in_cards(self, player: Player, card_indices: list[int]) -> int:
        """Trade 3 cards for armies. Returns armies gained or -1 on invalid."""
        if len(card_indices) != 3:
            return -1
        cards = [player.cards[i] for i in card_indices]
        types = [c.card_type for c in cards]

        valid = False
        # Three of same
        for t in ["Infantry", "Cavalry", "Artillery"]:
            if types.count(t) == 3 or (types.count(t) == 2 and "Wild" in types):
                valid = True
        # One of each
        has_types = set(t for t in types if t != "Wild")
        wilds = types.count("Wild")
        if len(has_types) + wilds >= 3 and len(has_types) <= 3:
            valid = True
        if "Infantry" in has_types and "Cavalry" in has_types and "Artillery" in has_types:
            valid = True
        if wilds >= 1 and len(has_types) == 2:
            valid = True
        if wilds >= 2:
            valid = True

        if not valid:
            return -1

        self.trade_count += 1
        idx = self.trade_count - 1
        if idx < len(TRADE_VALUES):
            armies = TRADE_VALUES[idx]
        else:
            armies = TRADE_VALUES[-1] + (idx - len(TRADE_VALUES) + 1) * 5

        # Bonus 2 if any card matches owned territory
        for c in cards:
            if c.territory and c.territory in self.territories and \
               self.territories[c.territory].owner == player.index:
                armies += 2
                break

        # Remove cards (in reverse index order)
        for i in sorted(card_indices, reverse=True):
            self.discard.append(player.cards.pop(i))

        return armies

    def roll_dice(self, n: int) -> list[int]:
        return sorted([random.randint(1, 6) for _ in range(n)], reverse=True)

    def do_attack(self, atk_name: str, def_name: str, atk_dice: int, def_dice: int):
        atk = self.territories[atk_name]
        df  = self.territories[def_name]
        a_rolls = self.roll_dice(atk_dice)
        d_rolls = self.roll_dice(def_dice)

        a_losses = 0
        d_losses = 0
        pairs = min(len(a_rolls), len(d_rolls))
        results = []
        for i in range(pairs):
            if a_rolls[i] > d_rolls[i]:
                d_losses += 1
                results.append((a_rolls[i], d_rolls[i], True))
            else:
                a_losses += 1
                results.append((a_rolls[i], d_rolls[i], False))

        atk.armies -= a_losses
        df.armies  -= d_losses

        self.dice_result = results
        self.show_dice = True
        self.dice_timer = pygame.time.get_ticks() + 2500

        msg = f"{atk.name} → {df.name}: Rolled {a_rolls} vs {d_rolls}"
        self._log(msg)

        if df.armies <= 0:
            # Conquer
            move = atk_dice  # min armies moved
            if move >= atk.armies:
                move = atk.armies - 1
            old_owner = df.owner
            df.owner = atk.owner
            df.armies = max(1, move)
            atk.armies -= df.armies
            if atk.armies < 1:
                atk.armies = 1
            self._log(f"⚔  {self.players[atk.owner].name} conquered {df.name}!")

            # Award card
            self.players[atk.owner]._earned_card = True

            # Check if defender eliminated
            if old_owner is not None and len(self.territories_of(old_owner)) == 0:
                self.players[old_owner].alive = False
                loser = self.players[old_owner]
                winner_p = self.players[atk.owner]
                self._log(f"💀 {loser.name} has been eliminated!")
                # Transfer cards
                for c in loser.cards:
                    winner_p.cards.append(c)
                loser.cards = []

        self._check_win()
        return a_losses, d_losses

    def _check_win(self):
        alive = [p for p in self.players if p.alive]
        if len(alive) == 1:
            self.winner = alive[0]
            self.phase = Phase.GAME_OVER
            self._log(f"🏆 {self.winner.name} has conquered the world!")

    def end_turn(self):
        """Advance to next living player, begin reinforcement phase."""
        # Guard: don't advance if game is already over
        if self.phase == Phase.GAME_OVER:
            return

        p = self.players[self.current_player]
        if p._earned_card:
            card = self.draw_card()
            if card:
                p.cards.append(card)
                self._log(f"{p.name} drew a {card.card_type} card ({card.territory or 'Wild'})")
            p._earned_card = False

        # Next player
        for _ in range(len(self.players)):
            self.current_player = (self.current_player + 1) % len(self.players)
            if self.players[self.current_player].alive:
                break

        # Guard again after player advancement (might have triggered win elsewhere)
        if self.phase == Phase.GAME_OVER:
            return

        self.phase = Phase.REINFORCE
        self.selected_territory = None
        self.attack_source = None
        self.attack_target = None
        self.fortify_source = None

        cp = self.players[self.current_player]
        self.armies_to_place = self.calculate_reinforcements(self.current_player)
        self._log(f"--- {cp.name}'s turn: {self.armies_to_place} reinforcements ---")
        self.message = f"{cp.name}: Reinforce! {self.armies_to_place} armies to place."

        if not cp.is_human:
            self.ai_action_pending = True
            self.ai_timer = pygame.time.get_ticks() + 800
            self.ai_timer = pygame.time.get_ticks() + 800

    # ── AI Logic ──────────────────────────────────────────────────────────────

    def ai_take_action(self):
        cp = self.players[self.current_player]

        if self.phase == Phase.SETUP_PLACE:
            self._ai_setup_place(cp)
        elif self.phase == Phase.REINFORCE:
            self._ai_reinforce(cp)
        elif self.phase == Phase.ATTACK:
            self._ai_attack(cp)
        elif self.phase == Phase.FORTIFY:
            self._ai_fortify(cp)
        self.ai_action_pending = False

    def _ai_setup_place(self, cp):
        """AI claims or reinforces during setup."""
        unclaimed = [t for t in self.territories.values() if t.owner is None]
        my_terrs = self.territories_of(cp.index)
        if unclaimed:
            t = random.choice(unclaimed)
            t.owner = cp.index
            t.armies = 1
            self.setup_armies_remaining[cp.index] -= 1
            self._log(f"{cp.name} claims {t.name}")
        elif self.setup_armies_remaining[cp.index] > 0:
            # Reinforce own weakest border
            borders = [t for t in my_terrs if any(
                self.territories[n].owner != cp.index for n in t.neighbours if n in self.territories)]
            if borders:
                t = min(borders, key=lambda x: x.armies)
            else:
                t = random.choice(my_terrs) if my_terrs else None
            if t:
                t.armies += 1
                self.setup_armies_remaining[cp.index] -= 1
        self._advance_setup()

    def _advance_setup(self):
        # Check if all territories claimed and all setup armies placed
        unclaimed = any(t.owner is None for t in self.territories.values())
        all_done = not unclaimed and all(a == 0 for a in self.setup_armies_remaining)
        if all_done:
            self.phase = Phase.REINFORCE
            self.current_player = 0
            while not self.players[self.current_player].alive:
                self.current_player = (self.current_player + 1) % len(self.players)
            cp = self.players[self.current_player]
            self.armies_to_place = self.calculate_reinforcements(self.current_player)
            self._log(f"Setup complete! {cp.name} goes first.")
            self.message = f"{cp.name}: Your turn! Reinforce {self.armies_to_place} armies."
            if not cp.is_human:
                self.ai_action_pending = True
                self.ai_timer = pygame.time.get_ticks() + 800
        else:
            # Move to next player in setup
            next_p = (self.current_player + 1) % len(self.players)
            for _ in range(len(self.players)):
                if self.players[next_p].alive and (
                    any(t.owner is None for t in self.territories.values()) or
                    self.setup_armies_remaining[next_p] > 0
                ):
                    break
                next_p = (next_p + 1) % len(self.players)
            self.current_player = next_p
            cp = self.players[next_p]
            self.message = f"{cp.name}: Place an army. ({self.setup_armies_remaining[next_p]} left)"
            if not cp.is_human:
                self.ai_action_pending = True
                self.ai_timer = pygame.time.get_ticks() + 500

    def _ai_reinforce(self, cp):
        # Trade cards if 5+
        if len(cp.cards) >= 5:
            self._ai_trade_cards(cp)
        # Place all armies on strongest border territory
        my_terrs = self.territories_of(cp.index)
        borders = [t for t in my_terrs if any(
            self.territories[n].owner != cp.index for n in t.neighbours if n in self.territories)]
        targets = borders if borders else my_terrs
        if targets:
            t = min(targets, key=lambda x: x.armies)
            t.armies += self.armies_to_place
            self._log(f"{cp.name} reinforced {t.name} (+{self.armies_to_place})")
            self.armies_to_place = 0
        self.phase = Phase.ATTACK
        self._log(f"{cp.name} attacks!")
        self.ai_action_pending = True
        self.ai_timer = pygame.time.get_ticks() + 700

    def _ai_trade_cards(self, cp):
        cards = cp.cards
        # Find any valid set of 3
        for combo in self._find_valid_combo(cards):
            gained = self.trade_in_cards(cp, combo)
            if gained > 0:
                self.armies_to_place += gained
                self._log(f"{cp.name} traded cards for {gained} armies")
                return

    def _find_valid_combo(self, cards):
        from itertools import combinations
        for combo in combinations(range(len(cards)), 3):
            types = [cards[i].card_type for i in combo]
            if self._is_valid_trade(types):
                yield list(combo)

    def _is_valid_trade(self, types):
        wilds = types.count("Wild")
        non_wild = [t for t in types if t != "Wild"]
        if wilds >= 3:
            return True
        if wilds == 2:
            return True
        if wilds == 1:
            return len(set(non_wild)) <= 2
        # No wilds
        if len(set(types)) == 1:
            return True
        if set(types) == {"Infantry", "Cavalry", "Artillery"}:
            return True
        return False

    def _ai_attack(self, cp):
        """Attack aggressively — keep going until no territory has enough armies."""
        safety = 300  # prevent infinite loop

        while safety > 0:
            safety -= 1
            my_terrs = self.territories_of(cp.index)
            attacks = []
            for src in my_terrs:
                if src.armies <= 1:
                    continue
                for nbr_name in src.neighbours:
                    if nbr_name not in self.territories:
                        continue
                    nbr = self.territories[nbr_name]
                    if nbr.owner != cp.index and nbr.owner is not None:
                        ratio = src.armies / max(1, nbr.armies)
                        attacks.append((ratio, src, nbr))

            if not attacks:
                break

            attacks.sort(key=lambda x: -x[0])
            best_ratio, best_src, best_dst = attacks[0]

            # Always attack best available target if we have > 1 army
            if best_src.armies > 1:
                atk_dice = min(3, best_src.armies - 1)
                def_dice = min(2, best_dst.armies)
                self.do_attack(best_src.name, best_dst.name, atk_dice, def_dice)
                if self.phase == Phase.GAME_OVER:
                    return  # Game won mid-attack — stop immediately
            else:
                break

        self.phase = Phase.FORTIFY
        self.ai_action_pending = True
        self.ai_timer = pygame.time.get_ticks() + 1200

    def _ai_fortify(self, cp):
        # Move armies from safest interior to weakest border via BFS path
        my_terrs = self.territories_of(cp.index)
        my_names = {t.name for t in my_terrs}
        interiors = [t for t in my_terrs if all(
            self.territories[n].owner == cp.index for n in t.neighbours if n in self.territories)]
        borders   = [t for t in my_terrs if any(
            self.territories[n].owner != cp.index for n in t.neighbours if n in self.territories)]

        if interiors and borders:
            src = max(interiors, key=lambda x: x.armies)
            dst = min(borders, key=lambda x: x.armies)
            if src.armies > 1:
                # FIX BUG 3: BFS to find path through owned territories
                path = self._bfs_path(src.name, dst.name, my_names)
                if path and len(path) >= 2:
                    # Only move between directly adjacent own territories along path
                    next_hop = self.territories[path[1]]
                    move = src.armies - 1
                    src.armies -= move
                    next_hop.armies += move
                    self._log(f"{cp.name} moved {move} armies {src.name}→{next_hop.name}")
        if self.phase != Phase.GAME_OVER:
            self.end_turn()

    def _bfs_path(self, start: str, end: str, allowed: set) -> list:
        """BFS returning shortest path through territories in `allowed`."""
        from collections import deque
        if start == end:
            return [start]
        queue = deque([[start]])
        visited = {start}
        while queue:
            path = queue.popleft()
            node = path[-1]
            for nbr in self.territories[node].neighbours:
                if nbr not in visited and nbr in allowed and nbr in self.territories:
                    new_path = path + [nbr]
                    if nbr == end:
                        return new_path
                    visited.add(nbr)
                    queue.append(new_path)
        return []

    # ── Save / Load ───────────────────────────────────────────────────────────

    def save_game(self, slot_name: str = "") -> str:
        """Serialise full game state to JSON. Returns path written."""
        os.makedirs(SAVE_DIR, exist_ok=True)
        if not slot_name:
            slot_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(SAVE_DIR, f"risk_save_{slot_name}.json")

        terr_data = {}
        for name, t in self.territories.items():
            terr_data[name] = {"owner": t.owner, "armies": t.armies}

        players_data = []
        for p in self.players:
            players_data.append({
                "index": p.index,
                "name": p.name,
                "color": list(p.color),
                "is_human": p.is_human,
                "armies": p.armies,
                "cards": [{"territory": c.territory, "card_type": c.card_type} for c in p.cards],
                "alive": p.alive,
                "_earned_card": p._earned_card,
            })

        state = {
            "version": 2,
            "saved_at": datetime.now().isoformat(),
            "phase": self.phase.name,
            "current_player": self.current_player,
            "trade_count": self.trade_count,
            "armies_to_place": self.armies_to_place,
            "setup_armies_remaining": self.setup_armies_remaining,
            "num_players": self.num_players,
            "player_types": self.player_types,
            "player_name_inputs": self.player_name_inputs,
            "message": self.message,
            "log": self.log,
            "winner_index": self.winner.index if self.winner else None,
            "territories": terr_data,
            "players": players_data,
            "deck": [{"territory": c.territory, "card_type": c.card_type} for c in self.deck],
            "discard": [{"territory": c.territory, "card_type": c.card_type} for c in self.discard],
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        self._log(f"💾 Game saved: {slot_name}")
        self.message = f"Game saved to slot '{slot_name}'"
        return path

    def load_game(self, path: str) -> bool:
        """Deserialise game state from JSON path. Returns True on success."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)

            if state.get("version", 1) < 2:
                self.message = "Save file too old — please start a new game."
                return False

            # Restore players first
            self.players = []
            for pd in state["players"]:
                p = Player(
                    index=pd["index"],
                    name=pd["name"],
                    color=tuple(pd["color"]),
                    is_human=pd["is_human"],
                    armies=pd["armies"],
                    alive=pd["alive"],
                )
                p.cards = [Card(cd["territory"], cd["card_type"]) for cd in pd["cards"]]
                p._earned_card = pd.get("_earned_card", False)
                self.players.append(p)

            # Restore territory ownership
            for name, td in state["territories"].items():
                if name in self.territories:
                    self.territories[name].owner = td["owner"]
                    self.territories[name].armies = td["armies"]

            # Restore game state
            self.phase = Phase[state["phase"]]
            self.current_player = state["current_player"]
            self.trade_count = state["trade_count"]
            self.armies_to_place = state["armies_to_place"]
            self.setup_armies_remaining = state["setup_armies_remaining"]
            self.num_players = state["num_players"]
            self.player_types = state["player_types"]
            self.player_name_inputs = state["player_name_inputs"]
            self.message = state.get("message", "Game loaded.")
            self.log = state.get("log", [])
            self.winner = self.players[state["winner_index"]] if state["winner_index"] is not None else None
            self.deck = [Card(c["territory"], c["card_type"]) for c in state["deck"]]
            self.discard = [Card(c["territory"], c["card_type"]) for c in state["discard"]]

            # Reset transient UI state
            self.selected_territory = None
            self.attack_source = None
            self.attack_target = None
            self.fortify_source = None
            self.show_dice = False
            self.show_cards = False
            self.show_save_menu = False
            self.show_load_menu = False
            self._selected_card_indices = set()
            self.ai_action_pending = False

            # Resume AI if it's an AI player's turn
            cp = self.players[self.current_player]
            if not cp.is_human and cp.alive and self.phase not in (Phase.GAME_OVER, Phase.SETUP_PLAYERS):
                self.ai_action_pending = True
                self.ai_timer = pygame.time.get_ticks() + 1000

            self._log(f"📂 Game loaded from {os.path.basename(path)}")
            self.message = f"Game loaded! {self.players[self.current_player].name}'s turn."
            return True

        except Exception as e:
            self.message = f"Load failed: {e}"
            return False

    @staticmethod
    def list_saves() -> list:
        """Return list of (path, display_name, timestamp) for all saves."""
        os.makedirs(SAVE_DIR, exist_ok=True)
        saves = []
        for path in sorted(glob.glob(os.path.join(SAVE_DIR, "risk_save_*.json")), reverse=True):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                saved_at = data.get("saved_at", "unknown")[:19].replace("T", " ")
                n_players = data.get("num_players", "?")
                phase = data.get("phase", "?")
                winner_idx = data.get("winner_index")
                players = data.get("players", [])
                if winner_idx is not None and winner_idx < len(players):
                    status = f"🏆 {players[winner_idx]['name']} won"
                else:
                    alive = sum(1 for p in players if p.get("alive", True))
                    status = f"{alive} players · {phase}"
                display = f"{saved_at}  [{n_players}p  {status}]"
                saves.append((path, display))
            except Exception:
                pass
        return saves

    # ── Drawing ───────────────────────────────────────────────────────────────

    def draw(self):
        self.screen.fill(COL_BG)

        if self.phase == Phase.SETUP_PLAYERS:
            self._draw_setup_screen()
        else:
            self._draw_map()
            self._draw_top_bar()
            self._draw_right_panel()
            self._draw_bottom_bar()
            if self.show_dice:
                self._draw_dice_overlay()
            if self.show_cards:
                self._draw_cards_overlay()
            if self.show_save_menu:
                self._draw_save_overlay()
            if self.show_load_menu:
                self._draw_load_overlay()
            if self.phase == Phase.GAME_OVER:
                self._draw_winner_screen()

        pygame.display.flip()

    # ── Setup screen ──────────────────────────────────────────────────────────

    def _draw_setup_screen(self):
        # Title
        title = self.font_title.render("⚔  RISK — GLOBAL DOMINATION", True, COL_GOLD)
        self.screen.blit(title, (SCREEN_W//2 - title.get_width()//2, 40))

        sub = self.font_med.render("Configure Players", True, COL_TEXT_DIM)
        self.screen.blit(sub, (SCREEN_W//2 - sub.get_width()//2, 80))

        # Player count selector
        pc_lbl = self.font_med.render("Number of Players:", True, COL_TEXT)
        self.screen.blit(pc_lbl, (SCREEN_W//2 - 250, 130))
        for n in range(2, 7):
            rect = pygame.Rect(SCREEN_W//2 - 90 + (n - 2) * 55, 125, 48, 32)
            color = COL_GOLD if self.num_players == n else COL_PANEL2
            pygame.draw.rect(self.screen, color, rect, border_radius=6)
            pygame.draw.rect(self.screen, COL_BORDER, rect, 1, border_radius=6)
            txt = self.font_med.render(str(n), True, COL_TEXT)
            self.screen.blit(txt, (rect.centerx - txt.get_width()//2, rect.centery - txt.get_height()//2))
            self._btn_rects_setup = getattr(self, '_btn_rects_setup', {})
            self._btn_rects_setup[n] = rect

        # Player rows
        for i in range(self.num_players):
            y = 185 + i * 75
            p_color = PLAYER_COLORS[i]

            # Color swatch
            pygame.draw.rect(self.screen, p_color, (SCREEN_W//2 - 320, y + 5, 28, 28), border_radius=4)
            pygame.draw.rect(self.screen, COL_BORDER, (SCREEN_W//2 - 320, y + 5, 28, 28), 1, border_radius=4)

            # Player label
            lbl = self.font_med.render(f"Player {i+1}:", True, COL_TEXT)
            self.screen.blit(lbl, (SCREEN_W//2 - 280, y + 7))

            # Name input box
            input_rect = pygame.Rect(SCREEN_W//2 - 175, y + 2, 180, 34)
            border_col = COL_GOLD if self.active_input == i else COL_BORDER
            pygame.draw.rect(self.screen, COL_PANEL, input_rect, border_radius=5)
            pygame.draw.rect(self.screen, border_col, input_rect, 1, border_radius=5)
            name_txt = self.font_med.render(self.player_name_inputs[i], True, COL_TEXT)
            self.screen.blit(name_txt, (input_rect.x + 8, input_rect.y + 8))
            if not hasattr(self, '_input_rects'):
                self._input_rects = {}
            self._input_rects[i] = input_rect

            # Human / AI toggle
            h_rect = pygame.Rect(SCREEN_W//2 + 20, y + 2, 90, 34)
            a_rect = pygame.Rect(SCREEN_W//2 + 120, y + 2, 80, 34)
            pygame.draw.rect(self.screen, COL_GREEN if self.player_types[i] else COL_PANEL2, h_rect, border_radius=5)
            pygame.draw.rect(self.screen, COL_RED if not self.player_types[i] else COL_PANEL2, a_rect, border_radius=5)
            pygame.draw.rect(self.screen, COL_BORDER, h_rect, 1, border_radius=5)
            pygame.draw.rect(self.screen, COL_BORDER, a_rect, 1, border_radius=5)
            ht = self.font_small.render("👤 Human", True, COL_WHITE)
            at = self.font_small.render("🤖 AI", True, COL_WHITE)
            self.screen.blit(ht, (h_rect.x + 6, h_rect.y + 10))
            self.screen.blit(at, (a_rect.x + 14, a_rect.y + 10))

            if not hasattr(self, '_type_rects'):
                self._type_rects = {}
            self._type_rects[i] = (h_rect, a_rect)

        # Start button
        pygame.draw.rect(self.screen, COL_GOLD, self.start_btn, border_radius=8)
        pygame.draw.rect(self.screen, COL_WHITE, self.start_btn, 2, border_radius=8)
        st = self.font_large.render("▶  START GAME", True, COL_BG)
        self.screen.blit(st, (self.start_btn.centerx - st.get_width()//2, self.start_btn.centery - st.get_height()//2))

        # Load saved game button
        self._setup_load_btn = pygame.Rect(SCREEN_W//2 + 120, 750, 180, 45)
        pygame.draw.rect(self.screen, (50, 70, 130), self._setup_load_btn, border_radius=8)
        pygame.draw.rect(self.screen, COL_BORDER, self._setup_load_btn, 1, border_radius=8)
        lt = self.font_med.render("📂 Load Game", True, COL_TEXT)
        self.screen.blit(lt, (self._setup_load_btn.centerx - lt.get_width()//2,
                               self._setup_load_btn.centery - lt.get_height()//2))

        # Rules summary
        rules = [
            "🌍 Conquer all 42 territories across 6 continents to win!",
            "🎲 Attack with up to 3 dice — defender rolls up to 2 dice",
            "🃏 Collect cards by conquering territories — trade sets for reinforcements",
            "🏰 Hold entire continents for bonus armies each turn",
        ]
        for k, r in enumerate(rules):
            rt = self.font_small.render(r, True, COL_TEXT_DIM)
            self.screen.blit(rt, (SCREEN_W//2 - rt.get_width()//2, 640 + k * 22))

    # ── Map ───────────────────────────────────────────────────────────────────

    def _draw_map(self):
        # Ocean background
        map_rect = pygame.Rect(MAP_X, MAP_Y, MAP_W, MAP_H)
        pygame.draw.rect(self.screen, COL_OCEAN, map_rect, border_radius=8)
        pygame.draw.rect(self.screen, COL_BORDER, map_rect, 2, border_radius=8)

        # Draw territory connections first (lines)
        drawn_edges = set()
        for t in self.territories.values():
            for nbr_name in t.neighbours:
                if nbr_name not in self.territories:
                    continue
                edge = tuple(sorted([t.name, nbr_name]))
                if edge in drawn_edges:
                    continue
                drawn_edges.add(edge)
                nbr = self.territories[nbr_name]
                # Skip very long "wrap-around" lines (Alaska-Kamchatka etc)
                dx = abs(t.pos[0] - nbr.pos[0])
                dy = abs(t.pos[1] - nbr.pos[1])
                if dx < 250 and dy < 200:
                    pygame.draw.line(self.screen, (40, 60, 100), t.pos, nbr.pos, 1)

        # Draw territories
        for t in self.territories.values():
            self._draw_territory(t)

    def _draw_territory(self, t: Territory):
        r = 22

        # Continent base color
        cont_col = CONTINENT_COLORS.get(t.continent, (80, 80, 80))

        # Determine fill color
        if t.owner is not None:
            base = self.players[t.owner].color
            fill = tuple(min(255, int(c * 0.85 + cont_col[i] * 0.15)) for i, c in enumerate(base))
        else:
            fill = tuple(int(c * 0.5) for c in cont_col)

        # Highlight selected / attack source / target
        glow = None
        thick = 1
        if t.name == self.attack_source:
            glow = COL_ATTACK_SRC
            thick = 3
        elif t.name == self.attack_target:
            glow = COL_ATTACK_DST
            thick = 3
        elif t.name == self.selected_territory:
            glow = COL_HIGHLIGHT
            thick = 2
        elif t.name == self.fortify_source:
            glow = COL_GREEN
            thick = 3

        # Draw glow
        if glow:
            pygame.draw.circle(self.screen, glow, t.pos, r + 5, 3)

        # Draw territory circle
        pygame.draw.circle(self.screen, fill, t.pos, r)
        border_c = glow if glow else (tuple(min(255, c + 60) for c in fill))
        pygame.draw.circle(self.screen, border_c, t.pos, r, thick)

        # Army count
        army_str = str(t.armies)
        atxt = self.font_med.render(army_str, True, COL_WHITE)
        self.screen.blit(atxt, (t.pos[0] - atxt.get_width()//2, t.pos[1] - atxt.get_height()//2))

        # Territory name (tiny, below circle)
        name_parts = t.name.split()
        short = name_parts[0] if len(name_parts) > 1 else t.name[:8]
        ntxt = self.font_tiny.render(short, True, COL_TEXT)
        self.screen.blit(ntxt, (t.pos[0] - ntxt.get_width()//2, t.pos[1] + r + 1))

    # ── Top bar ───────────────────────────────────────────────────────────────

    def _draw_top_bar(self):
        bar = pygame.Rect(0, 0, SCREEN_W, 115)
        pygame.draw.rect(self.screen, COL_PANEL, bar)
        pygame.draw.rect(self.screen, COL_BORDER, bar, 1)

        title = self.font_title.render("⚔  RISK", True, COL_GOLD)
        self.screen.blit(title, (15, 10))

        # Phase indicator
        phase_labels = {
            Phase.SETUP_PLACE: "SETUP — Place Armies",
            Phase.REINFORCE:   "REINFORCE",
            Phase.ATTACK:      "ATTACK",
            Phase.FORTIFY:     "FORTIFY",
            Phase.GAME_OVER:   "GAME OVER",
        }
        phase_str = phase_labels.get(self.phase, "")
        if self.phase in (Phase.REINFORCE, Phase.ATTACK, Phase.FORTIFY):
            cp = self.players[self.current_player]
            phase_str = f"{cp.name.upper()} — {phase_str}"

        pt = self.font_large.render(phase_str, True, COL_GOLD)
        self.screen.blit(pt, (SCREEN_W//2 - pt.get_width()//2, 10))

        # Message
        mt = self.font_med.render(self.message[:90], True, COL_TEXT)
        self.screen.blit(mt, (SCREEN_W//2 - mt.get_width()//2, 42))

        # Player strips
        strip_w = min(160, (SCREEN_W - 20) // len(self.players))
        for i, p in enumerate(self.players):
            x = 10 + i * strip_w
            strip = pygame.Rect(x, 70, strip_w - 4, 40)
            col = p.color if p.alive else (60, 60, 60)
            alpha_surf = pygame.Surface((strip_w - 4, 40), pygame.SRCALPHA)
            alpha_surf.fill((*col, 80 if i != self.current_player else 160))
            self.screen.blit(alpha_surf, (x, 70))
            if i == self.current_player and p.alive:
                pygame.draw.rect(self.screen, COL_GOLD, strip, 2, border_radius=4)
            else:
                pygame.draw.rect(self.screen, COL_BORDER, strip, 1, border_radius=4)

            n = self.font_small.render(p.name[:10], True, COL_WHITE if p.alive else COL_TEXT_DIM)
            terr_count = len(self.territories_of(i))
            info = self.font_tiny.render(f"🌍{terr_count}  🃏{len(p.cards)}", True, COL_TEXT_DIM)
            self.screen.blit(n, (x + 4, 73))
            self.screen.blit(info, (x + 4, 90))

            if not p.alive:
                dead = self.font_tiny.render("☠ ELIMINATED", True, COL_RED)
                self.screen.blit(dead, (x + 4, 88))

    # ── Right panel ───────────────────────────────────────────────────────────

    def _draw_right_panel(self):
        px = MAP_X + MAP_W + 15
        pw = SCREEN_W - px - 10
        panel = pygame.Rect(px, MAP_Y, pw, MAP_H)
        pygame.draw.rect(self.screen, COL_PANEL, panel, border_radius=6)
        pygame.draw.rect(self.screen, COL_BORDER, panel, 1, border_radius=6)

        y = MAP_Y + 10
        # Continent bonuses header
        ch = self.font_large.render("Continents", True, COL_GOLD)
        self.screen.blit(ch, (px + 10, y)); y += 28

        for cont, bonus in CONTINENT_BONUS.items():
            col = CONTINENT_COLORS[cont]
            # Who controls it?
            owners = set(t.owner for t in self.territories.values() if t.continent == cont and t.owner is not None)
            all_terrs = [t for t in self.territories.values() if t.continent == cont]
            total = len(all_terrs)
            dominated = None
            for oi in owners:
                if sum(1 for t in all_terrs if t.owner == oi) == total:
                    dominated = oi
                    break

            pygame.draw.rect(self.screen, col, (px + 8, y, 8, 16), border_radius=2)
            label = f"{cont[:14]:<14} +{bonus}"
            ct = self.font_tiny.render(label, True, COL_TEXT)
            self.screen.blit(ct, (px + 20, y + 1))
            if dominated is not None:
                dot = self.font_tiny.render("●", True, self.players[dominated].color)
                self.screen.blit(dot, (px + pw - 18, y + 1))
            y += 18

        y += 8
        # Divider
        pygame.draw.line(self.screen, COL_BORDER, (px + 8, y), (px + pw - 8, y)); y += 10

        # Current player info
        if self.phase not in (Phase.SETUP_PLAYERS, Phase.GAME_OVER):
            cp = self.players[self.current_player]
            ci = self.font_med.render(f"{cp.name}'s Turn", True, cp.color)
            self.screen.blit(ci, (px + 10, y)); y += 24

            if self.phase == Phase.REINFORCE:
                ai = self.font_small.render(f"Armies to place: {self.armies_to_place}", True, COL_GREEN)
                self.screen.blit(ai, (px + 10, y)); y += 20
                cards_btn = pygame.Rect(px + 10, y, pw - 20, 28)
                pygame.draw.rect(self.screen, COL_PANEL2, cards_btn, border_radius=5)
                pygame.draw.rect(self.screen, COL_BORDER, cards_btn, 1, border_radius=5)
                cbt = self.font_small.render(f"🃏 Cards ({len(cp.cards)})  — click to manage", True, COL_TEXT)
                self.screen.blit(cbt, (cards_btn.x + 5, cards_btn.y + 6))
                self._cards_btn_rect = cards_btn
                y += 34

            # Action buttons
            if cp.is_human:
                y += 5
                if self.phase == Phase.REINFORCE and self.armies_to_place == 0:
                    btn = pygame.Rect(px + 10, y, pw - 20, 32)
                    pygame.draw.rect(self.screen, COL_GREEN, btn, border_radius=6)
                    bt = self.font_med.render("→ Attack Phase", True, COL_WHITE)
                    self.screen.blit(bt, (btn.centerx - bt.get_width()//2, btn.centery - bt.get_height()//2))
                    self._phase_btn_rect = btn; y += 38
                elif self.phase == Phase.ATTACK:
                    btn = pygame.Rect(px + 10, y, pw - 20, 32)
                    pygame.draw.rect(self.screen, COL_GOLD, btn, border_radius=6)
                    bt = self.font_med.render("→ Fortify Phase", True, COL_BG)
                    self.screen.blit(bt, (btn.centerx - bt.get_width()//2, btn.centery - bt.get_height()//2))
                    self._phase_btn_rect = btn; y += 38
                elif self.phase == Phase.FORTIFY:
                    btn = pygame.Rect(px + 10, y, pw - 20, 32)
                    pygame.draw.rect(self.screen, (80, 100, 200), btn, border_radius=6)
                    bt = self.font_med.render("→ End Turn", True, COL_WHITE)
                    self.screen.blit(bt, (btn.centerx - bt.get_width()//2, btn.centery - bt.get_height()//2))
                    self._phase_btn_rect = btn; y += 38
                else:
                    self._phase_btn_rect = None

            y += 5
            pygame.draw.line(self.screen, COL_BORDER, (px + 8, y), (px + pw - 8, y)); y += 10

        # Save / Load buttons (always visible during active game)
        if self.phase not in (Phase.SETUP_PLAYERS,):
            btn_w = (pw - 24) // 2
            sb = pygame.Rect(px + 8, y, btn_w, 26)
            lb = pygame.Rect(px + 12 + btn_w, y, btn_w, 26)
            pygame.draw.rect(self.screen, (50, 80, 60), sb, border_radius=5)
            pygame.draw.rect(self.screen, COL_BORDER, sb, 1, border_radius=5)
            pygame.draw.rect(self.screen, (50, 60, 100), lb, border_radius=5)
            pygame.draw.rect(self.screen, COL_BORDER, lb, 1, border_radius=5)
            st = self.font_tiny.render("💾 Save Game", True, COL_TEXT)
            lt = self.font_tiny.render("📂 Load Game", True, COL_TEXT)
            self.screen.blit(st, (sb.centerx - st.get_width()//2, sb.centery - st.get_height()//2))
            self.screen.blit(lt, (lb.centerx - lt.get_width()//2, lb.centery - lt.get_height()//2))
            self._save_btn_rect = sb
            self._load_btn_rect = lb
            y += 32
            pygame.draw.line(self.screen, COL_BORDER, (px + 8, y), (px + pw - 8, y)); y += 8

        # Log
        lh = self.font_tiny.render("— Event Log —", True, COL_GOLD)
        self.screen.blit(lh, (px + 10, y)); y += 18
        for entry in self.log[:18]:
            lt = self.font_tiny.render(entry[:32], True, COL_TEXT_DIM)
            self.screen.blit(lt, (px + 8, y)); y += 15
            if y > MAP_Y + MAP_H - 20:
                break

    # ── Bottom bar ────────────────────────────────────────────────────────────

    def _draw_bottom_bar(self):
        bar = pygame.Rect(0, MAP_Y + MAP_H + 5, SCREEN_W, SCREEN_H - (MAP_Y + MAP_H + 5) - 5)
        pygame.draw.rect(self.screen, COL_PANEL, bar)
        pygame.draw.rect(self.screen, COL_BORDER, bar, 1)

        if self.phase == Phase.ATTACK and self.players[self.current_player].is_human:
            txt = self.font_small.render(
                "ATTACK: Click YOUR territory (source) then ENEMY territory (target). Use dice buttons to attack.",
                True, COL_TEXT_DIM)
            self.screen.blit(txt, (10, bar.y + 8))
            # Dice buttons
            if self.attack_source and self.attack_target:
                src = self.territories[self.attack_source]
                dst = self.territories[self.attack_target]
                max_atk = min(3, src.armies - 1)
                max_def = min(2, dst.armies)
                bx = 10
                for nd in range(1, max_atk + 1):
                    br = pygame.Rect(bx, bar.y + 30, 90, 30)
                    pygame.draw.rect(self.screen, COL_RED, br, border_radius=5)
                    bt = self.font_small.render(f"Attack {nd}🎲", True, COL_WHITE)
                    self.screen.blit(bt, (br.x + 5, br.y + 7))
                    if not hasattr(self, '_dice_btn_rects'):
                        self._dice_btn_rects = []
                    # store dynamically below
                    bx += 100

                # Re-draw properly
                bx = 10
                self._dice_btn_rects = []
                for nd in range(1, max_atk + 1):
                    br = pygame.Rect(bx, bar.y + 30, 100, 30)
                    pygame.draw.rect(self.screen, COL_RED, br, border_radius=5)
                    pygame.draw.rect(self.screen, (255, 120, 120), br, 1, border_radius=5)
                    bt = self.font_small.render(f"Attack {nd} 🎲", True, COL_WHITE)
                    self.screen.blit(bt, (br.x + 6, br.y + 7))
                    self._dice_btn_rects.append((br, nd, max_def))
                    bx += 110

                lbl = self.font_small.render(
                    f"{self.attack_source} ({src.armies}) → {self.attack_target} ({dst.armies})",
                    True, COL_GOLD)
                self.screen.blit(lbl, (bx + 10, bar.y + 35))
            else:
                self._dice_btn_rects = []
        elif self.phase == Phase.FORTIFY and self.players[self.current_player].is_human:
            if not self.fortify_source:
                txt = self.font_small.render("FORTIFY: Click YOUR territory to move armies FROM.", True, COL_TEXT_DIM)
            else:
                txt = self.font_small.render(f"FORTIFY: Now click adjacent territory to move armies TO from {self.fortify_source}.", True, COL_TEXT_DIM)
            self.screen.blit(txt, (10, bar.y + 15))
        elif self.phase == Phase.REINFORCE and self.players[self.current_player].is_human:
            txt = self.font_small.render("REINFORCE: Click your territories to add armies.", True, COL_TEXT_DIM)
            self.screen.blit(txt, (10, bar.y + 15))
        elif self.phase == Phase.SETUP_PLACE:
            cp = self.players[self.current_player]
            rem = self.setup_armies_remaining[self.current_player]
            txt = self.font_small.render(f"SETUP: {cp.name} — {rem} armies remaining. Click a territory.", True, COL_TEXT_DIM)
            self.screen.blit(txt, (10, bar.y + 15))

    # ── Dice overlay ──────────────────────────────────────────────────────────

    def _draw_dice_overlay(self):
        if pygame.time.get_ticks() > self.dice_timer:
            self.show_dice = False
            return
        # Semi-transparent overlay
        surf = pygame.Surface((400, 200), pygame.SRCALPHA)
        surf.fill((10, 10, 25, 210))
        ox = SCREEN_W//2 - 200
        oy = SCREEN_H//2 - 100
        self.screen.blit(surf, (ox, oy))
        pygame.draw.rect(self.screen, COL_GOLD, (ox, oy, 400, 200), 2, border_radius=10)

        title = self.font_large.render("⚔  Battle Result", True, COL_GOLD)
        self.screen.blit(title, (ox + 200 - title.get_width()//2, oy + 12))

        for k, (av, dv, atk_won) in enumerate(self.dice_result):
            col_a = COL_GREEN if atk_won else COL_RED
            col_d = COL_RED if atk_won else COL_GREEN
            xa = ox + 60 + k * 130
            xd = xa + 60

            # Attacker die
            pygame.draw.rect(self.screen, COL_RED, (xa, oy + 60, 50, 50), border_radius=6)
            pygame.draw.rect(self.screen, col_a, (xa, oy + 60, 50, 50), 3, border_radius=6)
            at = self.font_dice.render(str(av), True, COL_WHITE)
            self.screen.blit(at, (xa + 25 - at.get_width()//2, oy + 70))

            # vs label
            vs = self.font_small.render("vs", True, COL_TEXT_DIM)
            self.screen.blit(vs, (xd - 12, oy + 76))

            # Defender die
            pygame.draw.rect(self.screen, (80, 80, 200), (xd + 5, oy + 60, 50, 50), border_radius=6)
            pygame.draw.rect(self.screen, col_d, (xd + 5, oy + 60, 50, 50), 3, border_radius=6)
            dt = self.font_dice.render(str(dv), True, COL_WHITE)
            self.screen.blit(dt, (xd + 30 - dt.get_width()//2, oy + 70))

            result = "ATK ✓" if atk_won else "DEF ✓"
            rc = COL_GREEN if atk_won else COL_GOLD
            rt = self.font_small.render(result, True, rc)
            self.screen.blit(rt, (xa + 25, oy + 118))

        # Labels
        al = self.font_small.render("Attacker 🔴", True, COL_TEXT_DIM)
        dl = self.font_small.render("Defender 🔵", True, COL_TEXT_DIM)
        self.screen.blit(al, (ox + 40, oy + 158))
        self.screen.blit(dl, (ox + 230, oy + 158))

    # ── Cards overlay ─────────────────────────────────────────────────────────

    def _draw_cards_overlay(self):
        cp = self.players[self.current_player]
        cards = cp.cards
        w, h = 700, 400
        ox = SCREEN_W//2 - w//2
        oy = SCREEN_H//2 - h//2
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((15, 20, 40, 235))
        self.screen.blit(surf, (ox, oy))
        pygame.draw.rect(self.screen, COL_GOLD, (ox, oy, w, h), 2, border_radius=10)

        th = self.font_large.render(f"{cp.name}'s Cards ({len(cards)})", True, COL_GOLD)
        self.screen.blit(th, (ox + w//2 - th.get_width()//2, oy + 12))

        instr = self.font_small.render("Click 3 cards to select, then press TRADE to cash in for armies.", True, COL_TEXT_DIM)
        self.screen.blit(instr, (ox + 10, oy + 42))

        self._card_rects = []
        self._selected_card_indices = getattr(self, '_selected_card_indices', set())

        for i, card in enumerate(cards[:10]):  # show max 10 cards
            cx = ox + 20 + i * 65
            cy = oy + 75
            cr = pygame.Rect(cx, cy, 58, 100)

            type_colors = {
                "Infantry":  (100, 160, 80),
                "Cavalry":   (80,  130, 200),
                "Artillery": (200, 80,  80),
                "Wild":      (180, 130, 50),
            }
            card_col = type_colors.get(card.card_type, COL_PANEL2)
            bg = card_col if i in self._selected_card_indices else tuple(int(c * 0.5) for c in card_col)
            pygame.draw.rect(self.screen, bg, cr, border_radius=6)
            border = COL_GOLD if i in self._selected_card_indices else COL_BORDER
            pygame.draw.rect(self.screen, border, cr, 2 if i in self._selected_card_indices else 1, border_radius=6)

            type_icons = {"Infantry": "🪖", "Cavalry": "🐴", "Artillery": "💣", "Wild": "⭐"}
            icon = type_icons.get(card.card_type, "?")
            it = self.font_small.render(icon, True, COL_WHITE)
            self.screen.blit(it, (cx + 29 - it.get_width()//2, cy + 15))

            type_t = self.font_tiny.render(card.card_type[:8], True, COL_WHITE)
            self.screen.blit(type_t, (cx + 29 - type_t.get_width()//2, cy + 44))

            terr_short = (card.territory[:7] if card.territory else "WILD")
            tt = self.font_tiny.render(terr_short, True, COL_TEXT_DIM)
            self.screen.blit(tt, (cx + 29 - tt.get_width()//2, cy + 60))

            self._card_rects.append((cr, i))

        # Trade button
        trade_btn = pygame.Rect(ox + w//2 - 70, oy + h - 80, 140, 36)
        can_trade = len(self._selected_card_indices) == 3
        trade_col = COL_GOLD if can_trade else COL_PANEL2
        pygame.draw.rect(self.screen, trade_col, trade_btn, border_radius=6)
        pygame.draw.rect(self.screen, COL_BORDER, trade_btn, 1, border_radius=6)
        tbt = self.font_med.render("TRADE IN (3)", True, COL_TEXT if can_trade else COL_TEXT_DIM)
        self.screen.blit(tbt, (trade_btn.centerx - tbt.get_width()//2, trade_btn.centery - tbt.get_height()//2))
        self._trade_btn_rect = trade_btn

        close_btn = pygame.Rect(ox + w - 100, oy + h - 50, 80, 30)
        pygame.draw.rect(self.screen, COL_RED, close_btn, border_radius=5)
        ct = self.font_small.render("Close", True, COL_WHITE)
        self.screen.blit(ct, (close_btn.centerx - ct.get_width()//2, close_btn.centery - ct.get_height()//2))
        self._close_cards_btn = close_btn

        # Trade value info
        next_val = TRADE_VALUES[min(self.trade_count, len(TRADE_VALUES)-1)] if self.trade_count < len(TRADE_VALUES) else TRADE_VALUES[-1] + (self.trade_count - len(TRADE_VALUES) + 1) * 5
        vi = self.font_small.render(f"Next trade worth: {next_val} armies  (Set #{self.trade_count+1})", True, COL_TEXT_DIM)
        self.screen.blit(vi, (ox + 15, oy + h - 40))

    # ── Save overlay ──────────────────────────────────────────────────────────

    def _draw_save_overlay(self):
        w, h = 480, 230
        ox = SCREEN_W//2 - w//2
        oy = SCREEN_H//2 - h//2
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((12, 18, 35, 240))
        self.screen.blit(surf, (ox, oy))
        pygame.draw.rect(self.screen, COL_GOLD, (ox, oy, w, h), 2, border_radius=10)

        th = self.font_large.render("💾  Save Game", True, COL_GOLD)
        self.screen.blit(th, (ox + w//2 - th.get_width()//2, oy + 14))

        lbl = self.font_small.render("Save slot name (leave blank for timestamp):", True, COL_TEXT_DIM)
        self.screen.blit(lbl, (ox + 18, oy + 58))

        inp = pygame.Rect(ox + 18, oy + 80, w - 36, 36)
        border = COL_GOLD if self.save_input_active else COL_BORDER
        pygame.draw.rect(self.screen, COL_PANEL2, inp, border_radius=5)
        pygame.draw.rect(self.screen, border, inp, 2, border_radius=5)
        it = self.font_med.render(self.save_slot_input + ("|" if self.save_input_active else ""), True, COL_TEXT)
        self.screen.blit(it, (inp.x + 8, inp.y + 8))
        self._save_input_rect = inp

        # Existing saves list
        saves = self.list_saves()[:3]
        if saves:
            hint = self.font_tiny.render("Recent saves:", True, COL_TEXT_DIM)
            self.screen.blit(hint, (ox + 18, oy + 128))
            for i, (_, disp) in enumerate(saves):
                self.screen.blit(self.font_tiny.render(disp[:55], True, COL_TEXT_DIM), (ox + 18, oy + 145 + i * 14))

        # Buttons
        ok_btn = pygame.Rect(ox + w//2 - 120, oy + h - 45, 100, 32)
        cancel_btn = pygame.Rect(ox + w//2 + 20, oy + h - 45, 100, 32)
        pygame.draw.rect(self.screen, COL_GREEN, ok_btn, border_radius=6)
        pygame.draw.rect(self.screen, COL_RED,   cancel_btn, border_radius=6)
        self.screen.blit(self.font_small.render("Save ✓", True, COL_WHITE),
                         (ok_btn.centerx - 25, ok_btn.centery - 8))
        self.screen.blit(self.font_small.render("Cancel", True, COL_WHITE),
                         (cancel_btn.centerx - 24, cancel_btn.centery - 8))
        self._save_ok_btn = ok_btn
        self._save_cancel_btn = cancel_btn

    # ── Load overlay ──────────────────────────────────────────────────────────

    def _draw_load_overlay(self):
        w, h = 600, 380
        ox = SCREEN_W//2 - w//2
        oy = SCREEN_H//2 - h//2
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((12, 18, 35, 240))
        self.screen.blit(surf, (ox, oy))
        pygame.draw.rect(self.screen, (80, 120, 200), (ox, oy, w, h), 2, border_radius=10)

        th = self.font_large.render("📂  Load Game", True, COL_GOLD)
        self.screen.blit(th, (ox + w//2 - th.get_width()//2, oy + 14))

        saves = self._load_saves_cache
        if not saves:
            nt = self.font_med.render("No saved games found.", True, COL_TEXT_DIM)
            self.screen.blit(nt, (ox + w//2 - nt.get_width()//2, oy + h//2 - 10))
        else:
            lbl = self.font_tiny.render("Select a save to load:", True, COL_TEXT_DIM)
            self.screen.blit(lbl, (ox + 18, oy + 50))
            self._load_slot_rects = []
            for i, (path, disp) in enumerate(saves[:8]):
                row = pygame.Rect(ox + 14, oy + 68 + i * 34, w - 28, 30)
                bg = COL_GOLD if i == self._load_selected else COL_PANEL2
                pygame.draw.rect(self.screen, bg, row, border_radius=5)
                pygame.draw.rect(self.screen, COL_BORDER, row, 1, border_radius=5)
                tc = COL_BG if i == self._load_selected else COL_TEXT
                dt = self.font_tiny.render(disp[:72], True, tc)
                self.screen.blit(dt, (row.x + 8, row.centery - dt.get_height()//2))
                self._load_slot_rects.append((row, i, path))

        # Buttons
        ok_btn = pygame.Rect(ox + w//2 - 130, oy + h - 48, 110, 34)
        del_btn = pygame.Rect(ox + w//2 - 10, oy + h - 48, 110, 34)
        cancel_btn = pygame.Rect(ox + w//2 + 130, oy + h - 48, 100, 34)
        ok_col = COL_GREEN if self._load_selected >= 0 else COL_PANEL2
        del_col = COL_RED if self._load_selected >= 0 else COL_PANEL2
        pygame.draw.rect(self.screen, ok_col, ok_btn, border_radius=6)
        pygame.draw.rect(self.screen, del_col, del_btn, border_radius=6)
        pygame.draw.rect(self.screen, (80, 100, 180), cancel_btn, border_radius=6)
        self.screen.blit(self.font_small.render("Load ✓", True, COL_WHITE),
                         (ok_btn.centerx - 26, ok_btn.centery - 8))
        self.screen.blit(self.font_small.render("🗑 Delete", True, COL_WHITE),
                         (del_btn.centerx - 32, del_btn.centery - 8))
        self.screen.blit(self.font_small.render("Cancel", True, COL_WHITE),
                         (cancel_btn.centerx - 24, cancel_btn.centery - 8))
        self._load_ok_btn = ok_btn
        self._load_del_btn = del_btn
        self._load_cancel_btn = cancel_btn

    # ── Winner screen ─────────────────────────────────────────────────────────

    def _draw_winner_screen(self):
        surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 170))
        self.screen.blit(surf, (0, 0))

        w, h = 500, 250
        ox = SCREEN_W//2 - w//2
        oy = SCREEN_H//2 - h//2
        pygame.draw.rect(self.screen, COL_PANEL, (ox, oy, w, h), border_radius=12)
        pygame.draw.rect(self.screen, COL_GOLD, (ox, oy, w, h), 3, border_radius=12)

        wt = self.font_title.render("🏆  VICTORY!", True, COL_GOLD)
        self.screen.blit(wt, (ox + w//2 - wt.get_width()//2, oy + 30))

        wn = self.font_large.render(f"{self.winner.name} conquers the world!", True, self.winner.color)
        self.screen.blit(wn, (ox + w//2 - wn.get_width()//2, oy + 80))

        # Restart button
        rb = pygame.Rect(ox + w//2 - 110, oy + 160, 220, 50)
        pygame.draw.rect(self.screen, COL_GOLD, rb, border_radius=8)
        rt = self.font_large.render("▶ Play Again", True, COL_BG)
        self.screen.blit(rt, (rb.centerx - rt.get_width()//2, rb.centery - rt.get_height()//2))
        self._restart_btn = rb

    # ── Event handling ────────────────────────────────────────────────────────

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()

        if event.type == pygame.KEYDOWN:
            # Save menu text input
            if self.show_save_menu and self.save_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.save_slot_input = self.save_slot_input[:-1]
                elif event.key == pygame.K_RETURN:
                    self._do_save()
                elif event.key == pygame.K_ESCAPE:
                    self.show_save_menu = False
                elif len(self.save_slot_input) < 20 and event.unicode.isalnum() or event.unicode in ('-', '_'):
                    self.save_slot_input += event.unicode
                return

            if self.phase == Phase.SETUP_PLAYERS and self.active_input >= 0:
                if event.key == pygame.K_BACKSPACE:
                    self.player_name_inputs[self.active_input] = self.player_name_inputs[self.active_input][:-1]
                elif event.key == pygame.K_RETURN:
                    self.active_input = -1
                elif len(self.player_name_inputs[self.active_input]) < 12:
                    self.player_name_inputs[self.active_input] += event.unicode
            if event.key == pygame.K_ESCAPE:
                self.show_cards = False
                self.show_save_menu = False
                self.show_load_menu = False
            # Ctrl+S quick save
            if event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                if self.phase not in (Phase.SETUP_PLAYERS,):
                    self.save_game()
            # Ctrl+L open load menu
            if event.key == pygame.K_l and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                if self.phase not in (Phase.SETUP_PLAYERS,):
                    self._open_load_menu()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            self._handle_click(pos)

    def _do_save(self):
        slot = self.save_slot_input.strip() or ""
        self.save_game(slot)
        self.show_save_menu = False
        self.save_slot_input = ""
        self.save_input_active = False

    def _open_load_menu(self):
        self._load_saves_cache = self.list_saves()
        self._load_selected = -1
        self.show_load_menu = True

    def _handle_click(self, pos):
        # Save overlay
        if self.show_save_menu:
            if hasattr(self, '_save_ok_btn') and self._save_ok_btn.collidepoint(pos):
                self._do_save()
            elif hasattr(self, '_save_cancel_btn') and self._save_cancel_btn.collidepoint(pos):
                self.show_save_menu = False; self.save_slot_input = ""
            elif hasattr(self, '_save_input_rect') and self._save_input_rect.collidepoint(pos):
                self.save_input_active = True
            else:
                self.save_input_active = False
            return

        # Load overlay
        if self.show_load_menu:
            if hasattr(self, '_load_cancel_btn') and self._load_cancel_btn.collidepoint(pos):
                self.show_load_menu = False
                return
            if hasattr(self, '_load_ok_btn') and self._load_ok_btn.collidepoint(pos):
                if self._load_selected >= 0 and self._load_selected < len(self._load_saves_cache):
                    path, _ = self._load_saves_cache[self._load_selected]
                    self.load_game(path)
                    self.show_load_menu = False
                return
            if hasattr(self, '_load_del_btn') and self._load_del_btn.collidepoint(pos):
                if self._load_selected >= 0 and self._load_selected < len(self._load_saves_cache):
                    path, _ = self._load_saves_cache[self._load_selected]
                    try:
                        os.remove(path)
                        self._log(f"🗑 Deleted {os.path.basename(path)}")
                    except Exception:
                        pass
                    self._load_saves_cache = self.list_saves()
                    self._load_selected = -1
                return
            if hasattr(self, '_load_slot_rects'):
                for row, i, path in self._load_slot_rects:
                    if row.collidepoint(pos):
                        self._load_selected = i
                        return
            return

        if self.phase == Phase.GAME_OVER:
            if hasattr(self, '_restart_btn') and self._restart_btn.collidepoint(pos):
                self.phase = Phase.SETUP_PLAYERS
                self.winner = None
                self.log = []
            return

        if self.phase == Phase.SETUP_PLAYERS:
            # Load overlay can appear on setup screen too
            if self.show_load_menu:
                pass  # fall through to load overlay handling above
            else:
                self._handle_setup_click(pos)
                return

        # Cards overlay
        if self.show_cards:
            self._handle_cards_click(pos)
            return

        # Phase button
        if hasattr(self, '_phase_btn_rect') and self._phase_btn_rect and self._phase_btn_rect.collidepoint(pos):
            cp = self.players[self.current_player]
            if cp.is_human:
                if self.phase == Phase.REINFORCE and self.armies_to_place == 0:
                    self.phase = Phase.ATTACK
                    self.message = f"{cp.name}: Attack! Click your territory then enemy territory."
                elif self.phase == Phase.ATTACK:
                    self.phase = Phase.FORTIFY
                    self.attack_source = None
                    self.attack_target = None
                    self.message = f"{cp.name}: Fortify — move armies to adjacent territory."
                elif self.phase == Phase.FORTIFY:
                    self.end_turn()
            return

        # Cards button
        if self.phase == Phase.REINFORCE and hasattr(self, '_cards_btn_rect') and self._cards_btn_rect.collidepoint(pos):
            cp = self.players[self.current_player]
            if cp.is_human:
                self._selected_card_indices = set()
                self.show_cards = True
            return

        # Save / Load panel buttons
        if hasattr(self, '_save_btn_rect') and self._save_btn_rect.collidepoint(pos):
            self.show_save_menu = True
            self.save_input_active = True
            self.save_slot_input = ""
            return
        if hasattr(self, '_load_btn_rect') and self._load_btn_rect.collidepoint(pos):
            self._open_load_menu()
            return

        # Dice buttons
        if self.phase == Phase.ATTACK and hasattr(self, '_dice_btn_rects'):
            for br, nd, max_def in self._dice_btn_rects:
                if br.collidepoint(pos):
                    if self.attack_source and self.attack_target:
                        self.do_attack(self.attack_source, self.attack_target, nd, max_def)
                        src = self.territories[self.attack_source]
                        if src.armies <= 1 or self.territories.get(self.attack_target) and self.territories[self.attack_target].owner == self.current_player:
                            self.attack_source = None
                            self.attack_target = None
                    return

        # Territory click
        clicked = self._territory_at(pos)
        if clicked:
            self._handle_territory_click(clicked)

    def _handle_setup_click(self, pos):
        # Player count buttons
        for n, rect in getattr(self, '_btn_rects_setup', {}).items():
            if rect.collidepoint(pos):
                self.num_players = n
                # FIX BUG 6: extend or trim player_types to match num_players
                while len(self.player_types) < n:
                    self.player_types.append(False)
                self.player_types = self.player_types[:n]
                return

        # Input boxes
        self.active_input = -1
        for i, rect in getattr(self, '_input_rects', {}).items():
            if i < self.num_players and rect.collidepoint(pos):
                self.active_input = i
                return

        # Type toggles
        for i, (hr, ar) in getattr(self, '_type_rects', {}).items():
            if i < self.num_players:
                if hr.collidepoint(pos):
                    self.player_types[i] = True; return
                if ar.collidepoint(pos):
                    self.player_types[i] = False; return

        # Start button
        if self.start_btn.collidepoint(pos):
            self.start_game()
            return

        # Load saved game from setup screen
        if hasattr(self, '_setup_load_btn') and self._setup_load_btn.collidepoint(pos):
            self._open_load_menu()
            self.show_load_menu = True

    def _handle_cards_click(self, pos):
        if hasattr(self, '_close_cards_btn') and self._close_cards_btn.collidepoint(pos):
            self.show_cards = False
            self._selected_card_indices = set()
            return
        if hasattr(self, '_trade_btn_rect') and self._trade_btn_rect.collidepoint(pos):
            if len(self._selected_card_indices) == 3:
                cp = self.players[self.current_player]
                gained = self.trade_in_cards(cp, list(self._selected_card_indices))
                if gained > 0:
                    self.armies_to_place += gained
                    self._selected_card_indices = set()
                    self._log(f"{cp.name} traded cards for {gained} armies!")
                    self.message = f"Traded cards for {gained} armies!"
                    if len(cp.cards) == 0:
                        self.show_cards = False
            return
        for cr, i in getattr(self, '_card_rects', []):
            if cr.collidepoint(pos):
                if i in self._selected_card_indices:
                    self._selected_card_indices.discard(i)
                elif len(self._selected_card_indices) < 3:
                    self._selected_card_indices.add(i)
                return

    def _handle_territory_click(self, name: str):
        t = self.territories[name]
        cp = self.players[self.current_player]

        if self.phase == Phase.SETUP_PLACE:
            remaining = self.setup_armies_remaining[self.current_player]
            if remaining <= 0:
                return
            unclaimed = [x for x in self.territories.values() if x.owner is None]
            if unclaimed:
                # Must claim unclaimed
                if t.owner is None:
                    t.owner = self.current_player
                    t.armies = 1
                    self.setup_armies_remaining[self.current_player] -= 1
                    self._log(f"{cp.name} claims {t.name}")
                    self._advance_setup()
            else:
                # Reinforce own
                if t.owner == self.current_player:
                    t.armies += 1
                    self.setup_armies_remaining[self.current_player] -= 1
                    self._log(f"{cp.name} reinforces {t.name}")
                    self._advance_setup()

        elif self.phase == Phase.REINFORCE:
            if t.owner == self.current_player and self.armies_to_place > 0:
                t.armies += 1
                self.armies_to_place -= 1
                self.message = f"{cp.name}: {self.armies_to_place} armies left to place."
                if self.armies_to_place == 0:
                    self.message = f"{cp.name}: All reinforcements placed. Click '→ Attack Phase'."

        elif self.phase == Phase.ATTACK:
            if t.owner == self.current_player and t.armies > 1:
                self.attack_source = name
                self.attack_target = None
                self.message = f"Attacking from {name} ({t.armies} armies). Click enemy territory."
            elif self.attack_source and t.owner != self.current_player and t.owner is not None:
                src = self.territories[self.attack_source]
                if name in src.neighbours:
                    self.attack_target = name
                    self.message = f"{self.attack_source} → {name}. Choose dice count below."
                else:
                    self.message = f"{name} is not adjacent to {self.attack_source}!"

        elif self.phase == Phase.FORTIFY:
            if not self.fortify_source:
                if t.owner == self.current_player and t.armies > 1:
                    self.fortify_source = name
                    self.message = f"Moving from {name}. Click adjacent own territory."
            else:
                src = self.territories[self.fortify_source]
                if t.name == self.fortify_source:
                    self.fortify_source = None
                    self.message = "Cancelled fortify."
                elif t.owner == self.current_player and t.name in src.neighbours and src.armies > 1:
                    move = src.armies - 1
                    src.armies -= move
                    t.armies += move
                    self._log(f"{cp.name} moved {move} armies {src.name}→{t.name}")
                    self.fortify_source = None
                    self.message = f"Moved {move} armies. Click '→ End Turn'."
                else:
                    self.message = f"Must be adjacent own territory!"

    def _territory_at(self, pos) -> Optional[str]:
        for name, t in self.territories.items():
            dx = pos[0] - t.pos[0]
            dy = pos[1] - t.pos[1]
            if dx*dx + dy*dy <= 22*22:
                return name
        return None

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        while True:
            for event in pygame.event.get():
                self.handle_event(event)

            # AI actions
            if self.ai_action_pending and pygame.time.get_ticks() >= self.ai_timer:
                if self.phase not in (Phase.SETUP_PLAYERS, Phase.GAME_OVER):
                    cp = self.players[self.current_player]
                    if not cp.is_human and cp.alive:
                        self.ai_take_action()

            self.draw()
            self.clock.tick(FPS)

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    game = RiskGame()
    game.run()
