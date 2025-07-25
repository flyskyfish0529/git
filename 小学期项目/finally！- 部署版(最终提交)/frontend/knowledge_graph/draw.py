import re
from pyvis.network import Network
from pyvis.options import Options

def to_triplets(str_list: list):
    """
    将字符串列表转换为四元组列表
    :param    str_list: 包含四元组字符串的列表，每个字符串格式为 "(实体; 属性; 值; 关系)"
    :return:    四元组列表，每个四元组为 (实体, 属性, 值, 关系)
    """
    result = []
    for i in str_list:
        things = i.split(";")
        # 兼容性处理，防止分割不够
        if len(things) >= 4:
            result.append((things[1].strip(), things[2].strip(), things[3].strip().replace(")", "")))
    return result

def extract_kg_triplets(file_path):
    """
    从文件中提取知识图谱的四元组
    :param file_path:   包含知识图谱四元组的文件路径
    :return:    三个列表，分别包含实体四元组、实体属性四元组和实体关系四元组
    """
    with open(file_path, "r", encoding="utf-8") as f:
        output_stream = f.read()
    entity = re.findall(r"^\(实体;.*\)$", output_stream, flags=re.M)
    entity_triplets = to_triplets(entity)
    entity_property = re.findall(r"^\(实体属性;.*\)$", output_stream, flags=re.M)
    entity_propert_triplets = to_triplets(entity_property)
    entity_ref = re.findall(r"^\(实体关系;.*\)$", output_stream, flags=re.M)
    entity_ref_triplets = to_triplets(entity_ref)
    return entity_triplets, entity_propert_triplets, entity_ref_triplets

def display_graph_pyvis(options=0, triplets = []):
    """
    使用 Pyvis 库绘制知识图谱
    :param options:     绘图选项，0 为默认选项，1 为简化选项
    :param triplets:    四元组列表，每个四元组格式为 (实体, 属性, 值, 关系)
    :return:    返回生成的 HTML 字符串
    """
    # 对四元组去重
    unique_triplets = list({tuple(t) for t in triplets})
    entity_ref_triplets = unique_triplets

    g = Network(height="600px", width="1000px", directed=True)
    g.options = Options(options)
    nodes_id = {}
    nodes_exist = []
    # 先收集所有节点，分配id
    for triplet in entity_ref_triplets:
        if triplet[0] == "实体":
            sub = triplet[1]
            obj = triplet[3]
            if sub not in nodes_id:
                nodes_id[sub] = len(nodes_id)
            if obj not in nodes_id:
                nodes_id[obj] = len(nodes_id)
        elif triplet[0] == "实体关系":
            sub = triplet[1]
            obj = triplet[3]
            if sub not in nodes_id:
                nodes_id[sub] = len(nodes_id)
            if obj not in nodes_id:
                nodes_id[obj] = len(nodes_id)
    # 再添加节点和边
    for triplet in entity_ref_triplets:
        if triplet[0] == "实体关系":
            sub = triplet[1]
            rel = triplet[2]
            obj = triplet[3]
            if sub not in nodes_exist:
                g.add_node(nodes_id[sub], label=sub)
                nodes_exist.append(sub)
            if obj not in nodes_exist:
                g.add_node(nodes_id[obj], label=obj)
                nodes_exist.append(obj)
            title = "[{}] -[{}]-> [{}]".format(sub, rel, obj)
            g.add_edge(nodes_id[sub], nodes_id[obj], title=title)
    return g.generate_html()