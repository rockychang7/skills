# Project settings (.req-profile.json)

A JSON object in the project root holding what differs per project and cannot
be guessed. Every key is optional. The script finds the file by walking up
from the directory it runs in. `config set` writes `workspace` and `lang`;
change other keys only when the user asks, because the file is usually
committed and teammates share it.

| Key | Used by | What | Default |
| --- | --- | --- | --- |
| `workspace` | script | Requirements folder, relative to the project root. Set with `config set workspace <path>` | user settings, else ask |
| `lang` | script | Language of the generated files: `zh-CN` or `en` | user settings, else `zh-CN` |
| `envs` | script | Environments every config needs a value for | `["dev", "test", "prod"]` |
| `clients` | you | The project's frontends, `[{"id": "b", "name": "B 端后台"}]`; use these IDs and names in the analysis `clients` | find them in the code |
| `facts` | you | A file describing where this project keeps its facts; read it before checking the code | this skill's own list |
| `table_rules` | you | The team's table conventions; read it before writing `backend.tables` | none |
| `openapi` | script | Where the API description is: a URL (`http://localhost:8080/v3/api-docs`) or a file path relative to the project root; `contract` uses it when given no `--openapi` | none: pass `--openapi` |

```json
{
  "workspace": "docs/process/requirements",
  "envs": ["dev", "test", "prod"],
  "clients": [{ "id": "b", "name": "B 端后台" }, { "id": "c", "name": "C 端小程序" }],
  "facts": "docs/req-facts.md"
}
```

Settings come from, first match wins: the command line (`--dir`, `--lang`),
this file, then the user settings in
`~/.config/rein-analyzing-requirements/config.json` (`$XDG_CONFIG_HOME` when
set), which hold only `workspace` and `lang`.
