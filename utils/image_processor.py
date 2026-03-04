from PIL import Image
from pathlib import Path


def split_image_into_tiles(image_path: str, out_dir: str, tile_size: int = 30) -> None:
    """
    Split the image into non-overlapping tiles of size tile_size x tile_size.
    Stores tiles as PNGs in out_dir as tile_{row}_{col}.png
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    with Image.open(image_path) as img:
        img = img.convert("RGBA")
        width, height = img.size
        rows = height // tile_size
        cols = width // tile_size

        for r in range(rows):
            for c in range(cols):
                left = c * tile_size
                upper = r * tile_size
                right = left + tile_size
                lower = upper + tile_size
                tile = img.crop((left, upper, right, lower))
                tile.save(out_path / f"tile_{r}_{c}.png")
