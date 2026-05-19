import sys
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import QTimer

app = QApplication(sys.argv)
label = QLabel("Test")
label.show()

count = [0]
def tick():
    count[0] += 1
    print(f"Tick #{count[0]}", flush=True)

timer = QTimer()
timer.timeout.connect(tick)
timer.start(2000)
print("Timer started, waiting for ticks...", flush=True)

sys.exit(app.exec())
