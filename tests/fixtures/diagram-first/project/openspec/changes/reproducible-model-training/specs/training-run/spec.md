# Run training reproducibly

Use the same specified model settings for every full training run. Supporting notes call these settings the "fixed recipe".

Run a small trial first and check that inputs load, training completes, and output can be saved. Supporting notes call this a "smoke gate". Start full training only if every trial check passes; otherwise stop and report the failed checks.

When resuming a run, load its saved settings and sample assignments. Never include the evaluation answers in training.
