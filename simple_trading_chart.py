import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import seaborn as sns
from fn_2 import SingleStockMomentumVolBreakoutStrategy
import json
import os

# 设置中文字体和样式
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.style.use('seaborn-v0_8')

def load_stock_data(stock_code='601360', start_date='2024-01-01', end_date='2025-08-18'):
    """加载股票数据"""
    data_dir = "data"
    matches = [f for f in os.listdir(data_dir) if stock_code in f and f.endswith('.json')]
    if not matches:
        raise FileNotFoundError(f'No data file found for code: {stock_code}')
    
    file_path = os.path.join(data_dir, matches[0])
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    for col in ('open', 'high', 'low', 'close'):
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(subset=['open', 'high', 'low', 'close'])
    df = df[(df['date'] >= pd.to_datetime(start_date)) & 
            (df['date'] <= pd.to_datetime(end_date))]
    df = df.sort_values('date').set_index('date')
    return df

def create_trading_process_chart():
    """创建清晰的交易过程图表"""
    
    # 加载数据
    df = load_stock_data()
    strategy = SingleStockMomentumVolBreakoutStrategy()
    signals_df = strategy.generate_signals(df)
    
    # 创建图表
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 12))
    fig.suptitle('fn_2.py 策略完整交易过程可视化', fontsize=20, fontweight='bold', y=0.98)
    
    # 1. 主价格图 + 买卖信号
    ax1.plot(signals_df.index, signals_df['close'], 'navy', linewidth=2, label='股价', alpha=0.8)
    ax1.plot(signals_df.index, signals_df['fast_ma'], 'orange', linewidth=1.5, label='快均线(MA20)', alpha=0.9)
    ax1.plot(signals_df.index, signals_df['slow_ma'], 'red', linewidth=1.5, label='慢均线(MA60)', alpha=0.9)
    
    # 买卖信号
    buy_signals = signals_df[signals_df['signal'] == 'BUY']
    sell_signals = signals_df[signals_df['signal'] == 'SELL']
    add_signals = signals_df[signals_df['signal'] == 'ADD']
    
    if not buy_signals.empty:
        ax1.scatter(buy_signals.index, buy_signals['close'], color='red', marker='^', 
                   s=120, label=f'买入 ({len(buy_signals)}次)', zorder=6, edgecolors='darkred', linewidth=1)
    
    if not sell_signals.empty:
        ax1.scatter(sell_signals.index, sell_signals['close'], color='green', marker='v', 
                   s=120, label=f'卖出 ({len(sell_signals)}次)', zorder=6, edgecolors='darkgreen', linewidth=1)
    
    if not add_signals.empty:
        ax1.scatter(add_signals.index, add_signals['close'], color='purple', marker='s', 
                   s=100, label=f'加仓 ({len(add_signals)}次)', zorder=6, edgecolors='indigo', linewidth=1)
    
    ax1.set_title('股价走势 + 交易信号', fontsize=14, fontweight='bold')
    ax1.set_ylabel('价格 (元)', fontsize=12)
    ax1.legend(loc='upper left', fontsize=11)
    ax1.grid(True, alpha=0.3)
    
    # 2. 风险管理 - 止损止盈
    ax2.plot(signals_df.index, signals_df['close'], 'navy', linewidth=2, label='股价', alpha=0.8)
    ax2.plot(signals_df.index, signals_df['dynamic_stop_loss'], 'red', linewidth=1.5, 
             linestyle='--', label='动态止损', alpha=0.8)
    ax2.plot(signals_df.index, signals_df['take_profit_price'], 'green', linewidth=1.5, 
             linestyle='--', label='止盈目标', alpha=0.8)
    
    # 填充风险回报区间
    ax2.fill_between(signals_df.index, signals_df['dynamic_stop_loss'], signals_df['take_profit_price'], 
                    alpha=0.15, color='blue', label='风险回报区间')
    
    ax2.set_title('风险管理 - 止损止盈设置', fontsize=14, fontweight='bold')
    ax2.set_ylabel('价格 (元)', fontsize=12)
    ax2.legend(loc='upper left', fontsize=11)
    ax2.grid(True, alpha=0.3)
    
    # 3. 市场状态分析
    ax3_twin = ax3.twinx()
    
    # 趋势强度
    ax3.plot(signals_df.index, signals_df['trend_strength_pct'], 'purple', linewidth=2, 
             label='趋势强度%', alpha=0.8)
    ax3.axhline(y=strategy.trend_strength_threshold*100, color='red', linestyle=':', 
                alpha=0.8, label='趋势阈值')
    ax3.axhline(y=-strategy.trend_strength_threshold*100, color='red', linestyle=':', alpha=0.8)
    ax3.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
    
    # 波动率比率
    ax3_twin.plot(signals_df.index, signals_df['atr_filter_ratio'], 'brown', linewidth=2, 
                  label='波动率比率', alpha=0.8)
    ax3_twin.axhline(y=strategy.vol_min_pct, color='green', linestyle=':', alpha=0.8)
    ax3_twin.axhline(y=strategy.vol_max_pct, color='green', linestyle=':', alpha=0.8)
    ax3_twin.fill_between(signals_df.index, strategy.vol_min_pct, strategy.vol_max_pct, 
                         alpha=0.1, color='green', label='波动率有效区间')
    
    ax3.set_title('市场状态分析', fontsize=14, fontweight='bold')
    ax3.set_ylabel('趋势强度 (%)', fontsize=12, color='purple')
    ax3_twin.set_ylabel('波动率比率', fontsize=12, color='brown')
    ax3.legend(loc='upper left', fontsize=10)
    ax3_twin.legend(loc='upper right', fontsize=10)
    ax3.grid(True, alpha=0.3)
    
    # 4. 交易统计和信号分布
    ax4.axis('off')
    
    # 统计数据
    total_days = len(signals_df)
    buy_count = len(buy_signals)
    sell_count = len(sell_signals)
    add_count = len(add_signals)
    signal_days = len(signals_df[signals_df['signal'] != 'HOLD'])
    
    # 风险等级统计
    risk_counts = signals_df['risk_level'].value_counts()
    low_risk = risk_counts.get('LOW', 0)
    medium_risk = risk_counts.get('MEDIUM', 0)
    high_risk = risk_counts.get('HIGH', 0)
    
    # 创建统计文本
    stats_text = f"""
交易统计总览 ({signals_df.index[0].strftime('%Y-%m-%d')} 至 {signals_df.index[-1].strftime('%Y-%m-%d')})

📊 信号统计:
• 总交易天数: {total_days} 天
• 有信号天数: {signal_days} 天 ({signal_days/total_days*100:.1f}%)
• 买入信号: {buy_count} 次
• 卖出信号: {sell_count} 次  
• 加仓信号: {add_count} 次

🛡️ 风险分布:
• 低风险: {low_risk} 天 ({low_risk/total_days*100:.1f}%)
• 中风险: {medium_risk} 天 ({medium_risk/total_days*100:.1f}%)
• 高风险: {high_risk} 天 ({high_risk/total_days*100:.1f}%)

📈 策略特点:
• 平均信号强度: {signals_df['signal_strength'].mean():.3f}
• 最强信号强度: {signals_df['signal_strength'].max():.3f}
• 风险回报比平均: {signals_df['risk_reward_ratio'].mean():.2f}

🎯 最近表现:
• 最新价格: {signals_df['close'].iloc[-1]:.2f} 元
• 当前趋势强度: {signals_df['trend_strength_pct'].iloc[-1]:.2f}%
• 当前波动率: {signals_df['atr_filter_ratio'].iloc[-1]:.2f}x
• 当前风险等级: {signals_df['risk_level'].iloc[-1]}
    """
    
    ax4.text(0.05, 0.95, stats_text, transform=ax4.transAxes, fontsize=11,
             verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', 
             facecolor='lightblue', alpha=0.8))
    
    # 格式化所有日期轴
    for ax in [ax1, ax2, ax3]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    
    # 保存图表
    os.makedirs('backtest_out', exist_ok=True)
    filename = f'backtest_out/trading_process_visualization.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
    print(f'✅ 交易过程可视化图表已保存: {filename}')
    
    # 打印关键信息
    print("\n" + "="*60)
    print("📊 交易过程关键信息")
    print("="*60)
    print(f"策略表现总结:")
    print(f"• 买入信号: {buy_count} 次 (平均每 {total_days//buy_count if buy_count > 0 else 0} 天一次)")
    print(f"• 卖出信号: {sell_count} 次 (买卖比例 1:{sell_count/buy_count if buy_count > 0 else 0:.1f})")
    print(f"• 信号效率: {signal_days/total_days*100:.1f}% (有信号的交易日比例)")
    print(f"• 风险控制: {low_risk/total_days*100:.1f}% 低风险天数")
    
    return fig, signals_df

if __name__ == "__main__":
    print("🎯 生成简化版交易过程可视化...")
    try:
        fig, signals_df = create_trading_process_chart()
        print("✅ 可视化完成！请查看生成的图表文件。")
    except Exception as e:
        print(f"❌ 生成图表时出错: {str(e)}")
