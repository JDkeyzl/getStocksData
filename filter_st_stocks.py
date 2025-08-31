import json

# 读取原始JSON文件
with open("pure_stock.json", "r", encoding="utf-8") as f:
    stocks = json.load(f)

# 过滤掉名称中包含"st"的股票（不区分大小写）
filtered_stocks = [stock for stock in stocks if "st" not in stock["code_name"].lower()]

print(f"原始股票数量: {len(stocks)}")
print(f"过滤后股票数量: {len(filtered_stocks)}")
print(f"过滤掉的ST股票数量: {len(stocks) - len(filtered_stocks)}")

# 保存过滤后的数据到新文件
with open("all_pure_stock.json", "w", encoding="utf-8") as f:
    json.dump(filtered_stocks, f, ensure_ascii=False, indent=2)

print("已生成 all_pure_stock.json 文件")



# import baostock as bs
# import pandas as pd

# #### 登陆系统 ####
# lg = bs.login()
# # 显示登陆返回信息
# print('login respond error_code:'+lg.error_code)
# print('login respond  error_msg:'+lg.error_msg)

# #### 获取证券信息 ####
# rs = bs.query_all_stock(day="2025-06-20")            #day  表示查询的日期，为空默认为当前日期
# print('query_all_stock respond error_code:'+rs.error_code)
# print('query_all_stock respond  error_msg:'+rs.error_msg)

# #### 打印结果集 ####
# data_list = []
# while (rs.error_code == '0') & rs.next():
#     # 获取一条记录，将记录合并在一起
#     data_list.append(rs.get_row_data())
# result = pd.DataFrame(data_list, columns=rs.fields)

# #### 结果集输出到csv文件 ####   
# # result.to_csv("D:\\all_stock.csv", encoding="gbk", index=False)
# result.to_json("all_stock.json", orient='records', force_ascii=False, indent=2)

# print(result)

# #### 登出系统 ####
# bs.logout()