# promptfoo configs

Assertion-based model comparison with [promptfoo](https://www.promptfoo.dev/). The configs define the prompts, the models to compare (local Ollama and OpenRouter) and the assertions each answer must satisfy.

| Config | Focus |
|---|---|
| `configs/basic_text_quick.yaml` | One question, many models. Use it to check your setup. |
| `configs/basic_text.yaml` | Short factual and explanatory answers across many models |
| `configs/code_generation.yaml` | Code generation tasks |
| `configs/reasoning.yaml` | Logic and reasoning questions |
| `configs/seo_writing.yaml` | Long-form writing, checked with regex, JavaScript and `llm-rubric` assertions |

## Setup

Requires Node.js and pnpm. Ollama is optional and only needed for the `ollama:` providers.

```bash
cp .env.example .env     # set OPENROUTER_API_KEY
pnpm install
```

`package.json` allows the install script of `better-sqlite3` (`pnpm.onlyBuiltDependencies`). promptfoo needs that native binding for its local result database.

## Run

```bash
pnpm exec promptfoo validate config -c configs/basic_text_quick.yaml    # check a config without calling models
pnpm run eval:basic                                                      # or eval:code, eval:reasoning, eval:all
pnpm exec promptfoo eval -c configs/basic_text.yaml --output results/basic_text_results.json
pnpm run view                                                            # web viewer on http://localhost:15500
```

The same from Python: `python promptfoo_cli.py run basic|code|reasoning|all` and `python promptfoo_cli.py view`.

promptfoo caches responses. `pnpm run cache:clear` forces fresh calls on the next run.

## Rank models across runs

`analyze_rankings.py` reads every `results/*.json`, aggregates pass rate, score and latency per model, and writes `model_rankings.json`:

```bash
python analyze_rankings.py
```

`model_rankings.json` in this repository is a sample output. Its latency values are affected by cache hits and should not be compared. Run output in `results/` is git-ignored; a small raw example is in `../results/basic_text_quick_results.json`.
