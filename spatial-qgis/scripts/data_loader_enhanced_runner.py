from qgis.core import QgsProject
import pandas as pd

layer = QgsProject.instance().mapLayersByName("PAR_BUILDING_OUTLINE")[0]

class Feedback():
    
    def pushInfo(self, message):
        print(message)
        
    def setProgress(self, val):
        pass
        
    def isCanceled(self):
        return False
        
feedback = Feedback()

_manager = LayerManager(layer, feedback)
_manager.clean_attributes()

# add all attributes to the layer
#_manager.add_attributes()

base_url = "/Users/abhinavsharma13/Google Drive/Mission Data Science [2019-2020]/Semester 4/MAST90107/project-space-optimisation-group-3/project-data/"
campus_code = "PAR"

_extractor = DataExtractor(feedback, base_url)
meeting_rooms_data = _extractor.get_meeting_rooms_data(campus_code)
toilets_data = _extractor.get_toilets_data(campus_code)
employees_data = _extractor.get_employees_data(campus_code)
mr_equipment_data = _extractor.get_meeting_rooms_equipment_data(campus_code)
timetable_data = _extractor.get_timetable_data(campus_code)

_manager.create_grouped_data(meeting_rooms_data, 
                                    toilets_data,
                                    employees_data,
                                    mr_equipment_data,
                                    timetable_data)

total = 100.0 / layer.featureCount() if layer.featureCount() else 0
update = "false"
search_key = "BUILD_NO"
_manager.update_layer(search_key, layer, total, update)

if (update == "true"):
    feedback.pushInfo("-----")
    feedback.pushInfo("STOPPING SCRIPT TO AVOID CREATING NEW LAYER")
    feedback.pushInfo("-----")
    raise Exception("--- IGNORE THIS ---")   
#else:
    #_manager.clean_base_layer()
                        
                            


