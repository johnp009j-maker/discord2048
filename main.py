import os
import discord
from discord.ext import commands

from game2048 import Game2048

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


class Game2048View(discord.ui.View):
    """Buttons that control one specific game. Only the person who started it can press them."""

    def __init__(self, game: Game2048, owner_id: int):
        super().__init__(timeout=600)  # view stops responding after 10 min idle
        self.game = game
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This isn't your game! Start your own with /2048.", ephemeral=True
            )
            return False
        return True

    async def update_message(self, interaction: discord.Interaction):
        buf = self.game.render()
        file = discord.File(buf, filename="board.png")

        description = f"Score: {self.game.score}"
        if self.game.won:
            description += "\n🎉 You reached 2048!"
        if self.game.game_over:
            description += "\n💀 Game Over!"
            for child in self.children:
                child.disabled = True

        embed = discord.Embed(title="2048", description=description)
        embed.set_image(url="attachment://board.png")

        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

    async def _do_move(self, interaction: discord.Interaction, direction: str):
        self.game.move(direction)
        await self.update_message(interaction)

    @discord.ui.button(label="⬆️", style=discord.ButtonStyle.secondary, row=0)
    async def up(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._do_move(interaction, "up")

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary, row=1)
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._do_move(interaction, "left")

    @discord.ui.button(label="⬇️", style=discord.ButtonStyle.secondary, row=1)
    async def down(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._do_move(interaction, "down")

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary, row=1)
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._do_move(interaction, "right")

    @discord.ui.button(label="🔄 Restart", style=discord.ButtonStyle.danger, row=2)
    async def restart(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.game = Game2048()
        for child in self.children:
            child.disabled = False
        await self.update_message(interaction)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} — slash commands synced.")


@bot.tree.command(name="2048", description="Start a new game of 2048")
async def play_2048(interaction: discord.Interaction):
    game = Game2048()
    view = Game2048View(game, interaction.user.id)

    buf = game.render()
    file = discord.File(buf, filename="board.png")
    embed = discord.Embed(title="2048", description=f"Score: {game.score}")
    embed.set_image(url="attachment://board.png")

    await interaction.response.send_message(embed=embed, file=file, view=view)


if __name__ == "__main__":
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "No token found. Set the DISCORD_BOT_TOKEN environment variable before running the bot."
        )
    bot.run(token)
    