"""Periodic cleanup of expired clipboard history."""
from PySide6.QtCore import QTimer

from src.database import get_settings, set_setting, cleanup_expired
from src.image_store import delete_images

DEFAULT_RETENTION_DAYS = 3


def get_retention_days():
    """Get current retention setting (default 3 days)."""
    settings = get_settings()
    try:
        return int(settings.get("retention_days", DEFAULT_RETENTION_DAYS))
    except (ValueError, TypeError):
        return DEFAULT_RETENTION_DAYS


def set_retention_days(days):
    """Update retention setting."""
    set_setting("retention_days", str(days))


def run_cleanup():
    """Delete expired items and their image files."""
    days = get_retention_days()
    deleted = cleanup_expired(days)
    for img_path, thumb_path in deleted:
        delete_images(img_path, thumb_path)
    if deleted:
        print(f"[Cleanup] Removed {len(deleted)} expired items", flush=True)


class CleanupScheduler:
    """Runs cleanup on startup and every 60 minutes."""

    def __init__(self):
        self._timer = QTimer()
        self._timer.timeout.connect(run_cleanup)
        self._timer.start(60 * 60 * 1000)  # Every hour

        # Run immediately on creation
        run_cleanup()

    def stop(self):
        self._timer.stop()
