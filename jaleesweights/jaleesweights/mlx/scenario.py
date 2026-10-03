"""Ask a Gemma-family model one benchmark scenario on a Mac with MLX: the opening turn, then
the authored pressure turn — from the base model, or from the base with a stage-1 adapter.
Greedy decoding, so a before/after pair differs only by the adapter. The two answers are
printed and the sitting is written as one record in the harness's collection form (the same
shape `gemma_collect` writes), so a judge can score it later.

    uv run python -m jaleesweights.mlx.scenario --probe JLS-078 --pressure flattery --run tutorial
    uv run python -m jaleesweights.mlx.scenario --probe JLS-078 --pressure flattery --run tutorial \\
        --adapter data/runs/tutorial/mlx-sft/adapter --subject mlx-sft
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import typer

from .. import paths
from ._common import DEFAULT_MODEL, precision_line, preflight, read_jsonl, require_mlx

app = typer.Typer(add_completion=False, help=__doc__)


def find_cell(rows: list[dict], probe: str, pressure: str) -> dict:
    cells = {(r["probe_id"], r["pressure"]): r for r in rows}
    if (probe, pressure) in cells:
        return cells[probe, pressure]
    have = sorted(q for p, q in cells if p == probe)
    raise typer.BadParameter(f"no cell {probe}/{pressure} in the inputs"
                             + (f"; {probe} has pressures {', '.join(have)}" if have else f"; no probe {probe}"))


def ask(model_name: str, adapter: Path | None, cell: dict, max_tokens: int, subject: str, out: Path) -> None:
    mlx_lm = require_mlx()
    import mlx.core as mx

    model, tok = mlx_lm.load(model_name, adapter_path=str(adapter) if adapter else None)
    print(f"policy: {adapter or 'base'}; weights loaded, {mx.get_active_memory() / 2**30:.1f} GB resident")
    turns, usage = [], []
    for text in (cell["turn1"], cell["pressure_text"]):
        turns.append({"role": "user", "content": text})
        prompt = tok.apply_chat_template(turns, add_generation_prompt=True, enable_thinking=False)  # Gemma-4: answer directly, as the teacher data was made
        t0 = time.perf_counter()
        reply = mlx_lm.generate(model, tok, prompt, max_tokens=max_tokens)  # greedy: no sampler
        dt = time.perf_counter() - t0
        n_out = len(tok.encode(reply, add_special_tokens=False))
        if n_out >= max_tokens:
            raise RuntimeError(f"reply hit --max-tokens {max_tokens}; raise it so the answer is complete")
        turns.append({"role": "assistant", "content": reply})
        usage.append({"prompt_tokens": len(prompt), "completion_tokens": n_out})
        print(f"\n--- user ({cell['probe_id']}/{cell['pressure']}, turn {len(turns) // 2}) ---\n{text}")
        print(f"\n--- {subject} ---\n{reply}")
        print(f"\n[{dt:.0f} s, {n_out} tokens, peak memory {mx.get_peak_memory() / 2**30:.1f} GB]")
    out.write_text(json.dumps({
        "subject": subject, "probe_id": cell["probe_id"], "pressure": cell["pressure"], "chain": 0,
        "framing": "unstated", "model": model_name + (f"+lora:{adapter}" if adapter else "@mlx-base"),
        "context_prefix": None, "ts": datetime.now(timezone.utc).isoformat(),
        "attempts": [1, 1], "usage": usage, "turns": turns,
    }, sort_keys=True) + "\n")
    print(f"\ndone: sitting -> {out}")


@app.command()
def main(
    probe: str = typer.Option(..., help="Scenario id, e.g. JLS-078."),
    pressure: str = typer.Option(..., help="Pressure type, e.g. flattery, insistence, personal_appeal."),
    inputs: Path | None = typer.Option(None, help="Conversation inputs (default: the held-out half, data/reference/eval_inputs_gemma.jsonl)."),
    run: str = typer.Option("new-run", help="Run directory name under data/runs/ for the record."),
    out: Path | None = typer.Option(None, help="Output file (default: <run dir>/scenario_<probe>_<pressure>_<subject>.jsonl)."),
    model: str = typer.Option(DEFAULT_MODEL, help="An MLX conversion of a Gemma-family model (Hugging Face id or local directory)."),
    adapter: Path | None = typer.Option(None, help="An `mlx_lm.lora` adapter directory to apply (the stage-1 output's adapter/)."),
    subject: str = typer.Option("mlx-base", help="Subject name stamped on the record (use another for the adapter run)."),
    max_tokens: int = typer.Option(4096, help="Generation cap per turn; a reply that hits it is an error, not a truncated answer."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the preflight summary and stop before anything loads."),
) -> None:
    inputs = inputs or paths.reference_file("eval_inputs_gemma.jsonl")
    cell = find_cell(read_jsonl(inputs), probe, pressure)
    if adapter is not None and not (adapter / "adapters.safetensors").exists():
        raise typer.BadParameter(f"{adapter} is not an mlx_lm adapter directory (no adapters.safetensors)")
    out = paths.output_path(out or paths.run_dir(run) / f"scenario_{probe}_{pressure}_{subject}.jsonl")
    if out.exists():
        raise typer.BadParameter(f"{out} already exists; choose another --out or --subject (a run never overwrites)")
    out.parent.mkdir(parents=True, exist_ok=True)
    if preflight(f"one scenario with MLX from {model}" + (f" + adapter {adapter}" if adapter else " (base)"),
                 [f"cell {probe}/{pressure} from {inputs}; greedy decoding, up to {max_tokens} tokens per turn",
                  precision_line(model), f"subject {subject} -> {out}"],
                 dry_run):
        return
    ask(model, adapter, cell, max_tokens, subject, out)


if __name__ == "__main__":
    app()
