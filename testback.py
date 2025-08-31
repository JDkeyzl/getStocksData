import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import os
import json
import sys
import warnings
warnings.filterwarnings('ignore')

# 导入策略类
from fn_1 import TechStockStrategy
from fn_2 import SingleStockMomentumVolBreakoutStrategy

class BacktestEngine:
    """
    策略回测引擎
    """
    
    def __init__(self, initial_cash=1000000, strategy_type='fn1'):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions = {}  # 持仓记录
        self.trades = []     # 交易记录
        self.portfolio_value = []  # 组合价值记录
        
        # 根据策略类型选择策略
        if strategy_type == 'fn2':
            self.strategy = SingleStockMomentumVolBreakoutStrategy()
        else:
            self.strategy = TechStockStrategy()
        
    def load_stock_data(self, stock_code, start_date, end_date):
        """
        从data文件夹加载股票数据
        输入：股票代码、开始日期、结束日期
        """
        # 查找匹配的数据文件
        data_dir = "data"
        if not os.path.exists(data_dir):
            raise FileNotFoundError(f"数据目录 {data_dir} 不存在")
        
        # 查找包含股票代码的文件
        matching_files = []
        for file in os.listdir(data_dir):
            if stock_code in file and file.endswith('.json'):
                matching_files.append(file)
        
        if not matching_files:
            raise FileNotFoundError(f"未找到股票代码 {stock_code} 的数据文件")
        
        # 加载第一个匹配的文件
        file_path = os.path.join(data_dir, matching_files[0])
        print(f"加载数据文件: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 转换为DataFrame
            df = pd.DataFrame(data)
            
            # 转换数据类型
            df['date'] = pd.to_datetime(df['date'])
            df['open'] = pd.to_numeric(df['open'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['close'] = pd.to_numeric(df['close'])
            df['amount'] = pd.to_numeric(df['amount'])
            
            # 添加volume列（如果数据中没有）
            if 'volume' not in df.columns:
                # 使用amount作为volume的近似值
                df['volume'] = df['amount'] / df['close']
            
            # 设置日期索引
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
            
            # 过滤日期范围
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            if df.empty:
                raise ValueError(f"在指定日期范围内没有找到数据")
            
            print(f"成功加载 {len(df)} 条数据记录")
            print(f"数据范围: {df.index.min()} 到 {df.index.max()}")
            
            return df
            
        except Exception as e:
            raise Exception(f"加载数据文件失败: {str(e)}")
    
    def calculate_all_indicators(self, df):
        """
        计算所有技术指标
        """
        print("计算技术指标...")
        
        # 计算成交量指标
        df = self.strategy.calculate_volume_indicators(df)
        
        # 计算技术指标
        df = self.strategy.calculate_technical_indicators(df)
        
        # 计算动量指标（如果策略支持）
        if hasattr(self.strategy, 'calculate_momentum_indicators'):
            df = self.strategy.calculate_momentum_indicators(df)
        
        print("技术指标计算完成")
        return df
    
    def backtest_strategy(self, df):
        """
        执行策略回测
        """
        print("开始策略回测...")
        
        # 重置回测状态
        self.cash = self.initial_cash
        self.positions = {}
        self.trades = []
        self.portfolio_value = []
        
        # 生成交易信号
        signals_df = self.strategy.generate_signals(df)
        print(f"生成了 {len(signals_df)} 个交易信号")
        
        # 将DataFrame转换为信号列表格式
        signals = []
        for idx, row in signals_df.iterrows():
            if row['signal'] != 'HOLD':
                signals.append({
                    'date': idx,
                    'action': row['signal'],
                    'price': row['close'],
                    'reason': row['signal_reason'],
                    'strength': 1.0  # 默认强度
                })
        
        # 执行回测
        for signal in signals:
            if signal['action'] == 'BUY' and self.cash > 0:
                # 计算买入数量（根据信号强度调整仓位）
                position_size = min(self.cash * 0.1 * signal['strength'], self.cash)
                shares = int(position_size / signal['price'])
                
                if shares > 0:
                    self.positions[signal['date']] = {
                        'shares': shares,
                        'price': signal['price'],
                        'date': signal['date']
                    }
                    self.cash -= shares * signal['price']
                    
                    self.trades.append({
                        'date': signal['date'],
                        'action': 'BUY',
                        'price': signal['price'],
                        'shares': shares,
                        'reason': signal['reason'],
                        'cash_after': self.cash
                    })
                    
            elif signal['action'] == 'SELL' and self.positions:
                # 卖出所有持仓
                for pos_date, position in list(self.positions.items()):
                    if pos_date <= signal['date']:
                        profit = (signal['price'] - position['price']) * position['shares']
                        self.cash += position['shares'] * signal['price']
                        
                        self.trades.append({
                            'date': signal['date'],
                            'action': 'SELL',
                            'price': signal['price'],
                            'shares': position['shares'],
                            'profit': profit,
                            'reason': signal['reason'],
                            'cash_after': self.cash
                        })
                        
                        del self.positions[pos_date]
            
            # 计算当前组合价值
            current_value = self.cash
            for pos_date, position in self.positions.items():
                if pos_date <= signal['date']:
                    current_value += position['shares'] * signal['price']
            
            self.portfolio_value.append({
                'date': signal['date'],
                'value': current_value,
                'cash': self.cash,
                'positions': len(self.positions)
            })
        
        print("策略回测完成")
        print(f"生成了 {len(self.trades)} 笔交易，投资组合价值记录 {len(self.portfolio_value)} 条")
        return self.calculate_performance()
    
    def calculate_performance(self):
        """
        计算策略表现指标
        """
        if not self.portfolio_value:
            return {}
        
        initial_value = self.initial_cash
        final_value = self.portfolio_value[-1]['value']
        total_return = (final_value - initial_value) / initial_value * 100
        
        # 计算年化收益率
        if len(self.portfolio_value) > 1:
            start_date = self.portfolio_value[0]['date']
            end_date = self.portfolio_value[-1]['date']
            days = (end_date - start_date).days
            if days > 0:
                annual_return = (final_value / initial_value) ** (365 / days) - 1
                annual_return_pct = annual_return * 100
            else:
                annual_return_pct = 0
        else:
            annual_return_pct = 0
        
        # 计算最大回撤
        peak = initial_value
        max_drawdown = 0
        
        for pv in self.portfolio_value:
            if pv['value'] > peak:
                peak = pv['value']
            drawdown = (peak - pv['value']) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 计算胜率
        buy_trades = [t for t in self.trades if t['action'] == 'BUY']
        sell_trades = [t for t in self.trades if t['action'] == 'SELL']
        
        profitable_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
        win_rate = len(profitable_trades) / len(sell_trades) * 100 if sell_trades else 0
        
        # 计算夏普比率（简化版）
        if len(self.portfolio_value) > 1:
            returns = []
            for i in range(1, len(self.portfolio_value)):
                ret = (self.portfolio_value[i]['value'] - self.portfolio_value[i-1]['value']) / self.portfolio_value[i-1]['value']
                returns.append(ret)
            
            if returns:
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                sharpe_ratio = avg_return / std_return * np.sqrt(252) if std_return > 0 else 0
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        performance_data = {
            'total_return': total_return,
            'annual_return': annual_return_pct,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': len(self.trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'final_value': final_value,
            'initial_value': initial_value
        }
        
        return performance_data
    
    def plot_strategy_analysis(self, df, signals, out_dir="backtest_out", prefix="chart"):
        """
        Plot price with buy/sell signals (English) and save as PNG
        """
        os.makedirs(out_dir, exist_ok=True)
        fig, ax = plt.subplots(1, 1, figsize=(15, 6))

        # Price with moving averages
        ax.plot(df.index, df['close'], label='Close', color='blue', linewidth=1.2)
        if 'ma5' in df.columns:
            ax.plot(df.index, df['ma5'], label='MA5', color='red', alpha=0.8, linewidth=1)
        if 'ma20' in df.columns:
            ax.plot(df.index, df['ma20'], label='MA20', color='orange', alpha=0.8, linewidth=1)

        # Buy/Sell signals
        buy_signals = [s for s in signals if s['action'] == 'BUY']
        sell_signals = [s for s in signals if s['action'] == 'SELL']
        if buy_signals:
            buy_dates = [s['date'] for s in buy_signals]
            buy_prices = [s['price'] for s in buy_signals]
            ax.scatter(buy_dates, buy_prices, color='red', marker='^', s=80, label='Buy')
        if sell_signals:
            sell_dates = [s['date'] for s in sell_signals]
            sell_prices = [s['price'] for s in sell_signals]
            ax.scatter(sell_dates, sell_prices, color='green', marker='v', s=80, label='Sell')

        ax.set_title('Price with Buy/Sell Signals', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Price')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        png_path = os.path.join(out_dir, f"{prefix}_signals.png")
        plt.savefig(png_path)
        plt.close(fig)
        print(f"Saved chart: {png_path}")
    
    def plot_portfolio_performance(self, out_dir="backtest_out", prefix="chart"):
        """
        Plot equity curve as return (%) and save as PNG (English)
        """
        if not self.portfolio_value:
            print("No portfolio data to plot")
            return
        os.makedirs(out_dir, exist_ok=True)

        dates = [pv['date'] for pv in self.portfolio_value]
        values = [pv['value'] for pv in self.portfolio_value]
        initial = self.initial_cash if self.initial_cash else (values[0] if values else 1)
        returns_pct = [(v / initial - 1.0) * 100.0 for v in values]

        fig, ax = plt.subplots(1, 1, figsize=(15, 5))
        ax.plot(dates, returns_pct, color='blue', linewidth=1.6, label='Return %')
        ax.axhline(y=0, color='gray', linestyle='--', linewidth=1)
        ax.set_title('Equity Curve (Return %)', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Return (%)')
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.tight_layout()
        png_path = os.path.join(out_dir, f"{prefix}_portfolio.png")
        plt.savefig(png_path)
        plt.close(fig)
        print(f"Saved chart: {png_path}")
    
    def plot_combined(self, df, signals, out_dir="backtest_out", prefix="chart"):
        """
        Plot a single figure with two rows:
        (1) Price with Buy/Sell signals, (2) Equity curve as return (%),
        and add summary text at the bottom.
        """
        if not self.portfolio_value:
            print("No portfolio data to plot")
            return
        os.makedirs(out_dir, exist_ok=True)

        dates = [pv['date'] for pv in self.portfolio_value]
        values = [pv['value'] for pv in self.portfolio_value]
        initial = self.initial_cash if self.initial_cash else (values[0] if values else 1)
        final_value = values[-1] if values else initial
        total_return_pct = (final_value / initial - 1.0) * 100.0 if initial else 0.0

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)

        # Top: price with MAs and signals
        ax1.plot(df.index, df['close'], label='Close', color='blue', linewidth=1.2)
        if 'ma5' in df.columns:
            ax1.plot(df.index, df['ma5'], label='MA5', color='red', alpha=0.8, linewidth=1)
        if 'ma20' in df.columns:
            ax1.plot(df.index, df['ma20'], label='MA20', color='orange', alpha=0.8, linewidth=1)
        # Handle both DataFrame and list formats for signals
        if hasattr(signals, 'iterrows'):  # DataFrame format (from fn_2.py)
            buy_signals = signals[signals['signal'] == 'BUY']
            sell_signals = signals[signals['signal'] == 'SELL']
            if not buy_signals.empty:
                ax1.scatter(buy_signals.index, buy_signals['close'], color='red', marker='^', s=80, label='Buy')
            if not sell_signals.empty:
                ax1.scatter(sell_signals.index, sell_signals['close'], color='green', marker='v', s=80, label='Sell')
        else:  # List format (from fn_1.py)
            buy_signals = [s for s in signals if s['action'] == 'BUY']
            sell_signals = [s for s in signals if s['action'] == 'SELL']
            if buy_signals:
                buy_dates = [s['date'] for s in buy_signals]
                buy_prices = [s['price'] for s in buy_signals]
                ax1.scatter(buy_dates, buy_prices, color='red', marker='^', s=80, label='Buy')
            if sell_signals:
                sell_dates = [s['date'] for s in sell_signals]
                sell_prices = [s['price'] for s in sell_signals]
                ax1.scatter(sell_dates, sell_prices, color='green', marker='v', s=80, label='Sell')
        ax1.set_title('Price with Buy/Sell Signals', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Price')
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # Bottom: equity curve (return %)
        returns_pct = [(v / initial - 1.0) * 100.0 for v in values]
        ax2.plot(dates, returns_pct, color='blue', linewidth=1.6, label='Return %')
        ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1)
        ax2.set_title('Equity Curve (Return %)', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Return (%)')
        ax2.grid(True, alpha=0.3)
        ax2.legend()

        # Reserve bottom margin for summary text
        fig.subplots_adjust(bottom=0.16)
        summary_text = (
            f"Initial capital: {initial:,.0f}    "
            f"Final capital: {final_value:,.0f}    "
            f"Total return: {total_return_pct:.2f}%"
        )
        fig.text(0.01, 0.02, summary_text, ha='left', va='bottom', fontsize=12)

        plt.tight_layout(rect=[0, 0.06, 1, 1])
        png_path = os.path.join(out_dir, f"{prefix}_combined.png")
        plt.savefig(png_path)
        plt.close(fig)
        print(f"Saved chart: {png_path}")
    
    def print_strategy_summary(self, performance):
        """
        打印策略总结
        """
        print("=" * 60)
        print("牛市科技股票量化交易策略回测结果")
        print("=" * 60)
        
        if not performance or not isinstance(performance, dict):
            print("Error: performance data is empty or invalid")
            return
            
        try:
            print(f"总收益率: {performance['total_return']:.2f}%")
            print(f"年化收益率: {performance['annual_return']:.2f}%")
            print(f"最大回撤: {performance['max_drawdown']:.2f}%")
            print(f"胜率: {performance['win_rate']:.2f}%")
            print(f"夏普比率: {performance['sharpe_ratio']:.2f}")
            print(f"总交易次数: {performance['total_trades']}")
            print(f"买入次数: {performance['buy_trades']}")
            print(f"卖出次数: {performance['sell_trades']}")
            print(f"最终资金: {performance['final_value']:,.0f}")
            print(f"初始资金: {performance['initial_value']:,.0f}")
        except KeyError as e:
            print(f"Error: Missing key in performance data: {e}")
        except Exception as e:
            print(f"Error: {e}")
            
        print("=" * 60)
        
        # 打印最近的交易记录
        if self.trades:
            print("\n最近交易记录:")
            for trade in self.trades[-5:]:
                if trade['action'] == 'BUY':
                    print(f"买入: {trade['date'].strftime('%Y-%m-%d')} "
                          f"价格: {trade['price']:.2f} 数量: {trade['shares']} "
                          f"原因: {trade['reason']}")
                else:
                    profit = trade.get('profit', 0)
                    print(f"卖出: {trade['date'].strftime('%Y-%m-%d')} "
                          f"价格: {trade['price']:.2f} 数量: {trade['shares']} "
                          f"盈亏: {profit:.2f} 原因: {trade['reason']}")
    
    def run_backtest(self, stock_code, start_date, end_date):
        """
        运行完整的回测流程
        """
        print(f"开始回测股票: {stock_code}")
        print(f"回测期间: {start_date} 到 {end_date}")
        print("-" * 50)
        
        try:
            # 1. 加载数据
            df = self.load_stock_data(stock_code, start_date, end_date)
            
            # 2. 计算指标
            df = self.calculate_all_indicators(df)
            
            # 3. 执行回测
            performance = self.backtest_strategy(df)
            
            # 4. 生成交易信号（用于绘图）
            signals = self.strategy.generate_signals(df)
            
            # 5. 输出结果
            self.print_strategy_summary(performance)
            
            # 6. 保存合成图表（上下布局）
            strategy_name = "fn2_momentum_vol_breakout" if hasattr(self.strategy, 'vol_min_pct') else "fn1_tech_stock"
            prefix = f"{stock_code}_{start_date}_{end_date}_{strategy_name}"
            self.plot_combined(df, signals, prefix=prefix)
            
            return performance, df, signals
            
        except Exception as e:
            print(f"回测过程中发生错误: {str(e)}")
            return None, None, None

def main():
    """
    主函数 - 支持命令行参数
    用法: python3 testback.py <start_date> <end_date> <stock_code>
    日期格式: YYYY-MM-DD
    """
    print("牛市科技股票量化交易策略回测系统")
    print("=" * 50)
    
    # 解析参数（开始日期 结束日期 股票代码）
    if len(sys.argv) >= 4:
        start_date = sys.argv[1]
        end_date = sys.argv[2]
        stock_code = sys.argv[3]
    else:
        # 默认参数（可修改）
        start_date = "2025-06-01"
        end_date = "2025-08-18"
        stock_code = "601360"
    
    # 创建回测引擎（默认使用fn2策略，可以通过修改这里来切换策略）
    # strategy_type 选项: 'fn1' (牛市科技股策略) 或 'fn2' (动量+波动率+突破策略)
    strategy_type = 'fn2'  
    engine = BacktestEngine(initial_cash=1000000, strategy_type=strategy_type)
    
    print(f"使用策略: {'fn2 - 动量+波动率+突破策略' if strategy_type == 'fn2' else 'fn1 - 牛市科技股策略'}")
    
    print(f"示例回测参数:")
    print(f"股票代码: {stock_code}")
    print(f"开始日期: {start_date}")
    print(f"结束日期: {end_date}")
    print(f"初始资金: {engine.initial_cash:,.0f}")
    
    # 运行回测
    performance, df, signals = engine.run_backtest(stock_code, start_date, end_date)
    
    if performance:
        print("\n回测完成！图表已保存至 backtest_out/ 目录。")
    else:
        print("\n回测失败！")

if __name__ == "__main__":
    main()