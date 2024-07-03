# filecheck - A Python-native clone of LLVMs FileCheck tool

This tries to be as close a clone of LLVMs FileCheck as possible, without going crazy.

There are some features that are left out for now (e.g. [pseudo-numeric variables](https://llvm.org/docs/CommandGuide/FileCheck.html#filecheck-pseudo-numeric-variables) and parts of [numeric substitution](https://llvm.org/docs/CommandGuide/FileCheck.html#filecheck-numeric-substitution-blocks)).

The codebase is fully type checked by `pyright`, and automatically formatted using `black`. We aim to have tests
covering everything from normal matching down to error messages.

## Features:
Here's an overview of all FileCheck features and their implementation status.

- **Checks:**
  - [X] `CHECK`
  - [X] `CHECK-NEXT`
  - [X] `CHECK-NOT` (not sure, I think I may have missed something. Docs aren't great on this one.)
  - [X] `CHECK-LABEL`
  - [X] `CHECK-EMPTY`
  - [X] `CHECK-SAME`
  - [ ] `CHECK-DAG` Need to figure this one out exactly
  - [X] `CHECK-COUNT` (who uses this? Still around ~310 matches in MLIR...)
- **Flags:**
  - [X] `--check-prefix`
  - [ ] `--check-prefixes`
  - [X] `--comment-prefixes`
  - [ ] `--allow-unused-prefixes`
  - [X] `--input-file`
  - [X] `--match-full-lines`
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
  - [X] Literal matching (`CHECK{LITERAL}`)
  - [X] Weird regex features (`[:xdigits:]` and friends)
  - [X] Correct(?) handling of matching check lines
- **Testing:**
  - [X] Base cases
  - [ ] Negative tests
  - [ ] Error messages (started)
  - [ ] Lots of edge cases
  - [ ] MLIR/xDSL integration tests
- **UX:**
  - Good error messages: I have some error messages, but could be a lot better
    - [X] Parse errors
    - [ ] Matching errors
    - [ ] Malformed regexes
- **Infrastructure:**
  - [X] Formatting: black
  - [X] Pyright: Almost passes rn
  - [X] `pre-commit`: Didn't get to it yet
  - [X] CI for formatting

We are open to PRs for bugfixes or any features listed here.

## Differences to LLVMs FileCheck:
We want to be as close as possible to the original FileCheck, and document our differences very clearly.

If you encounter a difference that is not documented here, feel free to file a bug report.

### Better Regexes
We use pythons regex library, which is a flavour of a Perl compatible regular expression (PCRE), instead of FileChecks
POSIX regex falvour.

**Example:**
```
// LLVM filecheck:
// CHECK: %{{[:alnum:]+}}, %{{[:digit:]+}}

// our fileheck:
// CHECK: %{{[a-zA-Z0-9]+}}, %{{\d+}}
```

Some effort is made to translate character classes from POSIX to PCRE, although it might be wrong in edge cases.

### Relaxed Matchings:

We relax some of the matching rules, like:

- Allow a file to start with `CHECK-NEXT`


### No Numerical Substitution

While our filecheck supports [numeric capture](https://llvm.org/docs/CommandGuide/FileCheck.html#filecheck-numeric-substitution-blocks)
(`[[#%.3x,VAR:]]` will capture a three-digit hex number), we don't support arithmetic expressions on these captured
values at the moment. We also don't support the "Pseudo Numeric Variable" `@LINE`.
