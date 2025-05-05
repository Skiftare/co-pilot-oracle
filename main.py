import os
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QDir
from ui.main_window import MainWindow

# Force X11 backend instead of Wayland
os.environ["QT_QPA_PLATFORM"] = "xcb"


def main():
    # Create the application
    app = QApplication(sys.argv)

    # Set up stylesheet (with error handling)
    try:
        style_file = QDir.current().filePath("resources/styles/light_aero_theme.qss")
        with open(style_file, "r") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print(f"Error loading stylesheet: {e}")

    # Create and show the main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()