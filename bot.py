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
# Rectangle positions (top-left) and sizes
# ---------------------
RECT_COORDS = [
    (170, 420),  # Top row
    (480, 420),
    (790, 420),
    (1100, 420),
    (170, 710),  # Bottom row
    (480, 710),
    (790, 710),
    (1100, 710)
]

rect_width = 250
rect_height = 210

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
VANILLA_POOL = [str(x) for x in range(100, 50001, 100)]  # 3 prizes, 100 → 50k

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
# Card generation helpers
# ---------------------
def draw_centered_text(draw, box_x, box_y, box_w, box_h, text, font, fill="black"):
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    cx = box_x + (box_w - text_w) / 2
    cy = box_y + (box_h - text_h) / 2
    draw.text((cx, cy), text, font=font, fill=fill)

def generate_card(rewards, scratched):
    img = Image.open("scratch_template.png").convert("RGBA")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 35)
    except:
        font = ImageFont.load_default()

    for i, scratched_box in enumerate(scratched):
        if scratched_box:
            x, y = RECT_COORDS[i]
            reward = rewards[i]

            # Gold glow for "10k"
            if reward == "10k":
                for offset in range(1,4):
                    draw_centered_text(draw, x-offset, y, rect_width, rect_height, reward, font, fill=(255,215,0))
                    draw_centered_text(draw, x+offset, y, rect_width, rect_height, reward, font, fill=(255,215,0))
                    draw_centered_text(draw, x, y-offset, rect_width, rect_height, reward, font, fill=(255,215,0))
                    draw_centered_text(draw, x, y+offset, rect_width, rect_height, reward, font, fill=(255,215,0))

            draw_centered_text(draw, x, y, rect_width, rect_height, reward, font, fill="black")

    img.save("card.png")
    return "card.png"

# ---------------------
# Buttons
# ---------------------
class ScratchButton(discord.ui.Button):
    def __init__(self,index):
        super().__init__(label=f"Scratch {index+1}", style=discord.ButtonStyle.secondary)
        self.index = index

    async def callback(self,interaction:discord.Interaction):
        card = cards.get(interaction.message.id)
        if interaction.user.id != card["user"]:
            return await interaction.response.send_message("This isn't your card.", ephemeral=True)
        if card["scratched"][self.index]:
            return await interaction.response.send_message("Already scratched.", ephemeral=True)

        card["scratched"][self.index] = True
        reward = card["rewards"][self.index]
        img_path = generate_card(card["rewards"], card["scratched"])
        file = discord.File(img_path)

        # Disable only this button
        self.disabled = True
        await interaction.response.edit_message(attachments=[file], view=self.view)

        # Audit log (username only)
        log = get_log_channel(interaction.guild)
        if log:
            await log.send(
f"""http://⠀ ✶⠀⠀⠀ ͏ ͏͏͏ ͏﮾ ͏ ͏ ͏͏ ͏⠀✶⠀ ͏ ͏͏ ͏ ͏ ͏ ׄ͏͏𝑪𝑹𝑬𝑴𝑬＿ׄ＿𝑪𝑶𝑻𝑻𝑨𝑮𝑬 ͏ ͏ ͏͏ ͏ ͏ ͏ ͏͏ ͏ ͏ ͏ ͏͏͏ ͏﮾ ͏ ͏ ͏͏ ͏ ͏ ͏𝐒𝐂𝐑𝐀𝐓𝐂𝐇＿ּ＿𝐑𝐄𝐒𝐔𝐋𝐓
user scratched a panel
user ────── {interaction.user.name}
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

    # Initial card issued log
    log = get_log_channel(interaction.guild)
    if log:
        await log.send(
f"""http://⠀ ✶⠀⠀⠀ ͏ ͏͏͏ ͏﮾ ͏ ͏ ͏͏ ͏⠀✶⠀ ͏ ͏͏ ͏ ͏ ͏ ׄ͏͏𝑪𝑹𝑬𝑴𝑬＿ׄ＿𝑪𝑶𝑻𝑻𝑨𝑮𝑬 ͏ ͏ ͏͏ ͏ ͏ ͏ ͏͏ ͏ ͏ ͏ ͏͏͏ ͏﮾ ͏ ͏ ͏͏ ͏ ͏ ͏𝐒𝐂𝐑𝐀𝐓𝐂𝐇＿ּ＿𝐂𝐀𝐑𝐃
staff issued a scratch card
user ────── {user.name}
staff ────── {interaction.user.name}
type ────── {command} spin
"""
        )

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