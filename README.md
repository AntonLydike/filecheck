# filecheck - A Python-native clone of LLVMs FileCheck tool

**Note:** This project is the successor of [mull-project/FileCheck.py](https://github.com/mull-project/FileCheck.py).

This tries to be as close a clone of LLVMs FileCheck as possible, without going crazy. It currently passes 1576 out of
1645 (95.8%) of LLVMs MLIR filecheck tests. We are tracking all 69 remaining test failures in GitHub issues.

There are some features that are left out for now (e.g. parts of
[numeric substitution](https://llvm.org/docs/CommandGuide/FileCheck.html#filecheck-numeric-substitution-blocks)
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
  - [ ] `--implicit-check-not` (Tracked: [#20](https://github.com/AntonLydike/filecheck/issues/20))
  - [X] `--dump-input` (only `fail` and `never` supported)
  - [ ] `--dump-input-context`
  - [ ] `--dump-input-filter`
  - [X] `--enable-var-scope`
  - [X] `-D<VAR=VALUE>`
  - [ ] `-D#<FMT>,<NUMVAR>=<NUMERIC EXPRESSION>`
  - [X] `-version`
  - [ ] `-v`
  - [ ] `-vv`
  - [ ] `--allow-deprecated-dag-overlap`
  - [X] `--allow-empty`
  - [ ] `--color` Colored output is supported and automatically detected. No support for the flag.
- **Base Features:**
  - [X] Regex patterns
  - [X] Captures and Capture Matches (Bug: [#11](https://github.com/AntonLydike/filecheck/issues/11))
  - [X] Numeric Captures
  - [ ] Numeric Substitutions (jesus christ, wtf man) (Tracked: [#45](https://github.com/AntonLydike/filecheck/issues/45))
  - [X] Literal matching (`CHECK{LITERAL}`)
  - [X] Weird regex features (`[:xdigits:]` and friends)
  - [X] Correct(?) handling of matching check lines (Bug: [#22](https://github.com/AntonLydike/filecheck/issues/22))
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

### Better Regexes:
We use pythons regex library, which is a flavour of a Perl compatible regular expression (PCRE), instead of FileChecks
POSIX regex flavour.

**Example:**
```
// LLVM filecheck:
// CHECK: %{{[[:alnum:]]+}}, %{{[[:digit:]]+}}

// our fileheck:
// CHECK: %{{[a-zA-Z0-9]+}}, %{{\d+}}
```

Some effort is made to translate character classes from POSIX to PCRE, although it might be wrong in edge cases.

### Relaxed Matching:

We relax some of the matching rules, like:

- Allow a file to start with `CHECK-NEXT`


### No Numerical Substitution:

This is used in 2 out of 1645 tests in our benchmark (upstream MLIR tests).

While our filecheck supports [numeric capture](https://llvm.org/docs/CommandGuide/FileCheck.html#filecheck-numeric-substitution-blocks)
(`[[#%.3x,VAR:]]` will capture a three-digit hex number), we don't support arithmetic expressions on these captured
values at the moment.

### Special Feature Flags:

This version of filecheck implements some non-standard extensions to LLVMs filecheck. These are disabled by default but
can be enabled through the environment variable `FILECHECK_FEATURE_ENABLE=...`. Avialable extensions are documented here:

- `MLIR_REGEX_CLS`: Add additional special regex matchers to match MLIR/LLVM constructs:
  - `\V` will match any SSA value name

### Reject Empty Captures:

We introduce a new flag called `reject-empty-vars` that throws an error when a capture expression captures an empty
string.
