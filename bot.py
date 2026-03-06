import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import random
import json
import os
import asyncio

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
BOX_WIDTH = 320
BOX_HEIGHT = 260
RECT_COORDS = [
    (170, 420),
    (520, 420),
    (870, 420),
    (1220, 420),
    (170, 710),
    (520, 710),
    (870, 710),
    (1220, 710)
]

# ---------------------
# Prize pools
# ---------------------
SPRINKLE_POOL = ["5 Seasonal","15 Seasonal","20 Seasonal"]
SUGAR_POOL = [str(x) for x in [
    300,400,500,600,700,800,900,1000,1200,1500,
    2000,2200,2500,3000,3200,3500,4000,4200,4500,
    5000,6000,7000,8000,9000,9500,10000
]]
SWEET_POOL = ["Free","5%","10%","20%","25%","50%"]
VANILLA_POOL = [str(x) for x in range(100,50001,100)]

# ---------------------
# Helpers
# ---------------------
def get_log_channel(guild):
    return discord.utils.get(guild.text_channels, name="scratch-logs")

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
# Draw centered text
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
# Create gradient background
# ---------------------
def create_background(width=1800, height=1300):
    img = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(img)
    # Gradient
    for i in range(height):
        r = int(198 + (247-198)*(i/height))
        g = int(255 + (121-255)*(i/height))
        b = int(221 + (123-221)*(i/height))
        draw.line([(0,i),(width,i)], fill=(r,g,b))
    # Stars
    for _ in range(100):
        x = random.randint(0,width)
        y = random.randint(0,height)
        draw.ellipse([x-2,y-2,x+2,y+2], fill=(255,255,255,180))
    # Hearts
    for _ in range(50):
        x = random.randint(0,width)
        y = random.randint(0,height)
        draw.text((x,y), "❤", fill=(255,182,193,200))
    return img

# ---------------------
# Generate scratch card
# ---------------------
def generate_card(rewards, scratched, overlay=True):
    img = create_background()
    draw = ImageDraw.Draw(img)
    # Title
    try:
        font_title = ImageFont.truetype("arial.ttf", 120)
    except:
        font_title = ImageFont.load_default()
    title_text = "ׄ͏͏𝑪𝑹𝑬𝑴𝑬 𝑪𝑶𝑻𝑻𝑨𝑮𝑬 ͏ ͏ ͏𝐒𝐂𝐑𝐀𝐓𝐂𝐇 𝐂𝐚𝐫𝐝"
    bbox = draw.textbbox((0,0), title_text, font=font_title)
    title_w = bbox[2]-bbox[0]
    draw.text(((1800-title_w)/2, 150), title_text, font=font_title, fill="black")

    for i, (x, y) in enumerate(RECT_COORDS):
        draw.rounded_rectangle([x+5, y+5, x + BOX_WIDTH+5, y + BOX_HEIGHT+5], radius=40, fill=(210,210,210))
        draw.rounded_rectangle([x, y, x + BOX_WIDTH, y + BOX_HEIGHT], radius=40, fill=(240,240,240), outline=(200,200,200), width=4)
        # Overlay
        if overlay and not scratched[i]:
            overlay_layer = Image.new("RGBA", (BOX_WIDTH, BOX_HEIGHT), (192,192,192,200))
            for _ in range(500):
                ox = random.randint(0, BOX_WIDTH-1)
                oy = random.randint(0, BOX_HEIGHT-1)
                overlay_layer.putpixel((ox, oy), (192,192,192,random.randint(150,220)))
            img.paste(overlay_layer, (x, y), overlay_layer)
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

        # Simulate hold-to-scratch
        self.disabled = True
        await interaction.response.edit_message(view=self.view)
        progress = await interaction.followup.send("Scratching... ⏳", ephemeral=True)
        await asyncio.sleep(2)
        card["scratched"][self.index] = True
        reward = card["rewards"][self.index]
        img_path = generate_card(card["rewards"], card["scratched"])
        file = discord.File(img_path)
        await interaction.edit_original_message(attachments=[file], view=self.view)
        await progress.delete()

        # ---------------------
        # Audit log using your template
        # ---------------------
        log = get_log_channel(interaction.guild)
        if log:
            log_message = (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "🎀 SCRATCH CARD LOG 🎀\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"User: {interaction.user.name}\n"
                f"Panel Scratched: #{self.index+1}\n"
                f"Prize Won: {reward}\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            )
            await log.send(log_message)

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
    generate_card(rewards, scratched)
    file = discord.File("card.png")
    view = ScratchView()
    await interaction.response.send_message(f"{user.name} received a scratch card!", file=file, view=view)
    msg = await interaction.original_response()
    cards[msg.id] = {"user": user.id, "rewards": rewards, "scratched": scratched}

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