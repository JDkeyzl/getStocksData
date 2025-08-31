import os
import json
import glob
import csv
import datetime

def find_double_bottom(stock_data, file_path, min_days=300, price_diff_threshold=0.03, last_days=10, min_gap_days=40):
    if len(stock_data) < min_days:
        print(f"{file_path} 数据不足{min_days}天，实际{len(stock_data)}天")
        return None
    data = []
    for item in stock_data:
        try:
            converted = {
                "date": item["date"],
                "close": round(float(item["close"]), 2),
                "low": round(float(item["low"]), 2)
            }
            data.append(converted)
        except (ValueError, TypeError, KeyError):
            continue
    if len(data) < min_days:
        print(f"清洗后数据不足{min_days}天，实际{len(data)}天")
        return None
    last_lookback = data[-min_days:-last_days]  # 点A搜索范围
    point_a = min(last_lookback, key=lambda x: x["close"])
    a_index = data.index(point_a)
    a_close = point_a["close"]
    a_low = point_a["low"]
    a_date = point_a["date"]
    last_x_days = data[-last_days:]
    for point_b in last_x_days:
        b_index = data.index(point_b)
        b_close = point_b["close"]
        b_low = point_b["low"]
        b_date = point_b["date"]
        price_diff = abs(b_close - a_close)
        price_diff_percent = round(price_diff / a_close, 4)
        gap_days = b_index - a_index
        if (
            price_diff_percent <= price_diff_threshold
            and b_date > a_date
            and gap_days >= min_gap_days
        ):
            print(f"找到双底: A={a_close} {a_date}, B={b_close} {b_date}, 差异={price_diff_percent:.2%}, 间隔天数={gap_days}")
            return {
                "a_date": a_date,
                "a_low": a_low,
                "b_date": b_date,
                "b_low": b_low,
                "diff": price_diff_percent,
                "gap_days": gap_days
            }
    return None

def analyze_stock_files(directory, last_days=10, min_gap_days=40):
    json_files = glob.glob(os.path.join(directory, "*.json"))
    print(f"找到 {len(json_files)} 个 JSON 文件")
    double_bottom_stocks = []
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                stock_data = json.load(f)
            if not stock_data or not isinstance(stock_data, list):
                print(f"无效数据: {file_path}, type: {type(stock_data)}, 内容: {str(stock_data)[:100]}")
                continue
            result = find_double_bottom(stock_data, file_path, last_days=last_days, min_gap_days=min_gap_days)
            if result:
                filename = os.path.basename(file_path)
                base = filename.replace('.json', '')
                if '-' in base:
                    stock_name, stock_code = base.rsplit('-', 1)
                    stock_code = f"'{stock_code}"
                else:
                    stock_name = base
                    stock_code = ""
                double_bottom_stocks.append([
                    stock_name,
                    stock_code,
                    result["a_date"],
                    result["a_low"],
                    result["b_date"],
                    result["b_low"],
                    f"{round(result['diff']*100, 2)}%",
                    result["gap_days"]
                ])
                print(f"发现双底形态: {filename}")
        except (json.JSONDecodeError, IOError, PermissionError) as e:
            print(f"处理文件 {file_path} 时出错: {str(e)}")
            continue
    # 自动生成CSV文件名
    today = datetime.datetime.now().strftime("%m%d")
    csv_file = f"result-{today}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["stock_name", "stock_code", "a_date", "a_low", "b_date", "b_low", "diff", "gap days"])
        for row in double_bottom_stocks:
            writer.writerow(row)
    print(f"\n===== 分析结果 =====")
    print(f"扫描文件总数: {len(json_files)}")
    print(f"发现双底形态的股票数: {len(double_bottom_stocks)}")
    print(f"结果已保存到: {csv_file}")
    if double_bottom_stocks:
        print("\n符合条件的股票:")
        for row in double_bottom_stocks:
            print(f"  - {row[0]}")

if __name__ == "__main__":
    data_directory = "data"
    analyze_stock_files(data_directory, last_days=10, min_gap_days=40)