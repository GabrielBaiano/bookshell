import os
import shutil
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from InquirerPy import inquirer
from bookshell.core.drive_logic import get_or_create_folder, list_drive_files, upload_book, update_description, move_file, get_or_create_subfolder, download_book, set_file_visibility
from bookshell.core.library import list_local_files
from bookshell.core import database_manager

app = typer.Typer()
console = Console()

@app.command()
def list(category: str = typer.Option(None, "--category", "-c", help="Filter by category")):
    """Display all books in your local folder and on Google Drive."""
    console.print(Panel("[bold blue]Bookshell Library[/bold blue]", expand=False))
    
    # 1. Fetch data
    local_books = list_local_files()
    with console.status("[bold green]Checking Google Drive...") as status:
        drive_books = list_drive_files()

    # 2. Merge logic
    library = {}
    for b in local_books:
        library[b["name"]] = {
            "local": True, 
            "drive": False, 
            "size": b["size"], 
            "cat_local": b.get("category"),
            "cat_drive": None,
            "status": "new"
        }
    
    for b in drive_books:
        name = b["name"]
        size = int(b.get('size', 0))
        b_cat = b.get('category')
        
        # Parse status from description
        description = b.get('description', '')
        status_code = "new"
        if description:
            if '[reading]' in description: status_code = "reading"
            elif '[finished]' in description: status_code = "finished"

        if name in library:
            library[name]["drive"] = True
            library[name]["cat_drive"] = b_cat
            library[name]["status"] = status_code
        else:
            library[name] = {
                "local": False, 
                "drive": True, 
                "size": size, 
                "cat_local": None,
                "cat_drive": b_cat,
                "status": status_code
            }

    # 2.5 Filtering
    if category:
        c_lower = category.lower()
        library = {n: info for n, info in library.items() 
                   if (info["cat_local"] and info["cat_local"].lower() == c_lower) or
                      (info["cat_drive"] and info["cat_drive"].lower() == c_lower)}

    if not library:
        if category:
            console.print(f"[yellow]No books found in category '{category}'.[/yellow]")
        else:
            console.print("[yellow]Your library is empty. Add some PDF or EPUB files![/yellow]")
        return

    # 3. Render Minimalist List
    for name, info in sorted(library.items()):
        if info["local"] and info["drive"]:
            sync_icon = "[bold green][✨ Synced][/bold green]"
        elif info["local"]:
            sync_icon = "[bold blue][📂 Local ][/bold blue]"
        else:
            sync_icon = "[bold cyan][☁️ Drive ][/bold cyan]"
        
        # Status Text
        status_map = {
            "reading": "[bold yellow][ Reading  ][/bold yellow]",
            "finished": "[bold green][ Finished ][/bold green]",
            "new": "[dim][ Pending  ][/dim]"
        }
        status_text = status_map.get(info["status"], "[dim][ Pending  ][/dim]")

        display_cat = info["cat_local"] or info["cat_drive"]
        size_mb = info["size"] / (1024 * 1024)
        cat_str = f"[bold magenta][{display_cat:^9}][/bold magenta]" if display_cat else "[dim][ General ][/dim]"
        
        console.print(f"{sync_icon} {status_text} {cat_str} [dim][{size_mb:5.2f} MB][/dim] {name}")

@app.command()
def mark(book_name: str, status: str = typer.Option(..., "--status", "-s", help="Status: reading, finished, new")):
    """Update the reading status of a book."""
    status = status.lower()
    if status not in ['reading', 'finished', 'new']:
        console.print("[red]Invalid status. Use: reading, finished, or new.[/red]")
        raise typer.Exit(1)
        
    drive_books = list_drive_files()
    target_book = next((b for b in drive_books if b['name'] == book_name), None)
    
    if not target_book:
        console.print(f"[red]Book '{book_name}' not found on Drive. Please push it first.[/red]")
        raise typer.Exit(1)
        
    new_desc = f"[{status}] Updated via Bookshell"
    update_description(target_book['id'], new_desc)
    console.print(f"Status for [bold]{book_name}[/bold] updated to [bold blue]{status}[/bold blue]! [green]✔[/green]")

def format_size(size_bytes):
    # Helper to format bytes to MB/KB
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    return f"{size_bytes} B"

@app.command()
def pull(
    book_name: str = typer.Argument(None, help="Name of the book to download"),
    all: bool = typer.Option(False, "--all", "-a", help="Download all books from Drive that are missing locally")
):
    """Download books from Google Drive to your local library."""
    local_root = Path(database_manager.get_config("local_path"))
    
    if all:
        # Bulk Pull Logic
        console.print("[bold cyan]Checking for missing files...[/bold cyan]")
        drive_books = list_drive_files()
        local_files = list_local_files()
        local_names = {f['name'] for f in local_files}
        
        to_download = [b for b in drive_books if b['name'] not in local_names]
        
        if not to_download:
            console.print("[green]All Drive books are already downloaded! ✨[/green]")
            return

        total_size = sum(int(b.get('size', 0)) for b in to_download)
        count = len(to_download)
        
        console.print(f"\n[bold]Found {count} files to download:[/bold]")
        for b in to_download[:5]: # Show first 5
             console.print(f" - {b['name']}")
        if count > 5: console.print(f" ... and {count - 5} more.")
        
        formatted_size = format_size(total_size)
        if not Confirm.ask(f"\n[bold yellow][?][/bold yellow] Do you want to download {count} files ({formatted_size})?"):
            console.print("[red]Aborted.[/red]")
            raise typer.Exit()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task(f"[cyan]Downloading {count} files...[/cyan]", total=count)
            
            for book in to_download:
                category = book.get('category')
                target_dir = local_root / category if category else local_root
                target_dir.mkdir(parents=True, exist_ok=True)
                target_path = target_dir / book['name']
                
                success = download_book(book['id'], str(target_path))
                if success:
                    database_manager.save_book(
                        title=book['name'],
                        drive_id=book['id'],
                        local_path=str(target_path),
                        category=category
                    )
                progress.advance(task)
        
        console.print(f"[green]Successfully downloaded {count} files! ✔[/green]")
        return

    # Single File Pull Logic
    if not book_name:
         console.print("[red]Please provide a book name or use --all.[/red]")
         raise typer.Exit(1)

    drive_books = list_drive_files()
    target_book = next((b for b in drive_books if b['name'] == book_name), None)
    
    if not target_book:
        console.print(f"[red]Book '{book_name}' not found on Drive.[/red]")
        raise typer.Exit(1)
        
    category = target_book.get('category')
    target_dir = local_root / category if category else local_root
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / book_name
    
    if target_path.exists():
        console.print(f"[yellow]File '{book_name}' already exists locally.[/yellow]")
        return

    console.print(f"Downloading [bold]{book_name}[/bold]...")
    success = download_book(target_book['id'], str(target_path))
    
    if success:
         database_manager.save_book(
            title=book_name,
            drive_id=target_book['id'],
            local_path=str(target_path),
            category=category
        )
         console.print(f"[green]Downloaded successfully to {target_path} ✔[/green]")
    else:
         console.print("[red]Download failed.[/red]")


def _push_single_file(path: Path, category: str = None):
    # Core logic for pushing a single file
    
    # Auto-detect category from local folder if not provided
    if not category:
        try:
            local_root = Path(database_manager.get_config("local_path"))
            relative = path.relative_to(local_root)
            if len(relative.parts) > 1:
                category = relative.parts[0]
        except (ValueError, TypeError):
            pass

    console.print(Panel(f"[bold blue]Pushing:[/bold blue] {path.name}", expand=False))
    if category:
        console.print(f"Category: [bold magenta]{category}[/bold magenta]")

    # Check for existing file on Drive (Conflict Resolution)
    drive_books = list_drive_files()
    existing_files = [b for b in drive_books if b['name'] == path.name]
    
    existing_file = None
    if len(existing_files) > 1:
        console.print(f"\n[bold red]Duplicate Conflict:[/bold red] Found {len(existing_files)} copies of '{path.name}' on Drive.")
        choices = []
        for i, f in enumerate(existing_files):
            cat = f.get('category') or 'General'
            choices.append({"name": f"{i+1}. {cat} (ID: ...{f['id'][-4:]})", "value": f})
        
        choices.append({"name": "Skip this file", "value": "skip"})
        
        selected = inquirer.select(
            message="Which Drive file is the correct version to sync with?",
            choices=choices,
        ).execute()
        
        if selected == 'skip':
            console.print("[yellow]Skipping duplicate resolution.[/yellow]")
            return
        existing_file = selected
    elif existing_files:
        existing_file = existing_files[0]

    if existing_file:
        drive_cat = existing_file.get('category')
        
        # strict equality check for category (None vs None, or str vs str)
        cats_match = (category is None and drive_cat is None) or \
                     (category and drive_cat and category.lower() == drive_cat.lower())

        if not cats_match:
            console.print(f"\n[bold red]Conflict Detected:[/bold red] '{path.name}'")
            console.print(f"Drive Category: [cyan]{drive_cat or 'General'}[/cyan]")
            console.print(f"Local Category: [magenta]{category or 'General'}[/magenta]")
            
            choice = inquirer.select(
                message="How do you want to resolve this?",
                choices=[
                    {"name": f"Use Local (Move to {category or 'General'})", "value": "local"},
                    {"name": f"Use Drive (Keep in {drive_cat or 'General'})", "value": "drive"},
                    {"name": "Skip this file", "value": "skip"},
                ],
            ).execute()
            
            if choice == 'skip':
                console.print("[yellow]Skipped.[/yellow]")
                return
            elif choice == 'local':
                # Move file on Drive to match local Category
                console.print(f"[yellow]Moving file on Drive onto '{category or 'General'}'...[/yellow]")
                folder_id = database_manager.get_config("root_folder_id")
                target_folder_id = get_or_create_subfolder(folder_id, category) if category else folder_id
                move_file(existing_file['id'], existing_file.get('parents', []), target_folder_id)
                console.print("[green]File moved successfully![/green]")
                return # Done, no need to upload
            elif choice == 'drive':
                 console.print("[yellow]Keeping file as is on Drive.[/yellow]")
                 return # Done, keeping drive state
        else:
             console.print(f"[yellow]File already exists in '{category or 'General'}'. Skipping upload.[/yellow]")
             return

    # Upload if not exists
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description=f"Uploading {path.name} to Google Drive...", total=None)
        drive_id = upload_book(str(path), category=category)

    if drive_id:
        database_manager.save_book(
            title=path.name,
            drive_id=drive_id,
            local_path=str(path),
            category=category
        )
        console.print(f"Success! [bold green]{path.name}[/bold green] is now live and synced. [green]✔[/green]")
    else:
        console.print("[red]Upload failed. Please check your connection or Drive quota.[/red]")


@app.command()
def push(
    file_path: str = typer.Argument(None, help="Path to the book file"), 
    category: str = typer.Option(None, "--category", "-c", help="Book category (subfolder)"),
    all: bool = typer.Option(False, "--all", "-a", help="Upload all local books that are missing on Drive")
):
    """Upload a book to Google Drive and register it in the library."""
    
    if all:
         # Bulk Push Logic
        console.print("[bold cyan]Checking for files to upload...[/bold cyan]")
        local_files = list_local_files()
        drive_books = list_drive_files()
        drive_names = {b['name'] for b in drive_books}
        
        # Identify files not on Drive (simple name check for now)
        # Note: robust deduction of 'missing' might need more complex logic if we want to handle conflicts (same name different folder)
        # But 'push' logic handles existence check, so we just iterate ALL local files?
        # No, iterating all means checking 1000 files if only 1 is new. 
        # Better to filter those that are definitely NOT on drive by name.
        # However, the user wants Smart Push (Conflict Resolution).
        # Use case: User moved file locally to new folder. 'push --all' should detect conflict and ask to move?
        # If I filter by name IN drive_names, I miss the "Move" opportunity?
        # Actually, existing 'push' logic handles "Move" if name exists. 
        # So we SHOULD include files that exist on Drive to check for category mismatch?
        # That would mean 'push --all' runs interactively for EVERY file in the library. That's annoying.
        # Compromise: check all files, but silent-skip if category matches?
        # My `_push_single_file` prints "File already exists... Skipping" logic.
        # Let's just process files that are NOT fully synced (missing or category mismatch).
        
        to_process = []
        drive_map = {b['name']: b for b in drive_books}
        
        for f in local_files:
            d_file = drive_map.get(f['name'])
            # Condition to process:
            # 1. Not on Drive
            # 2. On Drive but category mismatch (and we want to fix it)
            
            if not d_file:
                to_process.append(f)
            else:
                # Check category mismatch
                local_cat = f.get('category')
                drive_cat = d_file.get('category')
                
                match = (local_cat is None and drive_cat is None) or \
                        (local_cat and drive_cat and local_cat.lower() == drive_cat.lower())
                
                if not match:
                    to_process.append(f)

        if not to_process:
            console.print("[green]All local files are synced to Drive! ✨[/green]")
            return

        total_size = sum(int(f.get('size', 0)) for f in to_process)
        count = len(to_process)
        
        console.print(f"\n[bold]Found {count} files to push (upload or fix category):[/bold]")
        for f in to_process[:5]: 
             console.print(f" - {f['name']}")
        if count > 5: console.print(f" ... and {count - 5} more.")
        
        formatted_size = format_size(total_size)
        if not Confirm.ask(f"\n[bold yellow][?][/bold yellow] Do you want to push/sync {count} files ({formatted_size})?"):
            console.print("[red]Aborted.[/red]")
            raise typer.Exit()

        # Process
        for f in to_process:
            path = Path(f['path'])
            _push_single_file(path, category=category)
        
        console.print(f"[green]Bulk push completed! ✔[/green]")
        return

    # Single File Logic
    if not file_path:
        console.print("[red]Please provide a file path or use --all.[/red]")
        raise typer.Exit(1)
        
    path = Path(file_path).expanduser().resolve()
    
    if not path.exists():
        console.print(f"[red]Error: File '{file_path}' not found.[/red]")
        raise typer.Exit(1)

    _push_single_file(path, category)

@app.command()
def sync(
    local: bool = typer.Option(False, "--local", "-l", help="Push local changes to Drive (Priority: Local). Use this to upload new files."),
    remote: bool = typer.Option(False, "--remote", "-r", help="Pull Drive changes to Local (Priority: Remote). Use this to download missing files."),
    all: bool = typer.Option(False, "--all", "-a", help="Bidirectional Sync. Performs both Push and Pull to ensure libraries are identical.")
):
    """
    Synchronize your library between Local and Google Drive.
    
    Modes:
    --local (-l):  Uploads local files that are missing on Drive.
    --remote (-r): Downloads Drive files that are missing locally.
    --all (-a):    Does both! The ultimate sync command.
    """
    
    if not (local or remote or all):
        console.print("[yellow]Please specify a mode: --local, --remote, or --all[/yellow]")
        return

    if local or all:
        console.print(Panel("[bold blue]Starting Push Sync (Local -> Remote)[/bold blue]", expand=False))
        push(file_path=None, category=None, all=True)
    
    if remote or all:
        console.print(Panel("[bold cyan]Starting Pull Sync (Remote -> Local)[/bold cyan]", expand=False))
        pull(book_name=None, all=True)
    
    console.print("\n[bold green]✨ Synchronization Complete! ✨[/bold green]")

@app.command()
def share():
    """Share books or your entire library via Google Drive links."""
    
    choice = inquirer.select(
        message="What would you like to share?",
        choices=[
            {"name": "Share specific files", "value": "files"},
            {"name": "Manage Library Privacy (Public/Private)", "value": "library"},
        ],
    ).execute()

    if choice == "files":
        console.print("[dim]Fetching file list from Drive...[/dim]")
        drive_books = list_drive_files()
        
        if not drive_books:
            console.print("[yellow]No files found on Drive to share.[/yellow]")
            return

        choices = []
        for b in drive_books:
            cat = b.get('category') or 'General'
            choices.append({"name": f"[{cat}] {b['name']}", "value": b})
            
        selected_books = inquirer.checkbox(
            message="Select books to share (Space to select, Enter to confirm):",
            choices=choices,
            instruction="(Space to select)"
        ).execute()
        
        if not selected_books:
            console.print("[yellow]No books selected.[/yellow]")
            return

        console.print("\n[bold]Generating Links...[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Book")
        table.add_column("Link")
        
        for book in selected_books:
            link = set_file_visibility(book['id'], public=True)
            table.add_row(book['name'], f"[link={link}]Click to Open[/link]" if link else "[red]Error[/red]")
            if link:
                console.print(f"[green]✔[/green] {book['name']}: {link}")
        
    elif choice == "library":
        folder_id = database_manager.get_config("root_folder_id")
        if not folder_id:
            console.print("[red]Library folder not found.[/red]")
            return
            
        action = inquirer.select(
            message="Set Library Visibility:",
            choices=[
                {"name": "Make Public (Anyone with link can view)", "value": True},
                {"name": "Make Private (Only you)", "value": False},
            ],
        ).execute()
        
        with console.status("[bold blue]Updating permissions..."):
            result = set_file_visibility(folder_id, public=action)
            
        if action and result:
            console.print(Panel(f"[bold green]Library is now Public![/bold green]\n\nLink: [blue underline]{result}[/blue underline]", title="Success"))
        elif not action and result:
            console.print("[bold green]Library is now Private.[/bold green]")
        else:
            console.print("[red]Failed to update permissions.[/red]")

@app.command()
def organize(
    book_name: str = typer.Argument(None, help="Name of the book to move"),
    category: str = typer.Argument(None, help="New category name")
):
    """Move a book to a different category (Folder) and sync changes."""
    
    local_files = list_local_files()
    
    # 1. Select Book
    if not book_name:
        choices = [f['name'] for f in local_files]
        if not choices:
            console.print("[yellow]No books found locally.[/yellow]")
            return
            
        book_name = inquirer.fuzzy(
            message="Select a book to organize:",
            choices=choices,
        ).execute()

    # Find book details
    book = next((f for f in local_files if f['name'] == book_name), None)
    if not book:
        console.print(f"[red]Book '{book_name}' not found locally.[/red]")
        return
        
    current_cat = book.get('category') or "General"
    
    # 2. Select Category
    if not category:
        # Get existing categories + option to create new
        existing_cats = list(set(f.get('category') for f in local_files if f.get('category')))
        existing_cats.append("General")
        existing_cats.sort()
        
        category = inquirer.select(
            message="Select new category:",
            choices=existing_cats + [{"name": "New Category...", "value": "NEW"}],
            default=current_cat
        ).execute()
        
        if category == "NEW":
            category = console.input("[bold]Enter new category name:[/bold] ").strip()
            
    if not category:
        console.print("[red]Invalid category.[/red]")
        return
        
    if category == current_cat:
        console.print("[yellow]Book is already in this category.[/yellow]")
        return

    # 3. Confirmation
    if not Confirm.ask(f"Move [bold]{book_name}[/bold] from [cyan]{current_cat}[/cyan] to [magenta]{category}[/magenta]?"):
        console.print("[red]Cancelled.[/red]")
        return

    # 4. Perform Move
    local_root = Path(database_manager.get_config("local_path"))
    
    # Local Move
    start_path = Path(book['path'])
    dest_dir = local_root / category
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / book_name
    
    try:
        shutil.move(str(start_path), str(dest_path))
        console.print(f"[green]✔ Local file moved to '{category}'[/green]")
    except Exception as e:
        console.print(f"[red]Error moving local file: {e}[/red]")
        return

    # Drive Move
    drive_books = list_drive_files()
    drive_file = next((b for b in drive_books if b['name'] == book_name), None)
    
    if drive_file:
        console.print("[dim]Moving on Google Drive...[/dim]")
        folder_id = database_manager.get_config("root_folder_id")
        target_folder_id = get_or_create_subfolder(folder_id, category)
        move_file(drive_file['id'], drive_file.get('parents', []), target_folder_id)
        console.print(f"[green]✔ Drive file moved to '{category}'[/green]")
    else:
        console.print("[yellow]File not found on Drive. It will be uploaded on next sync.[/yellow]")

    # Update Database
    database_manager.save_book(
        title=book_name,
        drive_id=drive_file['id'] if drive_file else "pending",
        local_path=str(dest_path),
        category=category
    )

    # 5. Sync Prompt
    if Confirm.ask("\n[bold blue]Do you want to sync changes now?[/bold blue]"):
        push(file_path=None, category=None, all=True)

@app.command()
def setup():
    """Complete initial setup flow."""
    console.print(Panel("[bold blue]Welcome to Bookshell[/bold blue]", subtitle="Initial Setup", expand=False))
    
    # Initialize Database
    database_manager.init_db()

    # 1. Configuration Type
    from InquirerPy import inquirer
    
    setup_type = inquirer.select(
        message="How would you like to configure Bookshell?",
        choices=[
            {"name": "Standard (recommended: ~/Bookshell_Library)", "value": "default"},
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
4. [blue]Marking:[/blue] Use [bold]bookshell mark "book.pdf" -s reading[/bold] to update status.

Use [bold]bookshell --help[/bold] to see all available commands.
    """
    console.print(Panel(instructions, title="[bold green]Ready to go![/bold green]", border_style="green", expand=False))

if __name__ == "__main__":
    app()
