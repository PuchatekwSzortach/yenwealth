# Changelog

### 0.4.1
- improved - improved error message for SequentialWithdrawStrategy.calculate_withdrawal_amounts if withdrawal over asset value is requested

### 0.4.0
- added - added Asset, DepositStrategy and WithdrawStrategy classes
- updated - all account classes are now based on assets that can grow independently instead of lump principal and gain values
- updated - InvestmentManager and FinancesSimulator  now accept simulated growth values for invididual assets and grow assets over time based on these values
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
