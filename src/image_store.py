"""Image file storage for clipboard history."""
import os
import base64

DATA_DIR = os.path.join(os.environ["APPDATA"], "HistoryClipboard")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
THUMBNAILS_DIR = os.path.join(DATA_DIR, "thumbnails")

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(THUMBNAILS_DIR, exist_ok=True)


def save_image(item_id, image_data):
    """
    Save full image and thumbnail. image_data is a QImage or bytes.
    Returns (image_rel_path, thumbnail_rel_path).
    """
    from PySide6.QtGui import QImage

    if isinstance(image_data, QImage):
        img = image_data
    elif isinstance(image_data, bytes):
        img = QImage()
        img.loadFromData(image_data)
    else:
        raise TypeError(f"Unsupported image data type: {type(image_data)}")

    image_path = os.path.join(IMAGES_DIR, f"{item_id}.png")
    img.save(image_path, "PNG")

    from PySide6.QtCore import Qt as QtCore
    thumb = img.scaledToWidth(300, QtCore.TransformationMode.SmoothTransformation)
    thumb_path = os.path.join(THUMBNAILS_DIR, f"{item_id}.png")
    thumb.save(thumb_path, "PNG")

    # Return relative paths
    return (f"images/{item_id}.png", f"thumbnails/{item_id}.png")


def delete_images(image_rel_path, thumb_rel_path):
    """Delete image and thumbnail files if they exist."""
    if image_rel_path:
        full = os.path.join(DATA_DIR, image_rel_path)
        if os.path.exists(full):
            os.remove(full)
    if thumb_rel_path:
        full = os.path.join(DATA_DIR, thumb_rel_path)
        if os.path.exists(full):
            os.remove(full)


def get_thumbnail_bytes(thumb_rel_path):
    """Read thumbnail file and return raw PNG bytes for QPixmap."""
    if not thumb_rel_path:
        return None
    full = os.path.join(DATA_DIR, thumb_rel_path)
    if not os.path.exists(full):
        return None
    with open(full, "rb") as f:
        return f.read()


def get_image_path(image_rel_path):
    """Return the absolute path for an image."""
    if not image_rel_path:
        return None
    full = os.path.join(DATA_DIR, image_rel_path)
    return full if os.path.exists(full) else None
