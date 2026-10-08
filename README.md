# Abathur

A Claude Code skill for shortening Korean responses, with a benchmark tool to measure which edits reduce token counts.

This project builds on [caveman](https://github.com/JuliusBrussee/caveman). Its contribution is a measured corpus of Korean compression rules; the author uses caveman for everyday work.

## Measurements

Five sample responses dropped from 446 to 142 tokens, a 68% reduction using tiktoken's `o200k_base`. This is a controlled benchmark, not a saving measured across real coding sessions.

Shorter text does not always use fewer tokens. Removing spaces increased token counts by 33% in the tested example. Replacing a written number with a digit increased them by 50%. Shortening sentence endings saved 0–43%, with a median of 17%.

Most savings come from removing greetings, repetition, and closing offers. Grammar and punctuation contribute less. An arrow saves tokens when it replaces a Korean causal connector, but replacing punctuation produced no saving. The rule does not carry over to English, where `causes` already takes one token.

See [BENCH.md](BENCH.md) for the corpus, full results, and raw experiments. Reproduce the measurements with `python -m abathur bench`.

### Compression rules

| Rule | Saving |
|---|---:|
| Remove greetings and thanks | 100% |
| Remove closing offers | 100% |
| Remove narration of tool use | 100% |
| Use standard technical terms such as API | 76% |
| Remove emoji and decoration | 75% |
| Remove repeated explanations and summaries | 70% |
| Remove hedging | 69% |
| Shorten indirect phrasing | 67% |
| Remove polite acknowledgments | 60% |
| Shorten loanwords using established forms | 50% |
| Remove unnecessary linking adverbs | 46% |
| Omit redundant predicates | 36% |
| Omit particles when their meaning is clear | 33% |
| Shorten sentence endings | 31% |
| Replace loanwords with standard abbreviations | 26% |
| Use noun phrases in lists | 22% |
| Use bullets for unordered lists | 18% |
| Replace causal connectors with arrows | 9% |

Percentages describe individual test pairs and are not additive.

### Rejected rules

| Rule | Saving |
|---|---:|
| Remove spaces | -33% |
| Replace commas and periods with arrows | 0% |
| Use Korean consonant abbreviations | 0% |
| Use Chinese characters | 0% |
| Invent abbreviations | 0% |

### Complete responses

| Sample | Original tokens | Compressed tokens | Saving |
|---|---:|---:|---:|
| Bug explanation | 95 | 28 | 71% |
| Concept explanation | 98 | 28 | 71% |
| Work report | 68 | 17 | 75% |
| Work plan | 84 | 24 | 71% |
| Code review | 101 | 45 | 55% |
| Total | 446 | 142 | 68% |

### Korean and English

These pairs express the same meaning. The average Korean-to-English token ratio in this small sample is 1.70.

| Meaning | Korean tokens | English tokens | Ratio |
|---|---:|---:|---:|
| This function does not validate user input. | 11 | 8 | 1.38x |
| Reuse database connections to reduce overhead. | 16 | 7 | 2.29x |
| All 42 tests passed. | 11 | 6 | 1.83x |
| The entry was not found in the configuration file. | 13 | 10 | 1.30x |
| Average | | | 1.70x |

## Corrections to earlier results

An initial test classified shortened sentence endings as ineffective. Expanding the sample from one sentence to twelve showed a median saving of 16.7%, with a range of 0–43%.

The initial arrow comparison used the wrong baseline: arrows saved tokens against causal connectors and tied against punctuation. An informal database abbreviation, previously described as ineffective, saved 50% in its test pair.

The corpus now separates rules by measured saving. Tests check both classification boundaries:

```text
RULES           saving >= 15%
MARGINAL_RULES  0 < saving < 15%
ANTI_RULES      saving <= 0%
```

Raw experiments cover twelve sentence-ending examples, six arrow alternatives with English controls, six loanword abbreviations, and six rejected candidates. See the [BENCH.md appendix](BENCH.md).

## Installation

### Claude Code skill

```text
/plugin marketplace add nohseongmin/abathur
/plugin install abathur
```

Use `/abathur` to enable the skill and `/abathur lite|full|ultra` to change its intensity. The exact Korean activation and deactivation phrases are listed in [SKILL.md](skills/abathur/SKILL.md).

| Mode | Behavior |
|---|---|
| `lite` | Remove greetings, hedging, and repetition; keep complete, polite sentences. |
| `full` | Use compact lists, omit obvious particles and redundant predicates, and remove decoration. Default. |
| `ultra` | Use one fact per line and list items instead of sentences. |

Compression relaxes for security warnings, irreversible actions, ordered procedures, and explanations that would otherwise become ambiguous.

### Benchmark tool

```bash
pip install -e .
python -m abathur bench
python -m abathur count README.md --price-per-mtok 15
```

Use `--format markdown|json` to choose the output format or `--encoding cl100k_base` to compare encodings. To use Anthropic's token-counting API, set `ANTHROPIC_API_KEY` and run:

```bash
python -m abathur bench --anthropic
```

Only `--anthropic` sends text to an external service. The default counter runs locally, although tiktoken downloads its BPE encoding file on first use and caches it afterward.

## Limitations

- Claude's tokenizer is not public. `o200k_base` is a proxy, and CI also checks `cl100k_base`. Use `--anthropic` for Claude token counts.
- The 68% result comes from controlled examples. Code blocks, paths, and error messages are preserved, so real coding sessions may save less.
- The benchmark measures sentences and sample responses. There is no long-term session A/B study yet.

## Related projects

| Project | Approach | Relationship |
|---|---|---|
| [caveman](https://github.com/JuliusBrussee/caveman) | Compress responses while preserving the user's language. | Basis for the project and its measurement approach. |
| [cavemankorean](https://github.com/blacknabis/cavemankorean) | Add Korean rules to a caveman fork. | Closest prior work. Several rules were confirmed here; its reported 65–75% saving comes from English tasks. |
| [k-laude](https://github.com/realkim93/k-laude) | Translate Korean input to English with an on-device model. | Addresses input tokens; requires macOS 26 and Apple Silicon. |
| [tokensave](https://github.com/epoko77-ai/tokensave) | Audit model tiers and caching in multi-agent harnesses. | Addresses harness costs. |

## Adding a rule

1. Add `verbose` and `terse` pairs to [src/abathur/rules.py](src/abathur/rules.py).
2. Run `python -m abathur bench`.
3. Use `RULES` for savings of at least 15%, `MARGINAL_RULES` for savings between 0% and 15%, or `ANTI_RULES` for no saving.
4. Run `pytest`, then add accepted guidance to [SKILL.md](skills/abathur/SKILL.md).

Use several examples before rejecting a rule. Keep unsuccessful experiments in the corpus so their results can be checked later.

## Files

```text
skills/abathur/SKILL.md   Response style and exceptions
src/abathur/rules.py      Rule corpus
src/abathur/bench.py      Measurements
src/abathur/cli.py        bench and count commands
tests/                   Rule and documentation checks
BENCH.md                 Generated benchmark tables
BLUEPRINT.md             Design notes
```

## License

MIT.
