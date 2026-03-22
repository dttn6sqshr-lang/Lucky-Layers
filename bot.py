import discord
from discord.ext import commands
import random, json, asyncio
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io
import os

# -------------------------
# CONFIG
# -------------------------
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN or TOKEN.strip() == "":
    raise ValueError("Discord token is missing! Set DISCORD_TOKEN in Railway secrets.")

STAFF_ROLE_ID = 1474517835261804656
DATA_FILE = "data.json"
AUDIT_CHANNEL_ID = 1475295896118755400  # ᐢᗜᐢ﹑logs！﹒

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
cards = {}  # card messages tracker

# -------------------------
# BADGES SYSTEM
# -------------------------
def generate_badges():
    badges = {}
    for i in range(1, 501):
        badges[f"open_{i}"] = {"name": f"Opened {i} Cards", "type": "cards_opened", "requirement": i}
    for i in range(1, 301):
        badges[f"give_{i}"] = {"name": f"Gave {i} Cards", "type": "cards_given", "requirement": i}
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

async def log_audit(action_type, details):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    message = f"[{ts}] {action_type}: {details}"
    # send to audit channel
    channel = bot.get_channel(AUDIT_CHANNEL_ID)
    if channel:
        try:
            await channel.send(message)
        except Exception as e:
            print(f"Failed to send audit log: {e}")
    # optional: also save to file
    with open("audit.log","a") as f:
        f.write(message + "\n")

async def check_badges(user_id, interaction=None):
    user = get_user(user_id)
    new_badges = []
    for badge_id, badge in BADGES.items():
        if badge_id in user["badges"]:
            continue
        if user[badge["type"]] >= badge["requirement"]:
            user["badges"].append(badge_id)
            new_badges.append(badge["name"])
            await log_audit("BADGE_UNLOCKED", f"{user_id} unlocked {badge['name']}")
    if new_badges and interaction:
        try:
            dm = await interaction.user.create_dm()
            for b in new_badges:
                await dm.send(f"🎉 You unlocked a new badge: **{b}**!")
        except:
            print(f"Could not DM user {user_id} for badges.")
    return new_badges

# -------------------------
# CARD REWARDS
# -------------------------
CARD_PRIZES = {
    "Vanilla": [100,150,200,250,500,1000,5000,10000,20000,50000],
    "Sugar": [300,500,1000,2000,5000,10000],
    "Sweet": [1,2,3,4,5,10,25],
    "Sprinkle": [1,2,3,4,5,10]
}

def generate_rewards(card_type):
    rewards = []
    for i in range(4):
        rewards.append(str(random.choices(CARD_PRIZES[card_type]+["Nothing"], weights=[1]*len(CARD_PRIZES[card_type])+[5], k=1)[0]))
    return rewards

def is_high_value(card_type, value):
    if value == "Nothing": return False
    try: value = int(value)
    except: return False
    if card_type=="Vanilla" and value>=20000: return True
    if card_type=="Sugar" and value>=5000: return True
    return False

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
    colors = [hex_to_rgb(c) for c in CARD_COLORS[card_type]]
    for y in range(320):
        pos = y/(319)*(len(colors)-1)
        i = int(pos)
        frac = pos-i
        c = colors[i] if i>=len(colors)-1 else tuple(int(colors[i][j]+(colors[i+1][j]-colors[i][j])*frac) for j in range(3))
        draw.line([(0,y),(520,y)], fill=c)
    font = ImageFont.load_default()
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
# CARD VIEW
# -------------------------
class CardDropdown(discord.ui.Select):
    def __init__(self, index, card_type):
        options = [discord.SelectOption(label="Scratch")]
        super().__init__(placeholder="🎀 Scratch Heart", min_values=1, max_values=1, options=options)
        self.index = index
        self.card_type = card_type

    async def callback(self, interaction: discord.Interaction):
        card = cards.get(interaction.message.id)
        if interaction.user != card["user"]:
            return await interaction.response.send_message("Not your card.", ephemeral=True)
        if card["scratched"][self.index]:
            return await interaction.response.send_message("Already scratched.", ephemeral=True)
        loading_img = create_loading_image(card["type"])
        await interaction.response.edit_message(attachments=[discord.File(img_to_bytes(loading_img),"card.png")], view=self.view)
        await asyncio.sleep(0.7)
        card["scratched"][self.index] = True
        img = create_card_image(card["type"], card["scratched"], card["rewards"])
        file = discord.File(img_to_bytes(img),"card.png")
        self.disabled = True
        await interaction.edit_original_response(attachments=[file], view=self.view)
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
        await log_audit("CARD_SCRATCHED", f"{interaction.user} scratched {card['type']} card, reward: {reward}")
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
# GIVE CARD DROPDOWN
# -------------------------
class GiveCardDropdown(discord.ui.Select):
    def __init__(self, staff_user, ticket_channel):
        options = [discord.SelectOption(label=ct) for ct in CARD_TYPES]
        super().__init__(placeholder="🎀 Choose a card type...", min_values=1, max_values=1, options=options)
        self.staff_user = staff_user
        self.ticket_channel = ticket_channel

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.staff_user:
            return await interaction.response.send_message("Only the staff who opened this dropdown can select a card type.", ephemeral=True)
        card_type = self.values[0]
        await interaction.response.send_message("Who do you want to give the card to? Reply with @user.", ephemeral=True)
        def check(m):
            return m.author == self.staff_user and m.channel == interaction.channel and m.mentions
        try:
            msg = await bot.wait_for("message", check=check, timeout=60)
            target = msg.mentions[0]
        except asyncio.TimeoutError:
            return await interaction.followup.send("You took too long to select a recipient.", ephemeral=True)
        rewards = generate_rewards(card_type)
        view = CardView(card_type, rewards, target)
        card_msg = await self.ticket_channel.send(f"{target.mention}, you received a {card_type} card! Scratch the hearts to reveal your rewards.", view=view)
        cards[card_msg.id] = {"user": target, "type": card_type, "rewards": rewards, "scratched":[False]*4}
        giver_data = get_user(self.staff_user.id)
        giver_data["cards_given"] += 1
        await log_audit("CARD_GIVEN", f"{self.staff_user} gave {card_type} card to {target}")
        await check_badges(self.staff_user.id)
        save_data(data)
        await interaction.followup.send(f"✅ {card_type} card sent to {target.display_name}.", ephemeral=True)

class GiveCardView(discord.ui.View):
    def __init__(self, staff_user, ticket_channel):
        super().__init__(timeout=None)
        self.add_item(GiveCardDropdown(staff_user, ticket_channel))

# -------------------------
# BOT SETUP
# -------------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.tree.command(name="givecard")
async def givecard_cmd(interaction: discord.Interaction):
    if not any(role.id == STAFF_ROLE_ID for role in interaction.user.roles):
        return await interaction.response.send_message("Only staff can give cards.", ephemeral=True)
    view = GiveCardView(interaction.user, interaction.channel)
    await interaction.response.send_message("Select a card type to give:", view=view, ephemeral=True)

bot.run(TOKEN)