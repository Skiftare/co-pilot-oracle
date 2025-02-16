import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import CryptoAnalyzerGUI

def main():
    app = QApplication(sys.argv)
    window = CryptoAnalyzerGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 