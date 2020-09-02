from qgis.core import QgsProject
import pandas as pd

campus_code = "PAR"
layer_name = "PAR_BUILDING_OUTLINE"
search_key = "BUILD_NO"
objective = 0
layer = QgsProject.instance().mapLayersByName(layer_name)[0]

features = layer.getFeatures()
layer_provider = layer.dataProvider()
def get_reward(node, objective, factors):
    if objective == 0:
        targetRewardKey = "MR_WEIGHTS"
    elif objective == 1:
        targetRewardKey = "TR_WEIGHTS"
    reward = node[targetRewardKey]
    if node[targetRewardKey] == None:
        reward = 0
    return reward
            
def get_cost(node1, node2):
    return node2.geometry().distance(node1.geometry())
        
def get_building_code(node2):
    return (str(node2['BUILD_NO']).strip())
def get_building_name(node2):
    return (str(node2['NAME']).strip())

for i in features:
    starting_node = str(i[search_key])
    for feature in layer.getFeatures():
        if str(feature[search_key]) == starting_node:
            print(feature["NAME"])
            startingFeature = feature
            #x = targetGeometry.asMultiPolygon()
            #print("MultiPolygon: ", x, "Area: ", targetGeometry.area())
            break
    graph = []
    for feature in layer.getFeatures():
        if feature.id() != startingFeature.id():
            node = (startingFeature, feature)
            #print(node[1]['TR_WEIGHTS'])
            graph.append(node)
    df = pd.DataFrame()
    code1 = []
    b_name = []
    cost = []
    reward = []
    for node in graph:
        v_s, v_i = node
        code1.append(get_building_code(v_i))
        b_name.append(get_building_name(v_i))
        cost.append(get_cost(v_s, v_i))
        reward.append(get_reward(v_i, objective, {}))

    df['BUILD_NO']=code1
    df['NAME'] = b_name
    df['COST']= cost
    df['REWARD'] = reward
    file_name = starting_node+".csv"
    df.to_csv (r'C:\Users\deshp\Google Drive\project-space-optimisation-group-3\project-data\mapped_data'+ '\\' +str(file_name), index = False, header=True)