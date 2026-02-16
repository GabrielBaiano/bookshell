# bookshell

A CLI tool to manage books from Google Drive.

## Architecture

- `src/bookshell/main.py`: Typer CLI entry point.
- `src/bookshell/core/`: Application logic (Drive, Library, Reader).
- `src/bookshell/utils/`: Utility functions.

## Setup

1. Install dependencies: `pip install -e .`
2. Configure `.env` with your Google API credentials.
3. Run with: `bookshell --help`
