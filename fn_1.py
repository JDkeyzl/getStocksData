import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class TechStockStrategy:
    """
    牛市科技股票量化交易策略
    重点关注：放量、缩量、技术指标、趋势分析
    """
    
    def __init__(self,
                 volume_ratio_buy_threshold: float = 1.2,
                 rsi_buy_max: float = 75,
                 sell_volume_ratio_threshold: float = 2.0,
                 rsi_sell_min: float = 80,
                 stop_loss_factor: float = 0.95,
                 pullback_volume_factor: float = 0.9,
                 pullback_rsi_max: float = 45,
                 require_macd_bullish: bool = True):
        self.volume_ratio_buy_threshold = volume_ratio_buy_threshold
        self.rsi_buy_max = rsi_buy_max
        self.sell_volume_ratio_threshold = sell_volume_ratio_threshold
        self.rsi_sell_min = rsi_sell_min
        self.stop_loss_factor = stop_loss_factor
        self.pullback_volume_factor = pullback_volume_factor
        self.pullback_rsi_max = pullback_rsi_max
        self.require_macd_bullish = require_macd_bullish
        
    def calculate_volume_indicators(self, df):
        """
        计算成交量相关指标
        """
        # 计算移动平均成交量
        df['volume_ma5'] = df['volume'].rolling(window=5).mean()
        df['volume_ma10'] = df['volume'].rolling(window=10).mean()
        df['volume_ma20'] = df['volume'].rolling(window=20).mean()
        
        # 放量指标：当前成交量 > 前N日平均成交量的倍数
        df['volume_ratio_5'] = df['volume'] / df['volume_ma5']
        df['volume_ratio_10'] = df['volume'] / df['volume_ma10']
        df['volume_ratio_20'] = df['volume'] / df['volume_ma20']
        
        # 缩量指标：当前成交量 < 前N日平均成交量的倍数
        df['volume_shrink_5'] = df['volume'] / df['volume_ma5']
        df['volume_shrink_10'] = df['volume'] / df['volume_ma10']
        
        # 价量配合指标
        df['price_volume_trend'] = np.where(
            (df['close'] > df['close'].shift(1)) & (df['volume'] > df['volume_ma5']),
            '价涨量增',
            np.where(
                (df['close'] < df['close'].shift(1)) & (df['volume'] < df['volume_ma5']),
                '价跌量缩',
                '价量背离'
            )
        )
        
        return df
    
    def calculate_technical_indicators(self, df):
        """
        计算技术指标
        """
        # 移动平均线
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        
        # MACD指标（简化版）
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # RSI指标
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # KDJ指标（简化版）
        low_min = df['low'].rolling(window=9).min()
        high_max = df['high'].rolling(window=9).max()
        df['k'] = 100 * ((df['close'] - low_min) / (high_max - low_min))
        df['d'] = df['k'].rolling(window=3).mean()
        df['j'] = 3 * df['k'] - 2 * df['d']
        
        # 布林带
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # 趋势强度指标
        df['trend_strength'] = np.where(
            (df['ma5'] > df['ma10']) & (df['ma10'] > df['ma20']) & (df['ma20'] > df['ma60']),
            '强上涨',
            np.where(
                (df['ma5'] < df['ma10']) & (df['ma10'] < df['ma20']) & (df['ma20'] < df['ma60']),
                '强下跌',
                '震荡'
            )
        )
        
        return df
    
    def calculate_bull_market_indicators(self, df):
        """
        计算牛市特征指标
        """
        # 牛市确认指标
        df['bull_confirmation'] = np.where(
            (df['close'] > df['ma20']) & 
            (df['ma20'] > df['ma60']) & 
            (df['volume'] > df['volume_ma20']) &
            (df['rsi'] > 50),
            '牛市确认',
            '非牛市'
        )
        
        # 突破强度
        df['breakout_strength'] = np.where(
            (df['close'] > df['bb_upper']) & (df['volume'] > df['volume_ma5'] * self.volume_ratio_buy_threshold),
            '放量突破',
            np.where(
                (df['close'] < df['bb_lower']) & (df['volume'] > df['volume_ma5'] * self.sell_volume_ratio_threshold),
                '放量跌破',
                '正常波动'
            )
        )
        
        # 回调买入机会
        df['pullback_buy'] = np.where(
            (df['close'] > df['ma20']) & 
            (df['close'] < df['ma5']) & 
            (df['volume'] < df['volume_ma5'] * 0.8) &
            (df['rsi'] < 40),
            '回调买入',
            '非买入'
        )
        
        return df
    
    def generate_signals(self, df):
        """
        生成交易信号
        """
        signals = []
        
        for i in range(20, len(df)):
            signal = {
                'date': df.index[i],
                'price': df['close'].iloc[i],
                'volume': df['volume'].iloc[i],
                'action': 'HOLD',
                'reason': '',
                'strength': 0
            }
            
            # 买入信号
            bullish_macd = (df['macd'].iloc[i] > df['macd_signal'].iloc[i]) if self.require_macd_bullish else True
            if (df['bull_confirmation'].iloc[i] == '牛市确认' and
                df['volume_ratio_5'].iloc[i] > self.volume_ratio_buy_threshold and
                df['rsi'].iloc[i] < self.rsi_buy_max and
                bullish_macd):
                
                signal['action'] = 'BUY'
                signal['reason'] = '放量上涨+技术指标共振'
                signal['strength'] = min(df['volume_ratio_5'].iloc[i] / 1.5, 3)
                
            # 回调买入信号
            elif (df['pullback_buy'].iloc[i] == '回调买入' and
                  df['trend_strength'].iloc[i] == '强上涨'):
                
                signal['action'] = 'BUY'
                signal['reason'] = '强势回调+缩量确认'
                signal['strength'] = 2
                
            # 卖出信号
            elif (df['volume_ratio_5'].iloc[i] > self.sell_volume_ratio_threshold and
                  df['close'].iloc[i] < df['close'].iloc[i-1] and
                  df['rsi'].iloc[i] > self.rsi_sell_min):
                
                signal['action'] = 'SELL'
                signal['reason'] = '放量下跌+超买'
                signal['strength'] = 3
                
            # 止损信号
            elif (df['close'].iloc[i] < df['ma20'].iloc[i] * self.stop_loss_factor and
                  df['volume'].iloc[i] > df['volume_ma5'].iloc[i]):
                
                signal['action'] = 'SELL'
                signal['reason'] = '跌破支撑+放量确认'
                signal['strength'] = 2
                
            signals.append(signal)
            
        return signals

# 示例使用
if __name__ == "__main__":
    # 创建策略实例
    strategy = TechStockStrategy()
    
    print("牛市科技股票量化交易策略已创建！")
    print("\n主要功能:")
    print("1. 成交量分析（放量、缩量指标）")
    print("2. 技术指标计算（MACD、RSI、KDJ、布林带等）")
    print("3. 牛市特征识别")
    print("4. 交易信号生成")
    
    print("\n使用方法:")
    print("1. 准备股票数据（包含OHLCV数据）")
    print("2. 调用 strategy.calculate_volume_indicators(df) 计算成交量指标")
    print("3. 调用 strategy.calculate_technical_indicators(df) 计算技术指标")
    print("4. 调用 strategy.calculate_bull_market_indicators(df) 计算牛市指标")
    print("5. 调用 strategy.generate_signals(df) 生成交易信号")