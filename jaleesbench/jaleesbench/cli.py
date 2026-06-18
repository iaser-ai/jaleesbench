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


@app.command(name="select-probes")
def select_probes(limit: int = typer.Option(None, help="Select only the first N pending clusters")):
    """Pick one representative bab per probe-worthy cluster."""
    from .mapping import select_probes as _select
    asyncio.run(_select(limit=limit))


@app.command(name="draft-probes")
def draft_probes(limit: int = typer.Option(None, help="Draft only the first N pending clusters")):
    """Draft probes for clusters not covered by pilot probes (design 3.2)."""
    from .authoring import draft_probes as _draft
    asyncio.run(_draft(limit=limit))


@app.command(name="batch-judge")
def batch_judge(action: str = typer.Argument(..., help="submit | collect"),
                limit: int = typer.Option(None, help="Submit only the first N pending judgments")):
    """Judge via the providers' batch APIs (50% pricing). Live `judge` stays
    the fallback for anything a batch leaves behind."""
    from . import batching
    if action == "submit":
        batching.submit(limit=limit)
    elif action == "collect":
        batching.collect()
    else:
        raise typer.BadParameter(f"unknown action: {action}")


@app.command(name="detect-citations")
def detect_citations(limit: int = typer.Option(None, help="Detect only the first N pending sittings")):
    """LLM (Flash Lite on Vertex) citation detection -> citations_llm.jsonl."""
    from .citation import detect_all
    asyncio.run(detect_all(limit=limit))


@app.command()
def report():
    """Aggregate judgments into the report. HTML is the canonical output
    (the PDF is rendered from it); no markdown is produced."""
    from .html_report import build_html
    build_html()


@app.command(name="export-web")
def export_web(
    out: str = typer.Option(..., help="Output dir for index.json + per-probe shards"),
    results_path: str = typer.Option(
        None, help="Results dir to read (default: the package results/)"),
    limit: int = typer.Option(None, help="Export only the first N probes (by id)"),
):
    """Export results into the static viewer's data contract (index.json +
    per-probe shards) for apps/jaleesbrowser. Read-only over the harness data."""
    from pathlib import Path
    from .export_web import export_web as _export
    _export(Path(results_path) if results_path else None, Path(out), limit=limit)


if __name__ == "__main__":
    app()


@app.command()
def rejudge(limit: int = typer.Option(None, help="Cap the number of v2 judgments")):
    """Re-judge >=2-band disagreement cells with the v2 boundary-rules prompt."""
    from .judge import rejudge_disagreements
    asyncio.run(rejudge_disagreements(limit=limit))
