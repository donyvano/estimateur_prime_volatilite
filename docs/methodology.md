# Methodology

**Question.** How much does the option market overpay for volatility on the S&P 500, can the realized volatility be forecast better than the market does, and is selling the premium a good trade once tail risk is accounted for?

All numbers below come from `python -m vrp.pipeline` on data up to 30 October 2026. Every parameter lives in [`config/config.yaml`](../config/config.yaml).

---

## 1. Data and cleaning

| Series | Source | Use |
|---|---|---|
| `^GSPC` S&P 500 daily OHLC, 2005 → today | Yahoo Finance | realized volatility |
| `^VIX` daily close | Yahoo Finance | 30-day implied volatility |
| `^IRX` 13-week T-bill yield | Yahoo Finance | risk-free rate |
| `SPY` option chain, one snapshot | Yahoo Finance | smile and surface |

Raw downloads are cached as parquet in `data/raw/` (git-ignored) so that runs are reproducible offline. `clean_prices` sorts, removes duplicated dates and non-positive prices (rates are allowed to be zero: T-bills yielded 0% in 2020). `validate_prices` fails loudly on non-increasing dates, negative prices, closes outside `[low, high]` (0.5% tolerance for Yahoo rounding) and gaps longer than 5 calendar days. The longest legitimate gap since 2005 is Hurricane Sandy (Friday → Wednesday). Series are joined on common trading days (5,492 days). The T-bill rate is forward-filled on bond-market holidays, which uses past information only.

**Known limitation.** Yahoo does not provide historical option chains. The historical premium therefore relies on the VIX, and the volatility surface on a single dated snapshot. Outside US market hours Yahoo reports zero bid/ask. In that case the snapshot falls back to the **last traded price**, only for contracts traded during the last session with non-zero volume. These prices are asynchronous, which shows up as small wiggles in the smile. Re-running with `--refresh-options` during US hours gives a bid/ask mid snapshot.

## 2. Realized volatility

Close-to-close estimator over `n = 21` daily log-returns, annualized with 252 trading days:

$$\sigma_t = \sqrt{\frac{252}{n}\sum_{i=t-n+1}^{t} r_i^2}, \qquad r_i = \ln(P_i/P_{i-1})$$

Returns are **not demeaned**: this is the variance-swap convention, and the VIX is a variance-swap rate. The daily mean (~0.03%) is negligible next to a ~1% daily move and noisy to estimate. A `demean=True` option gives the textbook sample standard deviation (tested against pandas).

The **Parkinson** range estimator, $\sigma^2 = \frac{252}{4\ln 2}\,\overline{\ln(H/L)^2}$, is computed for comparison. It runs at 0.82× the close-to-close estimate in median because it misses overnight gaps.

Facts: median realized vol is 12.8%, the maximum is 96% (6 April 2020), and the 21-day autocorrelation is 0.66 (volatility clustering).

## 3. Option pricing: Black-Scholes and Monte Carlo

`black_scholes.py` implements vectorized European prices with a continuous dividend yield, plus delta, gamma, vega and theta. Degenerate cases ($\sigma\sqrt{T} \to 0$) return the discounted intrinsic value on the forward. Tests check textbook values (Hull: call 10.4506, put 5.5735), put-call parity to $10^{-10}$, price bounds, monotonicity in $\sigma$, and **every greek against central finite differences**.

`monte_carlo.py` simulates the exact GBM terminal distribution (no time discretization is needed for a European payoff) and reports the standard error. On a 1-month ATM SPY call, the error falls from $3.8 at 100 paths to $0.002 at 300,000, and $\text{std error} \times \sqrt{N}$ stays flat at ≈ 21.5: the $1/\sqrt{N}$ rate predicted by the central limit theorem. Antithetic variates reduce the error at equal $N$. In the antithetic case the error is computed on pair means, because mirrored paths are not independent.

## 4. Implied volatility and surface

**Inversion.** Newton-Raphson on vega, started at the Brenner-Subrahmanyam approximation $\sigma_0 = \sqrt{2\pi/T}\,C/S$. If vega vanishes (deep OTM, short maturity) or the iterate leaves $[10^{-4}, 5]$, the solver falls back to Brent's method on that bracket, which always converges because Black-Scholes is monotone in $\sigma$. Prices outside the no-arbitrage bounds return `NaN`. Round-trip tests run over 5 vols × 5 strikes × 2 types.

**Forward and dividends.** For each expiry, the forward is backed out from put-call parity, $F = K + e^{rT}(C - P)$, using the median over the 6 strikes closest to spot. The dividend yield implied by $F$ is then used in Black-Scholes, so no dividend assumption is needed.

**Filters** (30/10/2026 snapshot: 7,651 quotes → 2,272 after filters 1–5 → 2,266 after the outlier filter):
1. price ≥ $0.10, far from the $0.01 tick where implied vol is meaningless;
2. maturity between 7 and 400 days;
3. when bid/ask are quoted: bid ≥ $0.05, relative spread ≤ 25%, open interest ≥ 10;
4. moneyness $K/F \in [0.75, 1.25]$;
5. **out-of-the-money options only**: puts below the forward, calls above. OTM options are the liquid ones, and since SPY options are American, OTM contracts carry almost no early-exercise premium, so the European formula is a good approximation;
6. a per-expiry outlier filter that drops points more than 3 vol points away from the rolling median of their neighbours.

For display, smiles, term structure and surface use the **standard monthly expiries** (third Friday), which are the most traded. The surface is linearly interpolated on a (moneyness × $\sqrt{T}$) grid, with no extrapolation outside the convex hull of the data.

**Snapshot (30/10/2026).** ATM 1-month vol is 15.8% (median over the 21–45-day expiries), the 90% put trades at 27.1% and the 110% call at 12.4%: a **14.7-point skew**. The VIX (19.4%) sits above ATM vol because it aggregates the whole strike range, including the expensive puts.

## 5. The volatility risk premium

$$VRP_t = VIX_t - RV_{t+1 \to t+21}$$

The VIX covers 30 calendar days, which is about 21 trading days. The forward realized vol at $t$ is the trailing 21-day vol at $t+21$, shifted back by 21 rows. It uses exactly the returns $r_{t+1},\dots,r_{t+21}$, as checked by a test against a manual computation.

**Look-ahead controls (tests).**
- Shocking prices after $t$ leaves every column labelled "known at $t$" (VIX, trailing RV, Parkinson, all forecasting features) unchanged up to $t$.
- The same shock *does* move `rv_fwd`, a sanity check that the target really looks forward.
- Prices after $t+21$ do not affect `rv_fwd` at $t$.
- The last 21 values of `rv_fwd` are `NaN`.

**Results (2005-01-03 → 2026-10-01, 5,471 days).**

| | Value |
|---|---|
| Mean VIX | 19.1% |
| Mean forward realized vol | 15.6% |
| **Mean VRP** | **+3.5 vol points** |
| Median VRP | +4.3 vol points |
| Share of days with VIX > realized | 83.7% |
| Worst VRP | −72 points (20 Feb 2020, the eve of the Covid crash) |
| corr(VIX, forward RV) vs corr(trailing RV, forward RV) | 0.71 vs 0.66 |

By VIX level, the premium is +2.3 points when VIX < 15 and +4.6 points when VIX > 30. The hit rate stays around 83–85% in every bucket. In crises the average premium turns negative (−3.8 points in the 2008 GFC window, −8.3 in the Covid window): insurance pays out exactly when it is needed.

## 6. Forecasting realized volatility

**Target:** `rv_fwd` at $t$. **Features (all known at the close of $t$):** realized vol over 1, 5, 22 and 63 days, 21-day Parkinson vol, VIX, 5-day VIX change, 1/5/21-day index returns (leverage effect), the last fully observed premium ($VIX_{t-21} - RV_{t-20 \to t}$), and VIX / RV.

**Models.**
- *Naive:* trailing 21-day RV.
- *HAR-RV* (Corsi, 2009): OLS of $RV^2_{fwd}$ on $RV^2_d, RV^2_w, RV^2_m$. Predictions are floored at a 5% vol, since OLS on variances can go negative.
- *HAR-RV + VIX:* adds $VIX^2$ as a regressor.
- *GARCH(1,1)* with Student-t innovations (`arch`). Parameters are fitted on returns strictly before each test year (`last_obs`), then frozen. Each 21-day forecast is the sum of the 1-to-21-step-ahead variances.
- *LightGBM* on $\ln(RV_{fwd})$, with Duan's smearing correction computed on training residuals.
- *VIX* itself as a reference forecast.

**Validation: walk-forward.** The window expands, models are refitted every calendar year from 2010, and the **21-day purge** guarantees that the last training target ends before the first test day (tested). A random split would leak the future through overlapping targets and volatility clustering.

**Out-of-sample results (2010-01-04 → 2026-10-01, 4,212 days):**

| Model | RMSE (vol pts) | MAE | Bias | QLIKE | RMSE vs naive |
|---|---|---|---|---|---|
| Naive | 8.95 | 5.31 | +0.01 | 0.605 | – |
| HAR-RV | 8.10 | 5.52 | +2.49 | 0.394 | −9.5% |
| GARCH(1,1) | 8.29 | 5.29 | +1.92 | 0.393 | −7.4% |
| **HAR-RV + VIX** | **7.72** | 5.08 | +2.14 | **0.374** | **−13.8%** |
| LightGBM | 7.95 | **4.79** | +0.36 | 0.501 | −11.2% |
| VIX (reference) | 8.21 | 6.01 | +3.75 | 0.382 | −8.3% |

**Reading.** A linear model with the VIX wins on RMSE and QLIKE. LightGBM has the best MAE and almost no bias, but it under-predicts volatility spikes, which QLIKE (asymmetric, it penalizes under-prediction) punishes. Its most important feature by gain is the VIX (55%): the market is already a strong forecaster, simply biased upward by the premium. A Diebold-Mariano test would be needed to claim that the gaps are statistically significant (see next steps).

## 7. Backtest: selling 1-month variance

**Instrument (proxy).** At the close of $t$, sell a 1-month variance swap struck at $K = VIX_t$. At $t+21$ the seller earns, per unit of vega notional and in vol points,

$$\text{P\&L} = \frac{K^2 - \min(RV, 2.5K)^2}{2K}$$

The payoff is convex: it is close to $K - RV$ for small moves, but losses grow with $RV^2$. The realized vol is capped at 2.5× the strike, the market standard on index variance swaps. The position size is 0.5% of capital per vol point, and costs are 0.5 vol point per trade. Trades do not overlap (one per 21 trading days), and the decision at $t$ uses only $VIX_t$ and the forecast made at $t$ (tested).

**Approximations.** The VIX is not tradable. Real swap strikes sit slightly above the VIX (convexity adjustment, bid-ask, jumps). 21 trading days only approximate 30 calendar days. Collateral interest is ignored, so returns are treated as excess returns.

**Strategies.** (a) Always sell. (b) Sell only if the forecast premium $VIX_t - \widehat{RV}_t$ exceeds 2 vol points. Both HAR-RV + VIX and LightGBM signals are reported, to avoid picking the best one after the fact. **The threshold was fixed a priori.** The threshold sensitivity is shown, not optimized.

**Results (201 monthly periods, 2010 → 2026, roll date offset 0):**

| | Always sell | Conditional HAR + VIX | Conditional LightGBM |
|---|---|---|---|
| Annual return | 10.2% | 6.8% | 7.5% |
| Annual vol | 14.5% | 7.5% | 11.6% |
| Sharpe | 0.76 | 0.92 | 0.69 |
| Max drawdown | −46.0% | −18.8% | −21.2% |
| Worst month | −32.0% (Mar 2020) | −18.8% (Aug 2011) | −20.6% (Feb 2020) |
| Skew / excess kurtosis | −4.5 / 26.5 | −3.4 / 32.1 | −3.8 / 19.8 |
| Months invested | 100% | 39% | 73% |

The HAR + VIX filter sat out Volmageddon (Feb 2018), Covid (Feb–Mar 2020) and the 2025 tariff shock, but not August 2011.

**Robustness to the roll date.** With monthly trades the result depends on which day of the month the swap is rolled. Over the 21 possible offsets:

| | Mean Sharpe | Min – Max Sharpe | Mean max drawdown |
|---|---|---|---|
| Always sell | 0.88 | 0.64 – 1.11 | −38% |
| Conditional HAR + VIX | 0.93 | 0.36 – 1.71 | −22% |
| Conditional LightGBM | 0.85 | 0.44 – 1.32 | −29% |

**Conclusion.** The premium is real and persistent, but harvesting it is a short-tail-risk trade: high hit rate, strongly negative skew, fat tails. Conditioning on a forecast mainly **cuts drawdowns**, by about 40% on average. The Sharpe gain is small and highly dependent on the roll date, so a single-path backtest would overstate it.

## 8. Limitations and next steps

- **Option history:** with OptionMetrics or CBOE DataShop, the premium could be measured per strike (is the skew overpriced?) and the backtest could use tradable straddles or strangles with delta hedging.
- **Intraday realized volatility** (5-minute returns) would give a far less noisy target and better HAR fits.
- **Statistical testing:** Diebold-Mariano tests between forecasts, and a bootstrap of Sharpe ratios.
- **Risk management:** volatility-targeted sizing, and stop rules on VIX term-structure inversion.
- **American exercise:** a binomial tree or Barone-Adesi-Whaley for ITM SPY options, if they are ever used.
