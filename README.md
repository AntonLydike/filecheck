# filecheck - A Python-native clone of LLVMs FileCheck tool

This tries to be as close a clone of LLVMs FileCheck as possible, without going crazy.

There are some features that are left out for now (e.g. [pseudo-numeric variables](https://llvm.org/docs/CommandGuide/FileCheck.html#filecheck-pseudo-numeric-variables) and parts of [numeric substitution](https://llvm.org/docs/CommandGuide/FileCheck.html#filecheck-numeric-substitution-blocks)).

## Features:

- **Checks:**
  - [X] `CHECK`
  - [X] `CHECK-NEXT`
  - [X] `CHECK-NOT` (not sure, I think I may have missed something. Docs aren't great on this one.)
  - [X] `CHECK-LABEL`
  - [X] `CHECK-EMPTY`
  - [X] `CHECK-SAME`
  - [ ] `CHECK-DAG` Need to figure this one out exactly
  - [ ] `CHECK-COUNT` (who uses this? Still around ~310 matches in MLIR...)
- **Flags:**
  - [X] `--check-prefix`
  - [ ] `--check-prefixes`
  - [X] `--comment-prefixes`
  - [ ] `--allow-unused-prefixes`
  - [X] `--input-file`
  - [ ] `--match-full-lines`
  - [X] `--strict-whitespace` (Kinda? Seems to be working.)
  - [ ] `--ignore-case`
  - [ ] `--implicit-check-not`
  - [ ] `--dump-input`
  - [ ] `--dump-input-context`
  - [ ] `--dump-input-filter`
  - [X] `--enable-var-scope`
  - [ ] `-D<VAR=VALUE>`
  - [ ] `-D#<FMT>,<NUMVAR>=<NUMERIC EXPRESSION>`
  - [ ] `-version`
  - [ ] `-v`
  - [ ] `-vv`
  - [ ] `--allow-deprecated-dag-overlap` Not sure what this means yet.
  - [ ] `--allow-empty` (I think I allow empty input rn?)
  - [ ] `--color` No color support yet
- **Base Features:**
  - [X] Regex patterns
  - [X] Captures and Capture Matches
  - [X] Numeric Captures
  - [ ] Numeric Substitutions (jesus christ, wtf man)
  - [X] Weird regex features (`[:xdigits:]` and friends)
  - [X] Correct(?) handling of matching check lines
- **Testing:**
  - [X] Base cases
  - [ ] Negative tests
  - [ ] Error messages
  - [ ] Lots of edge cases
  - [ ] MLIR/xDSL integration tests
- **UX:**
  - [ ] Good error messages: I have some error messages, but could be a lot better
- **Infrastructure:**
  - [X] Formatting: black
  - [X] Pyright: Almost passes rn
  - [X] `pre-commit`: Didn't get to it yet
  - [X] CI for formatting

Open to PRs for any such features.
