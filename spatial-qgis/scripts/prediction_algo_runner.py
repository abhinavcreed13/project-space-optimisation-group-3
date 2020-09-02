# -- Run: data_enhancer.py before this ---
# -- Run: prediction_algorithm.py before this ---

from qgis.core import QgsProject

campus_code = "PAR"
layer_name = "PAR_BUILDING_OUTLINE_WITH_DATA"
search_key = "BUILD_NO"

layer = QgsProject.instance().mapLayersByName(layer_name)[0]

stats = DataStats(layer)
print(stats.total_equipments)
factors = {
    "WITH_EQUIPMENTS": True
}
# alan gilbert building trial run
# 400m radius
# objective - meeting rooms
# penalty - 0.05
top_k_nodes = find_building_algorithm_2(
                        layer = layer, 
                        search_key = search_key,
                        current_building = 104, 
                        radius = 200, 
                        objective = 0,
                        k=3,
                        factors = factors,
                        stats = stats)
                        #penalty = 0.05)
        
# select top 3 buildings
iface.mapCanvas().setSelectionColor(QColor("green"))
selected_fids = []
for node in top_k_nodes:
    print(node[2]['BUILD_NO'], node[2]['NAME'], node[0], node[1])
    selected_fids.append(node[2].id())
    
layer.select(selected_fids)