# -- Run: data_loader.py before this ---

from qgis.core import QgsProject

campus_code = "PAR"
layer_name = "PAR_BUILDING_OUTLINE"
search_key = "BUILD_NO"

layer = QgsProject.instance().mapLayersByName(layer_name)[0]

iface.setActiveLayer(layer)

features = layer.getFeatures()
layer_provider = layer.dataProvider()

# recreate new weight field with every run
weightFieldIndex = layer_provider.fieldNameIndex('MR_WEIGHTS')

if weightFieldIndex != -1:
    layer_provider.deleteAttributes([weightFieldIndex])
    layer.updateFields()

layer_provider.addAttributes([QgsField("MR_WEIGHTS",  QVariant.Double)])
layer.updateFields()

# get index again
weightFieldIndex = layer_provider.fieldNameIndex('MR_WEIGHTS')

# filter data
filtered_meeting_rooms_data = possible_meeting_rooms_data[possible_meeting_rooms_data['Campus Code'] == campus_code]
filtered_employee_data = employee_data[employee_data['Campus Code']==campus_code]
print(len(filtered_meeting_rooms_data))
print(len(filtered_employee_data))

# merging data for getting supply
mr_data = filtered_meeting_rooms_data.groupby(by=['Campus Code','Building Code','Building Name'], as_index=False).agg({'Room Code':pd.Series.nunique,'Room Capacity':sum})
mr_data = mr_data.rename(columns={"Room Code": "MR_COUNT", "Room Capacity": "MR_CAP"})
# mr_data['LOC_CODE']=mr_data['Campus Code']+';'+mr_data['Building Code']

# merging data for getting demand
emp_data = filtered_employee_data.groupby(by=['Campus Code','Building Code','Building Name'], as_index=False).agg({'Employee Sequential ID':pd.Series.nunique})
emp_data = emp_data.rename(columns={'Employee Sequential ID':'EMP_COUNT'})
# emp_data['LOC_CODE']=emp_data['Campus Code']+';'+emp_data['Building Code']

# supply
def get_meeting_room_capacity(data, val):
    row = data[data['Building Code']==val]
    if len(row) > 0:
        return row.iloc[0]['MR_COUNT']
    else:
        return None
    
# demand
def get_employee_count(data, val):
    row = data[data['Building Code']==val]
    if len(row) > 0:
        return row.iloc[0]['EMP_COUNT']
    else:
        return None
        
# start layer editing
layer.startEditing()

for feature in layer.getFeatures():
    # retrieve every feature with its geometry and attributes print("Feature ID: ", feature.id())
    # fetch geometry
    # show some information about the feature geometry
    #geom = feature.geometry()
    #x = geom.asMultiPolygon()
    #print("MultiPolygon: ", x, "Area: ", geom.area())
    id = feature.id()
    print(feature[search_key])
    #print(feature.id())
    supply = get_meeting_room_capacity(mr_data, feature[search_key])
    
    demand = get_employee_count(emp_data, feature[search_key])
    
    if supply and demand:
        weight = float(supply/demand)
        print('weight->'+str(weight))
    else:
        weight = NULL
        print('weight->'+str(weight))
    attr_value={weightFieldIndex:weight}
    layer_provider.changeAttributeValues({id:attr_value})

# save changes
layer.commitChanges()