import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
import random, json, io, os
from datetime import datetime

# ---------------------
# CONFIG
# ---------------------
TOKEN = os.getenv("DISCORD_TOKEN")  # Railway sets env variables automatically

CARD_DATA_FILE = "scratch_data.json"
LOG_CHANNEL_NAME = "logs"

# Colors
GRADIENTS = {
    "vanilla": ["#F8F0C6", "#FFFDD1", "#FFD3AC", "#FFE5B4"],
    "sugar": ["#F88379", "#FFB6C1", "#DE5D83", "#FE828C"],
    "sweet": ["#E6E6FA", "#C8A2C8", "#DC92EF"],
    "sprinkle": ["#3EB489", "#98FB98", "#E0BBE4", "#FEC8D8"]
}

CARD_WIDTH, CARD_HEIGHT = 520, 320
HEART_COORDS = [(50, 100), (190, 100), (330, 100), (470, 100),
                (50, 200), (190, 200), (330, 200), (470, 200)]

BUTTON_EMOJI = "🎀"

# ---------------------
# BOT SETUP
# ---------------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------
# DATA
# ---------------------
if os.path.exists(CARD_DATA_FILE):
    with open(CARD_DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {"cards": {}, "users": {}, "givers": {}}

# ---------------------
# HELPERS
# ---------------------
def save_data():
    with open(CARD_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_log_channel(guild):
    return discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)

def generate_rewards(card_type):
    """Randomize rewards for a card type"""
    if card_type == "vanilla":
        pool = [str(x) for x in range(100, 5001, 100)]
    elif card_type == "sugar":
        pool = [100,200,300,400,500]
    elif card_type == "sweet":
        pool = ["Free", "5%", "10%", "20%", "50%"]
    elif card_type == "sprinkle":
        pool = ["5 Seasonal","15 Seasonal","20 Seasonal"]
    rewards = ["Nothing"] * 8
    positions = random.sample(range(8), 3)
    for pos in positions:
        rewards[pos] = str(random.choice(pool))
    return rewards

def img_to_bytes(img):
    b = io.BytesIO()
    img.save(b, format="PNG")
    b.seek(0)
    return b

def draw_heart(draw, x, y, size, fill):
    """Draw simple heart shape"""
    w = size
    h = size
    draw.polygon([
        (x+w*0.5, y+h*0.9),
        (x, y+h*0.3),
        (x+w*0.25, y),
        (x+w*0.5, y+h*0.2),
        (x+w*0.75, y),
        (x+w, y+h*0.3)
    ], fill=fill)

def create_card_image(rewards, scratched, card_type):
    img = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), "#FFF")
    draw = ImageDraw.Draw(img)
    gradient = GRADIENTS[card_type]
    for y in range(CARD_HEIGHT):
        ratio = y / CARD_HEIGHT
        idx = int(ratio * (len(gradient)-1))
        draw.line([(0,y),(CARD_WIDTH,y)], fill=gradient[idx])

    # Draw hearts
    for i, (x,y) in enumerate(HEART_COORDS):
        color = "#FFF"
        draw_heart(draw, x, y, 60, fill=color)
        # Draw reward if scratched
        if scratched[i]:
            font = ImageFont.load_default()
            draw.text((x+15,y+20), str(rewards[i]), fill="black", font=font)
        else:
            draw.text((x+20,y+25), "⍰", fill="black", font=ImageFont.load_default())
        # Tiny bow
        draw.text((x+45,y), BUTTON_EMOJI, fill="red", font=ImageFont.load_default())
    return img

# ---------------------
# VIEWS
# ---------------------
class ScratchButton(discord.ui.Button):
    def __init__(self, index):
        super().__init__(label="Scratch", style=discord.ButtonStyle.secondary)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        card = data["cards"].get(str(interaction.message.id))
        if not card: return
        if card["scratched"][self.index]:
            await interaction.response.send_message("Already scratched!", ephemeral=True)
            return
        card["scratched"][self.index] = True

        img = create_card_image(card["rewards"], card["scratched"], card["type"])
        file = discord.File(img_to_bytes(img), filename="card.png")
        await interaction.response.edit_message(attachments=[file], view=self.view)

        # Disable button after scratch
        self.disabled = True
        await interaction.message.edit(view=self.view)

        # Log scratch
        log_ch = get_log_channel(interaction.guild)
        if log_ch:
            reward = card["rewards"][self.index]
            await log_ch.send(f"{interaction.user.display_name} scratched panel {self.index+1} and got `{reward}`!")

        # Check if complete
        if all(card["scratched"]):
            if log_ch:
                await log_ch.send(f"{interaction.user.display_name} completed the card!")

        save_data()

class ScratchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for i in range(8):
            self.add_item(ScratchButton(i))

# ---------------------
# CARD GIVE COMMAND
# ---------------------
class CardTypeDropdown(discord.ui.Select):
    def __init__(self, user):
        options = [
            discord.SelectOption(label="Vanilla", description="Vanilla Card"),
            discord.SelectOption(label="Sugar", description="Sugar Card"),
            discord.SelectOption(label="Sweet", description="Sweet Card"),
            discord.SelectOption(label="Sprinkle", description="Sprinkle Card")
        ]
        super().__init__(placeholder="Select Card Type", options=options)
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        card_type = self.values[0].lower()
        rewards = generate_rewards(card_type)
        scratched = [False]*8
        img = create_card_image(rewards, scratched, card_type)
        file = discord.File(img_to_bytes(img), filename="card.png")
        view = ScratchView()
        await interaction.response.send_message(f"{self.user.display_name} received a {card_type} card!", file=file, view=view)
        msg = await interaction.original_response()
        data["cards"][str(msg.id)] = {
            "rewards": rewards,
            "scratched": scratched,
            "user_id": self.user.id,
            "type": card_type
        }
        # Track giver
        giver_id = interaction.user.id
        data["givers"][str(giver_id)] = data["givers"].get(str(giver_id),0)+1
        save_data()
        # Log
        log_ch = get_log_channel(interaction.guild)
        if log_ch:
            await log_ch.send(f"{interaction.user.display_name} gave a {card_type} card to {self.user.display_name}")

class CardGiveView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=None)
        self.add_item(CardTypeDropdown(user))

@bot.tree.command(name="give_card")
@app_commands.describe(user="The member to give the card")
async def give_card(interaction: discord.Interaction, user: discord.Member):
    view = CardGiveView(user)
    await interaction.response.send_message(f"{interaction.user.display_name}, select a card type for {user.display_name}:", view=view)

# ---------------------
# GIVER LEADERBOARD
# ---------------------
@bot.tree.command(name="giver_leaderboard")
async def giver_leaderboard(interaction: discord.Interaction):
    sorted_givers = sorted(data["givers"].items(), key=lambda x: x[1], reverse=True)
    desc = ""
    for i, (uid, count) in enumerate(sorted_givers[:10], start=1):
        member = interaction.guild.get_member(int(uid))
        if member:
            desc += f"{i}. {member.display_name} — {count} cards\n"
    if not desc: desc = "No givers yet!"
    embed = discord.Embed(title="Top Card Givers", description=desc, color=0xFFD700)
    await interaction.response.send_message(embed=embed)

# ---------------------
# PROFILE (BADGES)
# ---------------------
BADGES = ["Starter", "Collector", "Master Giver", "Heartbreaker"]  # Expand later

@bot.tree.command(name="profile")
@app_commands.describe(user="Member to view profile")
async def profile(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    cards_received = sum(1 for c in data["cards"].values() if c["user_id"]==target.id)
    desc = f"**{target.display_name}**\nCards Received: {cards_received}\nBadges: {', '.join(BADGES[:cards_received])}"
    embed = discord.Embed(title="Profile", description=desc, color=0xFFB6C1)
    embed.set_thumbnail(url=target.display_avatar.url)
    await interaction.response.send_message(embed=embed)

# ---------------------
# READY
# ---------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot ready as {bot.user}")

bot.run(TOKEN)