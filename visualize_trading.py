import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import seaborn as sns
from fn_2 import SingleStockMomentumVolBreakoutStrategy
import json
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class TradingVisualizer:
    def __init__(self, stock_code='601360', start_date='2024-01-01', end_date='2025-08-18'):
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.strategy = SingleStockMomentumVolBreakoutStrategy()
        
    def load_data(self):
        """加载股票数据"""
        data_dir = "data"
        matches = [f for f in os.listdir(data_dir) if self.stock_code in f and f.endswith('.json')]
        if not matches:
            raise FileNotFoundError(f'No data file found for code: {self.stock_code}')
        
        file_path = os.path.join(data_dir, matches[0])
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        for col in ('open', 'high', 'low', 'close'):
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna(subset=['open', 'high', 'low', 'close'])
        df = df[(df['date'] >= pd.to_datetime(self.start_date)) & 
                (df['date'] <= pd.to_datetime(self.end_date))]
        df = df.sort_values('date').set_index('date')
        return df
    
    def create_comprehensive_chart(self):
        """创建综合交易可视化图表"""
        # 加载数据并生成信号
        df = self.load_data()
        signals_df = self.strategy.generate_signals(df)
        
        # 筛选有信号的数据
        buy_signals = signals_df[signals_df['signal'] == 'BUY'].copy()
        sell_signals = signals_df[signals_df['signal'] == 'SELL'].copy()
        add_signals = signals_df[signals_df['signal'] == 'ADD'].copy()
        
        # 创建图表
        fig = plt.figure(figsize=(20, 16))
        gs = fig.add_gridspec(5, 2, height_ratios=[3, 2, 1.5, 1.5, 1], hspace=0.3, wspace=0.3)
        
        # 1. 主价格图表（左上）
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(signals_df.index, signals_df['close'], 'b-', linewidth=1.2, label='收盘价', alpha=0.8)
        ax1.plot(signals_df.index, signals_df['fast_ma'], 'orange', linewidth=1, label=f'MA{self.strategy.fast_ma_window}', alpha=0.8)
        ax1.plot(signals_df.index, signals_df['slow_ma'], 'red', linewidth=1, label=f'MA{self.strategy.slow_ma_window}', alpha=0.8)
        
        # 添加买卖信号点
        if not buy_signals.empty:
            ax1.scatter(buy_signals.index, buy_signals['close'], color='red', marker='^', 
                       s=100, label=f'买入信号 ({len(buy_signals)})', zorder=5, alpha=0.8)
        if not sell_signals.empty:
            ax1.scatter(sell_signals.index, sell_signals['close'], color='green', marker='v', 
                       s=100, label=f'卖出信号 ({len(sell_signals)})', zorder=5, alpha=0.8)
        if not add_signals.empty:
            ax1.scatter(add_signals.index, add_signals['close'], color='purple', marker='s', 
                       s=80, label=f'加仓信号 ({len(add_signals)})', zorder=5, alpha=0.8)
        
        ax1.set_title(f'{self.stock_code} 动量+波动率+突破策略 - 完整交易过程可视化', fontsize=16, fontweight='bold')
        ax1.set_ylabel('价格 (元)', fontsize=12)
        ax1.legend(loc='upper left', fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # 2. 趋势强度和波动率（左中）
        ax2 = fig.add_subplot(gs[1, 0])
        ax2.plot(signals_df.index, signals_df['trend_strength_pct'], 'purple', linewidth=1.5, label='趋势强度%')
        ax2.axhline(y=self.strategy.trend_strength_threshold*100, color='red', linestyle='--', alpha=0.7, label='趋势阈值')
        ax2.axhline(y=-self.strategy.trend_strength_threshold*100, color='red', linestyle='--', alpha=0.7)
        ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
        ax2.set_ylabel('趋势强度 (%)', fontsize=10)
        ax2.legend(fontsize=9)
        ax2.grid(True, alpha=0.3)
        
        # 3. ATR和波动率过滤（右中）
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.plot(signals_df.index, signals_df['atr_filter_ratio'], 'brown', linewidth=1.5, label='波动率比率')
        ax3.axhline(y=self.strategy.vol_min_pct, color='green', linestyle='--', alpha=0.7, label='波动率区间')
        ax3.axhline(y=self.strategy.vol_max_pct, color='green', linestyle='--', alpha=0.7)
        ax3.fill_between(signals_df.index, self.strategy.vol_min_pct, self.strategy.vol_max_pct, 
                        alpha=0.1, color='green', label='有效区间')
        ax3.set_ylabel('波动率比率', fontsize=10)
        ax3.legend(fontsize=9)
        ax3.grid(True, alpha=0.3)
        
        # 4. 信号强度热力图（左下中）
        ax4 = fig.add_subplot(gs[2, 0])
        signal_strength = signals_df['signal_strength'].values.reshape(1, -1)
        im = ax4.imshow(signal_strength, aspect='auto', cmap='RdYlGn', vmin=0, vmax=1)
        ax4.set_ylabel('信号强度', fontsize=10)
        ax4.set_yticks([])
        plt.colorbar(im, ax=ax4, orientation='horizontal', pad=0.1, shrink=0.8)
        
        # 5. 风险等级分布（右下中）
        ax5 = fig.add_subplot(gs[2, 1])
        risk_counts = signals_df['risk_level'].value_counts()
        colors = {'LOW': 'green', 'MEDIUM': 'yellow', 'HIGH': 'red'}
        bars = ax5.bar(risk_counts.index, risk_counts.values, 
                      color=[colors.get(x, 'gray') for x in risk_counts.index])
        ax5.set_ylabel('天数', fontsize=10)
        ax5.set_title('风险等级分布', fontsize=10)
        for bar in bars:
            height = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{int(height)}', ha='center', va='bottom', fontsize=9)
        
        # 6. 交易统计表格（左下）
        ax6 = fig.add_subplot(gs[3, 0])
        ax6.axis('off')
        
        # 计算统计数据
        total_signals = len(buy_signals) + len(sell_signals) + len(add_signals)
        buy_count = len(buy_signals)
        sell_count = len(sell_signals)
        add_count = len(add_signals)
        
        stats_data = [
            ['总交易信号', f'{total_signals}个'],
            ['买入信号', f'{buy_count}个'],
            ['卖出信号', f'{sell_count}个'],
            ['加仓信号', f'{add_count}个'],
            ['平均信号强度', f'{signals_df["signal_strength"].mean():.2f}'],
            ['高风险天数', f'{len(signals_df[signals_df["risk_level"]=="HIGH"])}天'],
            ['低风险天数', f'{len(signals_df[signals_df["risk_level"]=="LOW"])}天']
        ]
        
        table = ax6.table(cellText=stats_data, colLabels=['指标', '数值'],
                         cellLoc='center', loc='center', 
                         colWidths=[0.6, 0.4])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)
        ax6.set_title('交易统计', fontsize=12, fontweight='bold', pad=20)
        
        # 7. 最近信号详情（右下）
        ax7 = fig.add_subplot(gs[3, 1])
        ax7.axis('off')
        
        # 获取最近的信号
        recent_signals = signals_df[signals_df['signal'] != 'HOLD'].tail(5)
        signal_details = []
        for idx, row in recent_signals.iterrows():
            signal_details.append([
                idx.strftime('%m-%d'),
                row['signal'],
                f"{row['close']:.2f}",
                row['risk_level']
            ])
        
        if signal_details:
            table2 = ax7.table(cellText=signal_details, 
                              colLabels=['日期', '信号', '价格', '风险'],
                              cellLoc='center', loc='center',
                              colWidths=[0.25, 0.25, 0.25, 0.25])
            table2.auto_set_font_size(False)
            table2.set_fontsize(9)
            table2.scale(1, 1.5)
        ax7.set_title('最近信号', fontsize=12, fontweight='bold', pad=20)
        
        # 8. 止损止盈价格（底部）
        ax8 = fig.add_subplot(gs[4, :])
        ax8.plot(signals_df.index, signals_df['close'], 'b-', linewidth=1, label='收盘价', alpha=0.7)
        ax8.plot(signals_df.index, signals_df['dynamic_stop_loss'], 'r--', linewidth=1, label='动态止损', alpha=0.7)
        ax8.plot(signals_df.index, signals_df['take_profit_price'], 'g--', linewidth=1, label='止盈目标', alpha=0.7)
        ax8.fill_between(signals_df.index, signals_df['dynamic_stop_loss'], signals_df['take_profit_price'], 
                        alpha=0.1, color='blue', label='风险回报区间')
        ax8.set_ylabel('价格 (元)', fontsize=10)
        ax8.set_xlabel('日期', fontsize=10)
        ax8.legend(loc='upper left', fontsize=9)
        ax8.grid(True, alpha=0.3)
        
        # 格式化日期轴
        for ax in [ax1, ax2, ax3, ax8]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # 保存图表
        os.makedirs('backtest_out', exist_ok=True)
        filename = f'backtest_out/{self.stock_code}_{self.start_date}_{self.end_date}_comprehensive_trading_analysis.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f'综合交易分析图表已保存: {filename}')
        
        return fig, signals_df

    def create_signal_timeline(self, signals_df):
        """创建信号时间线图"""
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # 获取所有信号
        all_signals = signals_df[signals_df['signal'] != 'HOLD'].copy()
        
        if all_signals.empty:
            print("没有找到交易信号")
            return
        
        # 创建时间线
        signal_colors = {'BUY': 'red', 'SELL': 'green', 'ADD': 'purple'}
        signal_markers = {'BUY': '^', 'SELL': 'v', 'ADD': 's'}
        
        y_pos = 1
        for idx, row in all_signals.iterrows():
            color = signal_colors.get(row['signal'], 'blue')
            marker = signal_markers.get(row['signal'], 'o')
            
            # 绘制信号点
            ax.scatter(idx, y_pos, c=color, marker=marker, s=200, alpha=0.8, edgecolors='black')
            
            # 添加详细信息
            info_text = f"{row['signal']}\n价格:{row['close']:.2f}\n风险:{row['risk_level']}\n强度:{row['signal_strength']:.2f}"
            ax.annotate(info_text, (idx, y_pos), xytext=(0, 30), 
                       textcoords='offset points', ha='center',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.3),
                       fontsize=8)
        
        # 设置图表
        ax.set_ylim(0.5, 1.5)
        ax.set_ylabel('')
        ax.set_yticks([])
        ax.set_xlabel('日期', fontsize=12)
        ax.set_title(f'{self.stock_code} 交易信号时间线', fontsize=14, fontweight='bold')
        
        # 添加图例
        for signal, color in signal_colors.items():
            marker = signal_markers[signal]
            ax.scatter([], [], c=color, marker=marker, s=100, label=signal, edgecolors='black')
        ax.legend(loc='upper right')
        
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # 保存图表
        filename = f'backtest_out/{self.stock_code}_{self.start_date}_{self.end_date}_signal_timeline.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f'信号时间线图表已保存: {filename}')
        
        return fig

def main():
    """主函数"""
    print("🎯 开始生成交易过程可视化图表...")
    
    # 创建可视化器
    visualizer = TradingVisualizer(stock_code='601360', start_date='2024-01-01', end_date='2025-08-18')
    
    try:
        # 生成综合分析图表
        print("📊 生成综合交易分析图表...")
        fig1, signals_df = visualizer.create_comprehensive_chart()
        
        # 生成信号时间线
        print("📈 生成交易信号时间线...")
        fig2 = visualizer.create_signal_timeline(signals_df)
        
        # 打印交易统计
        buy_signals = signals_df[signals_df['signal'] == 'BUY']
        sell_signals = signals_df[signals_df['signal'] == 'SELL']
        add_signals = signals_df[signals_df['signal'] == 'ADD']
        
        print("\n" + "="*60)
        print("📊 交易过程统计")
        print("="*60)
        print(f"总交易天数: {len(signals_df)} 天")
        print(f"买入信号: {len(buy_signals)} 次")
        print(f"卖出信号: {len(sell_signals)} 次")
        print(f"加仓信号: {len(add_signals)} 次")
        print(f"平均信号强度: {signals_df['signal_strength'].mean():.3f}")
        print(f"高风险天数: {len(signals_df[signals_df['risk_level']=='HIGH'])} 天")
        print(f"中风险天数: {len(signals_df[signals_df['risk_level']=='MEDIUM'])} 天")
        print(f"低风险天数: {len(signals_df[signals_df['risk_level']=='LOW'])} 天")
        
        if not buy_signals.empty:
            print(f"\n最近买入信号:")
            for idx, row in buy_signals.tail(3).iterrows():
                print(f"  {idx.strftime('%Y-%m-%d')}: 价格{row['close']:.2f}, 风险{row['risk_level']}, 强度{row['signal_strength']:.2f}")
        
        if not sell_signals.empty:
            print(f"\n最近卖出信号:")
            for idx, row in sell_signals.tail(3).iterrows():
                print(f"  {idx.strftime('%Y-%m-%d')}: 价格{row['close']:.2f}, 原因:{row['signal_reason']}")
        
        print(f"\n📁 图表已保存到 backtest_out/ 目录")
        print("✅ 可视化完成！")
        
    except Exception as e:
        print(f"❌ 生成图表时出错: {str(e)}")

if __name__ == "__main__":
    main()
