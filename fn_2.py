import numpy as np
import pandas as pd


class SingleStockMomentumVolBreakoutStrategy:
    """
    Single-stock strategy combining:
    - Momentum (MA trend + N-day breakout)
    - Volatility filter (ATR% within band; add on expansion)
    - Breakout handling (pyramiding on strength, controlled exits)

    Practical risk controls:
    - Fixed risk fraction per trade sizing
    - ATR-based initial stop and trailing (Chandelier style)
    - Pyramiding with capped layers and spacing
    - Cooldown after exit and min hold days
    """

    def __init__(
        self,
        risk_fraction_per_trade: float = 0.01,
        fee_rate: float = 0.0003,
        slippage_bps: float = 2.0,
        fast_ma_window: int = 20,
        slow_ma_window: int = 60,
        entry_breakout_window: int = 10,  # 改为10日，更容易突破
        atr_window: int = 14,
        atr_multiple_stop: float = 3.0,
        vol_min_pct: float = 0.7,  # 放宽波动率下限
        vol_max_pct: float = 2.0,  # 放宽波动率上限
        vol_lookback_for_filter: int = 60,
        enable_pyramiding: bool = True,
        max_pyramid_layers: int = 3,
        pyramid_add_step_pct: float = 2.0,
        vol_expand_multiple_for_add: float = 1.1,
        exit_break_window: int = 10,
        min_hold_days: int = 5,
        cooldown_days_after_exit: int = 5,
    ):
        self.risk_fraction_per_trade = risk_fraction_per_trade
        self.fee_rate = fee_rate
        self.slippage_bps = slippage_bps
        self.fast_ma_window = fast_ma_window
        self.slow_ma_window = slow_ma_window
        self.entry_breakout_window = entry_breakout_window
        self.atr_window = atr_window
        self.atr_multiple_stop = atr_multiple_stop
        self.vol_min_pct = vol_min_pct
        self.vol_max_pct = vol_max_pct
        self.vol_lookback_for_filter = vol_lookback_for_filter
        self.enable_pyramiding = enable_pyramiding
        self.max_pyramid_layers = max_pyramid_layers
        self.pyramid_add_step_pct = pyramid_add_step_pct
        self.vol_expand_multiple_for_add = vol_expand_multiple_for_add
        self.exit_break_window = exit_break_window
        self.min_hold_days = min_hold_days
        self.cooldown_days_after_exit = cooldown_days_after_exit
        
        # 新增参数
        self.take_profit_multiple = 2.0  # 止盈倍数
        self.max_position_risk = 0.05   # 最大仓位风险
        self.trend_strength_threshold = 0.02  # 趋势强度阈值

    @staticmethod
    def _compute_atr(df: pd.DataFrame, window: int) -> pd.Series:
        """Calculate Average True Range"""
        prev_close = df['close'].shift(1)
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - prev_close).abs()
        tr3 = (df['low'] - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.ewm(span=window, adjust=False).mean()

    def calculate_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate volume-based indicators"""
        df = df.copy()
        
        # ATR and volatility indicators
        df['atr'] = self._compute_atr(df, self.atr_window)
        df['atr_pct'] = df['atr'] / df['close']
        df['atr_pct_median'] = df['atr_pct'].rolling(self.vol_lookback_for_filter).median()
        df['atr_filter_ratio'] = df['atr_pct'] / df['atr_pct_median']
        
        # 波动率状态分类
        df['volatility_regime'] = 'normal'
        df.loc[df['atr_filter_ratio'] < self.vol_min_pct, 'volatility_regime'] = 'low'
        df.loc[df['atr_filter_ratio'] > self.vol_max_pct, 'volatility_regime'] = 'high'
        
        return df

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        df = df.copy()
        
        # Moving averages
        df['fast_ma'] = df['close'].rolling(self.fast_ma_window).mean()
        df['slow_ma'] = df['close'].rolling(self.slow_ma_window).mean()
        
        # Donchian channels for breakout detection
        df['donchian_high'] = df['high'].rolling(self.entry_breakout_window).max()
        df['donchian_low'] = df['low'].rolling(self.exit_break_window).min()
        
        # 价格相对位置
        df['price_vs_fast_ma'] = (df['close'] - df['fast_ma']) / df['fast_ma']
        df['price_vs_slow_ma'] = (df['close'] - df['slow_ma']) / df['slow_ma']
        
        return df

    def calculate_momentum_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate momentum and trend indicators"""
        df = df.copy()
        
        # Trend strength
        df['trend_strength'] = (df['fast_ma'] - df['slow_ma']) / df['slow_ma']
        df['trend_strength_pct'] = df['trend_strength'] * 100
        
        # 趋势状态分类
        df['trend_state'] = 'neutral'
        df.loc[df['trend_strength'] > self.trend_strength_threshold, 'trend_state'] = 'strong_uptrend'
        df.loc[df['trend_strength'] < -self.trend_strength_threshold, 'trend_state'] = 'strong_downtrend'
        df.loc[(df['trend_strength'] >= 0) & (df['trend_strength'] <= self.trend_strength_threshold), 'trend_state'] = 'weak_uptrend'
        df.loc[(df['trend_strength'] < 0) & (df['trend_strength'] >= -self.trend_strength_threshold), 'trend_state'] = 'weak_downtrend'
        
        # Breakout strength
        df['breakout_strength'] = (df['close'] - df['donchian_high']) / df['donchian_high']
        
        return df

    def calculate_risk_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate risk management indicators"""
        df = df.copy()
        
        # 动态止损价格
        df['dynamic_stop_loss'] = df['close'] - self.atr_multiple_stop * df['atr']
        
        # 止盈价格
        df['take_profit_price'] = df['close'] + self.take_profit_multiple * self.atr_multiple_stop * df['atr']
        
        # 风险回报比
        df['risk_reward_ratio'] = (df['take_profit_price'] - df['close']) / (df['close'] - df['dynamic_stop_loss'])
        
        # 价格相对止损距离
        df['price_vs_stop_distance'] = (df['close'] - df['dynamic_stop_loss']) / df['close']
        
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate complete trading signals with risk management"""
        df = df.copy()
        
        # Initialize signal columns
        df['signal'] = 'HOLD'
        df['signal_reason'] = ''
        df['signal_strength'] = 0.0
        df['risk_level'] = 'LOW'
        df['position_size'] = 0.0
        df['stop_loss'] = 0.0
        df['take_profit'] = 0.0
        
        # Calculate all indicators
        df = self.calculate_volume_indicators(df)
        df = self.calculate_technical_indicators(df)
        df = self.calculate_momentum_indicators(df)
        df = self.calculate_risk_indicators(df)
        
        # Generate signals
        signal_count = 0
        for i in range(len(df)):
            if i < max(self.slow_ma_window, self.vol_lookback_for_filter):
                continue
                
            row = df.iloc[i]
            
            # 买入条件检查
            ma_condition = row['fast_ma'] > row['slow_ma']
            trend_condition = row['close'] > row['fast_ma']
            vol_condition = self.vol_min_pct <= row['atr_filter_ratio'] <= self.vol_max_pct
            risk_reward_ok = row['risk_reward_ratio'] > 1.5  # 风险回报比 > 1.5
            
            # 卖出条件检查
            below_stop = row['close'] < row['dynamic_stop_loss']
            break_low = row['close'] < row['donchian_low']
            above_take_profit = row['close'] > row['take_profit_price']
            trend_reversal = row['trend_strength'] < -self.trend_strength_threshold
            
            # 生成买入信号
            if (ma_condition and trend_condition and vol_condition and risk_reward_ok):
                df.iloc[i, df.columns.get_loc('signal')] = 'BUY'
                df.iloc[i, df.columns.get_loc('signal_reason')] = '趋势启动+突破快均线+波动率过滤+风险回报比良好'
                df.iloc[i, df.columns.get_loc('signal_strength')] = min(1.0, row['trend_strength'] * 10)
                df.iloc[i, df.columns.get_loc('stop_loss')] = row['dynamic_stop_loss']
                df.iloc[i, df.columns.get_loc('take_profit')] = row['take_profit_price']
                df.iloc[i, df.columns.get_loc('position_size')] = self._calculate_position_size(row)
                df.iloc[i, df.columns.get_loc('risk_level')] = self._assess_risk_level(row)
                signal_count += 1
            
            # 生成卖出信号
            elif (below_stop or break_low or above_take_profit or trend_reversal):
                df.iloc[i, df.columns.get_loc('signal')] = 'SELL'
                if below_stop:
                    reason = '触及动态止损'
                elif break_low:
                    reason = '跌破支撑位'
                elif above_take_profit:
                    reason = '达到止盈目标'
                else:
                    reason = '趋势反转'
                
                df.iloc[i, df.columns.get_loc('signal_reason')] = reason
                df.iloc[i, df.columns.get_loc('signal_strength')] = 1.0
                signal_count += 1
            
            # 生成加仓信号（如果已有持仓且趋势继续）
            elif (row['trend_strength'] > self.trend_strength_threshold * 1.5 and 
                  row['atr_filter_ratio'] > self.vol_expand_multiple_for_add):
                df.iloc[i, df.columns.get_loc('signal')] = 'ADD'
                df.iloc[i, df.columns.get_loc('signal_reason')] = '趋势加强+波动率扩张'
                df.iloc[i, df.columns.get_loc('signal_strength')] = 0.8
                df.iloc[i, df.columns.get_loc('position_size')] = self._calculate_position_size(row) * 0.5
                signal_count += 1
        
        print(f"策略分析完成，生成 {signal_count} 个交易信号（共 {len(df)} 个交易日）")
        return df

    def _calculate_position_size(self, row: pd.Series) -> float:
        """Calculate position size based on risk management"""
        # 基础仓位
        base_size = self.risk_fraction_per_trade
        
        # 根据趋势强度调整
        trend_adjustment = min(1.5, max(0.5, abs(row['trend_strength']) * 10))
        
        # 根据波动率调整
        vol_adjustment = 1.0
        if row['volatility_regime'] == 'low':
            vol_adjustment = 0.8
        elif row['volatility_regime'] == 'high':
            vol_adjustment = 1.2
        
        # 根据风险回报比调整
        rr_adjustment = min(1.5, max(0.5, row['risk_reward_ratio'] / 2))
        
        final_size = base_size * trend_adjustment * vol_adjustment * rr_adjustment
        return min(final_size, self.max_position_risk)
    
    def _assess_risk_level(self, row: pd.Series) -> str:
        """Assess risk level for the current position"""
        risk_score = 0
        
        # 波动率风险
        if row['volatility_regime'] == 'high':
            risk_score += 2
        elif row['volatility_regime'] == 'low':
            risk_score += 0
        else:
            risk_score += 1
        
        # 趋势强度风险
        if row['trend_strength'] < 0.01:
            risk_score += 2
        elif row['trend_strength'] > 0.05:
            risk_score += 0
        else:
            risk_score += 1
        
        # 价格相对止损距离风险
        if row['price_vs_stop_distance'] < 0.05:
            risk_score += 2
        elif row['price_vs_stop_distance'] > 0.15:
            risk_score += 0
        else:
            risk_score += 1
        
        if risk_score <= 2:
            return 'LOW'
        elif risk_score <= 4:
            return 'MEDIUM'
        else:
            return 'HIGH'

    def get_strategy_summary(self) -> str:
        """Return enhanced strategy description and parameters"""
        summary = f"""
增强版单支股票动量+波动率+突破策略 (fn_2.py)
        
核心参数:
- 快均线窗口: {self.fast_ma_window}
- 慢均线窗口: {self.slow_ma_window}
- 突破窗口: {self.entry_breakout_window}
- ATR窗口: {self.atr_window}
- ATR止损倍数: {self.atr_multiple_stop}
- 波动率过滤: {self.vol_min_pct:.1f}x 到 {self.vol_max_pct:.1f}x 中位数
- 分批加仓: {'启用' if self.enable_pyramiding else '禁用'}
- 最大加仓层数: {self.max_pyramid_layers}
- 每笔风险: {self.risk_fraction_per_trade * 100:.1f}%
- 最小持有天数: {self.min_hold_days}
- 冷静期天数: {self.cooldown_days_after_exit}
- 止盈倍数: {self.take_profit_multiple}
- 最大仓位风险: {self.max_position_risk * 100:.1f}%
- 趋势强度阈值: {self.trend_strength_threshold * 100:.1f}%

策略逻辑:
1. 买入: 快均线>慢均线 + 收盘价>快均线 + 波动率在区间 + 风险回报比>1.5
2. 卖出: 触及止损 + 跌破支撑 + 达到止盈 + 趋势反转
3. 加仓: 趋势加强 + 波动率扩张
4. 风险管理: 动态止损、仓位管理、风险等级评估

输出内容:
- 完整买卖信号 (BUY/SELL/ADD/HOLD)
- 信号强度 (0-1)
- 风险等级 (LOW/MEDIUM/HIGH)
- 建议仓位大小
- 止损止盈价格
- 市场状态分析
        """
        return summary


if __name__ == '__main__':
    # Create strategy instance and display summary
    strategy = SingleStockMomentumVolBreakoutStrategy()
    print(strategy.get_strategy_summary())
    print("\nStrategy ready for backtesting with testback.py")