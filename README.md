# filecheck - A Python-native clone of LLVMs FileCheck tool

**Note:** This project is the successor of [mull-project/FileCheck.py](https://github.com/mull-project/FileCheck.py).

This tries to be as close a clone of LLVMs FileCheck as possible, without going crazy. It currently passes 1576 out of
1645 (95.8%) of LLVMs MLIR filecheck tests.

There are some features that are left out for now (e.g.a
[pseudo-numeric variables](https://llvm.org/docs/CommandGuide/FileCheck.html#filecheck-pseudo-numeric-variables) and
parts of [numeric substitution](https://llvm.org/docs/CommandGuide/FileCheck.html#filecheck-numeric-substitution-blocks)
).

The codebase is fully type checked by `pyright`, and automatically formatted using `black`. We aim to have tests
covering everything from normal matching down to error messages.

Install by running `pip install filecheck`.

## Features:
Here's an overview of all FileCheck features and their implementation status.

- **Checks:**
  - [X] `CHECK`
  - [X] `CHECK-NEXT`
  - [X] `CHECK-NOT` (Bug: [#10](https://github.com/AntonLydike/filecheck/issues/10))
  - [X] `CHECK-LABEL` (Bug: [#8](https://github.com/AntonLydike/filecheck/issues/8))
  - [X] `CHECK-EMPTY`
  - [X] `CHECK-SAME`
  - [X] `CHECK-DAG`
  - [X] `CHECK-COUNT`
- **Flags:**
  - [X] `--check-prefix`
  - [X] `--check-prefixes`
  - [X] `--comment-prefixes`
  - [ ] `--allow-unused-prefixes`
  - [X] `--input-file`
  - [X] `--match-full-lines`
  - [X] `--strict-whitespace` (Bug: [#6](https://github.com/AntonLydike/filecheck/issues/6))
  - [ ] `--ignore-case`
  - [ ] `--implicit-check-not`
  - [ ] `--dump-input`
  - [ ] `--dump-input-context`
  - [ ] `--dump-input-filter`
  - [X] `--enable-var-scope`
  - [X] `-D<VAR=VALUE>`
  - [ ] `-D#<FMT>,<NUMVAR>=<NUMERIC EXPRESSION>`
  - [X] `-version`
  - [ ] `-v`
  - [ ] `-vv`
  - [ ] `--allow-deprecated-dag-overlap` Not sure what this means yet.
  - [X] `--allow-empty`
  - [ ] `--color` No color support yet
- **Base Features:**
  - [X] Regex patterns (Bugs: [#7](https://github.com/AntonLydike/filecheck/issues/7), [#9](https://github.com/AntonLydike/filecheck/issues/9))
  - [X] Captures and Capture Matches (Bug: [#11](https://github.com/AntonLydike/filecheck/issues/11))
  - [X] Numeric Captures
  - [ ] Numeric Substitutions (jesus christ, wtf man)
  - [X] Literal matching (`CHECK{LITERAL}`)
  - [X] Weird regex features (`[:xdigits:]` and friends)
  - [X] Correct(?) handling of matching check lines
- **Testing:**
  - [X] Base cases
  - [X] Negative tests
  - [ ] Error messages (started)
  - [ ] Lots of edge cases
  - [ ] MLIR/xDSL integration tests
- **UX:**
  - Good error messages: Error messages are on an okay level, not great, but not terrible either.
    - [X] Parse errors
    - [X] Matching errors
    - [X] Print possible intended matches (could be better still)
    - [X] Malformed regexes
    - [ ] Wrong/unkown command line arguments
    - [ ] Print variables and their origin in error messages
- **Infrastructure:**
  - [X] Formatting: black
  - [X] Pyright
  - [X] `pre-commit`
  - [X] CI for everything

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

### Special Feature Flags:

This version of filecheck implements some non-standard extensions to LLVMs filecheck. These are disabled by default but
can be enabled through the environment variable `FILECHECK_FEATURE_ENABLE=...`. Avialable extensions are documented here:

- `MLIR_REGEX_CLS`: Add additional special regex matchers to match MLIR/LLVM constructs:
  - `\V` will match any SSA value name

### Reject Empty Matches

We introduce a new flag called `reject-empty-vars` that throws an error when a capture expression captures an empty
string.
