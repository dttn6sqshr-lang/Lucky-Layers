import discord
from discord.ext import commands, tasks
from discord import app_commands
import random, json, asyncio
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io
import os

# -------------------------
# CONFIG
# -------------------------
# Safe token handling
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN or TOKEN.strip() == "":
    raise ValueError("Discord token is missing! Set DISCORD_TOKEN in Railway secrets.")

STAFF_ROLE_ID = 1474517835261804656

DATA_FILE = "data.json"
AUDIT_FILE = "audit.log"

CARD_TYPES = ["Vanilla", "Sugar", "Sweet", "Sprinkle"]
CARD_COLORS = {
    "Vanilla": ["#F8F0C6", "#FFFDD1", "#FFD3AC", "#FFE5B4"],
    "Sugar": ["#F88379", "#FFB6C1", "#DE5D83", "#FE828C"],
    "Sweet": ["#E6E6FA", "#E6E6FA", "#C8A2C8", "#DC92EF"],
    "Sprinkle": ["#3EB489", "#98FB98", "#E0BBE4", "#FEC8D8"]
}

# -------------------------
# DATA STORAGE
# -------------------------
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# -------------------------
# BADGES SYSTEM (1000+)
# -------------------------
def generate_badges():
    badges = {}
    # Cards Opened 1-500
    for i in range(1, 501):
        badges[f"open_{i}"] = {"name": f"Opened {i} Cards", "type": "cards_opened", "requirement": i}
    # Cards Given 1-300
    for i in range(1, 301):
        badges[f"give_{i}"] = {"name": f"Gave {i} Cards", "type": "cards_given", "requirement": i}
    # Sugar Bits 100-100000 step 500
    for i in range(100, 100001, 500):
        badges[f"sugar_{i}"] = {"name": f"Earned {i} Sugar Bits", "type": "sugar_bits", "requirement": i}
    return badges

BADGES = generate_badges()

# -------------------------
# UTILITIES
# -------------------------
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2],16) for i in (0,2,4))

def get_user(uid):
    uid = str(uid)
    if uid not in data:
        data[uid] = {
            "sugar_bits": 0,
            "bbc": 0,
            "cards_opened": 0,
            "cards_given": 0,
            "badges": []
        }
    return data[uid]

def log_audit(action_type, details):
    ts = datetime.utcnow().isoformat()
    with open(AUDIT_FILE,"a") as f:
        f.write(f"[{ts}] {action_type}: {details}\n")

# -------------------------
# BADGE CHECKER
# -------------------------
async def check_badges(user_id, interaction=None):
    user = get_user(user_id)
    new_badges = []
    for badge_id, badge in BADGES.items():
        if badge_id in user["badges"]:
            continue
        if user[badge["type"]] >= badge["requirement"]:
            user["badges"].append(badge_id)
            new_badges.append(badge["name"])
            log_audit("BADGE_UNLOCKED", f"{user_id} unlocked {badge['name']}")
    if new_badges and interaction:
        try:
            dm = await interaction.user.create_dm()
            for b in new_badges:
                await dm.send(f"🎉 You unlocked a new badge: **{b}**!")
        except:
            print(f"Could not DM user {user_id} for badges.")
    return new_badges

# -------------------------
# BOT SETUP
# -------------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------------
# CARD REWARDS
# -------------------------
CARD_PRIZES = {
    "Vanilla": [100,150,200,250,500,1000,5000,10000,20000,50000],
    "Sugar": [300,500,1000,2000,5000,10000],
    "Sweet": [1,2,3,4,5,10,25],
    "Sprinkle": [1,2,3,4,5,10]
}

def is_high_value(card_type, value):
    if value == "Nothing": return False
    try:
        value = int(value)
    except:
        return False
    if card_type=="Vanilla" and value>=20000: return True
    if card_type=="Sugar" and value>=5000: return True
    return False

def generate_rewards(card_type):
    rewards = []
    for i in range(4):  # 4 hearts
        rewards.append(str(random.choices(CARD_PRIZES[card_type]+["Nothing"], weights=[1]*len(CARD_PRIZES[card_type])+[5], k=1)[0]))
    return rewards

# -------------------------
# IMAGE UTILITIES
# -------------------------
def img_to_bytes(img):
    b = io.BytesIO()
    img.save(b, format="PNG")
    b.seek(0)
    return b

def create_card_image(card_type, scratched, rewards):
    img = Image.new("RGBA",(520,320))
    draw = ImageDraw.Draw(img)

    # Gradient background
    colors = [hex_to_rgb(c) for c in CARD_COLORS[card_type]]
    for y in range(320):
        pos = y/(319)*(len(colors)-1)
        i = int(pos)
        frac = pos-i
        c = colors[i] if i>=len(colors)-1 else tuple(int(colors[i][j]+(colors[i+1][j]-colors[i][j])*frac) for j in range(3))
        draw.line([(0,y),(520,y)], fill=c)

    font = ImageFont.load_default()

    # Draw hearts
    for i in range(4):
        x = 80 + i*110
        y = 120
        draw.ellipse([x,y,x+60,y+60], fill="red")
        if scratched[i]:
            text = "Nothing" if rewards[i]=="Nothing" else str(rewards[i])
            bbox = draw.textbbox((0,0), text, font=font)
            tx = x+30-(bbox[2]/2)
            ty = y+30-(bbox[3]/2)
            if is_high_value(card_type,rewards[i]):
                for offset in range(1,4):
                    draw.text((tx-offset, ty), text, fill="gold", font=font)
                    draw.text((tx+offset, ty), text, fill="gold", font=font)
                    draw.text((tx, ty-offset), text, fill="gold", font=font)
                    draw.text((tx, ty+offset), text, fill="gold", font=font)
            draw.text((tx,ty), text, fill="black", font=font)

    return img

def create_loading_image(card_type):
    img = Image.new("RGBA",(520,320))
    draw = ImageDraw.Draw(img)
    colors = [hex_to_rgb(c) for c in CARD_COLORS[card_type]]
    for y in range(320):
        pos = y/(319)*(len(colors)-1)
        i = int(pos)
        frac = pos-i
        c = colors[i] if i>=len(colors)-1 else tuple(int(colors[i][j]+(colors[i+1][j]-colors[i][j])*frac) for j in range(3))
        draw.line([(0,y),(520,y)], fill=c)
    font = ImageFont.load_default()
    text = "Scratching..."
    bbox = draw.textbbox((0,0), text, font=font)
    draw.text((260-(bbox[2]/2),160-(bbox[3]/2)), text, fill="black", font=font)
    return img

# -------------------------
# CARD INTERACTION VIEW
# -------------------------
cards = {}

class CardDropdown(discord.ui.Select):
    def __init__(self, index, card_type):
        options = [discord.SelectOption(label=ct) for ct in CARD_TYPES]
        super().__init__(placeholder="🎀 Choose a card type...", min_values=1, max_values=1, options=options)
        self.index = index
        self.card_type = card_type

    async def callback(self, interaction: discord.Interaction):
        card = cards.get(interaction.message.id)
        if interaction.user.id != card["user"].id:
            return await interaction.response.send_message("Not your card.", ephemeral=True)
        if card["scratched"][self.index]:
            return await interaction.response.send_message("Already scratched.", ephemeral=True)
        # loading animation
        loading_img = create_loading_image(card["type"])
        await interaction.response.edit_message(attachments=[discord.File(img_to_bytes(loading_img),"card.png")], view=self.view)
        await asyncio.sleep(0.7)
        # reveal
        card["scratched"][self.index] = True
        img = create_card_image(card["type"], card["scratched"], card["rewards"])
        file = discord.File(img_to_bytes(img),"card.png")
        self.disabled = True
        await interaction.edit_original_response(attachments=[file], view=self.view)
        # rewards
        user_data = get_user(interaction.user.id)
        reward = card["rewards"][self.index]
        if reward != "Nothing":
            if card["type"]=="Vanilla":
                user_data["sugar_bits"] += int(reward)
            elif card["type"]=="Sugar":
                user_data["bbc"] += int(reward)
        user_data["cards_opened"] += 1
        await check_badges(interaction.user.id, interaction)
        save_data(data)
        log_audit("CARD_SCRATCHED", f"{interaction.user} scratched {card['type']} card, reward: {reward}")
        if all(card["scratched"]):
            await interaction.followup.send(f"🎉 You completed your {card['type']} card!", ephemeral=True)

class CardView(discord.ui.View):
    def __init__(self, card_type, rewards, user):
        super().__init__(timeout=None)
        self.user = user
        self.card_type = card_type
        self.rewards = rewards
        self.scratched = [False]*4
        for i in range(4):
            self.add_item(CardDropdown(i, card_type))

# -------------------------
# COMMANDS
# -------------------------
@bot.tree.command(name="profile")
async def profile(interaction: discord.Interaction, user: discord.Member = None):
    user = user or interaction.user
    u = get_user(user.id)
    badge_list = u["badges"][:10]
    badge_text = "\n".join([BADGES[b]["name"] for b in badge_list]) or "No badges yet"
    embed = discord.Embed(title=f"{user.name}'s Profile 💖")
    embed.add_field(name="Sugar Bits 🍬", value=u["sugar_bits"])
    embed.add_field(name="BBC 💰", value=u["bbc"])
    embed.add_field(name="Cards Opened 🎴", value=u["cards_opened"])
    embed.add_field(name="Cards Given 🎁", value=u["cards_given"])
    embed.add_field(name="Badges 🏅", value=badge_text, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard")
async def leaderboard(interaction: discord.Interaction):
    sorted_users = sorted(data.items(), key=lambda x:x[1]["cards_given"], reverse=True)[:10]
    text = ""
    for i,(uid,info) in enumerate(sorted_users,start=1):
        try: user = await bot.fetch_user(int(uid))
        except: user = f"User-{uid}"
        text += f"{i}. {user} — {info['cards_given']} cards\n"
    embed = discord.Embed(title="🏆 Top Card Givers", description=text or "No data yet.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="givecard")
async def givecard(interaction: discord.Interaction, card_type: str, target: discord.Member):
    if not any(role.id==STAFF_ROLE_ID for role in interaction.user.roles):
        return await interaction.response.send_message("Only staff can give cards.", ephemeral=True)
    if card_type not in CARD_TYPES:
        return await interaction.response.send_message(f"Invalid card type. Choose: {CARD_TYPES}", ephemeral=True)
    rewards = generate_rewards(card_type)
    view = CardView(card_type, rewards, target)
    msg = await interaction.channel.send(f"{target.mention}, you received a {card_type} card!", view=view)
    cards[msg.id] = {"user":target, "type":card_type, "rewards":rewards, "scratched":[False]*4}
    giver_data = get_user(interaction.user.id)
    giver_data["cards_given"] += 1
    log_audit("CARD_GIVEN", f"{interaction.user} gave {card_type} card to {target}")
    await check_badges(interaction.user.id)
    save_data(data)

# -------------------------
# READY
# -------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Ready as {bot.user}")

bot.run(TOKEN)