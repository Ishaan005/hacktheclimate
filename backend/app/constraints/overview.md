## Overview

```mermaid 
graph TB

0["Raw data"]

1["model"]

2["input data"]

3["constraint checker"]

4["return pass / fail"]

0 --> 1
1 --> 2
2 --> 3 
3 --> 4
```

Raw data
- hacktheclimate/data/processed/canonical_ie.csv

model
- unsure

input data
- taken from the model / raw data

constraint checker
- snsp
- thermal_limit
- asset_availability

return
- pass
- fail
