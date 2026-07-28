import os
import random
import io
from PIL import Image, ImageDraw, ImageFont

# Folder where custom tile images live. Name each file after its tile value,
# e.g. assets/tiles/2.png, assets/tiles/4.png, ... assets/tiles/2048.png
# Any value without a matching image just falls back to the colored-number look.
TILE_IMAGE_DIR = os.path.join(os.path.dirname(__file__), "assets", "tiles")
_tile_image_cache = {}

TILE_COLORS = {
    0: (205, 193, 180),
    2: (238, 228, 218),
    4: (237, 224, 200),
    8: (242, 177, 121),
    16: (245, 149, 99),
    32: (246, 124, 95),
    64: (246, 94, 59),
    128: (237, 207, 114),
    256: (237, 204, 97),
    512: (237, 200, 80),
    1024: (237, 197, 63),
    2048: (237, 194, 46),
}
TEXT_DARK = (119, 110, 101)
TEXT_LIGHT = (249, 246, 242)
BG_COLOR = (187, 173, 160)


def _load_tile_image(value, size):
    """Loads assets/tiles/{value}.png resized to (size, size). Returns None if no such file exists."""
    cache_key = (value, size)
    if cache_key in _tile_image_cache:
        return _tile_image_cache[cache_key]

    path = os.path.join(TILE_IMAGE_DIR, f"{value}.png")
    if not os.path.isfile(path):
        _tile_image_cache[cache_key] = None
        return None

    img = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
    _tile_image_cache[cache_key] = img
    return img


class Game2048:
    """Holds the board state and knows how to move/merge tiles and render itself."""

    def __init__(self):
        self.board = [[0] * 4 for _ in range(4)]
        self.score = 0
        self.game_over = False
        self.won = False
        self._spawn_tile()
        self._spawn_tile()

    def _spawn_tile(self):
        empties = [(r, c) for r in range(4) for c in range(4) if self.board[r][c] == 0]
        if not empties:
            return
        r, c = random.choice(empties)
        self.board[r][c] = 4 if random.random() < 0.1 else 2

    def _compress_merge(self, row):
        """Slide non-zero values left and merge equal neighbors. Returns (new_row, points_gained)."""
        squeezed = [v for v in row if v != 0]
        result = []
        gained = 0
        i = 0
        while i < len(squeezed):
            if i + 1 < len(squeezed) and squeezed[i] == squeezed[i + 1]:
                val = squeezed[i] * 2
                result.append(val)
                gained += val
                if val == 2048:
                    self.won = True
                i += 2
            else:
                result.append(squeezed[i])
                i += 1
        result += [0] * (4 - len(result))
        return result, gained

    def move(self, direction):
        """direction: 'up', 'down', 'left', 'right'. Returns True if the board actually changed."""
        original = [row[:] for row in self.board]
        gained_total = 0

        if direction == "left":
            rows = [self.board[r][:] for r in range(4)]
        elif direction == "right":
            rows = [self.board[r][::-1] for r in range(4)]
        elif direction == "up":
            rows = [[self.board[r][c] for r in range(4)] for c in range(4)]
        elif direction == "down":
            rows = [[self.board[r][c] for r in range(3, -1, -1)] for c in range(4)]
        else:
            raise ValueError(f"Unknown direction: {direction}")

        new_rows = []
        for row in rows:
            new_row, gained = self._compress_merge(row)
            new_rows.append(new_row)
            gained_total += gained

        if direction == "left":
            self.board = new_rows
        elif direction == "right":
            self.board = [row[::-1] for row in new_rows]
        elif direction == "up":
            for c in range(4):
                for r in range(4):
                    self.board[r][c] = new_rows[c][r]
        elif direction == "down":
            for c in range(4):
                for r in range(4):
                    self.board[r][c] = new_rows[c][3 - r]

        self.score += gained_total
        changed = self.board != original
        if changed:
            self._spawn_tile()
            if not self._has_moves():
                self.game_over = True
        return changed

    def _has_moves(self):
        for r in range(4):
            for c in range(4):
                if self.board[r][c] == 0:
                    return True
                if c + 1 < 4 and self.board[r][c] == self.board[r][c + 1]:
                    return True
                if r + 1 < 4 and self.board[r][c] == self.board[r + 1][c]:
                    return True
        return False

    def render(self):
        """Draws the current board to a PNG in memory and returns a BytesIO ready to attach."""
        tile_size = 100
        padding = 10
        size = tile_size * 4 + padding * 5
        img = Image.new("RGB", (size, size), BG_COLOR)
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
            small_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        except OSError:
            font = ImageFont.load_default()
            small_font = font

        for r in range(4):
            for c in range(4):
                val = self.board[r][c]
                x0 = padding + c * (tile_size + padding)
                y0 = padding + r * (tile_size + padding)
                x1, y1 = x0 + tile_size, y0 + tile_size

                tile_img = _load_tile_image(val, tile_size) if val != 0 else None

                if tile_img is not None:
                    # Custom picture for this tile value: paste it in, rounded corners to match the board style.
                    mask = Image.new("L", (tile_size, tile_size), 0)
                    ImageDraw.Draw(mask).rounded_rectangle([0, 0, tile_size, tile_size], radius=8, fill=255)
                    img.paste(tile_img, (x0, y0), mask)
                else:
                    # No custom image for this value (or it's an empty tile) - use the classic colored-number look.
                    color = TILE_COLORS.get(val, (60, 58, 50))
                    draw.rounded_rectangle([x0, y0, x1, y1], radius=8, fill=color)

                    if val != 0:
                        text = str(val)
                        f = font if val < 1000 else small_font
                        bbox = draw.textbbox((0, 0), text, font=f)
                        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                        tcolor = TEXT_DARK if val <= 4 else TEXT_LIGHT
                        draw.text(
                            (x0 + (tile_size - tw) / 2 - bbox[0], y0 + (tile_size - th) / 2 - bbox[1]),
                            text,
                            font=f,
                            fill=tcolor,
                        )

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf