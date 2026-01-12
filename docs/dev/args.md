---

# Custom ArgParser YAML/Dict Schema

This document explains the structure and semantics of the `args` dictionary for defining command-line arguments. Users can define their own argument specifications using this schema.

## Top-Level Structure

```yaml
args:
  <argument_name>:
    help: <string>
    default: <value | null>
    nargs: <nargs-spec>
    choices: <list of strings>
    mutex: <group_name>
```

* `args` is a mapping from argument names to their specification.
* All fields under each argument are optional unless specified.

---

## Argument Fields

### `help` (string)

Human-readable description shown in the `--help` output.

Example:

```yaml
help: Input file to process
```

### `default` (string | bool | null)

Specifies the default value if the argument is not provided.

* **No `default` field** → the argument is required.
* **`default: null`** → the argument is optional and will use `None` if not provided.
* **Boolean (`true`/`false`)** → treated as a flag (`store_true` / `store_false`).

Examples:

```yaml
# Required argument (no default)
config:
  help: Path to config file

# Optional argument with default
mode:
  help: Run mode
  default: train

# Boolean flag
verbose:
  help: Enable verbose logging
  default: false
```

### `nargs` (string | integer)

Specifies how many command-line tokens the argument consumes.

Supported values:

| Value          | Meaning      | Result                |
| -------------- | ------------ | --------------------- |
| None / omitted | exactly one  | str                   |
| 1              | exactly one  | str in list ([value]) |
| `?`            | zero or one  | str or None           |
| `*`            | zero or more | list[str]             |
| `+`            | one or more  | list[str]             |
| N > 1          | exactly N    | list[str]             |

Notes:

* Scalars are always strings.
* Lists are always `list[str]`.
* Boolean flags cannot have `nargs`.

### `choices` (list of strings)

Specifies a set of valid values.

Example:

```yaml
mode:
  help: Run mode
  choices: [train, eval]
```

* Only values in the `choices` list are accepted.
* Works for scalar and list arguments.

### `mutex` (string)

Specifies a mutually exclusive group.

* Arguments with the same `mutex` value cannot take effect simultaneously.
* Optional arguments only.
* Example:

```yaml
cpu:
  help: Use CPU
  default: false
  mutex: device

gpu:
  help: Use GPU
  default: false
  mutex: device
```

* Argparse enforces mutual exclusion based on **values differing from defaults**, not mere presence.

---

## Type System

* Scalars: `str`
* Lists: `list[str]`
* Boolean flags: `bool` (inferred from default)
* Type is inferred from `default` or `nargs`.

---

## Argument Requirement Semantics

| YAML Setting       | Meaning                                                     |
| ------------------ | ----------------------------------------------------------- |
| No `default`       | Required argument. Parser enforces presence.                |
| `default: None`    | Optional argument. Value is `None` if flag not provided.    |
| `default: <value>` | Optional argument. Uses provided default if flag not given. |

* Required flags must be validated post-parse.
* Optional flags with default allow presence with or without specifying a value (via `nargs="?"`).

---

## Complete Example

```yaml
args:
  --input:
    help: Input file
    nargs: ?
    default: input.txt
    mutex: filemutex

  --output:
    help: Output file
    default: output.txt
    mutex: filemutex

  --files:
    help: Extra files
    nargs: +

  --mode:
    help: Run mode
    choices: [train, eval]
    default: train

  --verbose:
    help: Verbose logging
    default: false

  --cpu:
    help: Use CPU
    default: false
    mutex: device

  --gpu:
    help: Use GPU
    default: false
    mutex: device
```

* `--input` and `--output` are in the same mutex group `filemutex`.
* `--cpu` and `--gpu` are in `device` mutex group.
* `--files` requires at least one value.
* `--verbose` is a boolean flag.
* `--mode` has a default and a set of allowed choices.

---

## Notes for Users

* All scalars are strings; numeric conversion must be handled separately if needed.
* Boolean flags are inferred automatically from `default: true/false`.
* `nargs` determines whether the argument is scalar or a list.
* `choices` restricts valid input values.
* `mutex` groups ensure mutually exclusive options, enforced on values differing from defaults.
* Arguments without `default` are required and enforced by argparse.
* Arguments with `default` but no value provided are optional and use the default.
