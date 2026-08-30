import io
import sys
import warnings
from io import BytesIO
from pathlib import Path
import pytest
from filecheck.matcher import Matcher
from filecheck.options import DumpInputKind, Options


def test_utf8_file_matching(tmp_path: Path):
    check_file = tmp_path / "check.txt"
    check_file.write_text(
        "// CHECK: greeting: こんにちは 世界 🌍\n// CHECK-NEXT: math: α + β = γ\n",
        encoding="utf-8",
    )

    input_file = tmp_path / "input.txt"
    input_file.write_text(
        "greeting: こんにちは 世界 🌍\nmath: α + β = γ\n",
        encoding="utf-8",
    )

    opts = Options(match_filename=str(check_file), input_file=str(input_file))
    matcher = Matcher.from_opts(opts)
    assert matcher.run() == 0


def test_utf8_stdin_matching(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    check_file = tmp_path / "check.txt"
    check_file.write_text(
        "// CHECK: emoji test: ❤ 🗺️ 🚀\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "stdin",
        io.TextIOWrapper(BytesIO("emoji test: ❤ 🗺️ 🚀\n".encode())),
    )

    opts = Options(match_filename=str(check_file), input_file="-")
    matcher = Matcher.from_opts(opts)
    assert matcher.run() == 0


def test_no_encoding_warning(tmp_path: Path):
    check_file = tmp_path / "check.txt"
    check_file.write_text("// CHECK: plain ascii\n", encoding="utf-8")

    input_file = tmp_path / "input.txt"
    input_file.write_text("plain ascii\n", encoding="utf-8")

    opts = Options(
        match_filename=str(check_file),
        input_file=str(input_file),
        dump_input=DumpInputKind.NEVER,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", EncodingWarning)
        matcher = Matcher.from_opts(opts)
        assert matcher.run() == 0
