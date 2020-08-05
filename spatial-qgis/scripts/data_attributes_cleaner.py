from qgis.core import QgsProject

layer = QgsProject.instance().mapLayersByName("PAR_BUILDING_OUTLINE")[0]

iface.setActiveLayer(layer)

layer_provider = layer.dataProvider()

# clean MR_WEIGHTS
weightFieldIndex = layer_provider.fieldNameIndex('MR_WEIGHTS')

if weightFieldIndex != -1:
    layer_provider.deleteAttributes([weightFieldIndex])
    layer.updateFields()
    print("MR_WEIGHTS removed")