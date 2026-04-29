from __future__ import annotations

import math
import random
import struct
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

import arcade


SCREEN_WIDTH = 1152
SCREEN_HEIGHT = 812
SCREEN_TITLE = "Arcade Dungeon Crawl"

TILE_SIZE = 48
MAP_WIDTH = 24
MAP_HEIGHT = 18
HUD_HEIGHT = 140
INVENTORY_CAPACITY = 128
WEAPON_DROP_CHANCE = 0.06
FINAL_FLOOR = 20
BOSS_KIND = "abyss_titan"

WALL = "#"
FLOOR = "."
TREASURE = "treasure"
POTION = "potion"

BACKGROUND_COLOR = (13, 14, 20)
FLOOR_COLOR = (88, 77, 57)
WALL_COLOR = (34, 35, 43)
HUD_COLOR = (9, 10, 15)
ACCENT_COLOR = (110, 192, 255)
PLAYER_COLOR = (69, 161, 255)
ENEMY_COLOR = (214, 74, 74)
EXIT_COLOR = (118, 92, 255)
TREASURE_COLOR = (244, 197, 66)
POTION_COLOR = (82, 215, 173)

ENEMY_TYPES: dict[str, dict[str, object]] = {
	"skitter": {
		"label": "Skitter",
		"snippet": "Skitter: fast tunnel vermin that rush in swarms.",
		"health": 2,
		"damage": 1,
		"color": (146, 201, 102),
		"detail": (218, 247, 168),
		"speed": 16.0,
		"xp": 9,
		"gold": 6,
		"sense": 9,
		"weight": 4,
	},
	"guard": {
		"label": "Bone Guard",
		"snippet": "Bone Guard: disciplined sentries that hold chokepoints.",
		"health": 3,
		"damage": 1,
		"color": (214, 74, 74),
		"detail": (255, 214, 214),
		"speed": 13.0,
		"xp": 12,
		"gold": 8,
		"sense": 7,
		"weight": 5,
	},
	"brute": {
		"label": "Crypt Brute",
		"snippet": "Crypt Brute: heavy hitters that lumber but punish mistakes.",
		"health": 5,
		"damage": 2,
		"color": (171, 107, 69),
		"detail": (245, 207, 175),
		"speed": 8.5,
		"xp": 20,
		"gold": 12,
		"sense": 6,
		"weight": 2,
	},
	"wisp": {
		"label": "Wisp",
		"snippet": "Wisp: volatile spirits that dart and strike hard.",
		"health": 2,
		"damage": 2,
		"color": (132, 130, 255),
		"detail": (214, 213, 255),
		"speed": 18.0,
		"xp": 16,
		"gold": 10,
		"sense": 10,
		"weight": 2,
	},
	BOSS_KIND: {
		"label": "Abyss Titan",
		"snippet": "Abyss Titan: the final guardian of floor 20.",
		"health": 34,
		"damage": 4,
		"color": (186, 44, 44),
		"detail": (255, 188, 188),
		"speed": 6.0,
		"xp": 240,
		"gold": 220,
		"sense": 14,
		"weight": 0,
	},
}

WEAPON_TYPES: dict[str, dict[str, object]] = {
	"dual_blades": {
		"label": "Dual Blades",
		"damage_scale": 0.7,
		"strikes": 2,
		"crit": 0.12,
		"blurb": "Two quick cuts that can shred single targets.",
	},
	"greatsword": {
		"label": "Greatsword",
		"damage_scale": 1.9,
		"strikes": 1,
		"crit": 0.08,
		"blurb": "Slow but devastating heavy swings.",
	},
	"katana": {
		"label": "Katana",
		"damage_scale": 1.3,
		"strikes": 1,
		"crit": 0.24,
		"blurb": "Precise cuts with high critical potential.",
	},
	"shortsword_shield": {
		"label": "Shortsword & Shield",
		"damage_scale": 0.95,
		"strikes": 1,
		"crit": 0.12,
		"blurb": "Balanced blade + guard stance. Use Q to block.",
	},
}

RARITY_COLORS: dict[int, tuple[int, int, int]] = {
	1: (140, 140, 140),  # grey
	2: (90, 190, 92),    # green
	3: (72, 133, 255),   # blue
	4: (164, 95, 222),   # purple
	5: (236, 194, 66),   # gold
}

RARITY_NAMES: dict[int, str] = {
	1: "Rarity 1",
	2: "Rarity 2",
	3: "Rarity 3",
	4: "Rarity 4",
	5: "Rarity 5",
}

# Weighted so rarity 4 and 5 are drastically less likely than 1-3.
RARITY_DROP_WEIGHTS: dict[int, int] = {
	1: 58,
	2: 28,
	3: 12,
	4: 1,
	5: 1,
}

WEAPON_ORDER = ["dual_blades", "greatsword", "katana", "shortsword_shield"]
WEAPON_SELECT_HOTKEYS = {
	arcade.key.KEY_1: "dual_blades",
	arcade.key.KEY_2: "greatsword",
	arcade.key.KEY_3: "katana",
	arcade.key.KEY_4: "shortsword_shield",
}


@dataclass
class Enemy:
	x: int
	y: int
	kind: str
	health: int
	damage: int
	render_x: float = 0.0
	render_y: float = 0.0
	facing_x: int = 1
	facing_y: int = 0
	step_phase: float = 0.0
	hit_flash: float = 0.0


@dataclass
class AttackEffect:
	world_x: float
	world_y: float
	kind: str
	color: tuple[int, int, int]
	age: float = 0.0
	duration: float = 0.22


@dataclass
class Item:
	x: int
	y: int
	kind: str


@dataclass
class RunSummary:
	floors_cleared: int
	score: int
	level: int
	turns: int
	victory: bool = False


def generate_tone(path: Path, frequency: float, duration: float, volume: float = 0.35) -> None:
	"""Generate a tiny WAV file so the game has sound without external assets."""
	sample_rate = 22050
	amplitude = int(32767 * max(0.0, min(volume, 1.0)))
	frame_count = int(sample_rate * duration)

	with wave.open(str(path), "wb") as wav_file:
		wav_file.setnchannels(1)
		wav_file.setsampwidth(2)
		wav_file.setframerate(sample_rate)

		frames = bytearray()
		for index in range(frame_count):
			fade = 1.0 - (index / max(frame_count, 1))
			sample = math.sin((2.0 * math.pi * frequency * index) / sample_rate)
			frames.extend(struct.pack("<h", int(amplitude * sample * fade)))
		wav_file.writeframes(frames)


class SoundBank:
	"""Lazy-generated procedural sound effects used by the crawler."""

	def __init__(self) -> None:
		self.enabled = True
		self._sound_dir = Path(tempfile.gettempdir()) / "arcade_dungeon_sounds"
		self._sound_dir.mkdir(parents=True, exist_ok=True)

		self.attack = self._load_sound("attack.wav", 220, 0.10)
		self.hit = self._load_sound("hit.wav", 150, 0.12)
		self.pickup = self._load_sound("pickup.wav", 640, 0.10)
		self.stairs = self._load_sound("stairs.wav", 360, 0.25)
		self.level_up = self._load_sound("level_up.wav", 820, 0.22)
		self.game_over = self._load_sound("game_over.wav", 110, 0.40)

	def _load_sound(self, filename: str, frequency: float, duration: float) -> arcade.Sound | None:
		sound_path = self._sound_dir / filename
		try:
			if not sound_path.exists():
				generate_tone(sound_path, frequency, duration)
			return arcade.load_sound(sound_path)
		except Exception:
			self.enabled = False
			return None

	def play(self, sound: arcade.Sound | None, volume: float = 0.45) -> None:
		if not self.enabled or sound is None:
			return
		try:
			arcade.play_sound(sound, volume)
		except Exception:
			self.enabled = False


class TitleView(arcade.View):
	"""Opening screen with controls and gameplay summary."""

	def __init__(self, sound_bank: SoundBank) -> None:
		super().__init__()
		self.sound_bank = sound_bank
		self.animation_time = 0.0

	def on_show_view(self) -> None:
		self.window.background_color = BACKGROUND_COLOR

	def on_update(self, delta_time: float) -> None:
		self.animation_time += delta_time

	def on_draw(self) -> None:
		self.clear()

		pulse = 20 * math.sin(self.animation_time * 2.2)
		arcade.draw_text(
			"ARCADE DUNGEON CRAWL",
			SCREEN_WIDTH / 2,
			SCREEN_HEIGHT - 140,
			(240, 244, 255),
			34,
			anchor_x="center",
			font_name="Arial",
			bold=True,
		)
		arcade.draw_text(
			"Top-down dungeon crawling in Python Arcade",
			SCREEN_WIDTH / 2,
			SCREEN_HEIGHT - 185,
			ACCENT_COLOR,
			16,
			anchor_x="center",
			font_name="Arial",
		)

		for index in range(8):
			x_pos = 180 + index * 110
			size = 18 + (pulse * 0.1)
			arcade.draw_circle_filled(x_pos, SCREEN_HEIGHT - 255, size, (36, 41, 56))
			arcade.draw_circle_outline(x_pos, SCREEN_HEIGHT - 255, size + 6, (74, 100, 140), 2)

		instructions = [
			"Move with WASD or arrow keys.",
			"Bump into enemies or press Space to strike adjacent targets.",
			"Collect treasure, drink potions, and reach the stairs to descend.",
			"Every floor gets harder, and experience levels up your explorer.",
			"Press Enter to choose your weapon and start a run.",
		]
		for index, line in enumerate(instructions):
			arcade.draw_text(
				line,
				SCREEN_WIDTH / 2,
				SCREEN_HEIGHT - 310 - index * 38,
				(218, 220, 231),
				17,
				anchor_x="center",
				font_name="Arial",
			)

		arcade.draw_lrbt_rectangle_filled(176, SCREEN_WIDTH - 176, 120, 230, (18, 20, 28, 220))
		arcade.draw_text(
			"PRESS ENTER",
			SCREEN_WIDTH / 2,
			160,
			TREASURE_COLOR,
			28,
			anchor_x="center",
			font_name="Arial",
			bold=True,
		)
		arcade.draw_text(
			"Generated floors, leveling, title/result screens, and procedural sound effects.",
			SCREEN_WIDTH / 2,
			125,
			(150, 178, 214),
			13,
			anchor_x="center",
			font_name="Arial",
		)

	def on_key_press(self, symbol: int, modifiers: int) -> None:
		if symbol in (arcade.key.ENTER, arcade.key.RETURN, arcade.key.SPACE):
			self.window.show_view(WeaponSelectView(self.sound_bank))


class WeaponSelectView(arcade.View):
	"""Weapon picker shown before each run starts."""

	def __init__(self, sound_bank: SoundBank) -> None:
		super().__init__()
		self.sound_bank = sound_bank
		self.weapon_rarities: dict[str, int] = {}

	def on_show_view(self) -> None:
		self.window.background_color = (15, 16, 24)
		self.weapon_rarities = {weapon_key: 1 for weapon_key in WEAPON_ORDER}

	def on_draw(self) -> None:
		self.clear()
		arcade.draw_text(
			"Choose Your Weapon",
			SCREEN_WIDTH / 2,
			SCREEN_HEIGHT - 140,
			(241, 245, 255),
			34,
			anchor_x="center",
			font_name="Arial",
			bold=True,
		)
		arcade.draw_text(
			"Selection is locked for the run. Choose again after a run ends.",
			SCREEN_WIDTH / 2,
			SCREEN_HEIGHT - 184,
			ACCENT_COLOR,
			15,
			anchor_x="center",
			font_name="Arial",
		)

		for index, weapon_key in enumerate(WEAPON_ORDER, start=1):
			weapon = WEAPON_TYPES[weapon_key]
			rarity = self.weapon_rarities.get(weapon_key, 1)
			rarity_color = RARITY_COLORS[rarity]
			rarity_name = RARITY_NAMES[rarity]
			top = SCREEN_HEIGHT - 250 - (index - 1) * 115
			arcade.draw_lrbt_rectangle_filled(140, SCREEN_WIDTH - 140, top - 76, top, (24, 26, 38, 220))
			arcade.draw_text(
				f"{index}. {weapon['label']}",
				165,
				top - 32,
				(250, 250, 252),
				20,
				font_name="Arial",
				bold=True,
			)
			arcade.draw_text(
				f"{rarity_name}",
				SCREEN_WIDTH - 165,
				top - 32,
				rarity_color,
				16,
				anchor_x="right",
				font_name="Arial",
				bold=True,
			)
			arcade.draw_text(
				str(weapon["blurb"]),
				165,
				top - 58,
				(192, 198, 220),
				13,
				font_name="Arial",
				width=SCREEN_WIDTH - 300,
			)

		arcade.draw_text(
			"Press 1-4 to begin. Press Esc to return to title.",
			SCREEN_WIDTH / 2,
			72,
			TREASURE_COLOR,
			16,
			anchor_x="center",
			font_name="Arial",
		)

	def on_key_press(self, symbol: int, modifiers: int) -> None:
		if symbol in WEAPON_SELECT_HOTKEYS:
			weapon_key = WEAPON_SELECT_HOTKEYS[symbol]
			weapon_rarity = self.weapon_rarities.get(weapon_key, 1)
			self.window.show_view(GameView(self.sound_bank, weapon_key, weapon_rarity))
		elif symbol == arcade.key.ESCAPE:
			self.window.show_view(TitleView(self.sound_bank))


class ResultView(arcade.View):
	"""Shown when the run ends in defeat or victory."""

	def __init__(self, sound_bank: SoundBank, summary: RunSummary) -> None:
		super().__init__()
		self.sound_bank = sound_bank
		self.summary = summary

	def on_show_view(self) -> None:
		if self.summary.victory:
			self.window.background_color = (12, 20, 14)
		else:
			self.window.background_color = (16, 10, 12)

	def on_draw(self) -> None:
		self.clear()
		arcade.draw_text(
			"VICTORY" if self.summary.victory else "RUN ENDED",
			SCREEN_WIDTH / 2,
			SCREEN_HEIGHT - 160,
			(219, 255, 219) if self.summary.victory else (255, 220, 220),
			34,
			anchor_x="center",
			font_name="Arial",
			bold=True,
		)
		if self.summary.victory:
			arcade.draw_text(
				"You defeated the Abyss Titan on floor 20.",
				SCREEN_WIDTH / 2,
				SCREEN_HEIGHT - 218,
				(170, 232, 176),
				16,
				anchor_x="center",
				font_name="Arial",
			)
		arcade.draw_text(
			f"Floors cleared: {self.summary.floors_cleared}",
			SCREEN_WIDTH / 2,
			SCREEN_HEIGHT - (270 if self.summary.victory else 255),
			(240, 240, 246),
			20,
			anchor_x="center",
			font_name="Arial",
		)
		arcade.draw_text(
			f"Score: {self.summary.score}    Level: {self.summary.level}    Turns: {self.summary.turns}",
			SCREEN_WIDTH / 2,
			SCREEN_HEIGHT - (310 if self.summary.victory else 295),
			ACCENT_COLOR,
			18,
			anchor_x="center",
			font_name="Arial",
		)
		arcade.draw_text(
			"Press Enter for a new run or Esc for the title screen.",
			SCREEN_WIDTH / 2,
			150,
			TREASURE_COLOR,
			18,
			anchor_x="center",
			font_name="Arial",
		)

	def on_key_press(self, symbol: int, modifiers: int) -> None:
		if symbol in (arcade.key.ENTER, arcade.key.RETURN):
			self.window.show_view(WeaponSelectView(self.sound_bank))
		elif symbol == arcade.key.ESCAPE:
			self.window.show_view(TitleView(self.sound_bank))


class ConfirmQuitView(arcade.View):
	"""Pause overlay asking the player to confirm quitting to the title screen."""

	def __init__(self, game_view: "GameView") -> None:
		super().__init__()
		self.game_view = game_view

	def on_show_view(self) -> None:
		self.window.background_color = BACKGROUND_COLOR

	def on_draw(self) -> None:
		self.game_view.on_draw()

		arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT, (0, 0, 0, 160))

		box_w, box_h = 460, 190
		bx = SCREEN_WIDTH / 2 - box_w / 2
		by = SCREEN_HEIGHT / 2 - box_h / 2
		arcade.draw_lbwh_rectangle_filled(bx, by, box_w, box_h, (18, 20, 30, 245))
		arcade.draw_lbwh_rectangle_outline(bx, by, box_w, box_h, ACCENT_COLOR, 2)

		arcade.draw_text(
			"Quit to Title?",
			SCREEN_WIDTH / 2,
			by + box_h - 44,
			(241, 245, 255),
			26,
			anchor_x="center",
			font_name="Arial",
			bold=True,
		)
		arcade.draw_text(
			"Your run progress will be lost.",
			SCREEN_WIDTH / 2,
			by + box_h - 82,
			(180, 188, 210),
			15,
			anchor_x="center",
			font_name="Arial",
		)
		arcade.draw_text(
			"Enter  /  Y  —  Quit to title",
			SCREEN_WIDTH / 2,
			by + 68,
			TREASURE_COLOR,
			15,
			anchor_x="center",
			font_name="Arial",
		)
		arcade.draw_text(
			"Esc  /  N  —  Resume game",
			SCREEN_WIDTH / 2,
			by + 38,
			(140, 220, 160),
			15,
			anchor_x="center",
			font_name="Arial",
		)

	def on_key_press(self, symbol: int, modifiers: int) -> None:
		if symbol in (arcade.key.ENTER, arcade.key.RETURN, arcade.key.Y):
			self.window.show_view(TitleView(self.game_view.sound_bank))
		elif symbol in (arcade.key.ESCAPE, arcade.key.N):
			self.window.show_view(self.game_view)


class GameView(arcade.View):
	"""Arcade implementation of a top-down dungeon crawler."""

	def __init__(self, sound_bank: SoundBank, starting_weapon: str, starting_weapon_rarity: int) -> None:
		super().__init__()
		self.sound_bank = sound_bank
		self.animation_time = 0.0

		self.map_data: list[list[str]] = []
		self.floor_tiles: list[tuple[int, int]] = []
		self.enemies: list[Enemy] = []
		self.items: list[Item] = []
		self.player_pos = (1, 1)
		self.exit_pos = (1, 1)
		self.player_render_x = 1.0
		self.player_render_y = 1.0
		self.player_facing = (1, 0)
		self.player_walk_phase = 0.0
		self.player_hit_flash = 0.0
		self.attack_effects: list[AttackEffect] = []
		self.camera_x = 0.0
		self.camera_y = 0.0
		self.enemy_lore_seen: set[str] = set()
		self.equipped_weapon = starting_weapon if starting_weapon in WEAPON_TYPES else "shortsword_shield"
		self.weapon_rarity = min(5, max(1, int(starting_weapon_rarity)))
		self.weapon_rarities: dict[str, int] = {weapon_key: 1 for weapon_key in WEAPON_ORDER}
		self.weapon_rarities[self.equipped_weapon] = self.weapon_rarity
		self.block_active = False
		self.dual_blades_dash_timer = 0.0
		self.ability_cooldowns: dict[str, float] = {k: 0.0 for k in WEAPON_ORDER}
		self.inventory_open = False
		self.inventory_weapon_cursor = WEAPON_ORDER.index(self.equipped_weapon)
		self.inventory_items: list[str] = []

		self.floor_number = 1
		self.score = 0
		self.turn_count = 0
		self.level = 1
		self.experience = 0
		self.max_health = 6
		self.player_health = self.max_health
		self.player_attack = 1
		self.status_text = ""

		self.setup_new_run()

	def on_show_view(self) -> None:
		self.window.background_color = BACKGROUND_COLOR

	def setup_new_run(self) -> None:
		"""Reset run progression and create the opening floor."""
		self.floor_number = 1
		self.score = 0
		self.turn_count = 0
		self.level = 1
		self.experience = 0
		self.max_health = 6
		self.player_health = self.max_health
		self.player_attack = 1
		self.block_active = False
		self.dual_blades_dash_timer = 0.0
		self.ability_cooldowns = {k: 0.0 for k in WEAPON_ORDER}
		self.inventory_open = False
		self.inventory_items.clear()
		self.inventory_weapon_cursor = WEAPON_ORDER.index(self.equipped_weapon)
		self.enemy_lore_seen.clear()
		self.setup_floor(reset_health=False)
		rarity_name = RARITY_NAMES[self.weapon_rarity]
		self.status_text = f"{self.get_weapon_label()} ({rarity_name}) equipped. Find treasure and descend the stairs."

	def get_weapon_label(self) -> str:
		return str(WEAPON_TYPES[self.equipped_weapon]["label"])

	def equip_weapon(self, weapon_key: str) -> None:
		"""Switch equipped weapon from inventory selection."""
		if weapon_key not in WEAPON_TYPES:
			return
		self.equipped_weapon = weapon_key
		self.weapon_rarity = self.weapon_rarities.get(weapon_key, 1)
		self.block_active = False
		rarity_name = RARITY_NAMES[self.weapon_rarity]
		self.status_text = f"Equipped {self.get_weapon_label()} ({rarity_name})."

	def can_block(self) -> bool:
		"""Only shields can enter block stance."""
		return self.equipped_weapon == "shortsword_shield"

	def activate_block(self) -> None:
		"""Raise shield for the next enemy phase, if shield is equipped."""
		if not self.can_block():
			self.status_text = "You need to equip Shield (key 5) to block."
			return
		if self.block_active:
			self.status_text = "Shield is already raised."
			return

		self.block_active = True
		self.turn_count += 1
		self.status_text = "You raise your shield and brace for impact."
		self.enemy_turn()

	def add_inventory_item(self, item_name: str) -> None:
		"""Store collected item records up to the inventory capacity."""
		if len(self.inventory_items) >= INVENTORY_CAPACITY:
			self.status_text = "Inventory full (128). Item could not be stored."
			return
		self.inventory_items.append(item_name)

	def roll_weapon_drop_rarity(self) -> int:
		"""Roll rarity with very low odds for high tiers."""
		rarity_pool = list(RARITY_DROP_WEIGHTS.keys())
		rarity_weights = list(RARITY_DROP_WEIGHTS.values())
		return int(random.choices(rarity_pool, weights=rarity_weights, k=1)[0])

	def try_weapon_drop(self) -> str | None:
		"""Attempt enemy weapon drop; return message if a weapon drops."""
		if random.random() > WEAPON_DROP_CHANCE:
			return None

		dropped_weapon = random.choice(WEAPON_ORDER)
		dropped_rarity = self.roll_weapon_drop_rarity()
		weapon_label = str(WEAPON_TYPES[dropped_weapon]["label"])
		rarity_name = RARITY_NAMES[dropped_rarity]

		self.add_inventory_item(f"{weapon_label} ({rarity_name})")

		current_rarity = self.weapon_rarities.get(dropped_weapon, 1)
		if dropped_rarity > current_rarity:
			self.weapon_rarities[dropped_weapon] = dropped_rarity
			if self.equipped_weapon == dropped_weapon:
				self.weapon_rarity = dropped_rarity
			return f"Drop: {weapon_label} [{rarity_name}] upgraded in your inventory."

		return f"Drop: {weapon_label} [{rarity_name}] added to inventory."

	def compute_player_hit(self) -> tuple[int, bool]:
		"""Calculate damage and crit result based on equipped weapon."""
		weapon = WEAPON_TYPES[self.equipped_weapon]
		rarity_scale = 1.0 + (self.weapon_rarity - 1) * 0.12
		base = max(1, int(round(self.player_attack * float(weapon["damage_scale"]) * rarity_scale)))
		damage = max(1, base + random.randint(-1, 1))
		is_crit = random.random() < float(weapon["crit"])
		if is_crit:
			damage += max(1, self.level // 3)
		return damage, is_crit

	def get_attack_speed_multiplier(self) -> float:
		"""Return effective attack speed multiplier from weapon rarity.

		In this turn-based combat model, attack speed is represented by the
		number of hits that can occur during one attack action.
		"""
		return 1.0 + (self.weapon_rarity - 1) * 0.12

	def get_strike_count_for_attack(self) -> int:
		"""Convert attack speed into strike count for the current attack action."""
		weapon = WEAPON_TYPES[self.equipped_weapon]
		base_strikes = max(1.0, float(weapon["strikes"]))
		scaled_strikes = base_strikes * self.get_attack_speed_multiplier()
		whole = int(math.floor(scaled_strikes))
		fraction = scaled_strikes - whole
		if random.random() < fraction:
			whole += 1
		return max(1, whole)

	def setup_floor(self, reset_health: bool) -> None:
		"""Generate a fresh dungeon floor and populate it for the current depth."""
		self.map_data = [[WALL for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]
		current_x = MAP_WIDTH // 2
		current_y = MAP_HEIGHT // 2
		carved_tiles = {(current_x, current_y)}
		self.map_data[current_y][current_x] = FLOOR

		target_floor_count = min(160 + self.floor_number * 8, MAP_WIDTH * MAP_HEIGHT - 16)
		for _ in range(1200):
			step_x, step_y = random.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
			current_x = max(1, min(MAP_WIDTH - 2, current_x + step_x))
			current_y = max(1, min(MAP_HEIGHT - 2, current_y + step_y))
			self.map_data[current_y][current_x] = FLOOR
			carved_tiles.add((current_x, current_y))

			if random.random() < 0.14:
				for offset_y in range(-1, 2):
					for offset_x in range(-1, 2):
						room_x = current_x + offset_x
						room_y = current_y + offset_y
						if 1 <= room_x < MAP_WIDTH - 1 and 1 <= room_y < MAP_HEIGHT - 1:
							self.map_data[room_y][room_x] = FLOOR
							carved_tiles.add((room_x, room_y))

			if len(carved_tiles) >= target_floor_count:
				break

		self.floor_tiles = sorted(carved_tiles)
		self.player_pos = random.choice(self.floor_tiles)
		self.player_render_x = float(self.player_pos[0])
		self.player_render_y = float(self.player_pos[1])
		self.player_walk_phase = 0.0
		is_final_floor = self.floor_number >= FINAL_FLOOR
		self.exit_pos = (-1, -1) if is_final_floor else self.find_far_floor_tile(self.player_pos)

		reserved = {self.player_pos}
		if not is_final_floor:
			reserved.add(self.exit_pos)
			self.items = self.spawn_items(reserved)
			reserved.update((item.x, item.y) for item in self.items)
		else:
			# Final floor is a boss arena; no stairs or loot distraction.
			self.items = []
		self.enemies = self.spawn_enemies(reserved)
		self.update_camera(0.0, immediate=True)

		if reset_health:
			self.player_health = min(self.max_health, self.player_health + 1)

	def find_far_floor_tile(self, origin: tuple[int, int]) -> tuple[int, int]:
		"""Pick a floor tile far enough away to make each floor worth exploring."""
		far_tiles = [
			tile for tile in self.floor_tiles
			if abs(tile[0] - origin[0]) + abs(tile[1] - origin[1]) >= 10
		]
		return random.choice(far_tiles or self.floor_tiles)

	def spawn_items(self, reserved_tiles: set[tuple[int, int]]) -> list[Item]:
		"""Place treasure and potion pickups on open tiles."""
		items: list[Item] = []
		available_tiles = [tile for tile in self.floor_tiles if tile not in reserved_tiles]
		random.shuffle(available_tiles)

		for _ in range(6 + self.floor_number):
			tile_x, tile_y = available_tiles.pop()
			items.append(Item(tile_x, tile_y, TREASURE))

		for _ in range(max(2, 4 - self.floor_number // 2)):
			tile_x, tile_y = available_tiles.pop()
			items.append(Item(tile_x, tile_y, POTION))

		return items

	def spawn_enemies(self, reserved_tiles: set[tuple[int, int]]) -> list[Enemy]:
		"""Create a floor-appropriate enemy population away from the spawn tile."""
		if self.floor_number >= FINAL_FLOOR:
			boss_tile = self.find_far_floor_tile(self.player_pos)
			archetype = ENEMY_TYPES[BOSS_KIND]
			boss_health = int(archetype["health"]) + self.level * 2
			return [
				Enemy(
					boss_tile[0],
					boss_tile[1],
					BOSS_KIND,
					boss_health,
					int(archetype["damage"]),
					render_x=float(boss_tile[0]),
					render_y=float(boss_tile[1]),
					facing_x=-1,
					step_phase=random.random() * math.tau,
				)
			]

		enemies: list[Enemy] = []
		available_tiles = [
			tile for tile in self.floor_tiles
			if tile not in reserved_tiles
			and abs(tile[0] - self.player_pos[0]) + abs(tile[1] - self.player_pos[1]) >= 6
		]
		random.shuffle(available_tiles)

		enemy_count = min(5 + self.floor_number * 2, len(available_tiles))
		for _ in range(enemy_count):
			tile_x, tile_y = available_tiles.pop()
			enemy_kind = self.choose_enemy_kind()
			archetype = ENEMY_TYPES[enemy_kind]
			health = int(archetype["health"]) + self.floor_number // 3
			damage = int(archetype["damage"]) + self.floor_number // 5
			enemies.append(
				Enemy(
					tile_x,
					tile_y,
					enemy_kind,
					health,
					damage,
					render_x=float(tile_x),
					render_y=float(tile_y),
					facing_x=random.choice((-1, 1)),
					step_phase=random.random() * math.tau,
				)
			)

		return enemies

	def choose_enemy_kind(self) -> str:
		"""Pick an enemy archetype with floor-scaled weights."""
		weighted_kinds: list[str] = []
		for kind, archetype in ENEMY_TYPES.items():
			weight = int(archetype["weight"])
			if weight <= 0:
				continue
			if kind == "brute":
				weight += self.floor_number // 2
			elif kind == "wisp":
				weight += max(0, self.floor_number - 2)
			weighted_kinds.extend([kind] * max(1, weight))
		return random.choice(weighted_kinds)

	def on_update(self, delta_time: float) -> None:
		self.animation_time += delta_time
		if self.dual_blades_dash_timer > 0.0:
			self.dual_blades_dash_timer = max(0.0, self.dual_blades_dash_timer - delta_time)
		for key in self.ability_cooldowns:
			if self.ability_cooldowns[key] > 0.0:
				self.ability_cooldowns[key] = max(0.0, self.ability_cooldowns[key] - delta_time)
		self.player_render_x += (self.player_pos[0] - self.player_render_x) * min(1.0, delta_time * 18.0)
		self.player_render_y += (self.player_pos[1] - self.player_render_y) * min(1.0, delta_time * 18.0)
		movement_delta = abs(self.player_render_x - self.player_pos[0]) + abs(self.player_render_y - self.player_pos[1])
		self.player_walk_phase += movement_delta * 8.0
		self.player_hit_flash = max(0.0, self.player_hit_flash - delta_time * 4.0)

		for enemy in self.enemies:
			speed = float(ENEMY_TYPES[enemy.kind]["speed"])
			enemy.render_x += (enemy.x - enemy.render_x) * min(1.0, delta_time * speed)
			enemy.render_y += (enemy.y - enemy.render_y) * min(1.0, delta_time * speed)
			enemy.step_phase += delta_time * speed * 0.9
			enemy.hit_flash = max(0.0, enemy.hit_flash - delta_time * 4.0)

		for effect in list(self.attack_effects):
			effect.age += delta_time
			if effect.age >= effect.duration:
				self.attack_effects.remove(effect)

		self.update_camera(delta_time)

	def update_camera(self, delta_time: float, immediate: bool = False) -> None:
		"""Follow the player while clamping the camera to map bounds."""
		viewport_width = float(SCREEN_WIDTH)
		viewport_height = float(SCREEN_HEIGHT - HUD_HEIGHT)
		world_width = float(MAP_WIDTH * TILE_SIZE)
		world_height = float(MAP_HEIGHT * TILE_SIZE)

		player_world_x, player_world_y = self.tile_to_world_center(self.player_render_x, self.player_render_y)
		target_x = player_world_x - viewport_width / 2
		target_y = player_world_y - viewport_height / 2

		max_x = max(0.0, world_width - viewport_width)
		max_y = max(0.0, world_height - viewport_height)
		target_x = max(0.0, min(max_x, target_x))
		target_y = max(0.0, min(max_y, target_y))

		if immediate:
			self.camera_x = target_x
			self.camera_y = target_y
			return

		follow_strength = min(1.0, delta_time * 10.0)
		self.camera_x += (target_x - self.camera_x) * follow_strength
		self.camera_y += (target_y - self.camera_y) * follow_strength

	def on_draw(self) -> None:
		self.clear()
		self.draw_map()
		self.draw_attack_effects(layer="under")
		self.draw_items()
		self.draw_exit()
		self.draw_enemies()
		self.draw_player()
		self.draw_attack_effects(layer="over")
		self.draw_hud()
		self.draw_cooldown_panel()
		if self.inventory_open:
			self.draw_inventory_overlay()

	def on_key_press(self, symbol: int, modifiers: int) -> None:
		if symbol == arcade.key.I:
			self.inventory_open = not self.inventory_open
			if self.inventory_open:
				self.inventory_weapon_cursor = WEAPON_ORDER.index(self.equipped_weapon)
				self.status_text = "Inventory opened. Use Up/Down and Enter to equip."
			else:
				self.status_text = "Inventory closed."
			return

		if self.inventory_open:
			if symbol in (arcade.key.ESCAPE,):
				self.inventory_open = False
				self.status_text = "Inventory closed."
				return
			if symbol in (arcade.key.UP, arcade.key.W):
				self.inventory_weapon_cursor = (self.inventory_weapon_cursor - 1) % len(WEAPON_ORDER)
				return
			if symbol in (arcade.key.DOWN, arcade.key.S):
				self.inventory_weapon_cursor = (self.inventory_weapon_cursor + 1) % len(WEAPON_ORDER)
				return
			if symbol in (arcade.key.ENTER, arcade.key.RETURN, arcade.key.SPACE):
				self.equip_weapon(WEAPON_ORDER[self.inventory_weapon_cursor])
				return

		if symbol == arcade.key.ESCAPE:
			self.window.show_view(ConfirmQuitView(self))
			return

		if symbol == arcade.key.R:
			self.window.show_view(GameView(self.sound_bank, self.equipped_weapon, self.weapon_rarity))
			return

		if symbol == arcade.key.Q:
			self.activate_block()
			return

		if symbol == arcade.key.P:
			self.use_weapon_ability()
			return

		move_map = {
			arcade.key.W: (0, -1),
			arcade.key.UP: (0, -1),
			arcade.key.S: (0, 1),
			arcade.key.DOWN: (0, 1),
			arcade.key.A: (-1, 0),
			arcade.key.LEFT: (-1, 0),
			arcade.key.D: (1, 0),
			arcade.key.RIGHT: (1, 0),
		}

		if symbol in move_map:
			move_x, move_y = move_map[symbol]
			self.try_move_player(move_x, move_y)
		elif symbol == arcade.key.SPACE:
			self.player_attack_swing()

	def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> None:
		"""Use right-click to attack, targeting the clicked adjacent enemy if possible."""
		if self.inventory_open:
			return

		if button != arcade.MOUSE_BUTTON_RIGHT:
			return

		target_tile = self.screen_to_tile(x, y)
		if target_tile is None:
			return

		player_x, player_y = self.player_pos
		target_x, target_y = target_tile
		if abs(target_x - player_x) + abs(target_y - player_y) == 1:
			enemy = self.enemy_at(target_x, target_y)
			if enemy is not None:
				self.player_facing = (target_x - player_x, target_y - player_y)
				self.damage_enemy(enemy)
				return

		# Fallback: keep right-click responsive even when not clicking an adjacent tile.
		self.player_attack_swing()

	def try_move_player(self, delta_x: int, delta_y: int) -> None:
		"""Move one tile, or two tiles while dual-blades dash is active."""
		self.player_facing = (delta_x, delta_y)
		steps_to_take = 2 if self.equipped_weapon == "dual_blades" and self.dual_blades_dash_timer > 0.0 else 1
		moved_any = False

		for _ in range(steps_to_take):
			new_x = self.player_pos[0] + delta_x
			new_y = self.player_pos[1] + delta_y

			if not self.tile_is_walkable(new_x, new_y):
				if not moved_any:
					self.status_text = "Ancient stone blocks your path."
				break

			target_enemy = self.enemy_at(new_x, new_y)
			if target_enemy is not None:
				self.damage_enemy(target_enemy)
				return

			self.player_pos = (new_x, new_y)
			moved_any = True
			self.collect_item_if_present()

			if self.player_pos == self.exit_pos:
				self.advance_floor()
				return

		if not moved_any:
			return

		self.turn_count += 1
		self.enemy_turn()

	def use_weapon_ability(self) -> None:
		"""Trigger the equipped weapon's special ability with the P key."""
		cd = self.ability_cooldowns.get(self.equipped_weapon, 0.0)
		if cd > 0.0:
			self.status_text = f"Ability on cooldown ({cd:.1f}s remaining)."
			return
		if self.equipped_weapon == "greatsword":
			if self.use_greatsword_spin():
				self.ability_cooldowns["greatsword"] = 30.0
		elif self.equipped_weapon == "katana":
			if self.use_katana_teleport():
				self.ability_cooldowns["katana"] = 180.0
		elif self.equipped_weapon == "dual_blades":
			self.use_dual_blades_dash()
			self.ability_cooldowns["dual_blades"] = 60.0
		else:
			self.use_shield_bulwark()

	def award_enemy_defeat(self, enemy: Enemy, archetype: dict[str, object]) -> bool:
		"""Apply rewards and side effects for defeating an enemy. Return True if run ended."""
		self.score += int(archetype["gold"]) + self.floor_number * 2
		self.experience += int(archetype["xp"])
		if enemy.kind == BOSS_KIND:
			self.status_text = "The Abyss Titan falls. You escaped the dungeon."
			self.sound_bank.play(self.sound_bank.hit, 0.45)
			self.check_level_up()
			self.end_run(victory=True)
			return True

		if enemy.kind not in self.enemy_lore_seen:
			self.enemy_lore_seen.add(enemy.kind)
			self.status_text = str(archetype["snippet"])
		else:
			self.status_text = f"{archetype['label']} defeated. The dungeon quiets for a moment."
		drop_message = self.try_weapon_drop()
		if drop_message:
			self.status_text = f"{self.status_text} {drop_message}"
		self.sound_bank.play(self.sound_bank.hit, 0.40)
		self.check_level_up()
		return False

	def use_greatsword_spin(self) -> bool:
		"""Greatsword ability: strike all enemies in a ring around the player. Returns True if fired."""
		player_x, player_y = self.player_pos
		targets = [
			enemy
			for enemy in self.enemies
			if abs(enemy.x - player_x) <= 1 and abs(enemy.y - player_y) <= 1
		]
		if not targets:
			self.status_text = "Greatsword Spin finds no enemies nearby."
			return False

		self.turn_count += 1
		self.sound_bank.play(self.sound_bank.attack, 0.40)
		self.spawn_attack_effect(player_x, player_y, "burst", TREASURE_COLOR)
		kills = 0

		for enemy in list(targets):
			enemy.hit_flash = 1.0
			enemy.facing_x = self.player_pos[0] - enemy.x
			enemy.facing_y = self.player_pos[1] - enemy.y
			self.spawn_attack_effect(enemy.x, enemy.y, "slash", TREASURE_COLOR)
			hit_damage, _ = self.compute_player_hit()
			enemy.health -= hit_damage + 1 + self.level // 4
			if enemy.health <= 0 and enemy in self.enemies:
				self.enemies.remove(enemy)
				kills += 1
				if self.award_enemy_defeat(enemy, ENEMY_TYPES[enemy.kind]):
					return

		if kills > 0:
			self.status_text = f"Greatsword Spin crushes {kills} foe{'s' if kills != 1 else ''}."
		else:
			self.status_text = "Greatsword Spin lands, but nothing falls."
		self.enemy_turn()
		return True

	def use_katana_teleport(self) -> bool:
		"""Katana ability: blink to a random valid floor tile. Returns True if fired."""
		occupied = {(enemy.x, enemy.y) for enemy in self.enemies}
		valid_tiles = [tile for tile in self.floor_tiles if tile not in occupied and tile != self.player_pos]
		if not valid_tiles:
			self.status_text = "Katana Blink fails; nowhere to teleport."
			return False

		old_x, old_y = self.player_pos
		new_x, new_y = random.choice(valid_tiles)
		self.player_pos = (new_x, new_y)
		self.player_render_x = float(new_x)
		self.player_render_y = float(new_y)
		self.turn_count += 1
		self.spawn_attack_effect(old_x, old_y, "burst", (175, 175, 255))
		self.spawn_attack_effect(new_x, new_y, "burst", (175, 175, 255))
		self.collect_item_if_present()
		self.status_text = "Katana Blink warps you across the floor."

		if self.player_pos == self.exit_pos:
			self.advance_floor()
			return True
		self.enemy_turn()
		return True

	def use_dual_blades_dash(self) -> None:
		"""Dual blades ability: move two tiles per input for 60 seconds."""
		self.dual_blades_dash_timer = 60.0
		self.turn_count += 1
		self.status_text = "Dual Blades Dash active for 60 seconds. Movement is doubled."
		self.enemy_turn()

	def use_shield_bulwark(self) -> None:
		"""Shield ability: small heal plus immediate block stance."""
		self.player_health = min(self.max_health, self.player_health + 1)
		self.turn_count += 1
		self.status_text = "Bulwark: +1 HP and shield raised."
		self.block_active = True
		self.enemy_turn()

	def player_attack_swing(self) -> None:
		"""Strike the first adjacent enemy without stepping into its tile."""
		player_x, player_y = self.player_pos
		adjacent_positions = [
			(player_x + 1, player_y),
			(player_x - 1, player_y),
			(player_x, player_y + 1),
			(player_x, player_y - 1),
		]
		for target_x, target_y in adjacent_positions:
			enemy = self.enemy_at(target_x, target_y)
			if enemy is not None:
				self.player_facing = (target_x - player_x, target_y - player_y)
				self.damage_enemy(enemy)
				return

		self.status_text = "Your strike whistles through empty air."

	def damage_enemy(self, enemy: Enemy) -> None:
		"""Resolve player damage and then let surviving enemies act."""
		self.sound_bank.play(self.sound_bank.attack, 0.35)
		enemy.hit_flash = 1.0
		enemy.facing_x = self.player_pos[0] - enemy.x
		enemy.facing_y = self.player_pos[1] - enemy.y
		self.spawn_attack_effect(enemy.x, enemy.y, "slash", TREASURE_COLOR)
		self.turn_count += 1
		archetype = ENEMY_TYPES[enemy.kind]
		strike_count = self.get_strike_count_for_attack()
		hit_results: list[str] = []

		for _ in range(strike_count):
			hit_damage, hit_crit = self.compute_player_hit()
			enemy.health -= hit_damage
			hit_results.append(f"{hit_damage}{'!' if hit_crit else ''}")
			if enemy.health <= 0:
				break

		if enemy.health <= 0:
			self.enemies.remove(enemy)
			if self.award_enemy_defeat(enemy, archetype):
				return
		else:
			hits_text = ", ".join(hit_results)
			self.status_text = (
				f"{self.get_weapon_label()} hits ({hits_text}) on the "
				f"{str(archetype['label']).lower()}, but it fights on."
			)

		self.enemy_turn()

	def collect_item_if_present(self) -> None:
		"""Apply item effects for the player's current tile."""
		for item in list(self.items):
			if (item.x, item.y) != self.player_pos:
				continue

			self.items.remove(item)
			self.sound_bank.play(self.sound_bank.pickup, 0.45)
			if item.kind == TREASURE:
				gold_found = random.randint(10, 18) + self.floor_number
				self.score += gold_found
				self.add_inventory_item(f"Treasure Pouch (+{gold_found}g)")
				self.experience += 4
				self.status_text = f"You pocket {gold_found} gold."
				self.check_level_up()
			else:
				self.add_inventory_item("Potion Vial")
				self.player_health = min(self.max_health, self.player_health + 3)
				self.status_text = "You drink a potion and recover 3 health."
			return

		self.status_text = "You move deeper into the dungeon."

	def enemy_turn(self) -> None:
		"""Each enemy either attacks the player or takes a chase/wander step."""
		player_x, player_y = self.player_pos
		occupied_tiles = {(enemy.x, enemy.y) for enemy in self.enemies}
		blocked_any_hit = False

		for enemy in list(self.enemies):
			occupied_tiles.discard((enemy.x, enemy.y))
			distance = abs(enemy.x - player_x) + abs(enemy.y - player_y)
			archetype = ENEMY_TYPES[enemy.kind]
			sense = int(archetype["sense"])

			if distance == 1:
				if self.block_active and self.can_block():
					blocked_any_hit = True
					self.status_text = f"Shield block! You deflect the {str(archetype['label']).lower()} strike."
					self.spawn_attack_effect(player_x, player_y, "burst", (126, 201, 255))
					self.sound_bank.play(self.sound_bank.hit, 0.25)
					self.block_active = False
					occupied_tiles.add((enemy.x, enemy.y))
					continue

				self.player_health -= enemy.damage
				self.player_hit_flash = 1.0
				self.status_text = f"The {str(archetype['label']).lower()} strikes back."
				self.spawn_attack_effect(player_x, player_y, "burst", tuple(archetype["color"]))
				self.sound_bank.play(self.sound_bank.hit, 0.35)
				occupied_tiles.add((enemy.x, enemy.y))
				if self.player_health <= 0:
					self.player_health = 0
					self.end_run()
					return
				continue

			step_candidates: list[tuple[int, int]] = []
			if enemy.kind == "brute" and distance > 1 and (self.turn_count + enemy.x + enemy.y) % 2 == 0:
				occupied_tiles.add((enemy.x, enemy.y))
				continue

			if distance <= sense:
				step_x = 0 if player_x == enemy.x else (1 if player_x > enemy.x else -1)
				step_y = 0 if player_y == enemy.y else (1 if player_y > enemy.y else -1)
				step_candidates.extend(((enemy.x + step_x, enemy.y), (enemy.x, enemy.y + step_y)))
				if enemy.kind == "skitter":
					step_candidates.insert(0, (enemy.x + step_x, enemy.y + step_y))
				elif enemy.kind == "wisp":
					step_candidates.extend(((enemy.x, enemy.y + step_y), (enemy.x + step_x, enemy.y)))
			shuffled_offsets = [(1, 0), (-1, 0), (0, 1), (0, -1)]
			random.shuffle(shuffled_offsets)
			step_candidates.extend((enemy.x + off_x, enemy.y + off_y) for off_x, off_y in shuffled_offsets)

			for next_x, next_y in step_candidates:
				if not self.tile_is_walkable(next_x, next_y):
					continue
				if (next_x, next_y) == self.player_pos or (next_x, next_y) in occupied_tiles:
					continue
				enemy.facing_x = next_x - enemy.x
				enemy.facing_y = next_y - enemy.y
				enemy.x = next_x
				enemy.y = next_y
				break

			occupied_tiles.add((enemy.x, enemy.y))

		if self.block_active:
			if not blocked_any_hit:
				self.status_text = "Your shield stance drops; no hit connected this turn."
			self.block_active = False

	def advance_floor(self) -> None:
		"""Move to the next floor, grant rewards, and scale the difficulty up."""
		self.floor_number += 1
		self.score += 25 + self.floor_number * 5
		self.experience += 18
		self.sound_bank.play(self.sound_bank.stairs, 0.45)
		self.check_level_up()
		self.setup_floor(reset_health=True)
		if self.floor_number >= FINAL_FLOOR:
			self.status_text = "Floor 20: A massive presence stirs in the dark."
		else:
			self.status_text = f"You descend to floor {self.floor_number}. The air grows colder."

		if self.floor_number % 3 == 0 and self.floor_number < FINAL_FLOOR:
			bonus_hp = random.randint(5, 15)
			self.max_health += bonus_hp
			self.player_health = min(self.max_health, self.player_health + bonus_hp)
			self.sound_bank.play(self.sound_bank.level_up, 0.55)
			self.status_text = (
				f"{self.status_text} Floor {self.floor_number} milestone: +{bonus_hp} max HP!"
			)

	def check_level_up(self) -> None:
		"""Convert accumulated experience into stat upgrades."""
		while self.experience >= self.level * 28:
			self.experience -= self.level * 28
			self.level += 1
			self.max_health += 1
			self.player_health = min(self.max_health, self.player_health + 2)
			self.player_attack += 1
			self.status_text = f"Level up. You are now level {self.level}."
			self.sound_bank.play(self.sound_bank.level_up, 0.50)

	def end_run(self, victory: bool = False) -> None:
		"""Switch to the result screen when the player is defeated or wins."""
		if not victory:
			self.sound_bank.play(self.sound_bank.game_over, 0.55)
		summary = RunSummary(
			floors_cleared=self.floor_number if victory else self.floor_number - 1,
			score=self.score,
			level=self.level,
			turns=self.turn_count,
			victory=victory,
		)
		self.window.show_view(ResultView(self.sound_bank, summary))

	def tile_is_walkable(self, tile_x: int, tile_y: int) -> bool:
		"""Return True only when the tile is inside the map and carved as floor."""
		if not (0 <= tile_x < MAP_WIDTH and 0 <= tile_y < MAP_HEIGHT):
			return False
		return self.map_data[tile_y][tile_x] == FLOOR

	def screen_to_tile(self, x: float, y: float) -> tuple[int, int] | None:
		"""Convert mouse screen coordinates into map tile coordinates."""
		map_top = SCREEN_HEIGHT
		map_bottom = HUD_HEIGHT
		if y < map_bottom or y > map_top:
			return None

		world_x = x + self.camera_x
		world_y = (y - HUD_HEIGHT) + self.camera_y
		tile_x = int(world_x // TILE_SIZE)
		tile_y = MAP_HEIGHT - 1 - int(world_y // TILE_SIZE)
		if not (0 <= tile_x < MAP_WIDTH and 0 <= tile_y < MAP_HEIGHT):
			return None
		return tile_x, tile_y

	def enemy_at(self, tile_x: int, tile_y: int) -> Enemy | None:
		"""Find an enemy occupying a single tile, if any."""
		for enemy in self.enemies:
			if (enemy.x, enemy.y) == (tile_x, tile_y):
				return enemy
		return None

	def spawn_attack_effect(self, tile_x: int, tile_y: int, effect_kind: str, color: tuple[int, int, int]) -> None:
		"""Create a short-lived visual effect anchored to a tile center."""
		center_x, center_y = self.tile_to_world_center(tile_x, tile_y)
		self.attack_effects.append(AttackEffect(center_x, center_y, effect_kind, color))

	def draw_map(self) -> None:
		"""Render the dungeon tiles from the top down."""
		for row_index, row in enumerate(self.map_data):
			for column_index, tile in enumerate(row):
				center_x, center_y = self.tile_center(column_index, row_index)
				if center_x < -TILE_SIZE or center_x > SCREEN_WIDTH + TILE_SIZE:
					continue
				if center_y < HUD_HEIGHT - TILE_SIZE or center_y > SCREEN_HEIGHT + TILE_SIZE:
					continue
				base_color = FLOOR_COLOR if tile == FLOOR else WALL_COLOR
				arcade.draw_lbwh_rectangle_filled(
					center_x - TILE_SIZE / 2,
					center_y - TILE_SIZE / 2,
					TILE_SIZE,
					TILE_SIZE,
					base_color,
				)
				if tile == FLOOR:
					arcade.draw_lbwh_rectangle_filled(
						center_x - TILE_SIZE / 2,
						center_y + TILE_SIZE / 2 - 10,
						TILE_SIZE,
						10,
						(111, 98, 75),
					)
					arcade.draw_line(
						center_x - 12,
						center_y - 6,
						center_x + 8,
						center_y - 12,
						(64, 55, 43),
						1,
					)
				else:
					arcade.draw_lbwh_rectangle_filled(
						center_x - TILE_SIZE / 2,
						center_y + TILE_SIZE / 2 - 6,
						TILE_SIZE,
						6,
						(56, 58, 70),
					)
				border_color = (56, 49, 38) if tile == FLOOR else (22, 23, 28)
				arcade.draw_lbwh_rectangle_outline(
					center_x - TILE_SIZE / 2,
					center_y - TILE_SIZE / 2,
					TILE_SIZE,
					TILE_SIZE,
					border_color,
					1,
				)

	def draw_items(self) -> None:
		"""Draw potion and treasure pickups with a small bob animation."""
		bob = math.sin(self.animation_time * 5.0) * 2.0
		for item in self.items:
			center_x, center_y = self.tile_center(item.x, item.y)
			if item.kind == TREASURE:
				arcade.draw_circle_filled(center_x, center_y + bob - 2, 13, (88, 62, 18, 120))
				arcade.draw_circle_filled(center_x, center_y + bob, 9, TREASURE_COLOR)
				arcade.draw_circle_outline(center_x, center_y + bob, 12, (255, 236, 156), 2)
			else:
				arcade.draw_circle_filled(center_x, center_y + bob - 6, 11, (46, 112, 93, 110))
				arcade.draw_lbwh_rectangle_filled(
					center_x - 8,
					center_y + bob - 9,
					16,
					18,
					POTION_COLOR,
				)
				arcade.draw_lbwh_rectangle_outline(
					center_x - 9,
					center_y + bob - 10,
					18,
					20,
					(199, 255, 235),
					2,
				)

	def draw_exit(self) -> None:
		"""Draw the staircase tile used to advance to the next floor."""
		if self.exit_pos[0] < 0 or self.exit_pos[1] < 0:
			return
		center_x, center_y = self.tile_center(*self.exit_pos)
		arcade.draw_circle_filled(center_x, center_y - 4, 18, (72, 54, 138, 110))
		arcade.draw_lbwh_rectangle_filled(center_x - 14, center_y - 14, 28, 28, EXIT_COLOR)
		for offset in range(3):
			arcade.draw_lbwh_rectangle_filled(center_x - 12 + offset * 4, center_y - 8 + offset * 6, 18 - offset * 4, 4, (231, 226, 255))
		arcade.draw_text(
			">",
			center_x,
			center_y - 12,
			(255, 255, 255),
			24,
			anchor_x="center",
			font_name="Arial",
			bold=True,
		)

	def draw_attack_effects(self, layer: str) -> None:
		"""Render slash and hit-burst effects over a few frames."""
		for effect in self.attack_effects:
			effect_x, effect_y = self.world_to_screen(effect.world_x, effect.world_y)
			if effect_x < -40 or effect_x > SCREEN_WIDTH + 40:
				continue
			if effect_y < HUD_HEIGHT - 40 or effect_y > SCREEN_HEIGHT + 40:
				continue

			progress = effect.age / max(effect.duration, 0.001)
			alpha = int(255 * (1.0 - progress))
			if effect.kind == "slash" and layer == "over":
				radius = 12 + progress * 18
				arcade.draw_arc_outline(
					effect_x,
					effect_y,
					radius,
					radius * 0.75,
					effect.color + (alpha,),
					20,
					140,
					3,
				)
			elif effect.kind == "burst" and layer == "under":
				radius = 8 + progress * 26
				arcade.draw_circle_outline(effect_x, effect_y, radius, effect.color + (alpha,), 3)
				arcade.draw_circle_filled(effect_x, effect_y, 4 + progress * 8, effect.color + (max(0, alpha // 3),))

	def draw_enemies(self) -> None:
		"""Draw enemy archetypes with detailed non-circular silhouettes."""
		for index, enemy in enumerate(self.enemies):
			center_x, center_y = self.tile_center(enemy.render_x, enemy.render_y)
			wobble = math.sin(enemy.step_phase + index) * 1.5
			bob = math.sin(enemy.step_phase * 1.3 + index) * 2.4
			archetype = ENEMY_TYPES[enemy.kind]
			base_color = tuple(archetype["color"])
			detail_color = tuple(archetype["detail"])
			flash_mix = enemy.hit_flash
			body_color = tuple(min(255, int(color + (255 - color) * flash_mix * 0.6)) for color in base_color)

			# Ground shadow (rectangular smear) keeps enemies grounded without circular sprites.
			arcade.draw_lbwh_rectangle_filled(center_x - 14 + wobble, center_y - 17, 28, 5, (0, 0, 0, 80))
			if enemy.kind == BOSS_KIND:
				# Larger silhouette for the final boss.
				arcade.draw_lbwh_rectangle_filled(center_x - 21 + wobble, center_y - 24 + bob, 42, 42, body_color)
				arcade.draw_lbwh_rectangle_outline(center_x - 22 + wobble, center_y - 25 + bob, 44, 44, detail_color, 3)
				arcade.draw_triangle_filled(
					center_x - 20 + wobble,
					center_y + 18 + bob,
					center_x + 20 + wobble,
					center_y + 18 + bob,
					center_x + wobble,
					center_y + 31 + bob,
					body_color,
				)
				arcade.draw_lbwh_rectangle_filled(center_x - 10 + wobble, center_y + 2 + bob, 20, 4, detail_color)
				arcade.draw_lbwh_rectangle_filled(center_x - 10 + wobble, center_y - 9 + bob, 20, 4, detail_color)
			elif enemy.kind == "skitter":
				# Insect-like body: segmented rectangles + angular legs.
				arcade.draw_lbwh_rectangle_filled(center_x - 13 + wobble, center_y - 5 + bob, 10, 10, body_color)
				arcade.draw_lbwh_rectangle_filled(center_x - 3 + wobble, center_y - 6 + bob, 10, 12, body_color)
				arcade.draw_lbwh_rectangle_filled(center_x + 7 + wobble, center_y - 4 + bob, 8, 8, body_color)
				for leg_offset in (-10, -4, 4, 10):
					arcade.draw_line(center_x + wobble + leg_offset, center_y + bob - 1, center_x + wobble + leg_offset * 1.3, center_y + bob - 10, detail_color, 2)
				arcade.draw_lbwh_rectangle_filled(center_x + 8 + wobble, center_y + bob - 1, 4, 4, detail_color)
			elif enemy.kind == "brute":
				# Heavy armored silhouette.
				arcade.draw_lbwh_rectangle_filled(center_x - 14 + wobble, center_y - 14 + bob, 28, 28, body_color)
				arcade.draw_lbwh_rectangle_filled(center_x - 9 + wobble, center_y + 2 + bob, 18, 8, detail_color)
				arcade.draw_lbwh_rectangle_outline(center_x - 14 + wobble, center_y - 14 + bob, 28, 28, detail_color, 2)
				arcade.draw_line(center_x - 10 + wobble, center_y + bob + 1, center_x + 10 + wobble, center_y + bob + 1, (72, 45, 28), 2)
				arcade.draw_line(center_x - 10 + wobble, center_y - 4 + bob, center_x + 10 + wobble, center_y - 12 + bob, (60, 34, 24), 3)
			elif enemy.kind == "wisp":
				# Floating crystal/shard spirit silhouette.
				flare = 3 + math.sin(self.animation_time * 5.5 + index) * 2
				arcade.draw_triangle_filled(
					center_x + wobble,
					center_y + bob + 16,
					center_x - 11 - flare + wobble,
					center_y + bob - 2,
					center_x + 11 + flare + wobble,
					center_y + bob - 2,
					body_color,
				)
				arcade.draw_triangle_filled(
					center_x + wobble,
					center_y + bob - 20,
					center_x - 8 + wobble,
					center_y + bob - 4,
					center_x + 8 + wobble,
					center_y + bob - 4,
					detail_color,
				)
				arcade.draw_lbwh_rectangle_outline(center_x - 10 + wobble, center_y - 9 + bob, 20, 18, detail_color, 2)
			else:
				# Bone guard: helm + torso + glowing visor.
				arcade.draw_lbwh_rectangle_filled(center_x - 9 + wobble, center_y - 14 + bob, 18, 22, body_color)
				arcade.draw_triangle_filled(center_x - 11 + wobble, center_y + 8 + bob, center_x + 11 + wobble, center_y + 8 + bob, center_x + wobble, center_y + 17 + bob, body_color)
				arcade.draw_lbwh_rectangle_filled(center_x - 6 + wobble, center_y + 1 + bob, 12, 3, detail_color)
				arcade.draw_lbwh_rectangle_filled(center_x - 7 + wobble, center_y - 3 + bob, 14, 2, (76, 43, 43))

			if enemy.kind == BOSS_KIND:
				arcade.draw_lbwh_rectangle_outline(center_x - 24 + wobble, center_y - 27 + bob, 48, 48, detail_color, 1)
			else:
				arcade.draw_lbwh_rectangle_outline(center_x - 15 + wobble, center_y - 16 + bob, 30, 30, detail_color, 1)
			arcade.draw_text(
				str(enemy.health),
				center_x + wobble,
				center_y + bob - (14 if enemy.kind == BOSS_KIND else 9),
				(255, 248, 248),
				(12 if enemy.kind == BOSS_KIND else 10),
				anchor_x="center",
				font_name="Arial",
				bold=True,
			)

	def draw_player(self) -> None:
		"""Draw a layered explorer with cloak, head, and walking animation."""
		center_x, center_y = self.tile_center(self.player_render_x, self.player_render_y)
		stride = math.sin(self.player_walk_phase * 1.6) * 3.0
		cloak_sway = math.sin(self.player_walk_phase) * 2.0
		flash_tint = self.player_hit_flash
		body_color = tuple(min(255, int(color + (255 - color) * flash_tint * 0.6)) for color in PLAYER_COLOR)
		face_x = self.player_facing[0] * 3
		face_y = self.player_facing[1] * 2
		arcade.draw_ellipse_filled(center_x, center_y - 14, 22, 10, (0, 0, 0, 85))
		arcade.draw_triangle_filled(
			center_x - 14 + cloak_sway,
			center_y - 12,
			center_x + 14 + cloak_sway,
			center_y - 12,
			center_x,
			center_y + 14,
			body_color,
		)
		arcade.draw_circle_filled(center_x + face_x, center_y + 11 + face_y, 9, (244, 228, 202))
		arcade.draw_lbwh_rectangle_filled(center_x - 7, center_y - 4 + stride, 14, 18, body_color)
		arcade.draw_line(center_x - 4, center_y - 3, center_x - 8, center_y - 14 - stride, (220, 235, 255), 2)
		arcade.draw_line(center_x + 4, center_y - 3, center_x + 8, center_y - 14 + stride, (220, 235, 255), 2)
		arcade.draw_circle_outline(center_x, center_y + 5, 18, (206, 233, 255), 2)
		arcade.draw_circle_filled(center_x - 3 + face_x * 0.1, center_y + 12 + face_y * 0.2, 1.7, (24, 24, 24))
		arcade.draw_circle_filled(center_x + 3 + face_x * 0.1, center_y + 12 + face_y * 0.2, 1.7, (24, 24, 24))

	def draw_hud(self) -> None:
		"""Render stats, controls, and current status below the dungeon."""
		heading_size = max(14, min(18, SCREEN_WIDTH // 75))
		body_size = max(11, min(15, SCREEN_WIDTH // 92))
		help_size = max(10, min(13, SCREEN_WIDTH // 110))
		status_size = max(11, min(14, SCREEN_WIDTH // 100))

		arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, 0, HUD_HEIGHT, HUD_COLOR)
		arcade.draw_text(
			f"Floor {self.floor_number}    Level {self.level}    HP {self.player_health}/{self.max_health}",
			20,
			HUD_HEIGHT - 38,
			(241, 243, 248),
			heading_size,
			font_name="Arial",
			bold=True,
		)
		if self.floor_number >= FINAL_FLOOR:
			arcade.draw_text(
				"Final Floor: Defeat the Abyss Titan to win.",
				SCREEN_WIDTH - 20,
				HUD_HEIGHT - 38,
				(255, 192, 192),
				heading_size - 2,
				anchor_x="right",
				font_name="Arial",
				bold=True,
			)
		arcade.draw_text(
			f"Attack {self.player_attack}    XP {self.experience}/{self.level * 28}    Gold {self.score}    Turns {self.turn_count}",
			20,
			HUD_HEIGHT - 66,
			ACCENT_COLOR,
			body_size,
			font_name="Arial",
		)
		arcade.draw_text(
			f"Atk Speed x{self.get_attack_speed_multiplier():.2f}",
			SCREEN_WIDTH - 20,
			HUD_HEIGHT - 66,
			(184, 214, 255),
			body_size,
			anchor_x="right",
			font_name="Arial",
		)
		arcade.draw_text(
			f"Weapon: {self.get_weapon_label()}   Block: {'Ready (Q)' if self.can_block() else 'Unavailable'}",
			20,
			HUD_HEIGHT - 92,
			(181, 189, 206),
			help_size,
			font_name="Arial",
			width=SCREEN_WIDTH - 40,
		)
		rarity_name = RARITY_NAMES[self.weapon_rarity]
		rarity_color = RARITY_COLORS[self.weapon_rarity]
		arcade.draw_text(
			f"{rarity_name}",
			SCREEN_WIDTH - 20,
			HUD_HEIGHT - 92,
			rarity_color,
			help_size,
			anchor_x="right",
			font_name="Arial",
			bold=True,
		)
		arcade.draw_text(
			"Move: WASD/Arrows   Attack: Space or Right-Click   Ability: P   Block: Q (Shield)   Restart: R   Title: Esc",
			20,
			HUD_HEIGHT - 114,
			(156, 166, 186),
			max(10, help_size - 1),
			font_name="Arial",
			width=SCREEN_WIDTH - 40,
		)
		arcade.draw_text(
			"Inventory: I (store up to 128 collected items)",
			20,
			4,
			(138, 153, 186),
			max(10, help_size - 1),
			font_name="Arial",
		)

	def draw_cooldown_panel(self) -> None:
		"""Draw ability cooldown status in the top-right corner of the screen."""
		ability_info = [
			("dual_blades",   "Dual Blades",  "Dash",  60.0),
			("greatsword",    "Greatsword",   "Spin",  30.0),
			("katana",        "Katana",       "Blink", 180.0),
			("shortsword_shield", "Shield",   "Bulwark", 0.0),
		]
		panel_w = 220
		row_h = 22
		pad = 8
		rows = len(ability_info)
		panel_h = rows * row_h + pad * 2 + 20
		px = SCREEN_WIDTH - panel_w - 8
		py = SCREEN_HEIGHT - panel_h - 8

		arcade.draw_lbwh_rectangle_filled(px, py, panel_w, panel_h, (10, 12, 20, 200))
		arcade.draw_lbwh_rectangle_outline(px, py, panel_w, panel_h, (74, 96, 138), 1)
		arcade.draw_text(
			"[P] Abilities",
			px + pad,
			py + panel_h - 18,
			ACCENT_COLOR,
			12,
			font_name="Arial",
			bold=True,
		)

		for idx, (weapon_key, weapon_label, ability_name, max_cd) in enumerate(ability_info):
			cd = self.ability_cooldowns.get(weapon_key, 0.0)
			is_equipped = weapon_key == self.equipped_weapon
			row_y = py + panel_h - 38 - idx * row_h

			if is_equipped:
				arcade.draw_lbwh_rectangle_filled(px + 2, row_y - 2, panel_w - 4, row_h - 2, (36, 52, 80, 160))

			# Progress bar background
			bar_x = px + 118
			bar_w = panel_w - 118 - pad
			arcade.draw_lbwh_rectangle_filled(bar_x, row_y + 4, bar_w, 10, (30, 32, 44))

			if max_cd > 0.0 and cd > 0.0:
				fill = (1.0 - cd / max_cd) * bar_w
				arcade.draw_lbwh_rectangle_filled(bar_x, row_y + 4, fill, 10, (90, 160, 100))
				cd_text = f"{cd:.0f}s"
				text_color = (220, 140, 100)
			elif max_cd == 0.0:
				arcade.draw_lbwh_rectangle_filled(bar_x, row_y + 4, bar_w, 10, (80, 80, 80))
				cd_text = "N/A"
				text_color = (160, 160, 160)
			else:
				arcade.draw_lbwh_rectangle_filled(bar_x, row_y + 4, bar_w, 10, (60, 200, 100))
				cd_text = "READY"
				text_color = (130, 230, 150)

			label_color = (255, 230, 120) if is_equipped else (200, 205, 220)
			arcade.draw_text(
				f"{weapon_label} {ability_name}",
				px + pad,
				row_y + 4,
				label_color,
				11,
				font_name="Arial",
				bold=is_equipped,
			)
			arcade.draw_text(
				cd_text,
				bar_x + bar_w // 2,
				row_y + 3,
				text_color,
				10,
				anchor_x="center",
				font_name="Arial",
				bold=True,
			)

			# Show dash buff timer below the bar when active
			if weapon_key == "dual_blades" and self.dual_blades_dash_timer > 0.0:
				arcade.draw_text(
					f"Buff: {self.dual_blades_dash_timer:.0f}s",
					bar_x + bar_w // 2,
					row_y - 8,
					(160, 240, 200),
					9,
					anchor_x="center",
					font_name="Arial",
				)

	def draw_inventory_overlay(self) -> None:
		"""Draw inventory panel for weapon switching and collected item storage."""
		panel_left = 88
		panel_right = SCREEN_WIDTH - 88
		panel_bottom = 86
		panel_top = SCREEN_HEIGHT - 86

		arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT, (0, 0, 0, 150))
		arcade.draw_lrbt_rectangle_filled(panel_left, panel_right, panel_bottom, panel_top, (18, 20, 30, 242))
		arcade.draw_lrbt_rectangle_outline(panel_left, panel_right, panel_bottom, panel_top, ACCENT_COLOR, 2)

		arcade.draw_text(
			"Inventory",
			panel_left + 20,
			panel_top - 40,
			(242, 245, 255),
			24,
			font_name="Arial",
			bold=True,
		)
		arcade.draw_text(
			f"Items: {len(self.inventory_items)} / {INVENTORY_CAPACITY}",
			panel_right - 20,
			panel_top - 38,
			(198, 205, 224),
			14,
			anchor_x="right",
			font_name="Arial",
		)

		weapon_col_left = panel_left + 24
		weapon_col_right = panel_left + 470
		item_col_left = panel_left + 500

		arcade.draw_text(
			"Weapons (Up/Down + Enter)",
			weapon_col_left,
			panel_top - 76,
			TREASURE_COLOR,
			15,
			font_name="Arial",
		)
		for row, weapon_key in enumerate(WEAPON_ORDER):
			row_top = panel_top - 112 - row * 62
			selected = row == self.inventory_weapon_cursor
			is_equipped = weapon_key == self.equipped_weapon
			bg = (45, 63, 94, 220) if selected else (27, 31, 44, 190)
			arcade.draw_lrbt_rectangle_filled(weapon_col_left, weapon_col_right, row_top - 50, row_top, bg)
			arcade.draw_lrbt_rectangle_outline(weapon_col_left, weapon_col_right, row_top - 50, row_top, (74, 96, 138), 1)

			weapon_label = str(WEAPON_TYPES[weapon_key]["label"])
			rarity = self.weapon_rarities.get(weapon_key, 1)
			rarity_name = RARITY_NAMES[rarity]
			rarity_color = RARITY_COLORS[rarity]
			if is_equipped:
				weapon_label += " [EQUIPPED]"
			arcade.draw_text(weapon_label, weapon_col_left + 10, row_top - 24, (238, 240, 246), 13, font_name="Arial")
			arcade.draw_text(rarity_name, weapon_col_right - 10, row_top - 24, rarity_color, 13, anchor_x="right", font_name="Arial", bold=True)

		arcade.draw_text(
			"Collected Items",
			item_col_left,
			panel_top - 76,
			TREASURE_COLOR,
			15,
			font_name="Arial",
		)

		max_rows = 18
		visible_items = self.inventory_items[-max_rows:]
		if not visible_items:
			arcade.draw_text("No items collected yet.", item_col_left, panel_top - 110, (160, 168, 188), 13, font_name="Arial")
		else:
			for idx, entry in enumerate(visible_items):
				arcade.draw_text(f"- {entry}", item_col_left, panel_top - 108 - idx * 24, (220, 224, 236), 12, font_name="Arial")

		arcade.draw_text(
			"I: close inventory   Esc: close   Enter: equip highlighted weapon",
			panel_left + 20,
			panel_bottom + 16,
			(166, 176, 200),
			12,
			font_name="Arial",
		)

	def tile_to_world_center(self, tile_x: float, tile_y: float) -> tuple[float, float]:
		"""Convert map tile coordinates into world-space pixel centers."""
		center_x = tile_x * TILE_SIZE + TILE_SIZE / 2
		center_y = (MAP_HEIGHT - 1 - tile_y) * TILE_SIZE + TILE_SIZE / 2
		return center_x, center_y

	def world_to_screen(self, world_x: float, world_y: float) -> tuple[float, float]:
		"""Project world-space pixels into screen-space pixels."""
		screen_x = world_x - self.camera_x
		screen_y = world_y - self.camera_y + HUD_HEIGHT
		return screen_x, screen_y

	def tile_center(self, tile_x: float, tile_y: float) -> tuple[float, float]:
		"""Convert tile coordinates to screen coordinates using camera offset."""
		world_x, world_y = self.tile_to_world_center(tile_x, tile_y)
		return self.world_to_screen(world_x, world_y)


class DungeonWindow(arcade.Window):
	"""Root Arcade window that owns the title and gameplay views."""

	def __init__(self) -> None:
		super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, update_rate=1 / 60)
		self.sound_bank = SoundBank()
		self.show_view(TitleView(self.sound_bank))


def main() -> None:
	DungeonWindow()
	arcade.run()


if __name__ == "__main__":
	main()
