"""JaleesBench pilot CLI."""

import asyncio

import typer

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def collect(limit: int = typer.Option(None, help="Run only the first N pending sittings")):
    """Collect subject-model responses for the pilot grid."""
    from .collect import collect as _collect
    asyncio.run(_collect(limit=limit))


@app.command()
def smoke():
    """Run 2 sittings (one per subject) to verify model ids and keys."""
    from .collect import collect as _collect
    asyncio.run(_collect(limit=2))


@app.command()
def judge(limit: int = typer.Option(None, help="Judge only the first N pending judgments")):
    """Score collected sittings with both judges at both turns."""
    from .judge import judge_all
    asyncio.run(judge_all(limit=limit))


@app.command(name="map-chapters")
def map_chapters(limit: int = typer.Option(None, help="Map only the first N pending chapters")):
    """Characterize all 372 Riyad al-Salihin chapters as probe material."""
    from .mapping import map_chapters as _map
    asyncio.run(_map(limit=limit))


@app.command()
def report():
    """Aggregate judgments into the pilot report (markdown + HTML)."""
    from .html_report import build_html
    from .score import build_report
    build_report()
    build_html()


if __name__ == "__main__":
    app()


@app.command()
def rejudge(limit: int = typer.Option(None, help="Cap the number of v2 judgments")):
    """Re-judge >=2-band disagreement cells with the v2 boundary-rules prompt."""
    from .judge import rejudge_disagreements
    asyncio.run(rejudge_disagreements(limit=limit))
