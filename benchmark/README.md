# Cross-POC comparison

`pay-482-cases.json` defines case inputs and expected results. Record the shared definition and case versions, POC and platform versions, model and parameters, actual result for each case, execution time, errors, and available token usage. Use the same cases, model settings, and test conditions for comparisons, and mark any differences when matching settings are unavailable.

Record both whether the flow completed and whether it returned the correct result on failure. A required agent timeout in `ready` should produce `UNKNOWN`, which indicates correct failure handling rather than a fully successful run. Retain accessible source evidence for human actions and model calls.
