"""Application entry point. Run from the project root with python -m flask --app app run."""

from src.presentation.web import create_app

app = create_app()
