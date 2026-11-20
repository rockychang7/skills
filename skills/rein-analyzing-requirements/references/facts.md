# Where to find the facts

If `.req-profile.json` names a `facts` file, read it first: it describes this
project and comes before this list. What you cannot
find becomes a question; never guess. Only read: run no write queries,
migrations or deploys.

| What | Where |
| --- | --- |
| The document | The file, link or text the user gave. A link you cannot open (login, permissions): ask the user to export it as Markdown or text |
| Images in the document | Keep the ones that explain what gets built (screens, flow charts, tables drawn as images) in `<requirement folder>/source/img/`, look at each, and list them in `prototypes.images` |
| Existing APIs | Search for route declarations: `@GetMapping` / `@RequestMapping` (Spring), `router.get(` (Express, Koa), `@app.get` / `@router.get` (FastAPI, Flask), `HandleFunc` / `.GET(` (Go), `config/routes.rb` (Rails). Follow the handler into its service to write `now` |
| Who calls an API today (`online`) | Other services and frontends in the workspace, if present. What you could not check, say so in `online` |
| Table structure | Migrations (Flyway `V*__*.sql`, Liquibase, `schema.prisma`, Alembic, `db/migrate`), then ORM entities or models. None: ask the user for `SHOW CREATE TABLE` |
| Row counts, existing data | Not in the code. When it matters (data changes, old rows), write a question or ask the user to run a count |
| Configs and switches | `application*.yml`, `.env*`, `config/` folders, environment variables. Values per environment you cannot see: write a question |
| `meta.code_commit` | `git rev-parse --abbrev-ref HEAD` and `git rev-parse --short HEAD`, written `dev@1a2b3c4`. Add `+changes` when the working tree has uncommitted changes; `none` outside git |
| API description (OpenAPI) | springdoc `/v3/api-docs`, FastAPI `/openapi.json`, NestJS Swagger `/api-json`; otherwise the code. Needed later for the frontend guide |
