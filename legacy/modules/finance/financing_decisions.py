def debt_ratio(debt, total_capital):
    if total_capital == 0:
        return 0
    
    return (debt / total_capital) * 100

def equity_ratio(equity, total_capital):
    if total_capital == 0:
        return 0
    
    return (equity / total_capital) * 100

def financing_mix(debt, equity):
    total = debt + equity
    
    return {
        "debt_ratio": debt_ratio(debt, total),
        "equity_ratio": equity_ratio(equity, total)
    }

