import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
import random
import json
import os

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Load allowed roles from JSON
with open("roles.json") as f:
    allowed_roles = [int(r) for r in json.load(f)["allowed_roles"]]

# Store scratch card states
cards = {}

# Square positions on template
RECT_COORDS = [
    (210, 360),
    (480, 360),
    (750, 360),
    (1020, 360),
    (210, 620),
    (480, 620),
    (750, 620),
    (1020, 620)
]

rect_width = 200
rect_height = 200

# Prize pools
SPRINKLE = ["5 Seasonal", "15 Seasonal", "20 Seasonal", "Nothing"]
SUGAR = [
    "300","400","500","600","700","800","900","1k","1.2k","1.5k","2k","2.2k","2.5k",
    "3k","3.2k","3.5k","4k","4.2k","4.5k","5k","6k","7k","8k","9k","9.5k","10k","Nothing"
]
SWEET = ["Free","5%","10%","20%","25%","50%","Nothing"]
VANILLA = ["100","250","500","1k","2k","5k","10k","25k","50k","Nothing"]

# ---------------------------
# Helper Functions
# ---------------------------

def check_staff(member):
    """Check if member has allowed roles."""
    return any(role.id in allowed_roles for role in member.roles)

def generate_rewards(pool, num_prizes):
    """Generate 8 rewards with a fixed number of prizes."""
    rewards = ["Nothing"] * 8
    prize_positions = random.sample(range(8), num_prizes)
    available_prizes = [p for p in pool if p != "Nothing"]
    for pos in prize_positions:
        rewards[pos] = random.choice(available_prizes)
    return rewards

def generate_card(rewards, scratched):
    """Generate the scratch card image."""
    img = Image.open("templates/scratch_template.png")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    for i, scratched_box in enumerate(scratched):
        if scratched_box:
            x, y = RECT_COORDS[i]
            reward = rewards[i]
            # Draw white rectangle over scratched area
            draw.rectangle([x, y, x + rect_width, y + rect_height], fill="white")
            # Draw the reward text centered
            bbox = draw.textbbox((0,0), reward, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            draw.text(
                (x + (rect_width - text_width)/2, y + (rect_height - text_height)/2),
                reward,
                fill="black",
                font=font
            )

    path = "card.png"
    img.save(path)
    return path

# ---------------------------
# Buttons & Views
# ---------------------------

class ScratchButton(discord.ui.Button):
    def __init__(self, index):
        super().__init__(label=f"Scratch {index+1}", style=discord.ButtonStyle.secondary)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        card = cards.get(interaction.message.id)

        # Only assigned user can scratch
        if interaction.user.id != card["user"]:
            return await interaction.response.send_message(
                "This isn't your card!", ephemeral=True
            )

        if card["scratched"][self.index]:
            return await interaction.response.send_message(
                "Already scratched!", ephemeral=True
            )

        card["scratched"][self.index] = True
        reward = card["rewards"][self.index]

        # Regenerate card with scratched info
        img = generate_card(card["rewards"], card["scratched"])
        file = discord.File(img)

        await interaction.response.edit_message(
            attachments=[file],
            view=self.view
        )

        # Log to channel
        log_channel = discord.utils.get(interaction.guild.text_channels, name="ᐢᗜᐢ﹑logs！﹒")
        if log_channel:
            await log_channel.send(
                f"{interaction.user.mention} scratched **#{self.index+1}** and won **{reward}**"
            )

class ScratchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for i in range(8):
            self.add_item(ScratchButton(i))

# ---------------------------
# Card Creation
# ---------------------------

async def create_card(interaction, user, pool, num_prizes):
    rewards = generate_rewards(pool, num_prizes)
    scratched = [False] * 8

    img = generate_card(rewards, scratched)
    file = discord.File(img)
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

# ---------------------------
# Slash Commands
# ---------------------------

@bot.tree.command()
async def sprinkle(interaction: discord.Interaction, user: discord.Member):
    if not check_staff(interaction.user):
        return await interaction.response.send_message("No permission.", ephemeral=True)
    await create_card(interaction, user, SPRINKLE, num_prizes=1)

@bot.tree.command()
async def sugar(interaction: discord.Interaction, user: discord.Member):
    if not check_staff(interaction.user):
        return await interaction.response.send_message("No permission.", ephemeral=True)
    await create_card(interaction, user, SUGAR, num_prizes=3)

@bot.tree.command()
async def sweet(interaction: discord.Interaction, user: discord.Member):
    if not check_staff(interaction.user):
        return await interaction.response.send_message("No permission.", ephemeral=True)
    await create_card(interaction, user, SWEET, num_prizes=2)

@bot.tree.command()
async def vanilla(interaction: discord.Interaction, user: discord.Member):
    if not check_staff(interaction.user):
        return await interaction.response.send_message("No permission.", ephemeral=True)
    await create_card(interaction, user, VANILLA, num_prizes=3)

# ---------------------------
# Bot Ready
# ---------------------------

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot Ready")

bot.run(TOKEN)