from app import create_app
from app.extensions import db
from app import models # Ensure all 40 models are discovered by Alembic

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        "db": db,
        "models": models
    }

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

