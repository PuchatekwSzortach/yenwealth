# Getting started

## Set up the development environment

Install with `pip install yenwealth`

## Run an example

The deterministic example builds one `FinancesSimulatorInputs` object, runs a
single projection, and formats the result:

```sh
python examples/simple_simulation.py
```

The Monte Carlo example uses historical economic data to generate multiple
scenarios and reports how often selected portfolio targets are reached:

```sh
python examples/monte_carlo_simulation.py
```

Each example constructs investment accounts, income and cost callables, and
economic data in Python. Start from the example closest to your use case and
replace those inputs with your own assumptions.
