"""CLI entry point for study harness — subjects group."""
from __future__ import annotations

import click
from pathlib import Path


@click.group()
def main() -> None:
    """study — CLI study harness (TDD-driven)."""


@main.group("subjects")
def subjects_group() -> None:
    """Manage subject directories."""


# ---- new --------------------------------------------------------------- #

@subjects_group.command()
@click.argument("subject_id", type=str)
@click.argument("topic", type=str)
def new(subject_id: str, topic: str) -> None:  # noqa: D401 — CLI docs
    """Create a new subject directory.

    \b
        study subjects new <subject_id> <topic>
    """
    from .subjects import create_subject

    ws = Path.cwd()
    root = create_subject(ws, subject_id, topic)
    click.echo(f"Created subject '{subject_id}' at {root}")


# ---- list -------------------------------------------------------------- #

@subjects_group.command("list")
def _list() -> None:  # noqa: D401 — CLI docs
    """List all subjects in the current workspace.

    \b
        study subjects list
    """
    from .subjects import list_subjects as _ls

    results = _ls(Path.cwd())
    if not results:
        click.echo("No subjects found.")
        return

    # Simple ASCII table
    click.echo(f"{'Subject ID':<25} {'Topic':<30}")
    click.echo("-" * 55)
    for sid, topic in results:
        click.echo(f"{sid:<25} {topic:<30}")


# ---- delete ------------------------------------------------------------ #

@subjects_group.command("delete")
@click.argument("subject_id", type=str)
def _delete(subject_id: str) -> None:  # noqa: D401 — CLI docs
    """Delete a subject directory and all its contents.

    \b
        study subjects delete <subject_id>
    """
    from .subjects import list_subjects, delete_subject as _ds
    from pathlib import Path as P

    results = list_subjects(P.cwd())
    targets = [sid for sid, _ in results if sid == subject_id]
    if not targets:
        click.echo(f"Subject '{subject_id}' not found.", err=True)
        raise SystemExit(1)

    ws = P.cwd() / "subjects" / subject_id
    delete_subject(ws)
    click.echo(f"Deleted subject '{subject_id}'.")


if __name__ == "__main__":
    main()


# ── approve -------------------------------------------------------------- #

@subjects_group.command("approve")
@click.argument("subject_id", type=str)
def _approve(subject_id: str) -> None:  # noqa: D401 — CLI docs
    """Approve the draft so recall can begin.

    \b
        study subjects approve <subject_id>
    """
    from .subjects import approve_draft as _ad
    from pathlib import Path as P

    ws = P.cwd() / "subjects" / subject_id
    if not ws.exists():
        click.echo(f"Subject '{subject_id}' not found.", err=True)
        raise SystemExit(1)

    _ad(ws)
    click.echo(f"Draft approved for '{subject_id}'.")


if __name__ == "__main__":
    main()
