# AI Query Helpers

This package contains the first deterministic layer for the natural-language AI interface.

## Scope

The AI layer is currently authorized to read only the World Triathlon derived outputs listed in `sources.py`. CCNC files, raw files, and historical inventories are intentionally outside the query scope for now.

## Normalization

`normalization.py` converts user-facing or natural-language values into canonical table values:

- modalities: `Sprint`, `Standard`
- sex categories: `F`, `O`
- age groups by modality, including `Sprint` `16-19` and `Standard` `18-19`
- segments: `Swim`, `T1`, `Bike`, `T2`, `Run`, `Total`
- pairs: `swim_bike`, `swim_run`, `bike_run`
- times: numeric seconds from values such as `1:05:20`, `12:34`, `45 min`, or `1h 2m 3s`

## Next Step

`coverage.py` validates whether a normalized query can be answered from the authorized workbooks. It reads and caches the compact coverage sheets, and it enforces public category rules such as Sprint `16-19` and Standard `18-19`.

The next step is to add deterministic percentile lookup functions for 1D curves.

## 1D Lookups

`lookups_1d.py` provides deterministic lookup and inverse lookup for:

- official total-time curves
- segment curves, including segment-level `Total`

Returned display times use `h:mm:ss` when the value is one hour or longer, and `mm:ss` below one hour.

## Derived Totals

`derived_totals.py` estimates total time from the three main segments:

`swim + bike + run + average T1 + average T2`

The transition averages come from the same modality, sex category, and age group in the segment curves. The estimated total can then be compared against the official total-time curve.

## 2D Pair Lookups

`lookups_2d.py` provides deterministic lookup for swim-bike, swim-run, and bike-run pair planes:

- pair percentile from two marginal percentiles
- pair percentile from two segment times
- axis times plus joint percentile from two marginal percentiles

## 3D SBR Cube Lookups

`lookups_3d.py` provides deterministic lookup for the swim-bike-run cube:

- SBR percentile from three marginal percentiles
- SBR percentile from swim, bike, and run times
- axis times plus joint SBR percentile from three marginal percentiles

## Explanations

`explain.py` converts structured results into concise English explanations. It does not perform new calculations.

## Router

`router.py` maps deterministic intent payloads to the approved lookup functions. It also supports multi-step query plans and stops at the first invalid step.

## Orchestrator

`orchestrator.py` composes approved router intents into higher-level deterministic workflows, such as:

- evaluating a swim-bike-run profile
- finding the weakest main segment
- comparing current and target segment scenarios

## Tool Schema

`tool_schema.py` defines the LLM-facing contract: approved tools, required fields, clarification rules, and global constraints.

## Conditional Profiles

`conditional.py` calculates conditional segment percentiles from cumulative joint distributions using Bayes ratios. Conditions are cumulative thresholds, such as "Swim at least as good as 32:00"; they are not equality matches.

## Query Agent

`query_agent.py` is the structured-payload bridge for a future natural-language layer. It checks required fields, asks for clarification when needed, routes approved intents, and returns result plus explanation.

## Parser Contract

`parser_contract.py` defines the natural-language parser contract for a future LLM call. It provides the system prompt, allowed JSON output shapes, and validation before structured payloads reach the query agent.

## LLM Client

`llm_client.py` connects the parser contract to a real OpenAI Responses API call. It uses `OPENAI_API_KEY` and `AI_QUERY_MODEL`, defaulting to `gpt-5-nano`. Tests use fake transports and do not make live API calls.

## CLI Smoke Test

From the repository root:

```powershell
$env:OPENAI_API_KEY="..."
$env:AI_QUERY_MODEL="gpt-5-nano"
python -m WT.scripts.ai_query_cli "What percentile is a 45:00 run for Standard O 40-44?"
```

Use `--json` to inspect the parsed payload, result, and explanation.
