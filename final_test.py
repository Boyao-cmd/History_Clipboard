import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea
from PySide6.QtGui import QFont, QPixmap, QColor
from PySide6.QtCore import Qt

app = QApplication(sys.argv)
app.setFont(QFont("Microsoft YaHei", 10))
app.setStyle("Fusion")  
app.setStyleSheet("QToolTip { background: #FFFFFF; color: #1D1D1F; border: 1px solid #CCC; padding: 4px 8px; }")

win = QWidget(); win.resize(400, 400)
win.setStyleSheet("background: #FAFAFA;")
layout = QVBoxLayout(win)

# Card A: TEXT card (like text clipboard item)
cardA = QFrame()
cardA.setObjectName("cardA")
cardA.setStyleSheet("#cardA { background: white; border: 1px solid #E8E8E8; border-radius: 12px; } #cardA:hover { border-color: #29B6F6; }")
al = QHBoxLayout(cardA); al.setContentsMargins(12,8,8,8)
al.addWidget(QLabel("这是一段文字预览..."), stretch=1)
ba = QPushButton("📋"); ba.setFixedSize(24,24); ba.setToolTip("文字卡tooltip")
ba.setStyleSheet("QPushButton { background: transparent; border: none; border-radius: 4px; font-size: 12px; } QPushButton:hover { background: #E1F5FE; }")
al.addWidget(ba)
layout.addWidget(cardA)

# Card B: IMAGE card (with QPixmap like our image cards)
cardB = QFrame()
cardB.setObjectName("cardB")
cardB.setStyleSheet("#cardB { background: white; border: 1px solid #E8E8E8; border-radius: 12px; } #cardB:hover { border-color: #29B6F6; }")
bl = QHBoxLayout(cardB); bl.setContentsMargins(12,8,8,8)
# Create a colored pixmap to simulate an image thumbnail
pix = QPixmap(100, 50); pix.fill(QColor("#29B6F6"))
img_lbl = QLabel(); img_lbl.setPixmap(pix.scaledToHeight(40, Qt.TransformationMode.SmoothTransformation))
img_lbl.setStyleSheet("background: transparent; border: none;")
bl.addWidget(img_lbl, stretch=1)
bb = QPushButton("📋"); bb.setFixedSize(24,24); bb.setToolTip("图片卡tooltip")
bb.setStyleSheet("QPushButton { background: transparent; border: none; border-radius: 4px; font-size: 12px; } QPushButton:hover { background: #E1F5FE; }")
bl.addWidget(bb)
layout.addWidget(cardB)

layout.addStretch()
win.show()
sys.exit(app.exec())
