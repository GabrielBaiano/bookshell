import os
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from bookshell.core.drive_logic import get_or_create_folder
from bookshell.core import database_manager

app = typer.Typer()
console = Console()

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
        folder_path = Path.home() / "Bookshell"
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
    # This will trigger get_drive_service during folder check
    
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