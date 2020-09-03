from qgis.core import QgsProject

layers = QgsProject.instance().mapLayers().values()

for layer in layers:
    layer_provider = layer.dataProvider()

    # clean MR_WEIGHTS
    weightFieldIndex = layer_provider.fieldNameIndex('MR_WEIGHTS')
    
    # clean MR_WEIGHTS
    weightFieldIndex = layer_provider.fieldNameIndex('TR_WEIGHTS')

    if weightFieldIndex != -1:
        layer_provider.deleteAttributes([weightFieldIndex])
        layer.updateFields()
        print("MR_WEIGHTS removed")
        print("TR_WEIGHTS removed")