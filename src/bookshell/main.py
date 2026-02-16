import os
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from bookshell.core.drive_logic import get_or_create_folder, list_drive_files
from bookshell.core.library import list_local_files
from bookshell.core import database_manager

app = typer.Typer()
console = Console()

@app.command()
def list():
    """Display all books in your local folder and on Google Drive."""
    console.print(Panel("[bold blue]Bookshell Library[/bold blue]"))
    
    # 1. Local Files
    local_books = list_local_files()
    
    # 2. Drive Files
    with console.status("[bold green]Checking Google Drive...") as status:
        drive_books = list_drive_files()

    table = Table(title="Your Books", show_header=True, header_style="bold magenta")
    table.add_column("Source", style="dim")
    table.add_column("Title")
    table.add_column("Size (MB)", justify="right")

    # Add Local Books
    for book in local_books:
        table.add_row(
            "💻 Local", 
            book["name"], 
            f"{book['size'] / (1024*1024):.2f}"
        )

    # Add Drive Books
    # Identify which drive books are also local to avoid duplicates if needed, 
    # but for now let's just show them all separately to see the "sync status"
    for book in drive_books:
        # Check if already in local
        is_local = any(lb["name"] == book["name"] for lb in local_books)
        source = "☁️ Drive"
        if is_local:
            source = "✅ Synced"
            
        table.add_row(
            source,
            book["name"],
            f"{int(book.get('size', 0)) / (1024*1024):.2f}" if book.get('size') else "N/A"
        )

    if not local_books and not drive_books:
        console.print("[yellow]Your library is empty. Add some PDF or EPUB files![/yellow]")
    else:
        console.print(table)

@app.command()
def setup():
    """Complete initial setup flow."""
    console.print(Panel("[bold blue]Welcome to Bookshell[/bold blue]", subtitle="Initial Setup"))
    
    # Initialize Database
    database_manager.init_db()

    # 1. Configuration Type
    from InquirerPy import inquirer
    
    setup_type = inquirer.select(
        message="How would you like to configure Bookshell?",
        choices=[
            {"name": "Standard (recommended: ~/Bookshell)", "value": "default"},
            {"name": "Manual (custom install path)", "value": "manual"},
        ],
        default="default",
    ).execute()

    if setup_type == "default":
        folder_path = Path.home() / "Bookshell_Library"
        console.print(f"Using default path: [cyan]{folder_path}[/cyan]")
    else:
        folder_input = console.input("[bold]Enter the path where you want to store your books:[/bold] ")
        folder_path = Path(folder_input).expanduser().resolve()

    # Create folder if it doesn't exist
    if not folder_path.exists():
        if Confirm.ask(f"Folder [cyan]{folder_path}[/cyan] does not exist. Create it?"):
            folder_path.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]Folder created successfully![/green]")
        else:
            console.print("[red]Setup cancelled. We need a folder to continue.[/red]")
            raise typer.Exit()
    else:
        console.print(f"[green]Using existing folder: {folder_path}[/green]")

    # Save local path to DB
    database_manager.save_config("local_path", folder_path)

    # 2. Google Drive Configuration
    console.print("\n[yellow]Step 2: Google Drive Configuration[/yellow]")
    console.print("We will now link your Google account to Bookshell.")
    
    from bookshell.core.drive import get_drive_service
    console.print("[dim]Connecting to Google Drive...[/dim]")
    creds = get_drive_service()
    
    if creds:
        console.print("Logged in successfully! [green]✔[/green]")
    else:
        console.print("[red]Authentication failed. Please check your credentials.json file.[/red]")
        raise typer.Exit()
    
    # 3. Drive Folder Verification
    console.print("\n[yellow]Step 3: Cloud Verification[/yellow]")
    console.print("Verifying 'Bookshell_Files' folder on your Google Drive...")
    folder_id = get_or_create_folder("Bookshell_Files")
    
    if folder_id:
        database_manager.save_config("root_folder_id", folder_id)
        console.print(f"Drive path secured! [green]✔[/green]")
    else:
        console.print("[red]Failed to verify Drive folder.[/red]")
        raise typer.Exit()
    
    # 4. Final Instructions
    instructions = """
[bold green]Registration Complete![/bold green]

[bold]How to use Bookshell:[/bold]
1. [blue]Automatic:[/blue] Just drop any PDF/EPUB in your local folder.
2. [blue]Manual:[/blue] Use the command [bold yellow]bookshell push "path/to/book.pdf"[/bold yellow].
3. [blue]Cloud:[/blue] Add books directly to the 'Bookshell' folder in your Google Drive.

Use [bold]bookshell --help[/bold] to see all available commands.
    """
    console.print(Panel(instructions, title="[bold green]Ready to go![/bold green]", border_style="green"))

@app.command()
def push(path: str):
    """Upload a local book to Google Drive."""
    console.print(f"Uploading [cyan]{path}[/cyan] to Google Drive...")
    # Logic: Upload -> Get Link -> Save to Local DB

if __name__ == "__main__":
    app()