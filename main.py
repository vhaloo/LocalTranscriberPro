from src.utils import setup_logging
from src.gui import TranscriberApp

if __name__ == "__main__":
    setup_logging()
    app = TranscriberApp()
    app.mainloop()
