import pdfplumber
import pandas as pd

def convert_pdf_to_csv(pdf_file):
    # 打开pdf文件
    with pdfplumber.open(pdf_file) as pdf:
        # 初始化一个空的DataFrame用于存储所有页的数据
        df_all = pd.DataFrame()

        # 遍历每一页
        for page in pdf.pages:
            # 提取表格数据
            tables = page.extract_tables()
            for table in tables:
                # 将表格数据转化为DataFrame
                df = pd.DataFrame(table[1:], columns=table[0])
                df_all = pd.concat([df_all, df])

        # 保存为csv文件
        df_all.to_csv(pdf_file.replace('.pdf', '.csv'), index=False)

# 使用函数
convert_pdf_to_csv("D:\大二下\企业实习实训\workspace\\0715\documents\W020230419336779992203.pdf")
