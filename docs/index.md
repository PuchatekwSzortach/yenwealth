# yenwealth

yenwealth is a Python framework for simulating long-term personal finances for individuals living in Japan.
It aims to make it easy to run long term "what if" financial simulations involving investments held in tax advantaged accounts in Japan.

The most interesting features of yenwealth are building blocks for simulations that model selected
Japanese tax rules and account limits:

- ordinary, iDeCo, NISA and old NISA (旧NISA) investment account classes that model selected
  Japanese tax rules and limits, such as annual contribution caps and distribution periods.
- investment manager object that implements a tax efficient investing and spending strategy for different combinations of tax advantaged and ordinary accounts

Other useful features of yenwealth are:

- logic for simulating future returns on assets, and inflation, based on historical data.
- Monte Carlo simulation logic for running multiple simulations.
- callbacks for implementing your own annual costs and earnings patterns.
- logic to evaluate simulation results against financial targets (e.g portfolio value over x at age y)

Here's a minimal example showing a single, deterministic simulation that uses ordinary and NISA accounts:
```python
--8<-- "examples/front_page.py"
```

While this shows the very basics, other files in `examples` show more realistic scenarios.

## Start here

- [Getting started](getting-started.md) walks through the included examples.
- [Account model](account-model.md) explains the investment accounts and
  deposit and withdrawal priorities.
- [Simulation guides](simulations/index.md) cover deterministic and Monte Carlo
  projections, plus result analysis.

## Disclaimer

The Japanese account rules and limits modeled by yenwealth are intended to reflect requirements in
effect as of 2026. Laws and guidance can change, and the model may not cover every case. yenwealth
is for simulation and educational purposes; it does not provide financial, investment, tax, or
legal advice. Check current requirements with official sources or a qualified professional.
