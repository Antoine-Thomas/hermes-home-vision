# Dependency budget and pin discipline

Installing a chain into a fresh venv is not free and not neutral: pip resolves the **newest** version
of every package, and a new major version is exactly what breaks a working chain.

## Price the install before paying it

- A large wheel (torch and friends, 2-3 GB) is often already in the pip cache. Probe with
  `python -m pip install --dry-run <pkg>` and read for `Using cached <wheel>`.
- **Do not hunt for wheels by size in the cache directory.** Modern pip stores them as blobs under
  `pip/Cache/http-v2`, so a filename search reports an empty cache that is in fact full. The
  `--dry-run` probe is the reliable test: a few seconds, and it answers exactly the right question.
- **Pick the build that is already cached.** Several CUDA builds of the same package exist. The build
  this machine already has — and has already proven in another venv — is the one to install, even when
  the documentation points at a different index URL. The gigabytes saved are what the model weights need.
- Report the download total against the budget the user set, and say which part was avoided and how.

## Pin a known-good SET in one command

```
python -m pip install "transformers==4.57.6" "diffusers==0.36.0" "peft>=0.17" "accelerate>=1.4"
```

- One resolution pass. Iterating package by package burns cycles and ends in
  `ERROR: ResolutionImpossible: ... conflicting dependencies` — which means the pins contradict each
  other and no amount of retrying fixes it: go back to a set proven on this machine.
- A conflicting pair is often reported only after a partial install: `pip list` then shows an
  incoherent mix (one package already downgraded, another not), and the next error is different again.
  Re-install the whole set, never the single package named in the current error.

## The traceback names the wrong package

- An import failure inside library A that points at library B is usually a mismatched major version of
  B, or of a third package that A and B both import. Dump the real set with `python -m pip list` and
  compare it against the known-good set before believing the message.
- A known case: `transformers` 5.x makes `diffusers` and `peft` imports fail with messages that name
  `peft` (`name 'nn' is not defined`, `cannot import name 'disable_input_dtype_casting' from
  'peft.helpers'`). The fix is in transformers, not in peft.
- Never let a major version float: pin explicitly inside the chain's own venv, and re-check the pins
  after any install that touches shared libraries.

## Validating an install without running the real workload

- Import the top-level symbol you will actually use (`from diffusers import StableDiffusionXLPipeline`)
  before launching anything: it catches the whole class of mismatch in one second.
- Prefer a tiny 3-step run to validate a chain end to end; a full training run is a terrible first
  test of an install.

## Escalation rule

On a dependency conflict, stop and report the exact error. Do not improvise a workaround, do not
silently downgrade a package another venv depends on, and do not escalate to a heavier alternative
(Docker, another framework) without an explicit go-ahead.
