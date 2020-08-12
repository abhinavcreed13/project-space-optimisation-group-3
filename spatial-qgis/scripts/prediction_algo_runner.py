# -- Run: data_enhancer.py before this ---
# -- Run: prediction_algorithm.py before this ---

from qgis.core import QgsProject

campus_code = "PAR"
#layer_name = "PAR_BUILDING_OUTLINE"
layer_name = "HEATMAP_PAR_MR_LAYER"
search_key = "BUILD_NO"

layer = QgsProject.instance().mapLayersByName(layer_name)[0]

# alan gilbert building trial run
# 400m radius
# objective - meeting rooms
# penalty - 0.05
top_3_buildings = find_building_algorithm(
                        layer = layer, 
                        search_key = search_key,
                        current_building = 104, 
                        radius = 200, 
                        objective = 0, 
                        penalty = 0.05)
        
# select top 3 buildings
iface.mapCanvas().setSelectionColor(QColor("green"))
selected_fids = []
for building in top_3_buildings:
    print(building)
    selected_fids.append(building['feature_obj'].id())
    
layer.select(selected_fids)