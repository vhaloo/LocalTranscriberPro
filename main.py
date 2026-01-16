import os
import ssl
import certifi
from src.utils import setup_logging
from src.gui import TranscriberApp

# Fix for SSL Certificate errors on Mac/Windows
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# Create a default SSL context that uses certifi
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

if __name__ == "__main__":
    setup_logging()
    app = TranscriberApp()
    app.mainloop()