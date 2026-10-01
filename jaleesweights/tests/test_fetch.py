import hashlib
import io
import tarfile
import urllib.error

import pytest
from typer.testing import CliRunner

from jaleesweights import fetch_data, paths


def make_archive(path, files: dict[str, bytes]):
    with tarfile.open(path, "w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_committed_checksums_cover_both_archives():
    sums = fetch_data.expected_checksums()
    assert set(sums) == set(fetch_data.ARCHIVES)
    assert all(len(v) == 64 for v in sums.values())


def test_verify_names_the_archive_on_mismatch(tmp_path):
    a = tmp_path / "x.tar.gz"
    a.write_bytes(b"not the archive")
    with pytest.raises(RuntimeError, match="checksum mismatch for x.tar.gz"):
        fetch_data.verify(a, "0" * 64)
    fetch_data.verify(a, hashlib.sha256(b"not the archive").hexdigest())  # no raise


def test_download_404_means_not_published(tmp_path):
    def opener(url):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
    with pytest.raises(RuntimeError, match="has not been published yet"):
        fetch_data.download("jaleesweights-data.tar.gz", tmp_path / "a.tar.gz", opener=opener)


def test_download_other_http_errors_are_not_disguised(tmp_path):
    def opener(url):
        raise urllib.error.HTTPError(url, 500, "Server Error", {}, None)
    with pytest.raises(urllib.error.HTTPError):
        fetch_data.download("jaleesweights-data.tar.gz", tmp_path / "a.tar.gz", opener=opener)


def test_download_writes_the_asset(tmp_path):
    body = b"archive bytes"

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    seen = {}

    def opener(url):
        seen["url"] = url
        return Resp(body)

    out = fetch_data.download("jaleesbench-main-run.tar.gz", tmp_path / "d" / "m.tar.gz", opener=opener)
    assert out.read_bytes() == body
    assert seen["url"] == "https://github.com/iaser-ai/jaleesbench/releases/download/jaleesweights-data-v1/jaleesbench-main-run.tar.gz"


def test_extract_refuses_to_overwrite_unless_forced(tmp_path):
    a = tmp_path / "a.tar.gz"
    make_archive(a, {"one.jsonl": b"1\n", "tinker-runs/r/config.json": b"{}"})
    dest = tmp_path / "dest"
    assert sorted(fetch_data.extract(a, dest)) == ["one.jsonl", "tinker-runs/r/config.json"]
    assert (dest / "tinker-runs" / "r" / "config.json").read_bytes() == b"{}"
    with pytest.raises(RuntimeError, match="already has 2 of the files"):
        fetch_data.extract(a, dest)
    (dest / "one.jsonl").write_bytes(b"changed")
    fetch_data.extract(a, dest, force=True)
    assert (dest / "one.jsonl").read_bytes() == b"1\n"


def test_cli_installs_from_dir_into_both_destinations(tmp_path, monkeypatch):
    src = tmp_path / "staging"
    src.mkdir()
    sums = {}
    sums["jaleesweights-data.tar.gz"] = make_archive(src / "jaleesweights-data.tar.gz", {"ref.jsonl": b"r\n", "NOTICE": b"n"})
    sums["jaleesbench-main-run.tar.gz"] = make_archive(src / "jaleesbench-main-run.tar.gz", {"collect.jsonl": b"c\n", "NOTICE": b"n"})
    checks = tmp_path / "checksums.sha256"
    checks.write_text("".join(f"{v}  {k}\n" for k, v in sums.items()))
    monkeypatch.setattr(paths, "CHECKSUMS", checks)
    monkeypatch.setattr(paths, "REFERENCE", tmp_path / "reference")
    monkeypatch.setattr(paths, "BENCH_RESULTS", tmp_path / "results")

    res = CliRunner().invoke(fetch_data.app, ["--from-dir", str(src)])
    assert res.exit_code == 0, res.output
    assert (tmp_path / "reference" / "ref.jsonl").exists()
    assert (tmp_path / "results" / "collect.jsonl").exists()
    # second run without --force refuses
    res = CliRunner().invoke(fetch_data.app, ["--from-dir", str(src)])
    assert res.exit_code != 0 and "already has" in str(res.exception)


def test_cli_stops_on_checksum_mismatch_before_extracting(tmp_path, monkeypatch):
    src = tmp_path / "staging"
    src.mkdir()
    make_archive(src / "jaleesweights-data.tar.gz", {"ref.jsonl": b"r\n"})
    make_archive(src / "jaleesbench-main-run.tar.gz", {"collect.jsonl": b"c\n"})
    checks = tmp_path / "checksums.sha256"
    checks.write_text(f"{'0' * 64}  jaleesweights-data.tar.gz\n{'1' * 64}  jaleesbench-main-run.tar.gz\n")
    monkeypatch.setattr(paths, "CHECKSUMS", checks)
    monkeypatch.setattr(paths, "REFERENCE", tmp_path / "reference")
    monkeypatch.setattr(paths, "BENCH_RESULTS", tmp_path / "results")
    res = CliRunner().invoke(fetch_data.app, ["--from-dir", str(src)])
    assert res.exit_code != 0 and "checksum mismatch" in str(res.exception)
    assert not (tmp_path / "reference").exists()


def test_only_is_validated_and_destination_rejects_unknown_kind(tmp_path):
    res = CliRunner().invoke(fetch_data.app, ["--from-dir", str(tmp_path), "--only", "nope"])
    assert res.exit_code != 0 and "--only must be one of" in res.output
    with pytest.raises(ValueError):
        fetch_data.destination("nope")


def test_second_archive_mismatch_extracts_nothing(tmp_path, monkeypatch):
    src = tmp_path / "staging"
    src.mkdir()
    good = make_archive(src / "jaleesweights-data.tar.gz", {"ref.jsonl": b"r\n"})
    make_archive(src / "jaleesbench-main-run.tar.gz", {"collect.jsonl": b"c\n"})
    checks = tmp_path / "checksums.sha256"
    checks.write_text(f"{good}  jaleesweights-data.tar.gz\n{'1' * 64}  jaleesbench-main-run.tar.gz\n")
    monkeypatch.setattr(paths, "CHECKSUMS", checks)
    monkeypatch.setattr(paths, "REFERENCE", tmp_path / "reference")
    monkeypatch.setattr(paths, "BENCH_RESULTS", tmp_path / "results")
    res = CliRunner().invoke(fetch_data.app, ["--from-dir", str(src)])
    assert res.exit_code != 0 and "checksum mismatch" in str(res.exception)
    assert not (tmp_path / "reference").exists() and not (tmp_path / "results").exists()
