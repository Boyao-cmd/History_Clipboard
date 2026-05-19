"""Clipboard monitor — periodic polling with self-capture prevention."""
import hashlib
import os

from PySide6.QtCore import QObject, Signal, QTimer, QBuffer, QIODevice


IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp', '.ico'}


class ClipboardMonitor(QObject):
    """
    Polls clipboard every 4 seconds. Image wins over text.
    Uses hash-based dedup via raw clipboard mimeData bytes.
    """

    captured = Signal(dict)

    def __init__(self, app):
        super().__init__()
        self.clipboard = app.clipboard()
        self._last_text_hash = None
        self._last_image_hash = None
        self._poll_count = 0
        self._suppress = False  # When set, _poll updates hashes but doesn't emit

        self._timer = QTimer()
        self._timer.timeout.connect(self._poll)
        self._timer.start(2000)

        self._poll()
        print("[Clipboard] Monitor started (poll every 2s)", flush=True)

    def suppress_next(self):
        """
        Call after writing to clipboard from our own UI.
        Next poll will update hashes silently without emitting a capture.
        """
        self._suppress = True

    def _poll(self):
        self._poll_count += 1
        try:
            mime = self.clipboard.mimeData()
            has_img = mime.hasImage()
            text = self.clipboard.text()

            if self._poll_count <= 5:
                print(f"[Clipboard] Poll #{self._poll_count}: hasImage={has_img}, "
                      f"hasText={bool(text)}{', SUPPRESS' if self._suppress else ''}",
                      flush=True)

            # ── Image ──
            if has_img:
                raw = (mime.data("image/png")
                       or mime.data("image/bmp")
                       or mime.data("image/jpeg")
                       or mime.data("application/x-qt-image"))
                if raw and raw.size() > 0:
                    data_hash = hashlib.sha256(raw.data()).hexdigest()
                else:
                    img = self.clipboard.image()
                    if img and not img.isNull():
                        data_hash = self._hash_qimage(img)
                    else:
                        return

                if data_hash == self._last_image_hash:
                    return
                self._last_image_hash = data_hash

                if self._suppress:
                    self._suppress = False
                    print(f"[Clipboard] Poll #{self._poll_count}: self-write suppressed", flush=True)
                    return

                img = self.clipboard.image()
                if img and not img.isNull():
                    print(f"[Clipboard] CAPTURE IMAGE ({data_hash[:8]}...)", flush=True)
                    self.captured.emit({"type": "image", "data": img, "hash": data_hash})
                return

            # ── Text ──
            if text and len(text.strip()) > 0:
                stripped = text.strip()

                if self._looks_like_image_path(stripped):
                    from PySide6.QtGui import QImage
                    img = QImage(stripped)
                    if not img.isNull():
                        data_hash = self._hash_qimage(img)
                        if data_hash != self._last_image_hash:
                            self._last_image_hash = data_hash
                            if self._suppress:
                                self._suppress = False
                                return
                            print(f"[Clipboard] CAPTURE IMAGE from file ({data_hash[:8]}...)", flush=True)
                            self.captured.emit({"type": "image", "data": img, "hash": data_hash})
                    else:
                        print(f"[Clipboard] Skipped file path: \"{stripped[:60]}\"", flush=True)
                    return

                data_hash = hashlib.sha256(
                    text.encode("utf-8", errors="replace")
                ).hexdigest()
                if data_hash == self._last_text_hash:
                    return
                self._last_text_hash = data_hash

                if self._suppress:
                    self._suppress = False
                    print(f"[Clipboard] Poll #{self._poll_count}: self-write suppressed", flush=True)
                    return

                preview = text[:80].replace("\n", " ")
                print(f"[Clipboard] CAPTURE TEXT: \"{preview}\"", flush=True)
                self.captured.emit({"type": "text", "data": text, "hash": data_hash})

        except Exception as e:
            import traceback
            self._suppress = False
            print(f"[Clipboard] Error: {e}", flush=True)
            traceback.print_exc()

    def _looks_like_image_path(self, text):
        ext = os.path.splitext(text)[1].lower()
        return ext in IMAGE_EXTENSIONS

    def _hash_qimage(self, img):
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "PNG")
        data = buf.data().data()
        buf.close()
        return hashlib.sha256(data).hexdigest()

    def stop(self):
        self._timer.stop()
