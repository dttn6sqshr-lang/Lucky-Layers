import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
from PIL import Image, ImageDraw, ImageFont
import random
import json
import os

# -------------------- BOT SETUP --------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# -------------------- LOAD ROLE PERMISSIONS --------------------
with open("roles.json") as f:
    role_permissions = json.load(f)

# -------------------- PRIZE POOLS --------------------
prizes = {
    "sprinkle": ["5 seasonal", "15 seasonal", "20 seasonal", "Nothing"],
    "sugar": ["300","400","500","600","700","800","900","1k","1.2k","1.5k","2k","2.2k","2.5k","3k","3.2k","3.5k","4k","4.2k","4.5k","5k","6k","7k","8k","9k","9.5k","10k","Nothing"],
    "sweet": ["Free","5%","10%","20%","25%","50%","Nothing"],
    "vanilla": [str(i) for i in range(100,50001,100)] + ["Nothing"]
}

# -------------------- GUARANTEED PRIZES --------------------
prize_counts = {"sprinkle":1,"sugar":2,"sweet":2,"vanilla":3}

# -------------------- RECTANGLE COORDINATES --------------------
# Center positions for gray rectangles (adjust to match Canva template)
RECT_COORDS = [
    (110,210),(310,210),(510,210),(110,410),
    (310,410),(510,410),(210,610),(410,610)
]

# -------------------- HELPER FUNCTIONS --------------------
def can_run_command(interaction, card_type):
    user_roles = [str(r.id) for r in interaction.user.roles]
    allowed_roles = role_permissions.get(card_type, [])
    return any(r in allowed_roles for r in user_roles)

def pick_rectangles(card_type):
    rects = []
    total_prizes = prize_counts[card_type]
    guaranteed_indices = random.sample(range(8), total_prizes)

    for i in range(8):
        rect = {}
        if i in guaranteed_indices:
            rect['prize'] = random.choice([p for p in prizes[card_type] if p != "Nothing"])
        else:
            r = random.random()
            if r < 0.05:
                rect['prize'] = "Double-or-Nothing"
            elif r < 0.10:
                rect['prize'] = "Trap Rectangle: Better luck next time!"
            elif r < 0.15:
                rect['prize'] = "Hidden Symbol!"
            else:
                rect['prize'] = "Nothing"
        rects.append(rect)
    return rects

def draw_prize(draw, x, y, prize):
    # Simple centering for default font
    offset_x = len(prize) * 2
    offset_y = 5  # small vertical adjustment
    draw.text((x - offset_x, y - offset_y), prize, fill="black", font=ImageFont.load_default())

def generate_card(rects, revealed):
    template_path = "scratch_template.png"
    card = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(card)
    
    rect_width, rect_height = 180, 80  # adjust to fit your gray rectangles
    for i, rect in enumerate(rects):
        x, y = RECT_COORDS[i]
        if revealed[i]:
            # Draw white rectangle to "scratch" gray
            draw.rectangle([x, y, x + rect_width, y + rect_height], fill="white")
            # Draw prize text
            draw_prize(draw, x + rect_width//2, y + rect_height//2, rect['prize'])
    
    card.save("scratch_result.png")

# -------------------- INTERACTIVE BUTTONS --------------------
class ScratchButton(Button):
    def __init__(self, index, view):
        super().__init__(label=f"Scratch {index+1}", style=discord.ButtonStyle.gray)
        self.index = index
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        if self.view_ref.revealed[self.index]:
            return await interaction.response.send_message("Already scratched!", ephemeral=True)

        self.view_ref.revealed[self.index] = True
        generate_card(self.view_ref.rects, self.view_ref.revealed)
        self.view_ref.remove_item(self)

        # Defer interaction
        await interaction.response.defer()

        # Edit the original message so everyone sees updates
        await self.view_ref.interaction.message.edit(
            attachments=[discord.File("scratch_result.png")],
            view=self.view_ref
        )

class ScratchView(View):
    def __init__(self, interaction, rects, card_type):
        super().__init__(timeout=None)
        self.interaction = interaction
        self.rects = rects
        self.card_type = card_type
        self.revealed = [False]*8
        for i in range(8):
            self.add_item(ScratchButton(i, self))

# -------------------- CREATE SCRATCH CARD --------------------
async def create_scratch_card(interaction, card_type):
    if not can_run_command(interaction, card_type):
        return await interaction.response.send_message("❌ You do not have permission.", ephemeral=True)

    rects = pick_rectangles(card_type)
    generate_card(rects, [False]*8)
    view = ScratchView(interaction, rects, card_type)
    await interaction.response.send_message(
        file=discord.File("scratch_result.png"),
        view=view,
        content=f"🍬 {card_type.capitalize()} Scratch Card! Click the gray rectangles to scratch!",
        ephemeral=False
    )

# -------------------- SLASH COMMANDS --------------------
@bot.tree.command(name="sprinkle", description="Generate Sprinkle Scratch Card")
async def sprinkle(interaction: discord.Interaction):
    await create_scratch_card(interaction, "sprinkle")

@bot.tree.command(name="sugar", description="Generate Sugar Scratch Card")
async def sugar(interaction: discord.Interaction):
    await create_scratch_card(interaction, "sugar")

@bot.tree.command(name="sweet", description="Generate Sweet Scratch Card")
async def sweet(interaction: discord.Interaction):
    await create_scratch_card(interaction, "sweet")

@bot.tree.command(name="vanilla", description="Generate Vanilla Scratch Card")
async def vanilla(interaction: discord.Interaction):
    await create_scratch_card(interaction, "vanilla")

# -------------------- ON READY --------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# -------------------- RUN BOT --------------------
bot.run(os.environ['DISCORD_TOKEN'])