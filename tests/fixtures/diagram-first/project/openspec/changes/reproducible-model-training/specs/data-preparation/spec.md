# Prepare consistent samples

Combine datasets using the same field names and units. Divide the samples into training and evaluation groups before training starts.

Save each sample's group assignment. Supporting notes call this a "persisted split": resuming a run must reuse the same saved assignments instead of dividing the samples again.
