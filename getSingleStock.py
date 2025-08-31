import baostock as bs
import pandas as pd
import json
import os

# 配置参数
stock = {
    "start_date": "2024-01-01",
    "end_date": "2024-06-30",
    "output_dir": "data",
    "stock_code": "sz.002230",  # 你可以修改为任意股票代码
    "stock_name": "科大讯飞"      # 你可以修改为任意股票名称
}

# 登录baostock
lg = bs.login()
print("登录状态:", lg.error_code)

try:
    # 查询历史K线数据
    rs = bs.query_history_k_data_plus(
        stock["stock_code"],
        "date,open,high,low,close,volume",
        start_date=stock["start_date"],
        end_date=stock["end_date"],
        frequency="d",
        adjustflag="2"  # 前复权
    )
    stock_list = []
    while (rs.error_code == '0') & rs.next():
        stock_list.append(rs.get_row_data())
    if stock_list:
        df = pd.DataFrame(stock_list, columns=rs.fields)
        os.makedirs(stock["output_dir"], exist_ok=True)
        file_name = f"{stock['stock_name']}-{stock['stock_code'].split('.')[-1]}.json"
        file_path = os.path.join(stock["output_dir"], file_name)
        df.to_json(file_path, orient='records', force_ascii=False, indent=2)
        print(f"已保存数据到: {file_path}")
    else:
        print("未获取到数据")
except Exception as e:
    print("发生错误:", str(e))
finally:
    bs.logout()
    print("已登出系统")
