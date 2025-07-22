import re
from pyvis.network import Network
from pyvis.options import Options


# 读取 output/output_all.txt 文件内容
with open('output/output_all.txt', 'r', encoding='utf-8') as f:
    output_stream = f.read()

# 提取实体
entity = re.findall(r"^\(实体;.*\)$", output_stream, flags=re.M)
def to_triplets(str_list: list):
    result = []
    for i in str_list:
        things = i.split(";")
        # 兼容性处理，防止分割不够
        if len(things) >= 4:
            result.append((things[1].strip(), things[2].strip(), things[3].strip().replace(")", "")))
    return result
entity_triplets = to_triplets(entity)

# 提取实体属性
entity_property = re.findall(r"^\(实体属性;.*\)$", output_stream, flags=re.M)
entity_propert_triplets = to_triplets(entity_property)

# 提取实体关系
entity_ref = re.findall(r"^\(实体关系;.*\)$", output_stream, flags=re.M)
entity_ref_triplets = to_triplets(entity_ref)

# 后续函数可直接使用 entity_triplets、entity_propert_triplets、entity_ref_triplets

#定义绘图函数
from pyvis.network import Network
from pyvis.options import Options


def display_graph(options):
    g = Network(height="600px", width="1000px", directed=True)
    g.options = Options(options)
    nodes_id = {}
    for triplet in entity_ref_triplets:
        sub = triplet[0]
        obj = triplet[2]
        if sub not in nodes_id:
            nodes_id[sub] = len(nodes_id)
        if obj not in nodes_id:
            nodes_id[obj] = len(nodes_id)
    nodes_exist = []
    for triplet in entity_ref_triplets:
        sub = triplet[0]  # name, entity_description
        rel = triplet[1]  # label, relationship_description
        obj = triplet[2]  # name, entity_description

        if sub not in nodes_exist:
            g.add_node(nodes_id[sub], label=sub)
            nodes_exist.append(sub)
        if obj not in nodes_exist:
            g.add_node(nodes_id[obj], label=obj)
            nodes_exist.append(obj)

        title = "[{}] -[{}]-> [{}]".format(sub, rel, obj)
        g.add_edge(nodes_id[sub], nodes_id[obj], title=title)
    g.write_html("ex.html")

# 用法示例（在 streamlit 脚本中）：
# from data_extraction.draw import display_graph_pyvis
# import streamlit as st
# html_str = display_graph_pyvis(options=0, file_path='output/output_all.txt')
# st.components.v1.html(html_str, height=600, scrolling=True)
# st.components.v1.html(html_str, height=600, scrolling=True)
