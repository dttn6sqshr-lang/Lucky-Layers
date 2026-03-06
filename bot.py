import discord
from discord.ext import commands
from discord.ui import View, Button
from PIL import Image, ImageDraw, ImageFont
import random
import json
import os

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Load role permissions
with open("roles.json") as f:
    role_permissions = json.load(f)

# Prize pools
prizes = {
    "sprinkle": ["5 seasonal", "15 seasonal", "20 seasonal", "Nothing"],
    "sugar": ["300", "400", "500", "600", "700", "800", "900", "1k", "1.2k", "1.5k", "2k", "2.2k", "2.5k", "3k", "3.2k", "3.5k", "4k", "4.2k", "4.5k", "5k", "6k", "7k", "8k", "9k", "9.5k", "10k", "Nothing"],
    "sweet": ["Free", "5%", "10%", "20%", "25%", "50%", "Nothing"],
    "vanilla": [str(i) for i in range(100,50001,100)] + ["Nothing"]
}

# Number of guaranteed prizes per card
prize_counts = {
    "sprinkle": 1,
    "sugar": 2,
    "sweet": 2,
    "vanilla": 3
}

# Rectangle coordinates (approximate, adjust later)
RECT_COORDS = [
    (100, 200), (300, 200), (500, 200), (100, 400),
    (300, 400), (500, 400), (200, 600), (400, 600)
]

FONT_PATH = "arial.ttf"  # System font or include a ttf file
FONT_SIZE = 50

# Permission check for staff commands
def can_run_command(ctx, command_name):
    user_roles = [str(r.id) for r in ctx.author.roles]
    allowed_roles = role_permissions.get(command_name, [])
    return any(r in allowed_roles for r in user_roles)

# Pick prizes for rectangles
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

# Generate card PNG with revealed prizes
def generate_card(rects, revealed):
    template_path = "scratch_template.png"  # Single template in root
    card = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(card)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    for i, rect in enumerate(rects):
        if revealed[i]:
            x, y = RECT_COORDS[i]
            draw.text((x, y), rect['prize'], fill="black", font=font)
    card.save("scratch_result.png")

# Discord View for interactive buttons
class ScratchView(View):
    def __init__(self, ctx, rects, command_name):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.rects = rects
        self.command_name = command_name
        self.revealed = [False]*8
        for i in range(8):
            self.add_item(ScratchButton(i, self))

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
        prize = self.view_ref.rects[self.index]['prize']

        # Handle Double-or-Nothing / Hidden Symbol
        if prize == "Double-or-Nothing":
            await interaction.response.send_message(f"Rectangle {self.index+1} is Double-or-Nothing! You can risk your prize.", ephemeral=True)
        elif prize == "Hidden Symbol!":
            await interaction.response.send_message(f"Rectangle {self.index+1} revealed a Hidden Symbol!", ephemeral=True)
        elif prize.startswith("Trap Rectangle"):
            await interaction.response.send_message(f"{prize}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Rectangle {self.index+1} result: {prize}", ephemeral=True)

        # Update the image for everyone
        await self.view_ref.ctx.send(file=discord.File("scratch_result.png"))

# Command to create scratch card (staff only)
async def create_scratch_card(ctx, command_name):
    if not can_run_command(ctx, command_name):
        return await ctx.send("❌ You do not have permission to generate a scratch card.")

    rects = pick_rectangles(command_name)
    generate_card(rects, [False]*8)
    view = ScratchView(ctx, rects, command_name)
    await ctx.send(file=discord.File("scratch_result.png"), view=view, content=f"🍬 {command_name.capitalize()} Scratch Card! Click the rectangles to scratch!")

# Staff commands
@bot.command()
async def sprinkle(ctx):
    await create_scratch_card(ctx, "sprinkle")

@bot.command()
async def sugar(ctx):
    await create_scratch_card(ctx, "sugar")

@bot.command()
async def sweet(ctx):
    await create_scratch_card(ctx, "sweet")

@bot.command()
async def vanilla(ctx):
    await create_scratch_card(ctx, "vanilla")

# Run bot
bot.run(os.environ['DISCORD_TOKEN'])