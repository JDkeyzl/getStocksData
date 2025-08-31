import os
import json
import glob
import csv

daylength = 12
def is_nine_downward(closes):
    # closes: 最近daylength天的收盘价，长度必须为daylength
    # 统计最后9天中有多少天是下跌的
    down_days = 0
    for i in range(-11, 0):  # closes[-9]~closes[-2]与前一天比较
        if closes[i] < closes[i-1]:
            down_days += 1
    return down_days >= 9

def main():
    data_dir = "data"
    result = []
    for file_path in glob.glob(os.path.join(data_dir, "*.json")):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                stock_data = json.load(f)
            if not isinstance(stock_data, list) or len(stock_data) < daylength:
                continue
            lastdaylength = stock_data[-daylength:]
            closes = []
            for item in lastdaylength:
                try:
                    closes.append(round(float(item["close"]), 2))
                except (ValueError, TypeError, KeyError):
                    break  # 有异常直接跳过该股票
            if len(closes) != daylength:
                continue
            if is_nine_downward(closes):
                filename = os.path.basename(file_path)
                if '-' in filename:
                    stock_name, stock_code = filename.replace('.json', '').rsplit('-', 1)
                else:
                    stock_name = filename.replace('.json', '')
                    stock_code = ""
                result.append((stock_name, stock_code))
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue

    # 输出到csv
    with open("9high-result.csv", "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["stock_name", "stock_code"])
        for name, code in result:
            writer.writerow([name, code])
    print(f"已输出 {len(result)} 条结果到 9high-result.csv")

if __name__ == "__main__":
    main()
