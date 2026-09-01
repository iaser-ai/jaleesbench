"""Qur'an verbatim-quoting battery.

`run` asks one OpenAI-compatible endpoint for each verse in the truth file
("What is verse S:A of the Qur'an? ...", temperature 0, no tools, no system
prompt) and scores the reply against the Uthmani text. `report` tabulates one
or more result files. `truth` (re)builds the ground-truth file from
api.alquran.cloud.

Usage (from this directory):
  uv run python -m quranquote truth
  uv run python -m quranquote run --base-url <url>/v1 --api-key-env KEY_ENV \
      --model <model-id> --tag <label>
  uv run python -m quranquote report results/*.json
"""

import difflib
import json
import os
import pathlib
import re
import time
import unicodedata

import typer

app = typer.Typer(add_completion=False)
ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_TRUTH = ROOT / "data" / "quran_truth.json"
PROMPT = ("What is {ref} of the Qur'an? "
          "Give the exact Arabic text, then an English translation.")
BISMILLAH = "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"
REFS = ["1:1", "112:1", "2:255", "36:1", "49:12", "24:35",
        "103:2", "31:13", "58:11", "29:45", "83:1", "46:9"]
STOP = {"the", "of", "and", "a", "in", "to", "is", "who", "he", "it", "you", "o"}


def strip_ar(s: str) -> str:
    """Arabic normalization: drop diacritics/tatweel, unify alef/hamza forms."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[ـۖ-ࣰۭ-ࣿ]", "", s)
    for a, b in [("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ٱ", "ا"),
                 ("ى", "ي"), ("ة", "ه")]:
        s = s.replace(a, b)
    return re.sub(r"[^؀-ۿ]", "", s)


def arabic_of(text: str) -> str:
    chunks = re.findall(r"[؀-ۿ][؀-ۿ\sً-ْٰۖ-ۭ.,،؛:()\-]*", text)
    return max(chunks, key=len) if chunks else ""


def score(reply: str, truth: dict) -> tuple[float, float]:
    """(arabic_similarity, english_word_overlap). The truth text for a surah's
    first ayah includes the Bismillah prefix (api.alquran.cloud convention);
    a reply is scored against both the full text and the text with the prefix
    stripped, taking the better — so quoting the verse without the Bismillah
    is not penalized."""
    ar = strip_ar(arabic_of(reply))
    tn = strip_ar(truth["ar"])
    nb = strip_ar(BISMILLAH)
    variants = [tn]
    if tn.startswith(nb) and tn != nb:
        variants.append(tn[len(nb):])
    sim = max((difflib.SequenceMatcher(None, ar, v).ratio()
               for v in variants), default=0.0) if ar else 0.0
    ew = set(re.findall(r"[a-z']+", truth["en"].lower())) - STOP
    rw = set(re.findall(r"[a-z']+", reply.lower()))
    return sim, len(ew & rw) / max(1, len(ew))


@app.command()
def truth(out: pathlib.Path = DEFAULT_TRUTH):
    """Build the ground-truth file (quran-uthmani + en.sahih) from alquran.cloud."""
    import urllib.request
    data = {}
    for ref in REFS:
        for ed, key in (("quran-uthmani", "ar"), ("en.sahih", "en")):
            u = f"https://api.alquran.cloud/v1/ayah/{ref}/{ed}"
            d = json.load(urllib.request.urlopen(u, timeout=30))["data"]
            data.setdefault(ref, {})[key] = d["text"]
            data[ref]["surah"] = d["surah"]["englishName"]
        time.sleep(0.3)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    typer.echo(f"wrote {out} ({len(data)} verses)")


@app.command()
def run(model: str = typer.Option(...),
        tag: str = typer.Option(..., help="label for output file / report"),
        base_url: str = typer.Option(...),
        api_key_env: str = typer.Option(..., help="env var holding the API key"),
        truth_path: pathlib.Path = DEFAULT_TRUTH,
        max_tokens: int = 8192,
        temperature: float = 0.0,
        out_dir: pathlib.Path = ROOT / "results"):
    """Run the battery against one model on an OpenAI-compatible endpoint."""
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=os.environ[api_key_env],
                    timeout=600)
    truth_data = json.loads(truth_path.read_text())
    rows = []
    for ref, t in truth_data.items():
        ask = t.get("ask", f"verse {ref}")  # named refs override
        reply = ""
        for attempt in range(4):
            try:
                r = client.chat.completions.create(
                    model=model, max_tokens=max_tokens, temperature=temperature,
                    messages=[{"role": "user",
                               "content": PROMPT.format(ref=ask)}])
                reply = r.choices[0].message.content or ""
                if reply.strip():
                    break
            except Exception as e:  # noqa: BLE001
                reply = f"<ERROR {e}>"
                time.sleep(20)
        sim, ident = score(reply, t)
        rows.append({"ref": ref, "surah": t["surah"], "ar_sim": round(sim, 3),
                     "en_overlap": round(ident, 2), "reply": reply})
        typer.echo(f"[{tag}] {ref:6} ar_sim={sim:.3f} en_overlap={ident:.2f}")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{tag}.json"
    out.write_text(json.dumps({"model": model, "tag": tag, "rows": rows},
                              ensure_ascii=False, indent=1))
    typer.echo(f"wrote {out}")


@app.command()
def report(files: list[pathlib.Path],
           truth_path: pathlib.Path = DEFAULT_TRUTH,
           threshold: float = 0.90):
    """Tabulate result files: verbatim-correct count per subject (re-scored
    with the current scorer, so old files benefit from scoring fixes)."""
    truth_data = json.loads(truth_path.read_text())
    print(f"{'subject':28} correct  verses below threshold")
    for f in files:
        d = json.loads(f.read_text())
        subjects = ({d['tag']: d['rows']} if 'rows' in d else d)
        for tag, rows in subjects.items():
            sims = {r['ref']: score(r['reply'], truth_data[r['ref']])[0]
                    for r in rows}
            ok = sum(s >= threshold for s in sims.values())
            low = ", ".join(f"{k}({v:.2f})" for k, v in sims.items()
                            if v < threshold)
            print(f"{tag:28} {ok}/{len(sims)}   {low or '-'}")


if __name__ == "__main__":
    app()
