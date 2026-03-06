import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import json
import os

TOKEN = os.getenv("DISCORD_TOKEN")
bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

# ---------------------
# Load roles
# ---------------------
with open("roles.json") as f:
    role_data = json.load(f)

cards = {}

# ---------------------
# Box measurements and positions
# ---------------------
BOX_WIDTH = 250
BOX_HEIGHT = 210
RECT_COORDS = [
    (170, 420),
    (480, 420),
    (790, 420),
    (1100, 420),
    (170, 710),
    (480, 710),
    (790, 710),
    (1100, 710)
]

# ---------------------
# Prize pools
# ---------------------
SPRINKLE_POOL = ["5 Seasonal","15 Seasonal","20 Seasonal"]
SUGAR_POOL = [
    "300","400","500","600","700","800","900","1k","1.2k","1.5k",
    "2k","2.2k","2.5k","3k","3.2k","3.5k","4k","4.2k","4.5k",
    "5k","6k","7k","8k","9k","9.5k","10k"
]
SWEET_POOL = ["Free","5%","10%","20%","25%","50%"]
VANILLA_POOL = [str(x) for x in range(100, 50001, 100)]

# ---------------------
# Helpers
# ---------------------
def get_log_channel(guild):
    return discord.utils.get(guild.text_channels, name="ᐢᗜᐢ﹑logs！﹒")

def check_role(member, command):
    allowed = [int(r) for r in role_data[command]]
    return any(role.id in allowed for role in member.roles)

def generate_rewards(command):
    rewards = ["Nothing"] * 8
    if command == "sprinkle":
        prize = random.choice(SPRINKLE_POOL)
        pos = random.randint(0, 7)
        rewards[pos] = prize
    elif command == "sugar":
        prizes = random.sample(SUGAR_POOL, 3)
        positions = random.sample(range(8), 3)
        for pos, prize in zip(positions, prizes):
            rewards[pos] = prize
    elif command == "sweet":
        prizes = random.sample(SWEET_POOL, 2)
        positions = random.sample(range(8), 2)
        for pos, prize in zip(positions, prizes):
            rewards[pos] = prize
    elif command == "vanilla":
        prizes = random.sample(VANILLA_POOL, 3)
        positions = random.sample(range(8), 3)
        for pos, prize in zip(positions, prizes):
            rewards[pos] = prize
    return rewards

# ---------------------
# Draw centered text in boxes
# ---------------------
def draw_text_centered(draw, box_x, box_y, box_width, box_height, text, font_size=200, fill="black"):
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0,0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    center_x = box_x + box_width / 2
    center_y = box_y + box_height / 2
    draw.text(
        (center_x - text_width/2, center_y - text_height/2),
        text,
        font=font,
        fill=fill
    )

# ---------------------
# Generate gradient swirl background with hearts & sparkles
# ---------------------
def create_background(width=1800, height=1300):
    img = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(img)

    # Gradient swirl
    for i in range(height):
        r = int(198 + (247-198)*(i/height))
        g = int(255 + (121-255)*(i/height))
        b = int(221 + (123-221)*(i/height))
        draw.line([(0,i),(width,i)], fill=(r,g,b))

    # Sparkles
    for _ in range(100):
        x = random.randint(0,width)
        y = random.randint(0,height)
        draw.ellipse([x-2,y-2,x+2,y+2], fill=(255,255,255,180))

    # Hearts
    for _ in range(50):
        x = random.randint(0,width)
        y = random.randint(0,height)
        size = random.randint(8,20)
        draw.text((x,y), "❤", fill=(255,182,193,200)) # light pink

    return img

# ---------------------
# Generate scratch card
# ---------------------
def generate_card(rewards, scratched):
    img = create_background()
    draw = ImageDraw.Draw(img)

    # Draw boxes
    for i, (x, y) in enumerate(RECT_COORDS):
        color = (240, 240, 240)  # pastel gray
        border_color = (200, 200, 200)

        # 3D effect shadow
        draw.rounded_rectangle([x+5, y+5, x + BOX_WIDTH+5, y + BOX_HEIGHT+5], radius=40, fill=(210,210,210))
        # Main box
        draw.rounded_rectangle([x, y, x + BOX_WIDTH, y + BOX_HEIGHT], radius=40, fill=color, outline=border_color, width=4)

        if scratched[i]:
            draw_text_centered(draw, x, y, BOX_WIDTH, BOX_HEIGHT, rewards[i], font_size=200, fill="black")

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
        reward = card["rewards"][self.index]
        img_path = generate_card(card["rewards"], card["scratched"])
        file = discord.File(img_path)

        self.disabled = True
        await interaction.response.edit_message(attachments=[file], view=self.view)

        # Audit log (username only)
        log = get_log_channel(interaction.guild)
        if log:
            await log.send(f"SCRATCH RESULT\nUser: {interaction.user.name}\nPanel: #{self.index+1}\nReward: {reward}")

class ScratchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for i in range(8):
            self.add_item(ScratchButton(i))

# ---------------------
# Create card
# ---------------------
async def create_card(interaction, user, command):
    rewards = generate_rewards(command)
    scratched = [False]*8
    img_path = generate_card(rewards, scratched)
    file = discord.File(img_path)
    view = ScratchView()
    await interaction.response.send_message(
        f"{user.name} received a scratch card!",
        file=file,
        view=view
    )
    msg = await interaction.original_response()
    cards[msg.id] = {
        "user": user.id,
        "rewards": rewards,
        "scratched": scratched
    }

# ---------------------
# Commands
# ---------------------
@bot.tree.command()
async def sprinkle(interaction: discord.Interaction, user: discord.Member):
    if not check_role(interaction.user,"sprinkle"):
        return await interaction.response.send_message("No permission.", ephemeral=True)
    await create_card(interaction,user,"sprinkle")

@bot.tree.command()
async def sugar(interaction: discord.Interaction, user: discord.Member):
    if not check_role(interaction.user,"sugar"):
        return await interaction.response.send_message("No permission.", ephemeral=True)
    await create_card(interaction,user,"sugar")

@bot.tree.command()
async def sweet(interaction: discord.Interaction, user: discord.Member):
    if not check_role(interaction.user,"sweet"):
        return await interaction.response.send_message("No permission.", ephemeral=True)
    await create_card(interaction,user,"sweet")

@bot.tree.command()
async def vanilla(interaction: discord.Interaction, user: discord.Member):
    if not check_role(interaction.user,"vanilla"):
        return await interaction.response.send_message("No permission.", ephemeral=True)
    await create_card(interaction,user,"vanilla")

# ---------------------
# Bot ready
# ---------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Scratch Bot Ready")

bot.run(TOKEN)