from qgis.core import QgsProject

layer = QgsProject.instance().mapLayersByName("PAR_BUILDING_OUTLINE")[0]

iface.setActiveLayer(layer)

selected_fid = []

for f in layer.getFeatures():
    if f.attribute('LOC_CODE') == 'PAR;104':
        
        #geom = f.geometry()
        #x = geom.asMultiPolygon()
        #print("MultiPolygon: ", x, "Area: ", geom.area())
        
        selected_fid.append(f.id())
        
layer.select(selected_fid)

        