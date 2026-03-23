import random
import textwrap
import sys
import os
import json

# Simple text-based D&D-style game with AI DM-like generation
# The DM generates worlds, locations, encounters, and narrates the story.

class Player:
    def __init__(self, name="Adventurer"):
        self.name = name
        self.hp = 30
        self.max_hp = 30
        self.attack = 5
        self.defense = 2
        self.inventory = []  # list of item dicts
        self.gold = 0
        # proficiency lists: strings like 'Simple','Martial','Light','Heavy','Magic'
        self.weapon_prof = []
        self.armor_prof = []

    def can_use(self, item):
        """Return True if player is proficient with given item."""
        itype = item.get("type")
        prof = item.get("prof")
        if itype == "weapon":
            return prof in self.weapon_prof or prof is None
        if itype == "armor":
            return prof in self.armor_prof or prof is None
        # potions and misc are always usable
        return True

    def add_item(self, item):
        """Attempt to add item to inventory; return True if usable."""
        usable = self.can_use(item)
        self.inventory.append(item)
        return usable

    def is_alive(self):
        return self.hp > 0

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def take_damage(self, dmg):
        self.hp -= max(0, dmg - self.defense)

    def __str__(self):
        return f"{self.name}: HP {self.hp}/{self.max_hp}, ATK {self.attack}, DEF {self.defense}, Gold {self.gold}" 


class Monster:
    def __init__(self, name, hp, attack, defense, gold):
        self.name = name
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.gold = gold

    def is_alive(self):
        return self.hp > 0

    def take_damage(self, dmg):
        self.hp -= max(0, dmg - self.defense)

    def __str__(self):
        return f"{self.name}: HP {self.hp}, ATK {self.attack}, DEF {self.defense}"


def roll_dice(sides=6):
    return random.randint(1, sides)


def narrate(text):
    # simple wrap
    print(textwrap.fill(text, width=70))


def generate_location():
    adjectives = ["Ancient", "Dark", "Mystic", "Forgotten", "Sacred", "Haunted"]
    places = ["Forest", "Cavern", "Ruins", "Temple", "Castle", "Swamp"]
    return f"{random.choice(adjectives)} {random.choice(places)}"


def generate_monster(level=1):
    # more monster types with increasing difficulty
    templates = [
        ("Goblin", 8, 2, 0),
        ("Orc", 12, 3, 1),
        ("Skeleton", 10, 2, 1),
        ("Bandit", 11, 3, 1),
        ("Wolf", 9, 3, 0),
        ("Zombie", 14, 2, 2),
        ("Troll", 20, 5, 2),
        ("Giant Spider", 16, 4, 1),
        ("Dark Elf", 15, 4, 2),
        ("Ogre", 25, 6, 3),
        ("Dragonling", 18, 6, 2),
        ("Vampire Bat", 12, 5, 1),
        ("Necromancer", 20, 7, 3),
        ("Elemental", 22, 6, 4),
    ]
    base_name, base_hp, base_atk, base_def = random.choice(templates)
    # scale stats by level (1-10); use level multiplier
    hp = base_hp + level * random.randint(2, 8)
    attack = base_atk + level + roll_dice(4)
    defense = base_def + level // 2
    gold = random.randint(1, 15) * level
    name = f"{base_name} (lvl {level})"
    return Monster(name, hp, attack, defense, gold)


def generate_loot(level=1):
    """Return gold amount and list of items based on enemy level."""
    gold = random.randint(5, 20) * level
    # possible item templates with required proficiencies and value
    all_items = [
        {"name": "Healing Potion", "type": "potion", "prof": None, "price": 10, "min_level": 1},
        {"name": "Iron Sword", "type": "weapon", "prof": "Martial", "price": 50, "min_level": 2},
        {"name": "Shortsword", "type": "weapon", "prof": "Simple", "price": 30, "min_level": 1},
        {"name": "Magic Staff", "type": "weapon", "prof": "Magic", "price": 80, "min_level": 3},
        {"name": "Leather Armor", "type": "armor", "prof": "Light", "price": 40, "min_level": 1},
        {"name": "Chain Mail", "type": "armor", "prof": "Medium", "price": 70, "min_level": 3},
        {"name": "Plate Armor", "type": "armor", "prof": "Heavy", "price": 100, "min_level": 5},
        {"name": "Magic Ring", "type": "misc", "prof": None, "price": 60, "min_level": 4},
        {"name": "Old Scroll", "type": "misc", "prof": None, "price": 20, "min_level": 1},
    ]
    # choose a few items depending on level
    count = 1 if level < 3 else (2 if level < 7 else 3)
    loot = random.sample(all_items, count)
    return gold, loot


def generate_shop_items(level=1):
    """Generate 5 random items for sale with prices, filtered by min_level."""
    all_items = [
        {"name": "Healing Potion", "type": "potion", "prof": None, "price": 10, "min_level": 1},
        {"name": "Shortsword", "type": "weapon", "prof": "Simple", "price": 30 + level * 5, "min_level": 1},
        {"name": "Leather Armor", "type": "armor", "prof": "Light", "price": 40 + level * 8, "min_level": 1},
        {"name": "Old Scroll", "type": "misc", "prof": None, "price": 20 + level * 5, "min_level": 1},
        {"name": "Iron Sword", "type": "weapon", "prof": "Martial", "price": 50 + level * 10, "min_level": 2},
        {"name": "Chain Mail", "type": "armor", "prof": "Medium", "price": 70 + level * 12, "min_level": 3},
        {"name": "Magic Staff", "type": "weapon", "prof": "Magic", "price": 80 + level * 15, "min_level": 3},
        {"name": "Magic Ring", "type": "misc", "prof": None, "price": 60 + level * 10, "min_level": 4},
        {"name": "Plate Armor", "type": "armor", "prof": "Heavy", "price": 100 + level * 20, "min_level": 5},
    ]
    # Filter items available at this level
    available_items = [item for item in all_items if item["min_level"] <= level]
    # If not enough items, include all available
    num_items = min(5, len(available_items))
    return random.sample(available_items, num_items)


def shop(player, items_for_sale):
    """Handle buying and selling in the shop."""
    while True:
        print("\n" + "="*50)
        print("SHOP")
        print("="*50)
        print("1. Buy items")
        print("2. Sell items")
        print("3. Leave shop")
        choice = input("Choose: ").strip()
        if choice == "1":
            # Buy
            print("\nItems for sale:")
            for i, itm in enumerate(items_for_sale, 1):
                print(f"{i}. {itm['name']} - {itm['price']} gold")
            buy_choice = input("Enter item number to buy (or 0 to cancel): ").strip()
            if buy_choice.isdigit() and 1 <= int(buy_choice) <= len(items_for_sale):
                itm = items_for_sale[int(buy_choice)-1]
                if player.gold >= itm['price']:
                    player.gold -= itm['price']
                    player.add_item(itm)
                    narrate(f"You bought {itm['name']} for {itm['price']} gold.")
                else:
                    narrate("Not enough gold!")
            elif buy_choice == "0":
                pass
            else:
                narrate("Invalid choice.")
        elif choice == "2":
            # Sell
            if not player.inventory:
                narrate("You have no items to sell.")
                continue
            print("\nYour inventory:")
            for i, itm in enumerate(player.inventory, 1):
                sell_price = itm.get('price', 10) // 2  # sell for half
                print(f"{i}. {itm['name']} - Sell for {sell_price} gold")
            sell_choice = input("Enter item number to sell (or 0 to cancel): ").strip()
            if sell_choice.isdigit() and 1 <= int(sell_choice) <= len(player.inventory):
                itm = player.inventory[int(sell_choice)-1]
                sell_price = itm.get('price', 10) // 2
                player.gold += sell_price
                player.inventory.remove(itm)
                narrate(f"You sold {itm['name']} for {sell_price} gold.")
            elif sell_choice == "0":
                pass
            else:
                narrate("Invalid choice.")
        elif choice == "3":
            break
        else:
            narrate("Invalid option.")


def combat(player, monster):
    narrate(f"A wild {monster.name} appears! Prepare to fight.")
    while player.is_alive() and monster.is_alive():
        action = input("Choose action ([A]ttack, [R]un): ").strip().lower()
        if action.startswith('r'):
            if random.random() < 0.5:
                narrate("You managed to escape!")
                return False
            else:
                narrate("You failed to escape!")
        # player attack
        dmg = player.attack + roll_dice(6)
        monster.take_damage(dmg)
        narrate(f"You strike the {monster.name} for {dmg} damage.")
        if not monster.is_alive():
            narrate(f"You defeated the {monster.name}!")
            player.gold += monster.gold
            narrate(f"You loot {monster.gold} gold.")
            return True
        # monster attack
        dmg2 = monster.attack + roll_dice(4)
        player.take_damage(dmg2)
        narrate(f"The {monster.name} hits you for {dmg2} damage.")
        if not player.is_alive():
            narrate("You have been slain!")
            return False
    return False


def explore(player, level=1):
    location = generate_location()
    narrate(f"You enter the {location}...")
    # random encounter chance
    rand = random.random()
    if rand < 0.5:
        monster = generate_monster(level)
        success = combat(player, monster)
        if success:
            gold, items = generate_loot(level)
            player.gold += gold
            narrate(f"You found {gold} gold.")
            if items:
                for itm in items:
                    usable = player.add_item(itm)
                    if usable:
                        narrate(f"You also acquired a {itm['name']}!")
                    else:
                        narrate(f"You also acquired a {itm['name']}, but you can't use it.")
    elif rand < 0.7:
        # Vendor encounter
        narrate("You encounter a wandering merchant!")
        items_for_sale = generate_shop_items(level)
        shop(player, items_for_sale)
    else:
        narrate("The area seems peaceful. You find nothing of interest.")


def rest(player):
    heal_amount = random.randint(5, 15)
    player.heal(heal_amount)
    narrate(f"You rest and recover {heal_amount} HP.")


def show_help():
    print("Commands: explore, rest, stats, inventory, help, quit")


def choose_from(prompt, options):
    """Utility: prompt user to pick from numbered list."""
    narrate(prompt + ":")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        choice = input("Enter number: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice)-1]
        print("Invalid selection, try again.")


def create_character():
    narrate("Character creation begins...")
    name = input("Enter your character's name: ").strip() or "Adventurer"
    classes = ["Fighter", "Wizard", "Rogue", "Cleric"]
    races = ["Human", "Elf", "Dwarf", "Orc"]
    cls = choose_from("Choose your class", classes)
    race = choose_from("Choose your race", races)
    
    # base stats
    player = Player(name)
    # adjust stats and proficiencies by class
    if cls == "Fighter":
        player.max_hp += 10
        player.attack += 2
        player.defense += 1
        player.weapon_prof = ["Simple", "Martial"]
        player.armor_prof = ["Light", "Medium", "Heavy"]
    elif cls == "Wizard":
        player.max_hp -= 5
        player.attack += 4
        player.defense -= 1
        player.weapon_prof = ["Simple", "Magic"]
        player.armor_prof = []
    elif cls == "Rogue":
        player.attack += 3
        player.defense += 0
        player.weapon_prof = ["Simple", "Martial"]
        player.armor_prof = ["Light"]
    elif cls == "Cleric":
        player.max_hp += 5
        player.defense += 2
        player.weapon_prof = ["Simple", "Martial"]
        player.armor_prof = ["Light", "Medium"]
    
    # adjust stats by race (proficiencies unchanged)
    if race == "Human":
        player.max_hp += 2
        player.attack += 1
    elif race == "Elf":
        player.attack += 2
    elif race == "Dwarf":
        player.max_hp += 3
        player.defense += 1
    elif race == "Orc":
        player.max_hp += 5
        player.attack += 1
        player.defense -= 1
    
    # ensure current hp equals max
    player.hp = player.max_hp
    narrate(f"Created {race} {cls} named {player.name}.")
    narrate(str(player))
    return player


def save_game(player, level, story, filename="save.json"):
    data = {
        "name": player.name,
        "hp": player.hp,
        "max_hp": player.max_hp,
        "attack": player.attack,
        "defense": player.defense,
        "gold": player.gold,
        "inventory": player.inventory,
        "weapon_prof": player.weapon_prof,
        "armor_prof": player.armor_prof,
        "level": level,
        "story": story,
    }
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


def load_game(filename="save.json"):
    if not os.path.exists(filename):
        return None
    with open(filename, "r") as f:
        data = json.load(f)
    p = Player(data.get("name", "Adventurer"))
    p.hp = data.get("hp", 30)
    p.max_hp = data.get("max_hp", 30)
    p.attack = data.get("attack", 5)
    p.defense = data.get("defense", 2)
    p.gold = data.get("gold", 0)
    p.inventory = data.get("inventory", [])
    p.weapon_prof = data.get("weapon_prof", [])
    p.armor_prof = data.get("armor_prof", [])
    level = data.get("level", 1)
    story = data.get("story", [])
    return p, level, story


def main():
    print("Welcome to the AI Dungeon Master game!")
    story = []
    # check for existing save
    loaded = load_game()
    if loaded:
        player, level, story = loaded
        narrate(f"Welcome back, {player.name}! Continuing your adventure...")
    else:
        player = create_character()
        level = 1
    while True:  # loop continues even if player dies, death handled below
        command = input("\n> ").strip().lower()
        if command.startswith('e'):
            explore(player, level)
            story.append(f"Explored at level {level}")
            # level up based on gold maybe
            if player.gold > level * 50:
                level += 1
                player.max_hp += 5
                player.attack += 1
                player.defense += 1
                narrate("You feel yourself growing stronger! Level up!")
                story.append("Leveled up to " + str(level))
            save_game(player, level, story)
        elif command.startswith('r'):
            rest(player)
            save_game(player, level, story)
        elif command.startswith('s'):
            narrate(str(player))
        elif command.startswith('i'):
            if player.inventory:
                inv_list = ', '.join(itm['name'] for itm in player.inventory)
                narrate(f"Inventory: {inv_list}")
            else:
                narrate("Inventory: (empty)")
        elif command.startswith('h'):
            show_help()
        elif command.startswith('q'):
            save_game(player, level, story)
            break
        else:
            narrate("Unknown command. Type 'help' for a list of commands.")

        # check death and offer continuation
        if not player.is_alive():
            narrate("You have been defeated...")
            choice = input("Continue from last checkpoint? (y/n): ").strip().lower()
            if choice.startswith('y'):
                loaded = load_game()
                if loaded:
                    player, level, story = loaded
                    # revive with half health
                    player.hp = max(1, player.max_hp // 2)
                    narrate("You awaken at your last checkpoint with some wounds healed.")
                    continue
            break
    print("Game over. Thanks for playing!")

if __name__ == "__main__":
    main()
