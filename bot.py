import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import random
import json
import os

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Load role permissions
with open("roles.json") as f:
    role_data = json.load(f)

cards = {}

# ---------------------
# DPI & measurement helpers
# ---------------------
DPI = 300
def inch_to_px(value_in_inches):
    return int(value_in_inches * DPI)

# Box dimensions in inches
BOX_WIDTH_IN = 1.25
BOX_HEIGHT_IN = 1.15
BOX_WIDTH_PX = inch_to_px(BOX_WIDTH_IN)
BOX_HEIGHT_PX = inch_to_px(BOX_HEIGHT_IN)

# Rectangle centers in inches
RECT_CENTERS_INCH = [
    (1.30, 3.25),(2.90, 3.25),(4.50, 3.25),(6.10, 3.25),
    (1.30, 1.65),(2.90, 1.65),(4.50, 1.65),(6.10, 1.65)
]
RECT_CENTERS_PX = [(inch_to_px(x), inch_to_px(y)) for x, y in RECT_CENTERS_INCH]

# ---------------------
# Prize pools
# ---------------------
SPRINKLE_POOL = ["5 Seasonal","15 Seasonal","20 Seasonal"]  # 1 prize
SUGAR_POOL = [
    "300","400","500","600","700","800","900","1k","1.2k","1.5k",
    "2k","2.2k","2.5k","3k","3.2k","3.5k","4k","4.2k","4.5k",
    "5k","6k","7k","8k","9k","9.5k","10k"
]  # 3 prizes
SWEET_POOL = ["Free","5%","10%","20%","25%","50%"]  # 2 prizes
VANILLA_POOL = [
    "100","150","200","250","300","350","400","450","500","550","600","650","700","750","800","850","900","950","1k",
    "1.5k","2k","2.5k","3k","3.5k","4k","4.5k","5k","5.5k","6k","6.5k","7k","7.5k","8k","8.5k","9k","9.5k","10k",
    "11k","12k","13k","14k","15k","16k","17k","18k","19k","20k","21k","22k","23k","24k","25k","26k","27k","28k","29k","30k",
    "31k","32k","33k","34k","35k","36k","37k","38k","39k","40k","41k","42k","43k","44k","45k","46k","47k","48k","49k","50k"
]  # 3 prizes

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
# Card generation
# ---------------------
def generate_card(rewards, scratched):
    img = Image.open("scratch_template.png").convert("RGBA")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 45)
    except:
        font = ImageFont.load_default()

    for i, scratched_box in enumerate(scratched):
        if scratched_box:
            reward = rewards[i]
            center_x, center_y = RECT_CENTERS_PX[i]

            bbox = draw.textbbox((0,0), reward, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            cx = center_x - text_width / 2
            cy = center_y - text_height / 2

            # Gold glow for 10k
            if reward == "10k":
                for g in range(1, 4):
                    draw.text((cx - g, cy), reward, fill=(255,215,0), font=font)
                    draw.text((cx + g, cy), reward, fill=(255,215,0), font=font)
                    draw.text((cx, cy - g), reward, fill=(255,215,0), font=font)
                    draw.text((cx, cy + g), reward, fill=(255,215,0), font=font)

            draw.text((cx, cy), reward, font=font, fill="black")

    img.save("card.png")
    return "card.png"

# ---------------------
# Buttons
# ---------------------
class ScratchButton(discord.ui.Button):
    def __init__(self,index):
        super().__init__(label=f"Scratch {index+1}",style=discord.ButtonStyle.secondary)
        self.index = index

    async def callback(self,interaction:discord.Interaction):
        card = cards.get(interaction.message.id)
        if interaction.user.id != card["user"]:
            return await interaction.response.send_message("This isn't your card.",ephemeral=True)
        if card["scratched"][self.index]:
            return await interaction.response.send_message("Already scratched.",ephemeral=True)

        card["scratched"][self.index] = True
        reward = card["rewards"][self.index]
        img_path = generate_card(card["rewards"], card["scratched"])
        file = discord.File(img_path)

        # Remove only this button
        self.view.remove_item(self)
        await interaction.response.edit_message(attachments=[file], view=self.view)

        log = get_log_channel(interaction.guild)
        if log:
            await log.send(
f"""http://⠀ ✶⠀⠀⠀ ͏ ͏͏͏ ͏﮾ ͏ ͏ ͏͏ ͏⠀✶⠀ ͏ ͏͏ ͏ ͏ ͏ ׄ͏͏𝑪𝑹𝑬𝑴𝑬＿ׄ＿𝑪𝑶𝑻𝑻𝑨𝑮𝑬 ͏ ͏ ͏͏ ͏ ͏ ͏ ͏͏ ͏ ͏ ͏ ͏͏͏ ͏﮾ ͏ ͏ ͏͏ ͏ ͏ ͏𝐒𝐂𝐑𝐀𝐓𝐂𝐇＿ּ＿𝐑𝐄𝐒𝐔𝐋𝐓
user scratched a panel
user ────── {interaction.user.mention}
panel ────── #{self.index+1}
reward ────── {reward}
"""
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
    rewards = generate_rewards(command)
    scratched = [False]*8
    img_path = generate_card(rewards, scratched)
    file = discord.File(img_path)
    view = ScratchView()

    await interaction.response.send_message(
        f"{user.mention} received a scratch card!",
        file=file,
        view=view
    )

    msg = await interaction.original_response()
    cards[msg.id] = {
        "user": user.id,
        "rewards": rewards,
        "scratched": scratched
    }

    log = get_log_channel(interaction.guild)
    if log:
        await log.send(
f"""http://⠀ ✶⠀⠀⠀ ͏ ͏͏͏ ͏﮾ ͏ ͏ ͏͏ ͏⠀✶⠀ ͏ ͏͏ ͏ ͏ ͏ ׄ͏͏𝑪𝑹𝑬𝑴𝑬＿ׄ＿𝑪𝑶𝑻𝑻𝑨𝑮𝑬 ͏ ͏ ͏͏ ͏ ͏ ͏ ͏͏ ͏ ͏ ͏ ͏͏͏ ͏﮾ ͏ ͏ ͏͏ ͏ ͏ ͏𝐒𝐂𝐑𝐀𝐓𝐂𝐇＿ּ＿𝐂𝐀𝐑𝐃
staff issued a scratch card
user ────── {user.mention}
staff ────── {interaction.user.mention}
type ────── {command} spin
"""
        )

# ---------------------
# Commands
# ---------------------
@bot.tree.command()
async def sprinkle(interaction: discord.Interaction, user: discord.Member):
    if not check_role(interaction.user,"sprinkle"):
        return await interaction.response.send_message("No permission.",ephemeral=True)
    await create_card(interaction,user,"sprinkle")

@bot.tree.command()
async def sugar(interaction: discord.Interaction, user: discord.Member):
    if not check_role(interaction.user,"sugar"):
        return await interaction.response.send_message("No permission.",ephemeral=True)
    await create_card(interaction,user,"sugar")

@bot.tree.command()
async def sweet(interaction: discord.Interaction, user: discord.Member):
    if not check_role(interaction.user,"sweet"):
        return await interaction.response.send_message("No permission.",ephemeral=True)
    await create_card(interaction,user,"sweet")

@bot.tree.command()
async def vanilla(interaction: discord.Interaction, user: discord.Member):
    if not check_role(interaction.user,"vanilla"):
        return await interaction.response.send_message("No permission.",ephemeral=True)
    await create_card(interaction,user,"vanilla")

# ---------------------
# Bot ready
# ---------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Scratch Bot Ready")

bot.run(TOKEN)