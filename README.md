# custom.remote.python.calculated_metrics
Dynatrace ActiveGate extension generating values for a custom metric from a set of existing metrics and a formula (math expression).

Prerequisites: deployed ActiveGate that can reach out to Server's API endpoints.

- This extension does not work yet with dimensions. It was tested on simple, one dimension, metrics...
- The ultimate goal was to be able to alert on the result of a ratio (or other expression) taken from existing metrics; thus requiring to produce a new metrics upon which custom alerting could be configured...
- This implementation should hopefully be a temporary solution, until the new metrics explorer provides this capability...

## Inputs
![Example inputs](images/sample_inputs.png)

## Outputs
![Example outputs](images/sample_outputs.png)

