"""Ask a Gemma-family model one free-text question on a Mac with MLX — from the base model,
or from the base with a stage-1 adapter. One user turn, thinking mode off, greedy decoding
(as `scenario` asks), so a base/adapter pair differs only by the adapter. The answer is
printed; nothing is written. A reply that reaches --max-tokens is printed as far as it got
and the command exits non-zero: a small tuned model can repeat itself without end, and that
is shown, not hidden. With --first N the answer is deliberately cut at N tokens and ends
in "…": the start of an answer, for a short demonstration.

    uv run python -m jaleesweights.mlx.ask "I got offered a great job at a bank. I should take it, right?"
    uv run python -m jaleesweights.mlx.ask "..." --adapter data/runs/quick-demo/mlx-sft/adapter
"""

import time
from pathlib import Path

import typer

from ._common import DEFAULT_MODEL, precision_line, preflight, require_mlx

app = typer.Typer(add_completion=False, help=__doc__)


def ask(model_name: str, adapter: Path | None, question: str, max_tokens: int, first: int = 0) -> None:
    mlx_lm = require_mlx()
    import mlx.core as mx

    model, tok = mlx_lm.load(model_name, adapter_path=str(adapter) if adapter else None)
    print(f"policy: {adapter or 'base'}; weights loaded, {mx.get_active_memory() / 2**30:.1f} GB resident")
    prompt = tok.apply_chat_template([{"role": "user", "content": question}],
                                     add_generation_prompt=True, enable_thinking=False)  # Gemma-4: answer directly, as the teacher data was made
    t0 = time.perf_counter()
    reply = mlx_lm.generate(model, tok, prompt, max_tokens=first or max_tokens)  # greedy: no sampler
    dt = time.perf_counter() - t0
    n_out = len(tok.encode(reply, add_special_tokens=False))
    if first and n_out >= first:
        reply = reply.rstrip() + " …"
    print(f"\n--- user ---\n{question}")
    print(f"\n--- {'base + adapter' if adapter else 'base'} ---\n{reply}")
    print(f"\n[{dt:.0f} s, {n_out} tokens, peak memory {mx.get_peak_memory() / 2**30:.1f} GB]")
    if not first and n_out >= max_tokens:
        raise SystemExit(f"reply hit --max-tokens {max_tokens} and is cut off above; "
                         "raise the cap, or read it as a model that does not stop")


@app.command()
def main(
    question: str = typer.Argument(..., help="The question, as one user turn."),
    model: str = typer.Option(DEFAULT_MODEL, help="An MLX conversion of a Gemma-family model (Hugging Face id or local directory)."),
    adapter: Path | None = typer.Option(None, help="An `mlx_lm.lora` adapter directory to apply (the stage-1 output's adapter/)."),
    max_tokens: int = typer.Option(2048, help="Generation cap; a reply that hits it is printed, then the command fails."),
    first: int = typer.Option(0, help="Print only the first N tokens of the answer, ending in '…' at the cut (0: the whole answer)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the preflight summary and stop before anything loads."),
) -> None:
    if not question.strip():
        raise typer.BadParameter("the question is empty")
    if first < 0:
        raise typer.BadParameter("--first must be 0 or a positive number of tokens")
    if adapter is not None and not (adapter / "adapters.safetensors").exists():
        raise typer.BadParameter(f"{adapter} is not an mlx_lm adapter directory (no adapters.safetensors)")
    if preflight(f"one question with MLX from {model}" + (f" + adapter {adapter}" if adapter else " (base)"),
                 [f"question: {question}",
                  "one turn, thinking off, greedy decoding, "
                  + (f"the first {first} tokens only" if first else f"up to {max_tokens} tokens"),
                  precision_line(model), "the answer is printed; nothing is written"],
                 dry_run):
        return
    ask(model, adapter, question, max_tokens, first)


if __name__ == "__main__":
    app()
