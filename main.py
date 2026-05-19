"""History Clipboard — Windows 历史剪贴板管理软件"""
import sys
import ctypes
import datetime

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QScrollArea, QPushButton, QFrame, QToolTip,
)
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QFont, QPixmap, QPainter, QPen, QBrush, QColor, QPainterPath, QIcon, QFontDatabase

from src.database import init_db, upsert_item, get_all, delete_item, toggle_pin
from src.image_store import save_image, delete_images, get_thumbnail_bytes
from src.clipboard_monitor import ClipboardMonitor
from src.tray import setup_tray
from src.hotkey import register_hotkey, unregister_hotkey
from src.auto_start import enable as enable_auto_start, is_enabled as auto_start_enabled
from src.scheduler import CleanupScheduler, get_retention_days, set_retention_days


# ── Colors ────────────────────────────────────────────
PRIMARY = "#29B6F6"
PRIMARY_DARK = "#0288D1"
PRIMARY_LIGHT = "#E1F5FE"
BG = "#FAFAFA"
HEADER_BG = "#FFFFFF"
CARD_BG = "#FFFFFF"
INPUT_BG = "#F0F0F0"
BORDER = "#E8E8E8"

# Helper: QFont inheriting app's family (Outfit/Noto Sans SC) with custom size
def _font(size, weight=QFont.Weight.DemiBold):
    f = QFont()
    f.setPixelSize(size)
    f.setWeight(weight)
    return f
TEXT = "#212121"
TEXT_SECONDARY = "#757575"
TEXT_HINT = "#BDBDBD"
SCROLLBAR = "#D0D0D0"
SCROLLBAR_HOVER = "#B0B0B0"
DANGER_HOVER = "#FFEBEE"


# ── Pin icon ──────────────────────────────────────────
def _make_pin_icon(filled, color=None):
    pix = QPixmap(24, 24); pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(color) if color else QColor(PRIMARY if filled else TEXT_HINT)
    pen = QPen(c, 1.6); pen.setCapStyle(Qt.PenCapStyle.RoundCap); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    path = QPainterPath()
    path.moveTo(12, 2); path.cubicTo(6, 2, 5, 7, 5, 10)
    path.cubicTo(5, 14, 11, 21, 12, 22); path.cubicTo(13, 21, 19, 14, 19, 10)
    path.cubicTo(19, 7, 18, 2, 12, 2); path.closeSubpath()
    if filled:
        p.setBrush(QBrush(c)); p.drawPath(path)
        p.setBrush(QBrush(QColor("#FFFFFF"))); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(12, 9), 2, 2)
    else:
        p.setBrush(Qt.GlobalColor.transparent); p.drawPath(path)
        p.drawEllipse(QPointF(12, 10), 2.5, 2.5)
    p.end()
    return QIcon(pix)


def _make_top_icon(filled):
    """Pin-on-top icon — overlapping panels with dot. Distinct from card pin."""
    pix = QPixmap(24, 24); pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(PRIMARY if filled else TEXT_HINT)
    pen = QPen(c, 1.5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen); p.setBrush(Qt.GlobalColor.transparent)
    p.drawRoundedRect(7, 10, 12, 10, 2, 2)  # back panel
    p.drawRoundedRect(5, 6, 12, 10, 2, 2)   # front panel
    if filled:
        p.setBrush(QBrush(c))
    p.drawEllipse(QPointF(17, 5), 2.5, 2.5)  # dot indicator
    p.end()
    return QIcon(pix)


def _make_settings_icon():
    """Simple gear icon — line only."""
    pix = QPixmap(24, 24); pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(TEXT_HINT), 1.5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen); p.setBrush(Qt.GlobalColor.transparent)
    # Outer circle
    p.drawEllipse(QPointF(12, 12), 7, 7)
    # Inner circle
    p.drawEllipse(QPointF(12, 12), 3, 3)
    # Teeth (4 lines radiating)
    p.drawLine(12, 4, 12, 2); p.drawLine(12, 20, 12, 22)
    p.drawLine(4, 12, 2, 12); p.drawLine(20, 12, 22, 12)
    p.drawLine(6.3, 6.3, 5, 5); p.drawLine(17.7, 17.7, 19, 19)
    p.drawLine(17.7, 6.3, 19, 5); p.drawLine(6.3, 17.7, 5, 19)
    p.end()
    return QIcon(pix)


def _make_copy_icon(color=TEXT_HINT):
    """Simple copy icon — two overlapping squares, line only."""
    pix = QPixmap(24, 24); pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 1.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen); p.setBrush(Qt.GlobalColor.transparent)
    p.drawRoundedRect(8, 4, 12, 12, 2, 2)
    p.drawRoundedRect(5, 7, 12, 12, 2, 2)
    p.end()
    return QIcon(pix)


def _make_delete_icon(color=TEXT_HINT):
    """Simple trash icon — line only."""
    pix = QPixmap(24, 24); pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 1.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen); p.setBrush(Qt.GlobalColor.transparent)
    p.drawLine(6, 7, 18, 7)
    p.drawLine(9, 7, 9, 4); p.drawLine(15, 7, 15, 4)
    p.drawLine(9, 4, 12, 3); p.drawLine(15, 4, 12, 3)
    p.drawRoundedRect(7, 8, 10, 13, 1, 1)
    p.drawLine(10, 10, 10, 18); p.drawLine(14, 10, 14, 18)
    p.end()
    return QIcon(pix)


# ── MainWindow ────────────────────────────────────────
class MainWindow(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self._quitting = False
        self.setWindowTitle("History Clipboard")
        self.resize(440, 660)
        self.setMinimumSize(340, 420)
        self._items = []
        self._search_mode = False
        self._filter_type = "all"
        self._pinned_on_top = False
        # Set tooltip palette FIRST, before any widget creation
        from PySide6.QtGui import QPalette
        tp = QPalette()
        tp.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
        tp.setColor(QPalette.ColorRole.ToolTipText, QColor("#1D1D1F"))
        QToolTip.setPalette(tp)
        QToolTip.setFont(QFont("Times New Roman", 12))
        init_db()
        self._setup_ui()
        self._apply_styles()
        self._init_backend()
        self._load_items()
        print("[App] Ready", flush=True)

    # ── Styles ─────────────────────────────────────────

    def _apply_styles(self):
        # Window background

        # Window background
        self.setStyleSheet(f"background: {BG};")

        # Scroll
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{ background: transparent; width: 4px; margin: 0; }}
            QScrollBar::handle:vertical {{ background: {SCROLLBAR}; border-radius: 2px; min-height: 36px; }}
            QScrollBar::handle:vertical:hover {{ background: {SCROLLBAR_HOVER}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; border: none; }}
        """)

        # Header / Footer
        self._header.setStyleSheet(f"background: {HEADER_BG}; border-bottom: 1px solid {BORDER};")
        self._footer.setStyleSheet(f"background: {HEADER_BG}; border-top: 1px solid {BORDER};")

        # Search (scoped to objectName)
        self._search_wrap.setStyleSheet(f"""
            #{self._search_wrap.objectName()} {{ background: {INPUT_BG}; border: none; border-radius: 12px; }}
        """)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{ background: transparent; border: none; padding: 10px 0; color: {TEXT}; }}
            QLineEdit::placeholder {{ color: {TEXT_HINT}; }}
        """)

        # Header buttons
        self.pin_top_btn.setIcon(_make_top_icon(self._pinned_on_top))
        self.pin_top_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; border-radius: 8px; }}
            QPushButton:hover {{ background: {INPUT_BG}; }}
        """)

        # Labels
        self._title_lbl.setStyleSheet(f"font-family: 'Playfair Display'; color: {PRIMARY_DARK}; background: transparent; border: none;")
        self.header_count.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")
        self.status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")
        self._settings_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; border-radius: 8px; }}
            QPushButton:hover {{ background: {INPUT_BG}; }}
        """)
        # Empty state
        self._empty_icon.setStyleSheet(f"color: {TEXT_HINT}; background: transparent; border: none;")
        self._empty_text.setStyleSheet(f"color: {TEXT_HINT}; background: transparent; border: none;")
        # Search icon & clear
        self._search_icon_lbl.setStyleSheet(f"color: {TEXT_HINT}; background: transparent; border: none; font-size: 13px;")
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; color: {TEXT_HINT}; font-size: 12px; border-radius: 12px; }}
            QPushButton:hover {{ background: {BORDER}; }}
        """)
        # Card container
        self.card_container.setStyleSheet("background: transparent;")

        # Filter buttons
        for key, btn in self._filter_buttons.items():
            btn.setStyleSheet(self._filter_css(key, key == self._filter_type))

        # Re-render
        self._render_list()

    def _filter_css(self, key, active):
        if active:
            return f"""
                QPushButton {{ background: {PRIMARY}; color: white; border: none; border-radius: 15px; padding: 2px 16px; font-weight: 600; }}
            """
        return f"""
            QPushButton {{ background: {INPUT_BG}; color: {TEXT_SECONDARY}; border: none; border-radius: 15px; padding: 2px 16px; }}
            QPushButton:hover {{ color: {TEXT}; }}
        """

    # ── UI Setup ───────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self._header = QFrame(); self._header.setFixedHeight(48)
        h_layout = QHBoxLayout(self._header); h_layout.setContentsMargins(16, 0, 10, 0)
        self._title_lbl = QLabel("History Clipboard")
        self._title_lbl.setFont(_font(22, QFont.Weight.Normal))
        self._title_lbl.setStyleSheet(f"font-family: 'Playfair Display'; color: {PRIMARY_DARK}; background: transparent; border: none;")
        h_layout.addWidget(self._title_lbl); h_layout.addStretch()
        self.header_count = QLabel("0 条")
        self.header_count.setFont(_font(16))
        h_layout.addWidget(self.header_count); h_layout.addSpacing(6)
        self.pin_top_btn = QPushButton(); self.pin_top_btn.setFixedSize(34, 34)
        self.pin_top_btn.setIconSize(QPixmap(24, 24).size())
        self.pin_top_btn.setToolTip("窗口置顶")
        self.pin_top_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_top_btn.setStyleSheet(f"QPushButton {{ background: transparent; border: none; border-radius: 8px; }} QPushButton:hover {{ background: {INPUT_BG}; }}")
        self.pin_top_btn.clicked.connect(self._toggle_pin_on_top)
        h_layout.addWidget(self.pin_top_btn)
        layout.addWidget(self._header)

        # Body
        body = QVBoxLayout(); body.setContentsMargins(14, 12, 14, 0); body.setSpacing(10)

        self._search_wrap = QFrame()
        self._search_wrap.setObjectName("searchWrap")
        s_layout = QHBoxLayout(self._search_wrap); s_layout.setContentsMargins(14, 0, 6, 0); s_layout.setSpacing(8)
        self._search_icon_lbl = QLabel("🔍"); s_layout.addWidget(self._search_icon_lbl)
        self.search_input = QLineEdit(); self.search_input.setPlaceholderText("搜索历史记录...")
        self.search_input.setFont(_font(19))
        self.search_input.textChanged.connect(self._on_search)
        s_layout.addWidget(self.search_input, stretch=1)
        self._clear_btn = QPushButton("✕"); self._clear_btn.setFixedSize(24, 24)
        self._clear_btn.clicked.connect(lambda: self.search_input.clear())
        s_layout.addWidget(self._clear_btn)
        body.addWidget(self._search_wrap)

        # Filters
        filter_row = QHBoxLayout(); filter_row.setSpacing(8)
        self._filter_buttons = {}
        for key, label in [("all", "全部"), ("text", "文字"), ("image", "图片")]:
            btn = QPushButton(label); btn.setFont(_font(16)); btn.setFixedHeight(34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, k=key: self._on_filter(k))
            self._filter_buttons[key] = btn; filter_row.addWidget(btn)
        filter_row.addStretch()
        body.addLayout(filter_row)

        # Scroll
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.card_container = QWidget()
        self.card_layout = QVBoxLayout(self.card_container)
        self.card_layout.setContentsMargins(0, 4, 0, 4); self.card_layout.setSpacing(8)
        self.card_layout.addStretch()
        self.scroll.setWidget(self.card_container)
        body.addWidget(self.scroll, stretch=1)

        # Empty state
        self.empty_widget = QWidget()
        ev = QVBoxLayout(self.empty_widget); ev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_icon = QLabel("📋"); self._empty_icon.setFont(QFont("Segoe UI Emoji", 36))
        self._empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter); ev.addWidget(self._empty_icon)
        self._empty_text = QLabel("剪贴板历史为空\n\n复制任意文字或图片后\n内容会自动出现在这里")
        self._empty_text.setFont(_font(17))
        self._empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter); ev.addWidget(self._empty_text)
        body.addWidget(self.empty_widget)
        layout.addLayout(body, stretch=1)

        # Footer
        self._footer = QFrame(); self._footer.setFixedHeight(40)
        f_layout = QHBoxLayout(self._footer); f_layout.setContentsMargins(16, 0, 8, 0)
        _days = get_retention_days()
        _label = {1: "1 天", 2: "2 天", 5: "5 天", 15: "15 天", 30: "1 个月", 90: "3 个月"}.get(_days, f"{_days} 天")
        self.status_label = QLabel(f"保留 {_label}")
        self.status_label.setFont(_font(15))
        f_layout.addWidget(self.status_label); f_layout.addStretch()
        self._settings_btn = QPushButton(); self._settings_btn.setIcon(_make_settings_icon())
        self._settings_btn.setIconSize(QPixmap(24, 24).size()); self._settings_btn.setFixedSize(34, 34)
        self._settings_btn.setToolTip("设置")
        self._settings_btn.setStyleSheet(f"QPushButton {{ background: transparent; border: none; border-radius: 8px; }} QPushButton:hover {{ background: {INPUT_BG}; }}")
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.clicked.connect(self._show_settings)
        f_layout.addWidget(self._settings_btn)
        layout.addWidget(self._footer)

    # ── Backend ────────────────────────────────────────

    def _init_backend(self):
        self.monitor = ClipboardMonitor(QApplication.instance())
        self.monitor.captured.connect(self._on_captured)
        self._tray = setup_tray(self, self._app)
        self._hotkey_registered = False
        if not auto_start_enabled():
            enable_auto_start()
        self._scheduler = CleanupScheduler()

    def _load_items(self):
        items = get_all()
        self._items = self._apply_filter(items)
        self._render_list()

    def _apply_filter(self, items):
        if self._filter_type == "all":
            return items
        return [it for it in items if it["type"] == self._filter_type]

    def _on_captured(self, capture):
        item_type = capture["type"]; data_hash = capture["hash"]
        if item_type == "text":
            text = capture["data"]
            upsert_item("text", text, text[:200], None, None, data_hash)
        else:
            import uuid as _uuid
            file_id = str(_uuid.uuid4())
            img_path, thumb_path = save_image(file_id, capture["data"])
            item = upsert_item("image", None, None, img_path, thumb_path, data_hash)
            if item and item["image_path"] != img_path:
                delete_images(img_path, thumb_path)
        if not self._search_mode:
            self._load_items()

    # ── Search & Filter ────────────────────────────────

    def _on_search(self, text):
        if text.strip():
            self._search_mode = True
            from src.database import search as db_search
            items = db_search(text.strip())
        else:
            self._search_mode = False
            items = get_all()
        self._items = self._apply_filter(items)
        self._render_list()

    def _on_filter(self, filter_type):
        if filter_type == "all":
            self._filter_type = "all"
        elif self._filter_type == filter_type:
            self._filter_type = "all"
        else:
            self._filter_type = filter_type
        for key, btn in self._filter_buttons.items():
            btn.setStyleSheet(self._filter_css(key, key == self._filter_type))
        if self._search_mode:
            from src.database import search as db_search
            items = db_search(self.search_input.text().strip())
        else:
            items = get_all()
        self._items = self._apply_filter(items)
        self._render_list()

    # ── Render ─────────────────────────────────────────

    def _render_list(self):
        while self.card_layout.count() > 1:
            widget = self.card_layout.takeAt(0)
            if widget.widget():
                widget.widget().deleteLater()
        has = len(self._items) > 0
        self.empty_widget.setVisible(not has)
        self.scroll.setVisible(has)
        pinned_ids = {it["id"] for it in self._items if it["pinned"]}
        now = datetime.datetime.now()
        for item in self._items:
            card = self._build_card(item, item["id"] in pinned_ids, now)
            self.card_layout.insertWidget(self.card_layout.count() - 1, card)
        self.header_count.setText(f"{len(self._items)} 条记录")
        _days = get_retention_days()
        _label = {1: "1 天", 2: "2 天", 5: "5 天", 15: "15 天", 30: "1 个月", 90: "3 个月"}.get(_days, f"{_days} 天")
        self.status_label.setText(f"保留 {_label}")

    def _build_card(self, item, is_pinned, now):
        card = QFrame()
        card.setFixedHeight(88)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        cid = f"c_{item['id'][:8]}"
        card.setObjectName(cid)
        card_bg = "#B3E5FC" if is_pinned else CARD_BG
        card.setStyleSheet(f"""
            #{cid} {{ background: {card_bg}; border: 1px solid {BORDER}; border-radius: 12px; }}
            #{cid}:hover {{ background: {PRIMARY_LIGHT}; }}
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 8, 8); layout.setSpacing(10)

        if item["type"] == "text":
            preview = (item["text_preview"] or item["text_content"] or "").replace("\n", " ")[:110]
            content = QLabel(preview)
            content.setFont(_font(16))
            content.setStyleSheet(f"color: {TEXT}; background: transparent; border: none;")
            content.setWordWrap(True)
        else:
            content = QLabel()
            raw = get_thumbnail_bytes(item["thumbnail_path"])
            if raw:
                pix = QPixmap(); pix.loadFromData(raw)
                pix = pix.scaledToHeight(58, Qt.TransformationMode.SmoothTransformation)
                content.setPixmap(pix)
            else:
                content.setText("🖼"); content.setFont(QFont("Segoe UI Emoji", 18))
                content.setAlignment(Qt.AlignmentFlag.AlignCenter)
            content.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(content, stretch=1)

        # Meta
        meta = QHBoxLayout(); meta.setSpacing(8)
        dt = datetime.datetime.fromtimestamp(item["created_at"]); diff = now - dt
        if diff.seconds < 60: ts = "刚刚"
        elif diff.seconds < 3600: ts = f"{diff.seconds // 60} 分钟前"
        elif diff.days < 1: ts = dt.strftime("%H:%M")
        elif diff.days < 7: ts = f"{diff.days} 天前"
        else: ts = dt.strftime("%m/%d")
        tl = QLabel(ts); tl.setFont(_font(15))
        tl.setStyleSheet(f"color: {TEXT_HINT}; background: transparent; border: none;")
        tl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        tl.setMinimumWidth(65)
        meta.addWidget(tl)

        class _HoverIconButton(QPushButton):
            """Button that swaps icon to a darker version on hover, no background change."""
            def __init__(self, icon_normal, icon_hover, handler):
                super().__init__()
                self._icon_n = icon_normal; self._icon_h = icon_hover
                self.setIcon(icon_normal); self.setIconSize(QPixmap(24, 24).size())
                self.setFixedSize(34, 34); self.setCursor(Qt.CursorShape.PointingHandCursor)
                self.setStyleSheet("QPushButton { background: transparent; border: none; border-radius: 8px; }")
                self.clicked.connect(lambda checked=False: handler())

            def enterEvent(self, e):
                self.setIcon(self._icon_h); super().enterEvent(e)

            def leaveEvent(self, e):
                self.setIcon(self._icon_n); super().leaveEvent(e)

        br2 = QHBoxLayout(); br2.setSpacing(6)
        br2.addWidget(_HoverIconButton(_make_pin_icon(False), _make_pin_icon(False, TEXT_SECONDARY),
                        lambda iid=item["id"]: self._on_toggle_pin(iid)))
        br2.addWidget(_HoverIconButton(_make_copy_icon(TEXT_HINT), _make_copy_icon(TEXT_SECONDARY),
                        lambda iid=item["id"]: self._on_copy(iid)))
        br2.addWidget(_HoverIconButton(_make_delete_icon(TEXT_HINT), _make_delete_icon(TEXT_SECONDARY),
                        lambda iid=item["id"]: self._on_delete(iid)))

        meta.addLayout(br2)
        mw = QWidget(); mw.setStyleSheet("background: transparent; border: none;")
        mw.setLayout(meta); mw.setMinimumWidth(180)
        layout.addWidget(mw)
        return card

    # ── Actions ────────────────────────────────────────

    def _show_settings(self):
        from PySide6.QtWidgets import QDialog, QComboBox
        dlg = QDialog(self); dlg.setWindowTitle("设置"); dlg.setFixedSize(300, 160)
        dlg.setStyleSheet(f"""
            QDialog {{ background: {CARD_BG}; }}
            QLabel {{ color: {TEXT}; font-size: 13px; background: transparent; border: none; }}
            QComboBox {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 8px; padding: 8px 12px; color: {TEXT}; font-size: 13px; }}
            QComboBox:hover {{ border-color: {PRIMARY}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
        """)
        l = QVBoxLayout(dlg); l.setContentsMargins(20, 20, 20, 20); l.setSpacing(14)
        l.addWidget(QLabel("历史记录保留天数"))
        RETENTION_OPTIONS = {
            "1 天": 1, "2 天": 2, "5 天": 5, "15 天": 15,
            "1 个月": 30, "3 个月": 90,
        }
        combo = QComboBox(); combo.addItems(list(RETENTION_OPTIONS.keys()))
        current = get_retention_days()
        label_for_current = {v: k for k, v in RETENTION_OPTIONS.items()}.get(current, "3 天")
        combo.setCurrentText(label_for_current)
        l.addWidget(combo)
        save_btn = QPushButton("保存"); save_btn.setFont(_font(17))
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{ background: {PRIMARY}; color: white; border: none; border-radius: 10px; padding: 10px 0; font-weight: 600; }}
            QPushButton:hover {{ background: {PRIMARY_DARK}; }}
        """)
        def on_save():
            days = RETENTION_OPTIONS[combo.currentText()]
            set_retention_days(days)
            self.status_label.setText(f"保留 {combo.currentText()}")
            from src.scheduler import run_cleanup; run_cleanup()
            dlg.accept()
        save_btn.clicked.connect(on_save)
        l.addWidget(save_btn)
        dlg.exec()

    def _on_toggle_pin(self, item_id):
        toggle_pin(item_id); self._load_items()

    def _on_copy(self, item_id):
        item = next((it for it in self._items if it["id"] == item_id), None)
        if not item: return
        clipboard = QApplication.instance().clipboard()
        if item["type"] == "text":
            clipboard.setText(item["text_content"])
        else:
            from src.image_store import get_image_path
            path = get_image_path(item["image_path"])
            if path: clipboard.setPixmap(QPixmap(path))
        self.monitor.suppress_next()

    def _on_delete(self, item_id):
        item = next((it for it in self._items if it["id"] == item_id), None)
        if item and item["type"] == "image":
            delete_images(item["image_path"], item["thumbnail_path"])
        delete_item(item_id); self._load_items()

    # ── Pin-on-top ─────────────────────────────────────

    def _toggle_pin_on_top(self):
        self._pinned_on_top = not self._pinned_on_top
        self.pin_top_btn.setIcon(_make_top_icon(self._pinned_on_top))
        self._apply_always_on_top()

    def _apply_always_on_top(self):
        from ctypes import wintypes
        u32 = ctypes.windll.user32
        u32.SetWindowPos.restype = wintypes.BOOL
        u32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        h = wintypes.HWND(int(self.winId()))
        f = wintypes.HWND(-1) if self._pinned_on_top else wintypes.HWND(-2)
        u32.SetWindowPos(h, f, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0010)

    # ── Window events ──────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        if not self._hotkey_registered and self.winId():
            self._hotkey_registered = register_hotkey(int(self.winId()), self._on_hotkey)

    def nativeEvent(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312:
                self._on_hotkey(); return True, 0
        return False, 0

    def _on_hotkey(self):
        if self.isVisible(): self.hide()
        else: self.show(); self.raise_(); self.activateWindow()

    def closeEvent(self, event):
        if self._quitting:
            unregister_hotkey(int(self.winId())); self.monitor.stop()
            event.accept()
        else:
            self.hide(); event.ignore()


def main():
    print("[App] Starting History Clipboard...")
    app = QApplication(sys.argv)
    app.setApplicationName("History Clipboard")

    # Load custom fonts
    import os as _os
    _font_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "assets", "fonts")
    for _fn in _os.listdir(_font_dir):
        if _fn.endswith(".ttf"):
            QFontDatabase.addApplicationFont(_os.path.join(_font_dir, _fn))
    print("[Font] Custom fonts loaded", flush=True)

    # Default: Outfit for numbers/Latin, Noto Sans SC for Chinese
    _base = QFont()
    _base.setFamilies(["Segoe UI", "Microsoft YaHei"])
    _base.setPixelSize(17)
    _base.setWeight(QFont.Weight.DemiBold)
    app.setFont(_base)
    # Force tooltip colors via app palette
    from PySide6.QtGui import QPalette
    ap = QPalette()
    ap.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
    ap.setColor(QPalette.ColorRole.ToolTipText, QColor("#1D1D1F"))
    app.setPalette(ap)
    window = MainWindow(app)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
