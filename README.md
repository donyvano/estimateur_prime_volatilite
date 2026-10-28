# Volatility Risk Premium on the S&P 500

> Measure, explain and forecast the gap between the volatility the market **expects** (implied, VIX) and the volatility that **actually happens** (realized).

**Results:** _coming at the end of V1 (step 5)._

**Website:** _coming at the end of V1._

---

## The idea in one picture

```
   Market prices ──► Realized volatility ──┐
   (^GSPC, SPY)        "what happened"     │
                                           ├──► VRP = implied − future realized
   VIX / options ──► Implied volatility ───┘          │
                     "what was expected"              ├──► Forecast (HAR, GARCH, LightGBM)
                                                      └──► Backtest: sell volatility
```

## Roadmap

**V1: measure**
- [x] 0. Project setup (structure, environment, CI)
- [ ] 1. Data pipeline (yfinance + parquet cache)
- [ ] 2. Realized volatility (close-to-close, Parkinson)
- [ ] 3. Black-Scholes, greeks and Monte Carlo pricer
- [ ] 4. Implied volatility, smile and surface
- [ ] 5. Volatility risk premium + first website

**V2: forecast and trade**
- [ ] 6. Volatility forecasting (walk-forward validation)
- [ ] 7. Short volatility backtest
- [ ] 8. Methodology report and final website

## Quickstart

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Project structure

```
config/          single YAML config (tickers, dates, windows, seed)
data/            parquet cache (git-ignored)
src/vrp/         all business logic
tests/           pytest suite (incl. explicit look-ahead bias tests)
notebooks/       exploration only
web/             static website (reads JSON from web/data/)
docs/            methodology and interview pitch
```

## Limitations

- `yfinance` does not provide historical option chains: the historical VRP relies on the VIX, and the volatility surface on a dated snapshot of the SPY chain.

## License

MIT
