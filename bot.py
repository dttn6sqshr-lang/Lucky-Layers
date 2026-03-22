import discord
from discord.ext import commands
import os, random, io
from PIL import Image, ImageDraw, ImageFont

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1474038672830500966
STAFF_ROLE_ID = 1474517835261804656

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

cards = {}
data = {}

# -------------------------
# DATA
# -------------------------
def get_user(uid):
    uid = str(uid)
    if uid not in data:
        data[uid] = {"sugar": 0, "opened": 0, "given": 0}
    return data[uid]

# -------------------------
# REWARDS (RARITY)
# -------------------------
def generate_rewards():
    pool = [
        ("Nothing", 50),
        ("100", 25),
        ("250", 15),
        ("500", 7),
        ("1000", 3)
    ]
    rewards = []
    for _ in range(4):
        choices = [p[0] for p in pool]
        weights = [p[1] for p in pool]
        rewards.append(random.choices(choices, weights=weights)[0])
    return rewards

def is_rare(value):
    return value not in ["Nothing", "100"]

# -------------------------
# HEART DRAWING (PRETTY)
# -------------------------
def draw_heart(draw, x, y, size, color):
    # layered circles + triangle = smooth heart
    draw.ellipse((x, y, x+size//2, y+size//2), fill=color)
    draw.ellipse((x+size//2, y, x+size, y+size//2), fill=color)
    draw.polygon([
        (x, y+size//3),
        (x+size, y+size//3),
        (x+size//2, y+size)
    ], fill=color)

# -------------------------
# CARD IMAGE
# -------------------------
def create_card(card_type, scratched, rewards):
    img = Image.new("RGBA", (520, 320))
    draw = ImageDraw.Draw(img)

    # 🌸 pastel gradient
    base_colors = {
        "Vanilla": (255, 240, 200),
        "Sugar": (255, 182, 193),
        "Sweet": (220, 200, 255),
        "Sprinkle": (200, 255, 230)
    }

    base = base_colors.get(card_type, (255, 200, 200))

    for y in range(320):
        shade = tuple(min(255, c + int(y*0.1)) for c in base)
        draw.line([(0,y),(520,y)], fill=shade)

    font = ImageFont.load_default()

    for i in range(4):
        x = 60 + i*110
        y = 110

        # ❤️ heart
        draw_heart(draw, x, y, 70, (255, 60, 100))

        # 🎀 bow (simple)
        draw.ellipse((x-10, y+20, x+10, y+40), fill="pink")
        draw.ellipse((x+60, y+20, x+80, y+40), fill="pink")

        if scratched[i]:
            text = rewards[i]

            # ✨ glow for rare
            if is_rare(text):
                for glow in range(3):
                    draw.text((x+15-glow, y+20), text, fill="gold", font=font)

            draw.text((x+15, y+20), text, fill="black", font=font)

    return img

def img_bytes(img):
    b = io.BytesIO()
    img.save(b, "PNG")
    b.seek(0)
    return b

# -------------------------
# SCRATCH BUTTON
# -------------------------
class ScratchButton(discord.ui.Button):
    def __init__(self, index):
        super().__init__(label=f"💖", style=discord.ButtonStyle.secondary)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        card = cards.get(interaction.message.id)

        if interaction.user != card["user"]:
            return await interaction.response.send_message("Not your card.", ephemeral=True)

        if card["scratched"][self.index]:
            return await interaction.response.send_message("Already scratched.", ephemeral=True)

        card["scratched"][self.index] = True

        img = create_card(card["type"], card["scratched"], card["rewards"])
        file = discord.File(img_bytes(img), "card.png")

        self.disabled = True

        await interaction.response.edit_message(attachments=[file], view=self.view)

        reward = card["rewards"][self.index]
        user = get_user(interaction.user.id)

        if reward != "Nothing":
            user["sugar"] += int(reward)

        user["opened"] += 1

        if all(card["scratched"]):
            for child in self.view.children:
                child.disabled = True
            await interaction.followup.send("🎉 Card complete!", ephemeral=True)

# -------------------------
# CARD VIEW
# -------------------------
class CardView(discord.ui.View):
    def __init__(self, user, rewards, card_type):
        super().__init__(timeout=None)
        self.user = user

        for i in range(4):
            self.add_item(ScratchButton(i))

# -------------------------
# USER PICKER
# -------------------------
class UserPicker(discord.ui.UserSelect):
    def __init__(self, staff_user, card_type):
        super().__init__(placeholder="🎀 Select recipient", min_values=1, max_values=1)
        self.staff_user = staff_user
        self.card_type = card_type

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.staff_user:
            return await interaction.response.send_message("Not yours.", ephemeral=True)

        target = self.values[0]

        rewards = generate_rewards()
        view = CardView(target, rewards, self.card_type)

        img = create_card(self.card_type, [False]*4, rewards)
        file = discord.File(img_bytes(img), "card.png")

        msg = await interaction.channel.send(
            f"{target.mention} received a {self.card_type} card 💖",
            file=file,
            view=view
        )

        cards[msg.id] = {
            "user": target,
            "type": self.card_type,
            "rewards": rewards,
            "scratched": [False]*4
        }

        giver = get_user(interaction.user.id)
        giver["given"] += 1

        await interaction.response.send_message("✅ Sent!", ephemeral=True)

# -------------------------
# CARD TYPE DROPDOWN
# -------------------------
class CardTypeDropdown(discord.ui.Select):
    def __init__(self, staff_user):
        options = [
            discord.SelectOption(label="Vanilla"),
            discord.SelectOption(label="Sugar"),
            discord.SelectOption(label="Sweet"),
            discord.SelectOption(label="Sprinkle")
        ]
        super().__init__(placeholder="🎀 Choose card type", options=options)
        self.staff_user = staff_user

    async def callback(self, interaction: discord.Interaction):
        card_type = self.values[0]

        view = discord.ui.View()
        view.add_item(UserPicker(self.staff_user, card_type))

        await interaction.response.edit_message(
            content=f"Choose recipient for {card_type}",
            view=view
        )

class GiveCardView(discord.ui.View):
    def __init__(self, staff_user):
        super().__init__(timeout=None)
        self.add_item(CardTypeDropdown(staff_user))

# -------------------------
# COMMANDS
# -------------------------
@bot.tree.command(name="givecard", guild=discord.Object(id=GUILD_ID))
async def givecard(interaction: discord.Interaction):
    if not any(role.id == STAFF_ROLE_ID for role in interaction.user.roles):
        return await interaction.response.send_message("Staff only.", ephemeral=True)

    await interaction.response.send_message(
        "🎀 Choose a card type:",
        view=GiveCardView(interaction.user),
        ephemeral=True
    )

@bot.tree.command(name="profile", guild=discord.Object(id=GUILD_ID))
async def profile(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    await interaction.response.send_message(
        f"💖 Sugar: {user['sugar']}\n🎴 Opened: {user['opened']}\n🎁 Given: {user['given']}"
    )

@bot.tree.command(name="leaderboard", guild=discord.Object(id=GUILD_ID))
async def leaderboard(interaction: discord.Interaction):
    sorted_users = sorted(data.items(), key=lambda x: x[1]["sugar"], reverse=True)[:10]
    text = ""
    for i, (uid, stats) in enumerate(sorted_users, 1):
        text += f"{i}. <@{uid}> — {stats['sugar']} 💖\n"

    await interaction.response.send_message(text or "No data yet!")

# -------------------------
# READY
# -------------------------
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print("✅ Synced")
    print(f"🚀 {bot.user} ready")

# -------------------------
bot.run(TOKEN)