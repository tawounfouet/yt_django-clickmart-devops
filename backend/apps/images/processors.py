import io
from PIL import Image as PILImage


def extract_metadata(image_field):
    """Extract width, height, EXIF from an uploaded image."""
    img = PILImage.open(image_field)
    metadata = {
        'width': img.width,
        'height': img.height,
        'exif_data': {},
    }
    exif = img.getexif()
    if exif:
        for tag_id, value in exif.items():
            from PIL.ExifTags import TAGS
            tag_name = TAGS.get(tag_id, tag_id)
            if isinstance(value, bytes):
                value = value.hex()
            metadata['exif_data'][tag_name] = str(value)
    return metadata


def generate_thumbnail(image_field, size=(300, 300)):
    """Generate a square thumbnail."""
    img = PILImage.open(image_field)
    img = img.convert('RGB')
    img.thumbnail(size)
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    buf.seek(0)
    return buf


def resize_to_fit(image_field, max_width=1920, max_height=1080):
    """Resize image to fit within bounds, maintaining aspect ratio."""
    img = PILImage.open(image_field)
    img.thumbnail((max_width, max_height))
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=90)
    buf.seek(0)
    return buf


def convert_to_webp(image_field, quality=80):
    """Convert image to WebP format."""
    img = PILImage.open(image_field)
    img = img.convert('RGB')
    buf = io.BytesIO()
    img.save(buf, format='WEBP', quality=quality)
    buf.seek(0)
    return buf
