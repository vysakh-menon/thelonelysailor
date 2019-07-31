"""Provides the WSGI entry point for running the application
"""
from lsailor import create_app


application = create_app()

if __name__ == "__main__":
    application.run()