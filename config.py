import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "debug-event-secret-2024-xK9mP2")

    # MongoDB Atlas URI — set via environment variable in production
    # Format: mongodb+srv://user:pass@cluster.mongodb.net/debug_event?retryWrites=true&w=majority
    MONGODB_URI = os.environ.get(
        "MONGODB_URI",
        "mongodb://localhost:27017/debug_event"   # local fallback for dev
    )

    # Hardcoded admin credentials
    ADMIN_USERNAME = "Admin"
    ADMIN_PASSWORD = "admin123"
