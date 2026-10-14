# Speed up training

Avoid copying the complete training data when preparing each batch. The faster path must produce the same numerical results as the original path. Record the measured peak memory and running time. Use these improvements inside model training only after the equivalence check succeeds.
