import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import random
import json
import os
import asyncio
import io

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------
# Load roles
# ---------------------
with open("roles.json") as f:
    role_data = json.load(f)

cards = {}
card_counter = 0  # Incremental card ID

# ---------------------
# Card size and boxes
# ---------------------
CARD_WIDTH = 520
CARD_HEIGHT = 320
BOX_WIDTH = 120
BOX_HEIGHT = 95
RECT_COORDS = [
    (20,100),(140,100),(260,100),(380,100),
    (20,200),(140,200),(260,200),(380,200)
]

# ---------------------
# Prize pools & rarity weights
# ---------------------
SPRINKLE_POOL = ["5 Seasonal","15 Seasonal","20 Seasonal"]
SPRINKLE_WEIGHTS = [50,30,20]

SUGAR_POOL = [
300,400,500,600,700,800,900,
1000,1200,1500,
2000,2200,2500,
3000,3200,3500,
4000,4200,4500,
5000,6000,7000,
8000,9000,9500,10000
]
SUGAR_WEIGHTS = [10]*6 + [5]*6 + [2]*13

SWEET_POOL = ["Free","5%","10%","20%","25%","50%"]
SWEET_WEIGHTS = [50,30,10,5,3,2]

VANILLA_POOL = [str(x) for x in range(100,50001,100)]
VANILLA_WEIGHTS = [500 if int(x)<=1000 else 10 for x in VANILLA_POOL]

# ---------------------
# Helpers
# ---------------------
def check_role(member, command):
    allowed = [int(r) for r in role_data[command]]
    return any(role.id in allowed for role in member.roles)

def get_log_channel(guild):
    return discord.utils.get(guild.text_channels, name="ᐢᗜᐢ﹑logs！﹒")

def generate_rewards(command):
    rewards = ["Nothing"] * 8
    if command == "sprinkle":
        pos = random.randint(0,7)
        rewards[pos] = random.choices(SPRINKLE_POOL, weights=SPRINKLE_WEIGHTS)[0]
    elif command == "sugar":
        positions = random.sample(range(8),3)
        prizes = random.choices(SUGAR_POOL, weights=SUGAR_WEIGHTS, k=3)
        for pos, prize in zip(positions, prizes):
            rewards[pos] = str(prize)
    elif command == "sweet":
        positions = random.sample(range(8),2)
        prizes = random.choices(SWEET_POOL, weights=SWEET_WEIGHTS, k=2)
        for pos, prize in zip(positions, prizes):
            rewards[pos] = prize
    elif command == "vanilla":
        positions = random.sample(range(8),3)
        prizes = random.choices(VANILLA_POOL, weights=VANILLA_WEIGHTS, k=3)
        for pos, prize in zip(positions, prizes):
            rewards[pos] = prize
    return rewards

def img_to_bytes(img):
    b = io.BytesIO()
    img.save(b, format="PNG")
    b.seek(0)
    return b

# ---------------------
# Draw centered text
# ---------------------
def draw_text_centered(draw, x, y, w, h, text, font_size=40):
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0,0), text, font=font)
    tw = bbox[2]-bbox[0]
    th = bbox[3]-bbox[1]
    draw.text((x+(w-tw)/2, y+(h-th)/2), text, fill="black", font=font)

# ---------------------
# Background
# ---------------------
def create_background():
    img = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT))
    draw = ImageDraw.Draw(img)
    for y in range(CARD_HEIGHT):
        r = int(198 + (247-198)*(y/CARD_HEIGHT))
        g = int(255 + (215-255)*(y/CARD_HEIGHT))
        b = int(221 + (121-221)*(y/CARD_HEIGHT))
        draw.line([(0,y),(CARD_WIDTH,y)], fill=(r,g,b))
    return img

# ---------------------
# Generate scratch card with foil overlay
# ---------------------
def generate_card(rewards, scratched):
    img = create_background()
    draw = ImageDraw.Draw(img)
    # Title
    draw_text_centered(draw, 0, 25, CARD_WIDTH, 50, "CREME COTTAGE SCRATCH CARD", 36)
    # Boxes
    for i,(x,y) in enumerate(RECT_COORDS):
        draw.rounded_rectangle([x,y,x+BOX_WIDTH,y+BOX_HEIGHT], radius=18, fill=(235,235,235))
        if scratched[i]:
            font_size = 42 if rewards[i] in SWEET_POOL else 36
            draw_text_centered(draw, x, y, BOX_WIDTH, BOX_HEIGHT, rewards[i], font_size=font_size)
        else:
            overlay = Image.new("RGBA", (BOX_WIDTH,BOX_HEIGHT), (192,192,192,210))
            img.alpha_composite(overlay, (x,y))
    img.save("card.png")
    return "card.png"

# ---------------------
# Buttons
# ---------------------
class ScratchButton(discord.ui.Button):
    def __init__(self, index):
        super().__init__(
            label="Scratch",
            style=discord.ButtonStyle.secondary,
            emoji=discord.PartialEmoji(name="CC_bow", id=1479503070252765419)
        )
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        card = cards.get(interaction.message.id)
        if interaction.user.id != card["user"]:
            return await interaction.response.send_message("This isn't your card.", ephemeral=True)
        if card["scratched"][self.index]:
            return await interaction.response.send_message("Already scratched.", ephemeral=True)

        card["scratched"][self.index] = True
        img_path = generate_card(card["rewards"], card["scratched"])
        file = discord.File(img_path)
        await interaction.response.edit_message(attachments=[file], view=self.view)

        # Audit log
        log = get_log_channel(interaction.guild)
        if log:
            reward = card["rewards"][self.index]
            await log.send(
                f"⸻̸ ٢  SCRATCH CARD LOG ♱\n"
                f"Card ID: {card['id']}\n"
                f"User: {interaction.user.name}\n"
                f"Staff: {card['giver_name']}\n"
                f"Panel: {self.index+1}\n"
                f"Prize: {reward}\n"
                "━━━━━━━━━━━━━━━━━━"
            )

class ScratchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for i in range(8):
            self.add_item(ScratchButton(i))

# ---------------------
# Create card
# ---------------------
async def create_card(interaction, user, command):
    global card_counter
    card_counter += 1
    card_id = f"#{card_counter}"
    rewards = generate_rewards(command)
    scratched = [False]*8
    generate_card(rewards, scratched)
    file = discord.File("card.png")
    view = ScratchView()
    await interaction.response.send_message(f"{user.name} received a scratch card!", file=file, view=view)
    msg = await interaction.original_response()
    cards[msg.id] = {
        "id": card_id,
        "user": user.id,
        "rewards": rewards,
        "scratched": scratched,
        "giver_name": interaction.user.name
    }

    # Audit log for giving card
    log = get_log_channel(interaction.guild)
    if log:
        await log.send(
            f"⸻̸ ٢  SCRATCH CARD GIVEN ♱\n"
            f"Card ID: {card_id}\n"
            f"User: {user.name}\n"
            f"Staff: {interaction.user.name}\n"
            "━━━━━━━━━━━━━━━━━━"
        )

# ---------------------
# Commands
# ---------------------
@bot.tree.command()
async def sprinkle(interaction: discord.Interaction, user: discord.Member):
    if not check_role(interaction.user,"sprinkle"):
        return await interaction.response.send_message("No permission", ephemeral=True)
    await create_card(interaction,user,"sprinkle")

@bot.tree.command()
async def sugar(interaction: discord.Interaction, user: discord.Member):
    if not check_role(interaction.user,"sugar"):
        return await interaction.response.send_message("No permission", ephemeral=True)
    await create_card(interaction,user,"sugar")

@bot.tree.command()
async def sweet(interaction: discord.Interaction, user: discord.Member):
    if not check_role(interaction.user,"sweet"):
        return await interaction.response.send_message("No permission", ephemeral=True)
    await create_card(interaction,user,"sweet")

@bot.tree.command()
async def vanilla(interaction: discord.Interaction, user: discord.Member):
    if not check_role(interaction.user,"vanilla"):
        return await interaction.response.send_message("No permission", ephemeral=True)
    await create_card(interaction,user,"vanilla")

# ---------------------
# Bot ready
# ---------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Creme Cottage Scratch Bot Ready")

bot.run(TOKEN)