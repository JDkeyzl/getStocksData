import baostock as bs
import pandas as pd
import json
import os
from time import sleep

# 登录系统
lg = bs.login()
print("登录状态:", lg.error_code)

try:
    with open("pure_stock.json", "r", encoding="utf-8") as f:
        stocks = json.load(f)
    
    print("总共需要处理", len(stocks), "只股票")
    os.makedirs("data", exist_ok=True)
    
    success_count = 0
    for i, stock in enumerate(stocks, 1):
        print("处理第", i, "/", len(stocks), "只股票:", stock["code_name"])
        
        try:
            rs = bs.query_history_k_data_plus(
                stock["code"],
                "date,open,high,low,close",
                start_date="2024-06-01",
                end_date="2025-06-18",
                frequency="d",
                adjustflag="2"
            )
            
            stock_list = []
            while (rs.error_code == "0") & rs.next():
                stock_list.append(rs.get_row_data())
            
            if stock_list:
                df = pd.DataFrame(stock_list, columns=rs.fields)
                file_name = stock["code_name"] + "-" + stock["code"].split(".")[-1] + ".json"
                file_path = os.path.join("data", file_name)
                df.to_json(file_path, orient="records", force_ascii=False, indent=2)
                print("已保存数据到:", file_path)
                success_count += 1
            else:
                print("警告: 没有获取到数据")
            
            # sleep(0.5)
            
        except Exception as e:
            print("处理股票时出错:", str(e))
            continue
    
    print("处理完成！成功获取", success_count, "只股票的数据")

except Exception as e:
    print("发生错误:", str(e))

finally:
    bs.logout()
    print("已登出系统")
