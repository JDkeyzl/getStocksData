import os
import json
import glob
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta

DATA_DIR = "data"

# 1. 检查一个data文件，获取最新日期
def get_latest_date_from_any_file():
    for file_path in glob.glob(os.path.join(DATA_DIR, "*.json")):
        with open(file_path, "r", encoding="utf-8") as f:
            stock_data = json.load(f)
        if isinstance(stock_data, list) and stock_data:
            last_date = stock_data[-1]["date"]
            return last_date  # 格式如 '2024-06-01'
    return None

def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

# 2. 获取股票列表
def get_stock_list():
    stock_list = []
    for file_path in glob.glob(os.path.join(DATA_DIR, "*.json")):
        filename = os.path.basename(file_path)
        if '-' in filename:
            stock_name, stock_code = filename.replace('.json', '').rsplit('-', 1)
        else:
            stock_name = filename.replace('.json', '')
            stock_code = ""
        stock_list.append({
            "file_path": file_path,
            "stock_name": stock_name,
            "stock_code": stock_code
        })
    return stock_list

# 3. 获取并追加新数据
def update_all_stocks():
    latest_date = get_latest_date_from_any_file()
    if not latest_date:
        print("未找到有效的data文件或数据为空！")
        return
    today = get_today_str()
    print(f"将为所有股票补充 {latest_date} 到 {today} 的数据...")
    lg = bs.login()
    if lg.error_code != '0':
        print("baostock 登录失败：", lg.error_msg)
        return
    try:
        stock_list = get_stock_list()
        for stock in stock_list:
            file_path = stock["file_path"]
            code = stock["stock_code"]
            if not code:
                continue
            # 读取原有数据
            with open(file_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
            # 查询新数据
            rs = bs.query_history_k_data_plus(
                code if '.' in code else f"sh.{code}",
                "date,open,high,low,close",
                start_date=(datetime.strptime(latest_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d"),
                end_date=today,
                frequency="d",
                adjustflag="2"
            )
            new_data = []
            while (rs.error_code == '0') & rs.next():
                row = rs.get_row_data()
                # 字段顺序: date,open,high,low,close
                new_data.append({
                    "date": row[0],
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4]
                })
            if new_data:
                # 检查去重
                old_dates = set(item["date"] for item in old_data)
                filtered_new = [item for item in new_data if item["date"] not in old_dates]
                if filtered_new:
                    all_data = old_data + filtered_new
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(all_data, f, ensure_ascii=False, indent=2)
                    print(f"{file_path} 已追加 {len(filtered_new)} 条新数据")
                else:
                    print(f"{file_path} 没有新数据可追加")
            else:
                print(f"{file_path} 没有获取到新数据")
    finally:
        bs.logout()
        print("baostock 已登出")

if __name__ == "__main__":
    update_all_stocks()
