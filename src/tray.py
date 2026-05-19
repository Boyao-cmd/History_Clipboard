"""System tray icon for History Clipboard."""
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction
from PySide6.QtCore import Qt


def create_tray_icon():
    """Generate a simple clipboard tray icon programmatically."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Light blue rounded rectangle
    painter.setBrush(QColor("#29B6F6"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 2, 24, 28, 4, 4)
    # White clipboard lines
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawRoundedRect(8, 6, 8, 2, 1, 1)
    painter.drawRoundedRect(8, 10, 8, 2, 1, 1)
    painter.drawRoundedRect(8, 14, 5, 2, 1, 1)
    painter.end()
    return QIcon(pix)


def setup_tray(window, app):
    """Create system tray with context menu. Returns the tray icon."""
    tray = QSystemTrayIcon()
    tray.setIcon(create_tray_icon())
    tray.setToolTip("History Clipboard — 历史剪贴板")

    menu = QMenu()
    menu.addAction("显示窗口", lambda: _show_window(window))
    menu.addSeparator()
    menu.addAction("退出", lambda: _quit_app(app, window))

    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: _on_tray_activated(reason, window))
    tray.show()

    return tray


def _show_window(window):
    window.show()
    window.raise_()
    window.activateWindow()


def _quit_app(app, window):
    window._quitting = True
    app.quit()


def _on_tray_activated(reason, window):
    if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
        if window.isVisible():
            window.hide()
        else:
            _show_window(window)
