# Changelog

### 0.6.1
- improved - ProportionalAssetPurchaseStrategy.allocate now doesn't include in return value assets that would have nothing allocated to them

### 0.6.0
- improved - renamed a large number of classes from investment module so as to improve clarity
- improved - account objects sent to SimpleInvestmentManager are now optional
- improved - account objects now own their purchase and sale strategies
- improved - IdecoPensionPayoutPlan now owns its validation logic

### 0.5.3
- improved - SimpleInvestmentManager now validates all assets in accounts passed to it are accounted for in investment policies

### 0.5.2
- improved - OrdinaryInvestmentAccount.withdraw method now doesn't treat selling asset with negative gain as tax benefit, instead assuming no tax benefits from such transaction.

### 0.5.1
- improved - split fields of FinancesSimulatorInputs and MonteCarloSimulatorInputs into smaller, more focused classes
- improved - MonteCarloSimulatorInputs now accepts runtime_factory for creating FinancesSimulatorRuntime, which contains logic with possibly mutable elements, such as investment manager, income callable and annual costs callable

### 0.5.0
- added - added MonteCarloSimulator for running multiple financial simulations
- added - added SimulationAnalyzer that allows to check how many simulations hit target goals

### 0.4.5
- improved - various withdraw and deposit functions now throw an buy/sell value being zero
- improved - SimpleInvestmentManager.optimize_investments and SimpleInvestmentManager.withdraw don't initiate any transactions that involve zero amount of money

### 0.4.4
- improved - Asset.sell now throws InsufficientFunds instead of ValueError if not enough assets exist
- improved - Asset.portfolio_value now rounds down to nearest yen. This prevents a lot of fractional errors down the line

### 0.4.3
- improved - added examples/simple_simulation.py

### 0.4.2
- improved - constructors for ProportionalDepositStrategy and SequentialWithdrawStrategy now validate that inputs are not empty
- improved - SequentialWithdrawStrategy.calculate_withdrawal_amounts now validates that sufficient funds are available within target assets to satisfy withdrawal request

### 0.4.1
- improved - improved error message for SequentialWithdrawStrategy.calculate_withdrawal_amounts if withdrawal over asset value is requested

### 0.4.0
- added - added Asset, DepositStrategy and WithdrawStrategy classes
- updated - all account classes are now based on assets that can grow independently instead of lump principal and gain values
- updated - InvestmentManager and FinancesSimulator  now accept simulated growth values for individual assets and grow assets over time based on these values
- updated - FinancesSimulator.run_simulation now returns pandas.DataFrame with simulation result, including in case when accounts run out of money before simulation end

### 0.3.0
- updated - OrdinaryInvestmentAccount's capital_gain_tax_rate now has a default value
- improved - IdecoInvestmentAccount now correctly calculates max allowed tax free lump withdrawal amount based on when contributions to the account began

### 0.2.0
- renamed InvestmentManager to SimpleInvestmentManager, added InvestmentManager as a protocol
- added FinancesSimulator class

### 0.1.0
- added OrdinaryInvestmentAccount, IdecoInvestmentAccount, OldNisaAccount, NisaAccount classes
- added InvestmentManager class with a simple `maximize nisa deposts, withdraw from ordinary account, then ideco, then nisa` strategy
