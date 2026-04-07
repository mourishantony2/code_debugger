import mongoengine as me
from flask import Flask

# Load .env file (MONGODB_URI, SECRET_KEY, etc.)
from dotenv import load_dotenv
load_dotenv()

from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Connect to MongoDB (Atlas or local)
    me.connect(host=Config.MONGODB_URI)

    with app.app_context():
        from models import Language

        # Seed default languages on first run
        if Language.objects.count() == 0:
            for lang_name in ["Python", "C"]:
                Language(name=lang_name).save()

    # Register Blueprints
    from routes.auth  import auth_bp
    from routes.admin import admin_bp
    from routes.exam  import exam_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(exam_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
