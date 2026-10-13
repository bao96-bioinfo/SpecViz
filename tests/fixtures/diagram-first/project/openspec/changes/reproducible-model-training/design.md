# Model training design

## Prepare the samples

Put the datasets into one consistent format. Divide the samples into a training group and an evaluation group, and save those assignments.

## Train the model

Send only the training group to model training. Use the same settings for every run. Run a small trial first; start the full run only if the trial passes its checks. Otherwise stop and report the failed checks.

## Keep evaluation answers separate

Keep the evaluation group's known answers separate from training and prediction. Do not reveal them to the model.

## Make predictions

After training finishes, use the trained model to predict answers for the evaluation samples without revealing their known answers.

## Compare predictions with answers

Compare the predictions with the answers kept aside earlier. The acceptable error threshold is not yet decided; report the measured error without declaring the model ready for use.

## Save the run records

After evaluation, save the settings, sample assignments, predictions, and measured error so another person can repeat the run and check its results.
