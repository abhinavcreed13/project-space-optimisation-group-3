import pandas as pd

base_url = '/Users/abhinavsharma13/Google Drive/Mission Data Science [2019-2020]/Semester 4/MAST90107/project-space-optimisation-group-3/project-data/'
uom_space_url = base_url+'uom-space.xlsx'
rm_category_type_url = base_url+'rm-category-type-cleaned.xlsx'
em_location_url = base_url+'em-location.xlsx'
av_equipment_url = base_url+'av-equipment.xlsx'
timetable_2020_url = base_url+'2020-timetable-v2.xlsx'
floor_name_url = base_url+'fl-name-cleaned.xlsx'
meeting_room_usage_url = base_url+'meeting-room-usage.xlsx'

_processor = DataProcessor(uom_space_url,rm_category_type_url,em_location_url,av_equipment_url,
                           timetable_2020_url,floor_name_url,meeting_room_usage_url)
_processor.load_data()

# get datasets - after cleaning, mutation and merging
space_data, employee_data, av_equipment_data, timetable_data, mr_usage_data = _processor.get_all_datasets()
    
_extractor = DataExtractor()
possible_meeting_rooms_data = _extractor.get_meeting_rooms_data(_processor.rm_category_type_df, space_data)
possible_toilets_data = _extractor.get_toilets_data(_processor.rm_category_type_df, space_data)

