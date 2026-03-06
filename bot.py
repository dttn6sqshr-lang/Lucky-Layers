import discord
from discord import app_commands
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
    "sugar": ["300","400","500","600","700","800","900","1k","1.2k","1.5k","2k","2.2k","2.5k","3k","3.2k","3.5k","4k","4.2k","4.5k","5k","6k","7k","8k","9k","9.5k","10k","Nothing"],
    "sweet": ["Free","5%","10%","20%","25%","50%","Nothing"],
    "vanilla": [str(i) for i in range(100,50001,100)] + ["Nothing"]
}

# Guaranteed prizes per card
prize_counts = {"sprinkle":1,"sugar":2,"sweet":2,"vanilla":3}

# Rectangle coordinates (adjust for your PNG)
RECT_COORDS = [
    (100,200),(300,200),(500,200),(100,400),
    (300,400),(500,400),(200,600),(400,600)
]

FONT_PATH = "arial.ttf"  # Include ttf in repo or system font
FONT_SIZE = 50

# Permission check
def can_run_command(interaction, command_name):
    user_roles = [str(r.id) for r in interaction.user.roles]
    allowed_roles = role_permissions.get(command_name, [])
    return any(r in allowed_roles for r in user_roles)

# Pick prizes
def pick_rectangles(card_type):
    rects = []
    total_prizes = prize_counts[card_type]
    guaranteed_indices = random.sample(range(8), total_prizes)

    for i in range(8):
        rect = {}
        if i in guaranteed_indices:
            rect['prize'] = random.choice([p for p in prizes[card_type] if p!="Nothing"])
        else:
            r=random.random()
            if r<0.05: rect['prize']="Double-or-Nothing"
            elif r<0.10: rect['prize']="Trap Rectangle: Better luck next time!"
            elif r<0.15: rect['prize']="Hidden Symbol!"
            else: rect['prize']="Nothing"
        rects.append(rect)
    return rects

# Generate card PNG
def generate_card(rects, revealed):
    template_path = "scratch_template.png"  # Single PNG in root folder
    card = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(card)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    for i, rect in enumerate(rects):
        if revealed[i]:
            x, y = RECT_COORDS[i]
            draw.text((x, y), rect['prize'], fill="black", font=font)
    card.save("scratch_result.png")

# Interactive buttons
class ScratchView(View):
    def __init__(self, interaction, rects, card_type):
        super().__init__(timeout=None)
        self.interaction = interaction
        self.rects = rects
        self.card_type = card_type
        self.revealed = [False]*8
        for i in range(8):
            self.add_item(ScratchButton(i,self))

class ScratchButton(Button):
    def __init__(self,index,view):
        super().__init__(label=f"Scratch {index+1}", style=discord.ButtonStyle.gray)
        self.index=index
        self.view_ref=view

    async def callback(self,interaction:discord.Interaction):
        if self.view_ref.revealed[self.index]:
            return await interaction.response.send_message("Already scratched!",ephemeral=True)
        self.view_ref.revealed[self.index]=True
        generate_card(self.view_ref.rects,self.view_ref.revealed)
        prize=self.view_ref.rects[self.index]['prize']

        # Special prize messages
        if prize=="Double-or-Nothing":
            await interaction.response.send_message(f"Rectangle {self.index+1} is Double-or-Nothing! You can risk your prize.",ephemeral=True)
        elif prize=="Hidden Symbol!":
            await interaction.response.send_message(f"Rectangle {self.index+1} revealed a Hidden Symbol!",ephemeral=True)
        elif prize.startswith("Trap Rectangle"):
            await interaction.response.send_message(f"{prize}",ephemeral=True)
        else:
            await interaction.response.send_message(f"Rectangle {self.index+1} result: {prize}",ephemeral=True)

        # Update card image for everyone
        await self.view_ref.interaction.followup.send(file=discord.File("scratch_result.png"))

# Create scratch card
async def create_scratch_card(interaction, card_type):
    if not can_run_command(interaction, card_type):
        return await interaction.response.send_message("❌ You do not have permission.",ephemeral=True)

    rects = pick_rectangles(card_type)
    generate_card(rects,[False]*8)
    view = ScratchView(interaction,rects,card_type)
    await interaction.response.send_message(file=discord.File("scratch_result.png"),view=view,content=f"🍬 {card_type.capitalize()} Scratch Card! Click the rectangles to scratch!")

# Slash commands
@bot.tree.command(name="sprinkle",description="Generate Sprinkle Scratch Card")
async def sprinkle(interaction:discord.Interaction):
    await create_scratch_card(interaction,"sprinkle")

@bot.tree.command(name="sugar",description="Generate Sugar Scratch Card")
async def sugar(interaction:discord.Interaction):
    await create_scratch_card(interaction,"sugar")

@bot.tree.command(name="sweet",description="Generate Sweet Scratch Card")
async def sweet(interaction:discord.Interaction):
    await create_scratch_card(interaction,"sweet")

@bot.tree.command(name="vanilla",description="Generate Vanilla Scratch Card")
async def vanilla(interaction:discord.Interaction):
    await create_scratch_card(interaction,"vanilla")

# Sync commands on ready
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

bot.run(os.environ['DISCORD_TOKEN'])