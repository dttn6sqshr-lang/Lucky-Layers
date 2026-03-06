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

# ---------------------
# Card size
# ---------------------
CARD_WIDTH = 520
CARD_HEIGHT = 320

BOX_WIDTH = 110
BOX_HEIGHT = 80

RECT_COORDS = [
    (20,100),
    (145,100),
    (270,100),
    (395,100),
    (20,200),
    (145,200),
    (270,200),
    (395,200)
]

# ---------------------
# Prize pools
# ---------------------

SPRINKLE_POOL = [
"5 Seasonal",
"15 Seasonal",
"20 Seasonal"
]

SUGAR_POOL = [
"300","400","500","600","700","800","900",
"1000","1200","1500","2000","2200","2500",
"3000","3200","3500","4000","4200","4500",
"5000","6000","7000","8000","9000","9500","10000"
]

SWEET_POOL = [
"Free",
"5%",
"10%",
"20%",
"25%",
"50%"
]

# Vanilla weighted system
VANILLA_COMMON = list(range(100,2001,100))
VANILLA_UNCOMMON = list(range(2000,10001,200))
VANILLA_RARE = list(range(10000,30001,500))
VANILLA_ULTRA = [50000]

# ---------------------
# Helpers
# ---------------------

def check_role(member, command):
    allowed = [int(r) for r in role_data[command]]
    return any(role.id in allowed for role in member.roles)

def get_log_channel(guild):
    return discord.utils.get(guild.text_channels, name="ᐢᗜᐢ﹑logs！﹒")

def weighted_vanilla():

    roll = random.random()

    if roll < 0.70:
        prize = random.choice(VANILLA_COMMON)

    elif roll < 0.90:
        prize = random.choice(VANILLA_UNCOMMON)

    elif roll < 0.99:
        prize = random.choice(VANILLA_RARE)

    else:
        prize = 50000

    return f"{prize} Sugar Bits"

# ---------------------
# Reward generation
# ---------------------

def generate_rewards(command):

    rewards = ["Nothing"] * 8

    if command == "sprinkle":

        prize = random.choice(SPRINKLE_POOL)
        pos = random.randint(0,7)
        rewards[pos] = prize

    elif command == "sugar":

        prizes = random.sample(SUGAR_POOL,3)
        positions = random.sample(range(8),3)

        for pos, prize in zip(positions, prizes):
            rewards[pos] = prize

    elif command == "sweet":

        prizes = random.sample(SWEET_POOL,2)
        positions = random.sample(range(8),2)

        for pos, prize in zip(positions, prizes):
            rewards[pos] = prize

    elif command == "vanilla":

        positions = random.sample(range(8),3)

        for pos in positions:
            rewards[pos] = weighted_vanilla()

    return rewards

# ---------------------
# Convert image
# ---------------------

def img_to_bytes(img):

    b = io.BytesIO()
    img.save(b, format="PNG")
    b.seek(0)
    return b

# ---------------------
# Centered text
# ---------------------

def draw_text_centered(draw,x,y,w,h,text,font_size=42):

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",font_size)
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0,0),text,font=font)

    text_w = bbox[2]-bbox[0]
    text_h = bbox[3]-bbox[1]

    draw.text(
        (x + (w-text_w)/2, y + (h-text_h)/2),
        text,
        fill="black",
        font=font
    )

# ---------------------
# Background
# ---------------------

def create_background():

    img = Image.new("RGBA",(CARD_WIDTH,CARD_HEIGHT))
    draw = ImageDraw.Draw(img)

    for y in range(CARD_HEIGHT):

        r = int(198 + (247-198)*(y/CARD_HEIGHT))
        g = int(255 + (215-255)*(y/CARD_HEIGHT))
        b = int(221 + (121-221)*(y/CARD_HEIGHT))

        draw.line([(0,y),(CARD_WIDTH,y)],fill=(r,g,b))

    for _ in range(25):

        x = random.randint(0,CARD_WIDTH)
        y = random.randint(0,CARD_HEIGHT)

        draw.ellipse((x,y,x+3,y+3),fill=(255,255,255))

    return img

# ---------------------
# Generate card
# ---------------------

def generate_card(rewards,scratched):

    img = create_background()
    draw = ImageDraw.Draw(img)

    draw_text_centered(
        draw,
        0,
        10,
        CARD_WIDTH,
        50,
        "CREME COTTAGE SCRATCH CARD",
        38
    )

    for i,(x,y) in enumerate(RECT_COORDS):

        draw.rounded_rectangle(
        (x,y,x+BOX_WIDTH,y+BOX_HEIGHT),
        radius=20,
        fill=(230,230,230)
        )

        if not scratched[i]:

            overlay = Image.new("RGBA",(BOX_WIDTH,BOX_HEIGHT),(180,180,180,200))
            img.alpha_composite(overlay,(x,y))

        else:

            draw_text_centered(
            draw,
            x,
            y,
            BOX_WIDTH,
            BOX_HEIGHT,
            rewards[i],
            36
            )

    img.save("card.png")

    return "card.png"

# ---------------------
# Buttons
# ---------------------

class ScratchButton(discord.ui.Button):

    def __init__(self,index):

        super().__init__(
        label="Scratch",
        style=discord.ButtonStyle.secondary,
        emoji=discord.PartialEmoji(name="CC_bow", id=1479503070252765419)
        )

        self.index=index

    async def callback(self,interaction:discord.Interaction):

        card = cards.get(interaction.message.id)

        if interaction.user.id != card["user"]:
            return await interaction.response.send_message("Not your card.",ephemeral=True)

        if card["scratched"][self.index]:
            return await interaction.response.send_message("Already scratched.",ephemeral=True)

        self.disabled=True

        await interaction.response.edit_message(view=self.view)

        x,y = RECT_COORDS[self.index]

        for alpha in [200,150,100,50,0]:

            img = create_background()
            draw = ImageDraw.Draw(img)

            for i,(bx,by) in enumerate(RECT_COORDS):

                draw.rounded_rectangle(
                (bx,by,bx+BOX_WIDTH,by+BOX_HEIGHT),
                radius=20,
                fill=(230,230,230)
                )

                if not card["scratched"][i] or i==self.index:

                    overlay = Image.new("RGBA",(BOX_WIDTH,BOX_HEIGHT),(180,180,180,alpha))
                    img.alpha_composite(overlay,(bx,by))

                else:

                    draw_text_centered(
                    draw,
                    bx,
                    by,
                    BOX_WIDTH,
                    BOX_HEIGHT,
                    card["rewards"][i],
                    36
                    )

            file = discord.File(img_to_bytes(img),"card.png")

            await interaction.edit_original_message(attachments=[file],view=self.view)

            await asyncio.sleep(0.2)

        card["scratched"][self.index]=True

        img_path = generate_card(card["rewards"],card["scratched"])

        file = discord.File(img_path)

        await interaction.edit_original_message(attachments=[file],view=self.view)

        # log
        log = get_log_channel(interaction.guild)

        if log:

            reward = card["rewards"][self.index]

            await log.send(
            f"""
⸻̸ ٢ ⠀  CREME COTTAGE SCRATCH LOG ⠀ ♱

User: {interaction.user.name}
Staff: {card["giver_name"]}

Panel: {self.index+1}
Prize: {reward}
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

    generate_card(rewards,scratched)

    file = discord.File("card.png")

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
    "scratched": scratched,
    "giver_name": interaction.user.name
    }

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
# Ready
# ---------------------

@bot.event
async def on_ready():

    await bot.tree.sync()

    print("Creme Cottage Scratch Bot Ready")

bot.run(TOKEN)