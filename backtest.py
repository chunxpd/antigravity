
import pandas as pd
import numpy as np

def analyze_stock_history(df, compare_days, period_days=10, surge_threshold=0.10):
    """
    Analyzes historical data to find 'Breakout' patterns and subsequent performance.
    Pattern: Close[t] > Close[t - compare_days] (Breakout)
             AND Close[t-1] <= Close[t - compare_days - 1]
    """
    if len(df) < compare_days + period_days + 1:
        return None

    target_price = df['Close'].shift(compare_days)
    conditions = (df['Close'] > target_price) & (df['Close'].shift(1) <= target_price.shift(1))
    
    return _calculate_stats(df, conditions, period_days, surge_threshold)

def analyze_ma_breakout(df, window, period_days=10, surge_threshold=0.10):
    """
    Analyzes average breakout patterns.
    Pattern: Close > MA(window) AND Prev_Close <= Prev_MA(window)
    """
    if len(df) < window + period_days + 1:
        return None
        
    ma_series = df['Close'].rolling(window=window).mean()
    
    # Crossover: Close > MA and Prev_Close <= Prev_MA
    conditions = (df['Close'] > ma_series) & (df['Close'].shift(1) <= ma_series.shift(1))
    
    return _calculate_stats(df, conditions, period_days, surge_threshold)

def _calculate_stats(df, conditions, period_days, surge_threshold):
    valid_indices = conditions[conditions].index
    valid_locs = [df.index.get_loc(idx) for idx in valid_indices]
    
    total_signals = 0
    success_count = 0
    total_max_return = 0.0
    
    n_rows = len(df)
    
    for loc in valid_locs:
        if loc + period_days >= n_rows:
            continue
            
        total_signals += 1
        entry_price = df['Close'].iloc[loc]
        future_window = df['High'].iloc[loc+1 : loc+period_days+1]
        
        if future_window.empty: 
            continue
            
        max_price = future_window.max()
        max_return = (max_price - entry_price) / entry_price
        
        if max_return >= surge_threshold:
            success_count += 1
            
        total_max_return += max_return

    if total_signals == 0:
        return {
            'total_signals': 0,
            'success_count': 0,
            'success_rate': 0.0,
            'avg_max_return': 0.0
        }
        
    return {
        'total_signals': total_signals,
        'success_count': success_count,
        'success_rate': round((success_count / total_signals) * 100, 2),
        'avg_max_return': round((total_max_return / total_signals) * 100, 2)
    }
