# Data input

Place Aswath Damodaran's historical return CSV at:

- `data/histretSP.csv`

The analysis script auto-detects columns for:

- Year
- S&P 500 annual return (nominal)
- 10-year Treasury return (nominal)
- CPI inflation

Then run:

```bash
python run_analysis.py
```

Outputs are written to `outputs/`.
