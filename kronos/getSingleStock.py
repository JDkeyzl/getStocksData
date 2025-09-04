import baostock as bs
import pandas as pd
import json
import os

# 配置参数
stock = {
    "start_date": "2024-01-01",
    "end_date": "2025-07-30",
    "output_dir": "data",
    "stock_code": "sz.002130",  # 你可以修改为任意股票代码
    "stock_name": "沃尔核材"      # 你可以修改为任意股票名称
}

# 登录baostock
lg = bs.login()
print("登录状态:", lg.error_code)

try:
    # 查询历史K线数据
    rs = bs.query_history_k_data_plus(
        stock["stock_code"],
        # "date,open,high,low,close,volume",
        "date,time,open,high,low,close,volume,amount",
        start_date=stock["start_date"],
        end_date=stock["end_date"],
        frequency="5",
        adjustflag="3"  # 前复权
    )
    stock_list = []
    while (rs.error_code == '0') & rs.next():
        stock_list.append(rs.get_row_data())
    if stock_list:
        df = pd.DataFrame(stock_list, columns=rs.fields)
        
        # 重命名列以匹配要求的格式
        df = df.rename(columns={
            'date': 'timestamps',
            'time': 'time_temp'  # 临时列名，稍后删除
        })
        
        # 合并日期和时间作为timestamps，格式化为易读格式
        def format_timestamp(date_str, time_str):
            # 时间格式: 20240102093500000 -> 2024-01-02 09:35:00
            if len(time_str) >= 8:
                year = time_str[:4]
                month = time_str[4:6]
                day = time_str[6:8]
                hour = time_str[8:10]
                minute = time_str[10:12]
                second = time_str[12:14]
                return f"{year}-{month}-{day} {hour}:{minute}:{second}"
            else:
                return f"{date_str} {time_str}"
        
        df['timestamps'] = df.apply(lambda row: format_timestamp(row['timestamps'], row['time_temp']), axis=1)
        df = df.drop('time_temp', axis=1)
        
        # 重新排列列的顺序
        df = df[['timestamps', 'open', 'high', 'low', 'close', 'volume', 'amount']]
        
        # 将数值列转换为float类型并限制小数位数为2位
        numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').round(2)
        
        os.makedirs(stock["output_dir"], exist_ok=True)
        
        # 保存为CSV文件
        csv_file_name = f"{stock['stock_name']}-{stock['stock_code'].split('.')[-1]}.csv"
        csv_file_path = os.path.join(stock["output_dir"], csv_file_name)
        df.to_csv(csv_file_path, index=False, encoding='utf-8-sig')
        print(f"已保存CSV数据到: {csv_file_path}")
        
        # 同时保存为JSON文件（保持原有功能）
        json_file_name = f"{stock['stock_name']}-{stock['stock_code'].split('.')[-1]}.json"
        json_file_path = os.path.join(stock["output_dir"], json_file_name)
        df.to_json(json_file_path, orient='records', force_ascii=False, indent=2)
        print(f"已保存JSON数据到: {json_file_path}")
        
        # 显示数据预览
        print(f"\n数据预览（前5行）:")
        print(df.head())
        print(f"\n数据形状: {df.shape}")
    else:
        print("未获取到数据")
except Exception as e:
    print("发生错误:", str(e))
finally:
    bs.logout()
    print("已登出系统")
