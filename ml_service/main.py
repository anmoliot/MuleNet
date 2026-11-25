"""Compatibility entrypoint for the strict, artifact-backed internal service."""

from serving import create_app

app = create_app()
