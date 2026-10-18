"""
Module with analysis logic
"""

import collections
import dataclasses
import decimal

import pandas

import yenwealth.utilities


@dataclasses.dataclass(frozen=True)
class FinancialTarget:

    age: int
    net_portfolio_value: decimal.Decimal


class SimulationAnalyzer:

    def get_target_hit_count_map(
            self, simulations: list[pandas.DataFrame], targets: list[FinancialTarget]) -> dict[FinancialTarget, int]:

        counter = collections.Counter()

        for simulation in simulations:
            for target in targets:

                if target.age in simulation.index:

                    actual_value = simulation.loc[target.age, "net_portfolio_value"]

                    if isinstance(actual_value, decimal.Decimal) and (not actual_value.is_nan()) and \
                            actual_value >= target.net_portfolio_value:
                        counter[target] += 1

        # Add an entry for targets that were never hit
        for target in targets:
            if target not in counter:
                counter[target] = 0

        return dict(counter)

    def get_report(self, simulations: list[pandas.DataFrame], targets: list[FinancialTarget]) -> str:

        hit_count = self.get_target_hit_count_map(simulations=simulations, targets=targets)

        lines = []

        for target in sorted(targets, key=lambda t: t.age):
            hit_percentage = (hit_count[target] / len(simulations)) * 100

            lines.append(
                f"Age: {target.age}, net value: {yenwealth.utilities.format_million_yen(target.net_portfolio_value)}: "
                f"{hit_count[target]}/{len(simulations)} ({hit_percentage:.2f}%)"
            )

        return "\n".join(lines)
