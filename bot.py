import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
import io
import os
import random

TOKEN = os.getenv("DISCORD_TOKEN")
STAFF_ROLE_ID = 1474517835261804656

# ---------------------
# CONFIG
# ---------------------
CARD_COLORS = {
    "Vanilla": ["#F8F0C6", "#FFFDD1", "#FFD3AC", "#FFE5B4"],
    "Sugar": ["#F88379", "#FFB6C1", "#DE5D83", "#FE828C"],
    "Sweet": ["#E6E6FA", "#E6E6FA", "#C8A2C8", "#DC92EF"],
    "Sprinkle": ["#3EB489", "#98FB98", "#E0BBE4", "#FEC8D8"]
}

PRIZES = {
    "Sweet": ["Free","5%","10%","20%","25%","50%"],
    "Sprinkle": ["5 Seasonal","15 Seasonal","20 Seasonal"]
}

cards = {}

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------
# HELPERS
# ---------------------
def is_staff(member):
    return any(r.id == STAFF_ROLE_ID for r in member.roles)

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2],16) for i in (0,2,4))

def img_to_bytes(img):
    b = io.BytesIO()
    img.save(b, format="PNG")
    b.seek(0)
    return b

# ---------------------
# PRIZE SYSTEM
# ---------------------
def generate_rewards(card_type):
    rewards = ["Nothing"] * 8

    if card_type == "Sprinkle":
        for i in random.sample(range(8), 2):
            rewards[i] = random.choice(PRIZES["Sprinkle"])

    elif card_type == "Sweet":
        for i in random.sample(range(8), 2):
            rewards[i] = random.choice(PRIZES["Sweet"])

    elif card_type == "Sugar":
        for i in random.sample(range(8), 2):
            rewards[i] = random.choices(
                list(range(300,10001,50)),
                weights=[10000-x for x in range(300,10001,50)],
                k=1
            )[0]

    elif card_type == "Vanilla":
        count = random.choice([2,3,4])
        for i in random.sample(range(8), count):
            rewards[i] = random.choices(
                list(range(100,50001,50)),
                weights=[50000-x for x in range(100,50001,50)],
                k=1
            )[0]

    return rewards

# ---------------------
# DRAW HEART + BOW
# ---------------------
def draw_heart(size=60):
    img = Image.new("RGBA", (size,size))
    d = ImageDraw.Draw(img)

    d.ellipse((0,0,size//2,size//2), fill=(255,105,180))
    d.ellipse((size//2,0,size,size//2), fill=(255,105,180))
    d.polygon([(0,size//3),(size,size//3),(size//2,size)], fill=(255,105,180))

    return img

def draw_bow(size=18):
    img = Image.new("RGBA",(size,size))
    d = ImageDraw.Draw(img)

    d.ellipse((0,4,8,14), fill=(255,182,193))
    d.ellipse((10,4,18,14), fill=(255,182,193))
    d.rectangle((6,6,12,12), fill=(255,105,180))

    return img

# ---------------------
# IMAGE
# ---------------------
def create_card_image(card_type, scratched, rewards):
    img = Image.new("RGBA",(520,320))
    draw = ImageDraw.Draw(img)

    # gradient
    colors = [hex_to_rgb(c) for c in CARD_COLORS[card_type]]
    for y in range(320):
        pos = y/(319)*(len(colors)-1)
        i = int(pos)
        frac = pos-i
        c = colors[i] if i>=len(colors)-1 else tuple(
            int(colors[i][j]+(colors[i+1][j]-colors[i][j])*frac) for j in range(3)
        )
        draw.line([(0,y),(520,y)], fill=c)

    coords = [
        (40,80),(160,80),(280,80),(400,80),
        (40,180),(160,180),(280,180),(400,180)
    ]

    font = ImageFont.load_default()
    heart = draw_heart()
    bow = draw_bow()

    for i,(x,y) in enumerate(coords):
        h = heart.copy()

        if not scratched[i]:
            overlay = Image.new("RGBA",h.size,(255,255,255,120))
            h.alpha_composite(overlay)

        img.alpha_composite(h,(x,y))
        img.alpha_composite(bow,(x+20,y-5))

        # TEXT (blank until scratched)
        if scratched[i] and rewards[i] != "Nothing":
            text = str(rewards[i])
            bbox = draw.textbbox((0,0), text, font=font)
            draw.text((x+30-(bbox[2]/2), y+30-(bbox[3]/2)), text, fill="black", font=font)

    return img

# ---------------------
# UI
# ---------------------
class ScratchButton(discord.ui.Button):
    def __init__(self, index):
        super().__init__(
            label="Scratch",
            style=discord.ButtonStyle.secondary,
            custom_id=f"scratch_{index}"
        )
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        card = cards.get(interaction.message.id)

        if interaction.user.id != card["user"].id:
            return await interaction.response.send_message("Not your card.", ephemeral=True)

        if card["scratched"][self.index]:
            return await interaction.response.send_message("Already scratched.", ephemeral=True)

        card["scratched"][self.index] = True

        img = create_card_image(card["type"], card["scratched"], card["rewards"])
        file = discord.File(img_to_bytes(img), filename="card.png")

        self.disabled = True
        await interaction.response.edit_message(attachments=[file], view=self.view)

        if all(card["scratched"]):
            await interaction.followup.send(
                f"🎉 You completed your {card['type']} card!",
                ephemeral=True
            )

class ScratchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for i in range(8):
            self.add_item(ScratchButton(i))

class CardDropdown(discord.ui.Select):
    def __init__(self, target):
        super().__init__(
            placeholder="🎀 Choose a card type...",
            options=[
                discord.SelectOption(label="Vanilla"),
                discord.SelectOption(label="Sugar"),
                discord.SelectOption(label="Sweet"),
                discord.SelectOption(label="Sprinkle")
            ]
        )
        self.target = target

    async def callback(self, interaction: discord.Interaction):
        card_type = self.values[0]
        rewards = generate_rewards(card_type)
        scratched = [False]*8

        img = create_card_image(card_type, scratched, rewards)
        file = discord.File(img_to_bytes(img), filename="card.png")

        view = ScratchView()

        await interaction.response.send_message(
            f"{self.target.mention} got a {card_type} card!",
            file=file,
            view=view
        )

        msg = await interaction.original_response()
        cards[msg.id] = {
            "user": self.target,
            "type": card_type,
            "scratched": scratched,
            "rewards": rewards
        }

class CardView(discord.ui.View):
    def __init__(self, target):
        super().__init__()
        self.add_item(CardDropdown(target))

# ---------------------
# COMMAND
# ---------------------
@bot.tree.command(name="give_card")
async def give_card(interaction: discord.Interaction, user: discord.Member):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("No permission.", ephemeral=True)

    await interaction.response.send_message(
        f"Choose a card for {user.mention}",
        view=CardView(user)
    )

# ---------------------
# READY
# ---------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    bot.add_view(ScratchView())  # 🔥 fixes interaction failed
    print("Bot ready!")

bot.run(TOKEN)