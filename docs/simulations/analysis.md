# Analyze results

`SimulationAnalyzer` compares each simulation with one or more
`FinancialTarget` values. A target consists of an age and a desired net
portfolio value.

`get_target_hit_count_map()` returns the number of simulations that meet each
target at the specified age. A run only counts as a hit when the result has a
non-missing `Decimal` value at that age and the value is at least the target.
`get_report()` formats those counts as a short report with hit percentages.

The Monte Carlo example shows both methods in use after a batch of simulations.
