from PIL import Image
import os

def split_image_into_tiles(image_path, output_dir, grid=(4, 4)):
    """
    Splits an image into multiple tiles for secure storage.
    """
    img = Image.open(image_path)
    w, h = img.size
    tile_w, tile_h = w // grid[0], h // grid[1]

    for i in range(grid[1]):
        for j in range(grid[0]):
            box = (j * tile_w, i * tile_h, (j + 1) * tile_w, (i + 1) * tile_h)
            tile = img.crop(box)
            tile.save(os.path.join(output_dir, f"tile_{i}_{j}.png"))
    return True
