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

# Box positions and size
BOXES = [
    (210,360),(480,360),(750,360),(1020,360),
    (210,620),(480,620),(750,620),(1020,620)
]
BOX_SIZE = 200

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
# Helper functions
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
        font = ImageFont.truetype("arial.ttf", 35)
    except:
        font = ImageFont.load_default()

    for i, (x, y) in enumerate(BOXES):
        if scratched[i]:
            reward = rewards[i]

            bbox = draw.textbbox((0, 0), reward, font=font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]

            # Center horizontally, slightly lower vertically (+5px)
            cx = x + BOX_SIZE // 2 - width // 2
            cy = y + BOX_SIZE // 2 - height // 2 + 5

            # Gold glow for 10k
            if reward == "10k":
                for g in range(1, 4):
                    draw.text((cx - g, cy), reward, fill=(255, 215, 0), font=font)
                    draw.text((cx + g, cy), reward, fill=(255, 215, 0), font=font)
                    draw.text((cx, cy - g), reward, fill=(255, 215, 0), font=font)
                    draw.text((cx, cy + g), reward, fill=(255, 215, 0), font=font)

            # Draw reward text in black
            draw.text((cx, cy), reward, fill="black", font=font)

    path = "card.png"
    img.save(path)
    return path

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
        img = generate_card(card["rewards"],card["scratched"])
        file = discord.File(img)

        # Remove only this button
        self.view.remove_item(self)

        await interaction.response.edit_message(attachments=[file],view=self.view)

        # Scratch panel log
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

        # Card completion log
        if all(card["scratched"]):
            prize_count = sum(1 for r in card["rewards"] if r != "Nothing")
            if log:
                await log.send(
f"""http://⠀ ✶⠀⠀⠀ ͏ ͏͏͏ ͏﮾ ͏ ͏ ͏͏ ͏⠀✶⠀ ͏ ͏͏ ͏ ͏ ͏ ׄ͏͏𝑪𝑹𝑬𝑴𝑬＿ׄ＿𝑪𝑶𝑻𝑻𝑨𝑮𝑬 ͏ ͏ ͏͏ ͏ ͏ ͏ ͏͏ ͏ ͏ ͏ ͏͏͏ ͏﮾ ͏ ͏ ͏͏ ͏ ͏ ͏𝐂𝐀𝐑𝐃＿ּ＿𝐅𝐈𝐍𝐈𝐒𝐇𝐄𝐃

all panels scratched
user ────── {interaction.user.mention}
total prizes ────── {prize_count}
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
async def create_card(interaction,user,command):
    rewards = generate_rewards(command)
    scratched = [False]*8
    img = generate_card(rewards,scratched)
    file = discord.File(img)
    view = ScratchView()

    await interaction.response.send_message(
        f"{user.mention} received a scratch card!",
        file=file,
        view=view
    )

    msg = await interaction.original_response()
    cards[msg.id] = {
        "user":user.id,
        "rewards":rewards,
        "scratched":scratched
    }

    # Card issued log
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
async def sprinkle(interaction:discord.Interaction,user:discord.Member):
    if not check_role(interaction.user,"sprinkle"):
        return await interaction.response.send_message("No permission.",ephemeral=True)
    await create_card(interaction,user,"sprinkle")

@bot.tree.command()
async def sugar(interaction:discord.Interaction,user:discord.Member):
    if not check_role(interaction.user,"sugar"):
        return await interaction.response.send_message("No permission.",ephemeral=True)
    await create_card(interaction,user,"sugar")

@bot.tree.command()
async def sweet(interaction:discord.Interaction,user:discord.Member):
    if not check_role(interaction.user,"sweet"):
        return await interaction.response.send_message("No permission.",ephemeral=True)
    await create_card(interaction,user,"sweet")

@bot.tree.command()
async def vanilla(interaction:discord.Interaction,user:discord.Member):
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