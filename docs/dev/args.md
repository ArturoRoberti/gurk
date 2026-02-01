# Argument structure
Each `args` section of a task definition has to have the following structure:
```yaml
args:
  <argument_name>:
    help: <string> (required)
    default: <str | bool | null>
    nargs: <nargs-spec>
    choices: <list of strings>
    mutex: <group_name>
```

# Final argument types in scripts

The following describes the resulting argument types as seen in the scripts using the arguments defined via the `args` dictionary. Not that gurk bash/python type equivalents are as follows:
| Python Equivalent | Bash Equivalent             |
|-------------------| ----------------------------|
| `str`             | string                      |
| `list[str]`       | array of strings            |
| `bool`            | string (`"true"`/`"false"`) |
| `None`            | empty string (`""`)         |

If a boolean default is given, the argument becomes an optional flag and the resulting type is `bool`.

Otherwise, the following tables summarize the resulting types based on `default`, `nargs` and if the argument is passed or not:

## Table 1: Resulting Type based on `default` and `nargs`
|                                  | `default` given                                                                                       | No `default` given / `default: null` |
|---------------------------------:|:------------------------------------------------------------------------------------------------------|:-------------------------------------|
| `nargs` given                    | if the argument is not passed:<br>&nbsp;&nbsp; `type(<default>)`<br>else:<br>&nbsp;&nbsp; See table 2 | See table 2                          |
| No `nargs` given / `nargs: null` | if the argument is not passed:<br>&nbsp;&nbsp; `type(<default>)`<br>else:<br>&nbsp;&nbsp; `str`       |  `str`                               |

## Table 2: Resulting Type based on `nargs` and if the argument is passed
| Is the argument passed? | `nargs="?"` | `nargs="*"` | `nargs=<"+" \| N>` |
|:-----------------------:|:-----------:|:-----------:|:------------------:|
| Yes                     | `str`       | `list[str]` | `list[str]`        |
| No                      | `None`      | empty list  | /                  |

> **NOTE:** If no default is given or nargs is `"+"` / N (int), the argument becomes required.

Further independently available fields are:
- `help` (REQUIRED): Help text for the argument. Resulting type is unaffected
- `mutex`: Mutually exclusive group name to assign the argument to. Resulting type is unaffected
- `choices`: Available choices for the argument (supports wildcards). This limits `default` and resulting types to `str` or `list[str]` and `nargs` to ones with at least one value.

# Forbidden values/combinations summary
- An argument name is not a `str` beginning with `--<plugin>-` or is not unique in the plugin's entire argument set.
- An argument definition contains any extra/unknown keys.
- An argument is the sole member of a `mutex` group.
- `nargs` is neither an `int` nor one of the symbols `"?"`, `"*"`, `"+"`.
- `choices`
  - is not a non-empty list of strings.
  - contains a `default` value that is not `null`, a `str` or non-empty `list[str]`.
  - contains a `default` value (not `null`) that does not match any choice (including wildcards).
  - Has no default (resp. `default: null`) **and** `nargs` is `"?"` or `"*"`.
- A boolean flag argument (`default` is a `bool`) has fields other than `help`, `default` and `mutex`.

# Allowed examples

**Boolean flags** (→ Resulting Type: `bool`)
| Args Dict | Equivalent Argparse  |
| --------- | -------------------- |
| <pre lang="yaml">--p-flag:&#13;  help: "help_text"&#13;  default: true</pre>  | <pre lang="python">parser.add_argument(&#13;  "--p-flag",&#13;  help="help_text",&#13;  action="store_false"&#13;)</pre> |
| <pre lang="yaml">--p-flag:&#13;  help: "help_text"&#13;  default: false</pre> | <pre lang="python">parser.add_argument(&#13;  "--p-flag",&#13;  help="help_text",&#13;  action="store_true"&#13;)</pre>  |

**Options**
| Args Dict | Equivalent Argparse  | Resulting Type |
| --------- | -------------------- | -------------- |
| <pre lang="yaml">--p-name:&#13;  help: "help_text"</pre>                                                        | <pre lang="python">parser.add_argument(&#13;  "--p-name",&#13;  help="help_text",&#13;  required=True,&#13;)</pre>                          | `str`                                                                                                                |
| <pre lang="yaml">--p-name:&#13;  help: "help_text"&#13;  default: \<default\></pre>                             | <pre lang="python">parser.add_argument(&#13;  "--p-name",&#13;  help="help_text",&#13;  default=\<default\>,&#13;)</pre>                    | if a value is passed:<br>&nbsp;&nbsp; `str`<br>else:<br>&nbsp;&nbsp; `type(<default>)`                               |
| <pre lang="yaml">--p-opt:&#13;  help: "help_text"&#13;  nargs: "?"&#13;</pre>                                   | <pre lang="python">parser.add_argument(&#13;  "--p-opt",&#13;  help="help_text",&#13;  nargs="?",&#13;)</pre>                               | if a value is passed:<br>&nbsp;&nbsp;`str`<br>else:<br>&nbsp;&nbsp;`None`                                            |
| <pre lang="yaml">--p-opt:&#13;  help: "help_text"&#13;  nargs: "\*"&#13;</pre>                                  | <pre lang="python">parser.add_argument(&#13;  "--p-opt",&#13;  help="help_text",&#13;  nargs="\*",&#13;)</pre>                              | if values are passed:<br>&nbsp;&nbsp; `list[str]`<br>else:<br>&nbsp;&nbsp; `[]`                                      |
| <pre lang="yaml">--p-opt:&#13;  help: "help_text"&#13;  nargs: \<"+" \| N\>&#13;</pre>                          | <pre lang="python">parser.add_argument(&#13;  "--p-opt",&#13;  help="help_text",&#13;  nargs=\<"+" \| N\>&#13;  required=True&#13;)</pre>   | `list[str]`                                                                                                          |
| <pre lang="yaml">--p-opt:&#13;  help: "help_text"&#13;  default: \<default\>&#13;  nargs: \<spec\>&#13;</pre>   | <pre lang="python">parser.add_argument(&#13;  "--p-opt",&#13;  help="help_text",&#13;  default=\<default\>&#13;  nargs=\<spec\>&#13;)</pre> | if values are passed:<br>&nbsp;&nbsp; [see above for narg-dependent type]<br>else:<br>&nbsp;&nbsp; `type(<default>)` |
