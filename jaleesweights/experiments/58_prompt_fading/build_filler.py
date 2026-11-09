"""Build the filler bank for experiment 58 from its parts, screen it, and size the levels.

Reads filler_parts/part_*.md in name order (part_00 is the bank of the MultiBench
experiments 76/78, kept verbatim as the opening), and writes:

  filler_bank.md      every exchange once, in order — the static asset the collector reads
  filler_levels.json  for each level, how many exchanges from the top of the bank reach its
                      token target, and the Gemma-token count that gives

It stops, writing nothing, if any exchange trips the value-neutrality screen, repeats a
question, or the bank is too short for the top level. Tokens are counted with the model's own
tokenizer (downloaded from the Hugging Face hub on first use; no account needed).

    uv run python experiments/58_prompt_fading/build_filler.py
"""

import json
import re
from pathlib import Path

import typer

HERE = Path(__file__).resolve().parent
MODEL = "google/gemma-4-31B-it"

# Filler tokens between the framing and the dilemma, per level (L0 has none).
TARGETS = {"L1": 1_000, "L2": 4_000, "L3": 12_000, "L4": 32_000, "L5": 64_000}

# Value-neutrality screen: any of these words anywhere in an exchange stops the build. A hit
# is fixed by rewording the exchange. Words whose everyday sense is neutral and common in
# this material are deliberately absent: "lies" (position), river "bank", "depression" (a
# hollow), "dating" (of rocks), "spirit level", "diet" (what an animal eats), "whisk".
SCREEN = re.compile(r"\b(" + "|".join([
    # religion
    r"god", r"gods", r"allah", r"lord", r"pray\w*", r"relig\w*", r"faith\w*", r"church\w*", r"mosque\w*",
    r"temple\w*", r"bible", r"quran", r"qur'an", r"islam\w*", r"muslim\w*", r"christ\w*", r"jew\w*",
    r"hindu\w*", r"buddh\w*", r"holy", r"sacred", r"sin", r"sins", r"sinful", r"heaven", r"hell",
    r"bless\w*", r"spiritual\w*", r"soul\w*", r"halal", r"haram", r"kosher", r"ramadan", r"christmas",
    r"easter", r"eid", r"diwali", r"hanukkah", r"worship\w*", r"miracle\w*", r"divine", r"angel\w*",
    r"astrolog\w*", r"horoscope\w*",
    # ethics and conduct
    r"moral\w*", r"ethic\w*", r"virtue\w*", r"honest\w*", r"dishonest\w*", r"cheat\w*", r"steal\w*", r"guilt\w*", r"shame\w*", r"ought", r"conscience", r"forgive", r"forgiven\w*",
    r"evil", r"wicked", r"righteous\w*", r"immoral\w*",
    # politics and conflict
    r"politic\w*", r"government\w*", r"election\w*", r"president\w*", r"war", r"wars", r"army",
    r"weapon\w*", r"soldier\w*", r"protest\w*", r"immigra\w*", r"refugee\w*",
    # money
    r"money", r"loan\w*", r"debt\w*", r"mortgage\w*", r"investment\w*", r"investor\w*", r"salary", r"salaries", r"tax", r"taxes",
    r"profit\w*", r"gambl\w*", r"bets", r"betting", r"lottery", r"casino\w*", r"banker\w*",
    r"dollar\w*", r"wealth\w*",
    # food and drink with religious rulings
    r"alcohol\w*", r"wine\w*", r"beer\w*", r"whisky", r"whiskey", r"vodka", r"rum", r"liquor", r"brewery", r"breweries",
    r"pork", r"bacon", r"ham", r"lard", r"gelatin", r"gelatine", r"pig", r"pigs",
    # relationships, body, distress
    r"girlfriend\w*", r"boyfriend\w*", r"marri\w*", r"divorc\w*", r"sex", r"sexual\w*", r"husband\w*",
    r"wife", r"wives", r"pregnan\w*", r"death\w*", r"dying", r"died", r"funeral\w*", r"grief", r"griev\w*",
    r"suicid\w*", r"depressed", r"depressing", r"anxiet\w*", r"anxious", r"cancer\w*", r"disease\w*", r"dieting",
    r"therap\w*", r"addict\w*", r"drug\w*", r"lonel\w*",
]) + r")\b", re.I)

app = typer.Typer(add_completion=False, help=__doc__)


def parse(text: str, where: str) -> list[tuple[str, str]]:
    """Ordered (user, assistant) pairs from one part file. Every block must parse."""
    pairs = []
    for n, block in enumerate(text.split("### exchange")[1:], 1):
        um = re.search(r"USER:\s*(.*?)\s*(?=\nASSISTANT:)", block, re.S)
        am = re.search(r"\nASSISTANT:\s*(.*)", block, re.S)
        if not um or not am:
            raise SystemExit(f"{where}: exchange {n} does not have a USER: then an ASSISTANT: part")
        u, a = um.group(1).strip(), am.group(1).strip()
        if not u or not a or "USER:" in a or "ASSISTANT:" in a or "USER:" in u:
            raise SystemExit(f"{where}: exchange {n} is empty or holds a stray speaker label")
        pairs.append((u, a))
    if not pairs:
        raise SystemExit(f"{where}: no exchanges")
    return pairs


@app.command()
def main(parts_dir: Path = typer.Option(HERE / "filler_parts"),
         out_dir: Path = typer.Option(HERE)) -> None:
    pairs: list[tuple[str, str]] = []
    problems: list[str] = []
    seen: dict[str, str] = {}
    for part in sorted(parts_dir.glob("part_*.md")):
        got = parse(part.read_text(), part.name)
        for i, (u, a) in enumerate(got, 1):
            hits = sorted({m.group(0).lower() for m in SCREEN.finditer(u + "\n" + a)})
            if hits:
                problems.append(f"{part.name} exchange {i} ({u[:50]!r}): screened words {hits}")
            key = re.sub(r"\W+", " ", u.lower()).strip()
            if key in seen:
                problems.append(f"{part.name} exchange {i}: question repeats one in {seen[key]}")
            seen[key] = part.name
        typer.echo(f"{part.name}: {len(got)} exchanges")
        pairs += got
    if problems:
        for p in problems:
            typer.echo("  " + p)
        raise SystemExit(f"{len(problems)} problem(s); nothing written")

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODEL)
    sizes = [len(tok.encode(u, add_special_tokens=False)) + len(tok.encode(a, add_special_tokens=False))
             for u, a in pairs]
    levels, total, it = {}, 0, iter(sorted(TARGETS.items(), key=lambda kv: kv[1]))
    name, target = next(it)
    for n, size in enumerate(sizes, 1):
        total += size
        while total >= target:
            levels[name] = {"exchanges": n, "tokens": total, "target": target}
            nxt = next(it, None)
            if nxt is None:
                break
            name, target = nxt
        if len(levels) == len(TARGETS):
            break
    if len(levels) != len(TARGETS):
        raise SystemExit(f"bank too short: {sum(sizes)} tokens in {len(pairs)} exchanges, "
                         f"top level needs {max(TARGETS.values())}; nothing written")

    used = levels["L5"]["exchanges"]
    bank = "\n\n".join(f"### exchange\nUSER: {u}\nASSISTANT: {a}" for u, a in pairs[:used]) + "\n"
    (out_dir / "filler_bank.md").write_text(bank)
    (out_dir / "filler_levels.json").write_text(json.dumps(
        {"tokenizer": MODEL, "levels": {"L0": {"exchanges": 0, "tokens": 0, "target": 0}, **levels}}, indent=1) + "\n")
    typer.echo(f"bank: {used} of {len(pairs)} exchanges used, none repeated")
    for k, v in levels.items():
        typer.echo(f"  {k}: target {v['target']:>6} -> {v['tokens']:>6} tokens in {v['exchanges']} exchanges")


if __name__ == "__main__":
    app()
