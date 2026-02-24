import click
from flask.cli import with_appcontext
from app.extensions import db

@click.command("reset-db")
@with_appcontext
def reset_db_command():
    """Clear existing data and create new tables."""
    click.confirm("This will delete all data in the database. Continue?", abort=True)
    
    click.echo("Dropping all tables...")
    db.drop_all()
    
    click.echo("Creating all tables...")
    db.create_all()
    
    click.echo("Database reset and re-initialized successfully.")

def register_commands(app):
    """Register CLI commands with the application instance."""
    app.cli.add_command(reset_db_command)
