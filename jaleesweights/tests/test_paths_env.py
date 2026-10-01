import os
import subprocess
import sys
from pathlib import Path

import pytest

from jaleesweights import common, env, paths

REPO = Path(__file__).resolve().parents[2]


def test_repo_root_is_the_clone():
    assert paths.REPO_ROOT == REPO
    assert (paths.REPO_ROOT / "jaleesbench" / "pyproject.toml").exists()
    assert paths.SPLIT.exists() and paths.GUIDED_PREFIX.exists()


def test_benchmark_is_installed_editable_from_the_clone():
    import jaleesbench
    assert Path(jaleesbench.__file__).resolve().is_relative_to(REPO / "jaleesbench")


@pytest.mark.parametrize("cwd", [REPO, REPO / "jaleesweights"])
def test_paths_do_not_depend_on_working_directory(cwd):
    out = subprocess.run(
        [sys.executable, "-c", "from jaleesweights import paths; print(paths.REPO_ROOT)"],
        cwd=cwd, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == str(REPO)


def test_env_overrides_for_data_locations(tmp_path):
    out = subprocess.run(
        [sys.executable, "-c",
         "from jaleesweights import paths; print(paths.BENCH_RESULTS, paths.REFERENCE, paths.RUNS)"],
        env={**os.environ, "JW_BENCH_RESULTS": str(tmp_path / "r"),
             "JW_REFERENCE": str(tmp_path / "ref"), "JW_RUNS": str(tmp_path / "runs")},
        capture_output=True, text=True, check=True)
    assert out.stdout.split() == [str(tmp_path / "r"), str(tmp_path / "ref"), str(tmp_path / "runs")]


def test_main_run_file_fails_naming_the_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "BENCH_RESULTS", tmp_path)
    with pytest.raises(FileNotFoundError) as e:
        paths.main_run_file("collect.jsonl")
    assert "collect.jsonl" in str(e.value) and "fetch_data" in str(e.value)
    with pytest.raises(ValueError):
        paths.main_run_file("not-a-main-run-file.jsonl")


def test_main_run_files_checks_all_three(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "BENCH_RESULTS", tmp_path)
    for n in paths.MAIN_RUN_FILES:
        (tmp_path / n).write_text("")
    assert set(paths.main_run_files()) == set(paths.MAIN_RUN_FILES)
    (tmp_path / "citations_llm.jsonl").unlink()
    with pytest.raises(FileNotFoundError, match="citations_llm.jsonl"):
        paths.main_run_files()


def test_run_dir_is_created_under_runs(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "RUNS", tmp_path)
    assert paths.run_dir("demo") == tmp_path / "demo"
    assert (tmp_path / "demo").is_dir()


def _clear(monkeypatch, *keys):
    for k in keys:
        monkeypatch.delenv(k, raising=False)


def test_load_keys_names_only_the_missing_required_keys(monkeypatch, tmp_path):
    monkeypatch.setattr(env, "ENV_PATH", tmp_path / ".env")
    monkeypatch.setattr(env, "VERTEX_SA", tmp_path / "sa.json")
    _clear(monkeypatch, "ANTHROPIC_API_KEY", "TINKER_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sekrit-value")
    env.load_keys(["ANTHROPIC_API_KEY"])  # no raise
    with pytest.raises(RuntimeError) as e:
        env.load_keys(["ANTHROPIC_API_KEY", "TINKER_API_KEY"])
    msg = str(e.value)
    assert msg.endswith("TINKER_API_KEY") and "OPENAI" not in msg and "sekrit-value" not in msg


def test_load_keys_gemini_credential_check(monkeypatch, tmp_path):
    monkeypatch.setattr(env, "ENV_PATH", tmp_path / ".env")
    monkeypatch.setattr(env, "VERTEX_SA", tmp_path / "sa.json")
    _clear(monkeypatch, "GEMINI_API_KEY")
    env.load_keys([], gemini=False)
    with pytest.raises(RuntimeError, match="Gemini"):
        env.load_keys([], gemini=True)
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    env.load_keys([], gemini=True)


def test_load_keys_reads_env_file_but_environment_wins(monkeypatch, tmp_path):
    f = tmp_path / ".env"
    f.write_text("# c\nTINKER_API_KEY='fromfile'\nANTHROPIC_API_KEY=fromfile\n")
    monkeypatch.setattr(env, "ENV_PATH", f)
    _clear(monkeypatch, "TINKER_API_KEY", "ANTHROPIC_API_KEY")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "preset")
    env.load_keys(["TINKER_API_KEY", "ANTHROPIC_API_KEY"])
    assert os.environ["TINKER_API_KEY"] == "fromfile"   # quotes stripped
    assert os.environ["ANTHROPIC_API_KEY"] == "preset"


def test_common_filters():
    turns = [{"role": "user", "content": "q"}, {"role": "assistant", "content": "see [1]"},
             {"role": "user", "content": "p"}, {"role": "assistant", "content": "ok"}]
    assert common.dangling_markers(turns)
    turns[3]["content"] = "ok\n\nReferences\n[1] Sahih al-Bukhari 1"
    assert not common.dangling_markers(turns)
    assert common.GUIDE_REF.search("As instructed, I will")
    assert not common.GUIDE_REF.search("Allah guides whom He wills")
    rec = {"sitting_key": "s|JLS-001|flattery|unstated", "judge": "j", "scope": "full"}
    assert common.judgment_key(rec).startswith("s|JLS-001|flattery|unstated|j|full")
    split = common.load_split()
    assert len(split["train"]) == 70 and len(split["test"]) == 70 and split["seed"] == 3446


def test_output_path_refuses_reference_and_main_run(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "REFERENCE", tmp_path / "reference")
    monkeypatch.setattr(paths, "BENCH_RESULTS", tmp_path / "results")
    (tmp_path / "reference").mkdir()
    for bad in (tmp_path / "reference" / "x.jsonl", tmp_path / "reference", tmp_path / "results" / "collect.jsonl",
                tmp_path / "runs" / ".." / "reference" / "y.jsonl"):
        with pytest.raises(RuntimeError, match="read-only"):
            paths.output_path(bad)
    assert paths.output_path(tmp_path / "runs" / "r" / "x.jsonl") == (tmp_path / "runs" / "r" / "x.jsonl").resolve()


def test_run_dir_rejects_paths_that_escape_runs(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "RUNS", tmp_path)
    for bad in ("../reference", "a/b", "..", ""):
        with pytest.raises(ValueError):
            paths.run_dir(bad)
