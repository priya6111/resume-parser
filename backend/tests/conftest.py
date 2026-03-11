import os
import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app()
    app.config.update(
        TESTING=True,
        UPLOAD_FOLDER=str(tmp_path / "uploads"),
    )
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    with app.test_client() as test_client:
        yield test_client
