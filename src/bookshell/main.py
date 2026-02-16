import typer

app = typer.Typer(help="Bookshell - Direct access to your Google Drive library")

@app.command()
def list():
    """List all books in the library."""
    typer.echo("Listing books...")

@app.command()
def open(book_id: str):
    """Open a book by its ID."""
    typer.echo(f"Opening book {book_id}...")

if __name__ == "__main__":
    app()
