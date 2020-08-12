class DataCleaner():

    def clean_uom_space(self,uom_space_df):
        uom_space_df['Campus Code']=uom_space_df['Campus Code'].astype(str).str.strip()
        uom_space_df['Building Code']=uom_space_df['Building Code'].astype(str).str.strip()
        uom_space_df['Building Name']=uom_space_df['Building Name'].astype(str).str.strip()
        uom_space_df['Room Type']=uom_space_df['Room Type'].astype(str).str.strip()
        uom_space_df['Room Category']=uom_space_df['Room Category'].astype(str).str.strip()
        uom_space_df['Floor Code']=uom_space_df['Floor Code'].astype(str).str.strip()
        uom_space_df['Room Code']=uom_space_df['Room Code'].astype(str).str.strip()
        return uom_space_df

    def clean_rm_category_type(self,rm_category_type_df):
        rm_category_type_df['Room Type']=rm_category_type_df['Room Type'].astype(str).str.strip()
        rm_category_type_df['Room Category']=rm_category_type_df['Room Category'].astype(str).str.strip()
        rm_category_type_df['Room Type Abbreviation']=rm_category_type_df['Room Type Abbreviation'].str.lower().str.strip()
        rm_category_type_df['Description']=rm_category_type_df['Description'].str.lower().str.strip()
        rm_category_type_df['Room Type Definition']=rm_category_type_df['Room Type Definition'].str.lower().str.strip()
        return rm_category_type_df

    def clean_floor_data(self,floor_df):
        floor_df['Building Code'] = floor_df['Building Code'].astype(str).str.strip()
        floor_df['Floor Code'] = floor_df['Floor Code'].astype(str).str.strip()
        floor_df['Floor Name'] = floor_df['Floor Name'].astype(str).str.strip()
        return floor_df

    def clean_em_location(self,em_location_df):
        em_location_df['Floor Code'] = em_location_df['Floor Code'].astype(int)
        em_location_df['Floor Code'] = em_location_df['Floor Code'].astype(str).str.strip()
        return em_location_df

    def clean_av_equipment(self,av_equipment_df):
        av_equipment_df['Room Type'] = av_equipment_df['Room Type'].astype(str).str.strip()
        av_equipment_df['Room Code'] = av_equipment_df['Room Code'].astype(str).str.strip()
        av_equipment_df['Building Code'] = av_equipment_df['Building Code'].astype(str).str.strip()
        av_equipment_df['Campus Code'] = av_equipment_df['Campus Code'].astype(str).str.strip()
        av_equipment_df['Equip. Status'] = av_equipment_df['Equip. Status'].astype(str).str.strip()
        av_equipment_df['Floor Code'] = av_equipment_df['Floor Code'].astype(int).astype(str).str.strip()
        return av_equipment_df

    def clean_timetable_data(self,timetable_df):
        # remove all NaN rows
        timetable_df = timetable_df.dropna(how='all')

        # drop duplicate records
        timetable_df = timetable_df.drop_duplicates()

        # dropping classes whose location is not planned
        timetable_df = timetable_df[timetable_df['Host Key of Allocated Locations'].notna()]

        # dropping classes whose location is online option
        timetable_df = timetable_df[timetable_df['Host Key of Allocated Locations']!='Online option.']

        # dropping classes with off-site location
        timetable_df = timetable_df[timetable_df['Name of Zone of Allocated Locations']!='Off-Site']
        return timetable_df

    def clean_meeting_room_usage(self,meeting_room_usage_df):
        meeting_room_usage_df = meeting_room_usage_df[meeting_room_usage_df['Campus Code'].notna()]
        meeting_room_usage_df = meeting_room_usage_df[meeting_room_usage_df['Building Code'].notna()]
        meeting_room_usage_df = meeting_room_usage_df[meeting_room_usage_df['Floor Code'].notna()]
        meeting_room_usage_df = meeting_room_usage_df[meeting_room_usage_df['Room Code'].notna()]

        meeting_room_usage_df['Campus Code'] = meeting_room_usage_df['Campus Code'].astype(str).str.strip()
        meeting_room_usage_df['Building Code'] = meeting_room_usage_df['Building Code'].astype(str).str.strip()
        meeting_room_usage_df['Building Name'] = meeting_room_usage_df['Building Name'].astype(str).str.strip()
        meeting_room_usage_df['Floor Code'] = meeting_room_usage_df['Floor Code'].astype(int).astype(str).str.strip()
        meeting_room_usage_df['Room Code'] = meeting_room_usage_df['Room Code'].astype(str).str.strip()
        return meeting_room_usage_df


class DataMutator():

    def mutate_em_location(self,em_location_df):
        # mutate room codes
        for idx,row in em_location_df.iterrows():
            if "." in row['Room Code']:
                code = row['Room Code'].split(".")[0]
                em_location_df.at[idx,'Room Code'] = code
        return em_location_df

    def mutate_timetable_data(self,timetable_df):
        building_codes = []
        room_codes = []
        campus_codes = []
        class_duration_minutes = []
        for idx,row in timetable_df.iterrows():
            s = row['Host Key of Allocated Locations'].split('-')
            building_codes.append(s[0])
            room_codes.append(s[1])
            c = row['Name of Allocated Locations'].split('-')[0]
            if c == 'zzzPAR':
                c = 'PAR'
            campus_codes.append(c)
            d = row['Duration as duration']
            class_duration_minutes.append(d.hour * 60 + d.minute)
        timetable_df['Building Code'] = building_codes
        timetable_df['Room Code'] = room_codes
        timetable_df['Campus Code'] = campus_codes
        timetable_df['Class Duration In Minutes'] = class_duration_minutes
        return timetable_df



class DataMerger():

    def get_merged_space_data(self,uom_space_df,rm_category_type_df, floor_df):
        uom_space_df_enhanced = pd.merge(uom_space_df,floor_df,on=['Building Code','Floor Code'])
        print("# Merge - uom_space + floor_data")
        print((uom_space_df.shape, uom_space_df_enhanced.shape))
        print('Unable to merge records:',uom_space_df.shape[0]-uom_space_df_enhanced.shape[0])
        merged_space_data_df = pd.merge(uom_space_df_enhanced,rm_category_type_df,on=['Room Category','Room Type'])
        print("# Merge - enhanced_uom_space + rm_category_type")
        print((uom_space_df_enhanced.shape, merged_space_data_df.shape))
        print('Unable to merge records:',uom_space_df_enhanced.shape[0]-merged_space_data_df.shape[0])
        return merged_space_data_df

    def get_merged_em_location_data(self,em_location_df,merged_space_data_df):
        print("# merge - space_data + em_location")
        merged_em_location_df = pd.merge(em_location_df,merged_space_data_df,on=['Building Code','Floor Code','Room Code'])
        print((em_location_df.shape, merged_em_location_df.shape))
        print('Unable to merge records:',em_location_df.shape[0]-merged_em_location_df.shape[0])
        return merged_em_location_df

    def get_merged_av_equipment_data(self,av_equipment_df,merged_space_data_df):
        print("# merge - space_data + av_equipment")
        merged_av_equipment_df = pd.merge(av_equipment_df,merged_space_data_df,on=['Campus Code','Building Code','Floor Code','Room Code'])
        print((av_equipment_df.shape, merged_av_equipment_df.shape))
        print('Unable to merge records:',av_equipment_df.shape[0]-merged_av_equipment_df.shape[0])
        return merged_av_equipment_df

    def get_merged_timetable_data(self,timetable_df,merged_space_data_df):
        print("# merge - space_data + timetable_data")
        merged_timetable_df = pd.merge(timetable_df,merged_space_data_df,on=['Campus Code','Building Code','Room Code'])
        print((timetable_df.shape, merged_timetable_df.shape))
        print('Unable to merge records:',timetable_df.shape[0]-merged_timetable_df.shape[0])
        return merged_timetable_df

    def get_merged_meeting_room_usage_data(self,meeting_room_usage_df,merged_space_data_df):
        print("# merge - space_data + meeting_room_usage")
        merged_meeting_room_usage_df = pd.merge(meeting_room_usage_df,merged_space_data_df,on=['Campus Code','Building Code','Floor Code','Room Code'])
        print((meeting_room_usage_df.shape, merged_meeting_room_usage_df.shape))
        print('Unable to merge records:',meeting_room_usage_df.shape[0]-merged_meeting_room_usage_df.shape[0])
        return merged_meeting_room_usage_df

class DataProcessor():
    def __init__(self,uom_space_url,rm_category_type_url,
                 em_location_url,av_equipment_url,
                 timetable_2020_url,floor_name_url,
                 meeting_room_usage_url):
        self.uom_space_url = uom_space_url
        self.rm_category_type_url = rm_category_type_url
        self.em_location_url = em_location_url
        self.av_equipment_url = av_equipment_url
        self.timetable_2020_url = timetable_2020_url
        self.floor_name_url = floor_name_url
        self.meeting_room_usage_url = meeting_room_usage_url

    def load_data(self):
        self.uom_space_df = pd.read_excel(uom_space_url)
        self.rm_category_type_df = pd.read_excel(rm_category_type_url)
        self.em_location_df = pd.read_excel(em_location_url)
        self.av_equipment_df = pd.read_excel(av_equipment_url)
        self.timetable_df = pd.read_excel(timetable_2020_url, delim_whitespace=True)
        self.floor_df = pd.read_excel(floor_name_url)
        self.meeting_room_usage_df = pd.read_excel(meeting_room_usage_url)
        print('Data loaded successfully!')
        # data shapes
        print("UOM space shape:"+str(self.uom_space_df.shape))
        print("RM category:"+str(self.rm_category_type_df.shape))
        print("EM location:"+str(self.em_location_df.shape))
        print("AV equipment:"+str(self.av_equipment_df.shape))
        print("2020 timetable:"+str(self.timetable_df.shape))
        print("Floor data shape:"+str(self.floor_df.shape))
        print("Meeting room usage shape:"+str(self.meeting_room_usage_df.shape))

    def get_all_datasets(self):

        print("# clean data")
        _cleaner = DataCleaner()
        self.uom_space_df = _cleaner.clean_uom_space(self.uom_space_df)
        self.rm_category_type_df = _cleaner.clean_rm_category_type(self.rm_category_type_df)
        self.floor_df = _cleaner.clean_floor_data(self.floor_df)
        self.em_location_df = _cleaner.clean_em_location(self.em_location_df)
        self.av_equipment_df = _cleaner.clean_av_equipment(self.av_equipment_df)
        self.timetable_df = _cleaner.clean_timetable_data(self.timetable_df)
        self.meeting_room_usage_df = _cleaner.clean_meeting_room_usage(self.meeting_room_usage_df)

        print("# mutate data")
        _mutator = DataMutator()
        self.em_location_df = _mutator.mutate_em_location(self.em_location_df)
        self.timetable_df = _mutator.mutate_timetable_data(self.timetable_df)

        print("# merge data")
        _merger = DataMerger()
        self.merged_space_data = _merger.get_merged_space_data(self.uom_space_df, self.rm_category_type_df, self.floor_df)
        self.merged_em_location_data = _merger.get_merged_em_location_data(self.em_location_df,self.merged_space_data)
        self.merged_av_equipment_data = _merger.get_merged_av_equipment_data(self.av_equipment_df,self.merged_space_data)
        self.merged_timetable_data = _merger.get_merged_timetable_data(self.timetable_df,self.merged_space_data)
        self.merged_meeting_room_usage_data = _merger.get_merged_meeting_room_usage_data(self.meeting_room_usage_df,self.merged_space_data)

        return self.merged_space_data, self.merged_em_location_data, self.merged_av_equipment_data, self.merged_timetable_data, self.merged_meeting_room_usage_data

class DataExtractor():

    def get_meeting_rooms_data(self,rm_category_type_df,space_data):
        # possible meeting rooms
        possible_rooms = rm_category_type_df[rm_category_type_df['Room Type'].str.contains("601|629")]
        meeting_room_types = possible_rooms['Room Type'].tolist()

        # supply of meeting rooms
        possible_meeting_rooms_df = space_data[space_data['Room Type'].isin(meeting_room_types)]
        return possible_meeting_rooms_df

    def get_toilets_data(self,rm_category_type_df,space_data):
        possible_rooms = rm_category_type_df[rm_category_type_df['Room Type Definition'].str.contains("toilet|washroom")]
        toilet_room_types = possible_rooms['Room Type'].tolist()

        possible_toilets_df = space_data[space_data['Room Type'].isin(toilet_room_types)]
        return possible_toilets_df