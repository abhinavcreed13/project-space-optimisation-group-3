class LayerManager():

    def __init__(self, layer, feedback):
        self.layer = layer
        self.feedback = feedback
        self.features = layer.getFeatures()
        self.layer_provider = layer.dataProvider()
        self.attributes = {
            'MR_CNT': QVariant.Int,
            'MR_CAP': QVariant.Int,
            'TR_CNT': QVariant.Int,
            'TR_CAP': QVariant.Int,
            'EMP_CNT': QVariant.Int,
            'EQP_CNT': QVariant.Int,
            'STU_CNT': QVariant.Int,
            'MR_WEIGHTS': QVariant.Double,
            'TR_WEIGHTS': QVariant.Double      
        }
        self.grouped_mr_data = None
        self.grouped_to_data = None
        self.grouped_av_data = None
        self.grouped_emp_data = None
        self.grouped_stu_data = None
        self.data_attributes = {}
        
    def add_attributes(self):
        self.feedback.pushInfo("Cleaning attributes")
        self.clean_attributes()
        self.feedback.pushInfo("Adding attributes")
        attributes_to_add = []
        for attribute, attr_type in self.attributes.items():
            attributes_to_add.append(QgsField(attribute, attr_type))
        self.layer_provider.addAttributes(attributes_to_add)
        self.layer.updateFields()

    def clean_attributes(self):
        attributes_to_delete = []
        for attribute in self.attributes.keys():
            field_index = self.layer.fields().indexFromName(attribute)
            if field_index != -1:
                attributes_to_delete.append(field_index)
        if len(attributes_to_delete) > 0:
            # clean attributes
            self.layer_provider.deleteAttributes(attributes_to_delete)
            self.layer.updateFields()

    def update_layer(self, search_key, sink, total, update_current_layer = "false"):
        features = self.features
        for current, feature in enumerate(features):
            if self.feedback.isCanceled():
                break
            id = feature.id()
            
            # add/update all data attributes
            attr_vals = {}
            for attribute, data in self.data_attributes.items():
                attribute_index = self.layer_provider.fieldNameIndex(attribute)
                row = data[data['Building Code']==feature[search_key]]
                if len(row) > 0:
                    if self.attributes[attribute] == QVariant.Int:
                        feature[attribute] = int(row.iloc[0][attribute])
                    else:
                        feature[attribute] = row.iloc[0][attribute]
                else:
                    feature[attribute] = QVariant()
                # update value
                attr_vals[attribute_index] = feature[attribute]
                
            #self.feedback.pushInfo(attr_vals)
            self.layer_provider.changeAttributeValues({id: attr_vals})

            # add calc attributes
            mr_supply = feature['MR_CAP']
            mr_demand = feature['EMP_CNT']
            tr_supply = feature['TR_CAP']
            tr_demand = feature['STU_CNT']
            mr_attr_index = self.layer_provider.fieldNameIndex("MR_WEIGHTS")
            tr_attr_index = self.layer_provider.fieldNameIndex("TR_WEIGHTS")
            attr_vals = {}
            if mr_supply and mr_demand:
                attr_vals[mr_attr_index] = float(mr_supply/mr_demand)
            else:
                attr_vals[mr_attr_index] = QVariant()
            if tr_supply and tr_demand:
                attr_vals[tr_attr_index] = float(tr_supply/tr_demand)
            else:
                attr_vals[tr_attr_index] = QVariant()
            #self.feedback.pushInfo(attr_vals)
            self.layer_provider.changeAttributeValues({id:attr_vals})
            
            #if(update_current_layer == "false"):
                #sink.addFeature(feature, QgsFeatureSink.FastInsert)
            self.feedback.setProgress(int(current * total))
            
    def clean_base_layer(self):
        attribute_indexes = []
        for attribute in self.attributes.keys():
            idx = self.layer_provider.fieldNameIndex(attribute)
            if idx != -1:
                attribute_indexes.append(idx)
        if len(attribute_indexes) > 0:
            self.layer_provider.deleteAttributes(attribute_indexes)
            self.layer.updateFields()
            self.layer.commitChanges()   

    def create_grouped_data(self, meeting_rooms_data, 
                                    toilets_data,
                                    employees_data,
                                    mr_equipment_data,
                                    timetable_data):
        self._create_grouped_mr_data(meeting_rooms_data)
        self._create_grouped_to_data(toilets_data)
        self._create_grouped_av_data(mr_equipment_data)
        self._create_grouped_emp_data(employees_data)
        self._create_grouped_stu_data(timetable_data)

    def _create_grouped_mr_data(self, data):
        cols = ['Campus Code','Building Code','Building Name']
        aggs = {'Room Code':pd.Series.nunique,'Room Capacity':sum}
        names = {"Room Code": "MR_CNT", "Room Capacity": "MR_CAP"}
        self.grouped_mr_data = self.get_grouped_data(data, cols, aggs)
        self.grouped_mr_data = self.rename_columns(self.grouped_mr_data, names)
        self.data_attributes['MR_CNT'] = self.grouped_mr_data
        self.data_attributes['MR_CAP'] = self.grouped_mr_data

    def _create_grouped_to_data(self, data):
        cols = ['Campus Code','Building Code','Building Name']
        aggs = {'Room Code':pd.Series.nunique,'Room Capacity':sum}
        names = {"Room Code": "TR_CNT", "Room Capacity": "TR_CAP"}
        self.grouped_to_data = self.get_grouped_data(data, cols, aggs)
        self.grouped_to_data = self.rename_columns(self.grouped_to_data, names)
        self.data_attributes['TR_CNT'] = self.grouped_to_data
        self.data_attributes['TR_CAP'] = self.grouped_to_data
        
    def _create_grouped_emp_data(self, data):
        cols = ['Campus Code','Building Code','Building Name']
        aggs = {'Employee Sequential ID':pd.Series.nunique}
        names = {'Employee Sequential ID':'EMP_CNT'}
        self.grouped_emp_data = self.get_grouped_data(data, cols, aggs)
        self.grouped_emp_data = self.rename_columns(self.grouped_emp_data, names)
        self.data_attributes['EMP_CNT'] = self.grouped_emp_data
        
    def _create_grouped_av_data(self, data):
        cols = ['Campus Code','Building Code','Building Name']
        aggs = {'Equipment Code': pd.Series.nunique}
        names = {'Equipment Code': 'EQP_CNT'}
        self.grouped_av_data = self.get_grouped_data(data, cols, aggs)
        self.grouped_av_data = self.rename_columns(self.grouped_av_data, names)
        self.data_attributes['EQP_CNT'] = self.grouped_av_data
        
    def _create_grouped_stu_data(self, data):
        cols = ['Campus Code','Building Code','Building Name']
        aggs = {'Planned Size':sum}
        names = {'Planned Size':'STU_CNT'}
        self.grouped_stu_data = self.get_grouped_data(data, cols, aggs)
        self.grouped_stu_data = self.rename_columns(self.grouped_stu_data, names)
        self.data_attributes['STU_CNT'] = self.grouped_stu_data
        
    def get_grouped_data(self, data, cols, aggs):
        grouped_data = data.groupby(by=cols, as_index=False).agg(aggs)
        return grouped_data

    def rename_columns(self, data, cols):
        return data.rename(columns=cols)
        
class DataExtractor():
    
    def __init__(self, feedback, base_url):
        uom_space_url = base_url+'uom-space.xlsx'
        rm_category_type_url = base_url+'rm-category-type-cleaned.xlsx'
        em_location_url = base_url+'em-location.xlsx'
        av_equipment_url = base_url+'av-equipment.xlsx'
        timetable_2020_url = base_url+'2020-timetable-v2.xlsx'
        floor_name_url = base_url+'fl-name-cleaned.xlsx'
        meeting_room_usage_url = base_url+'meeting-room-usage.xlsx'
        self.feedback = feedback
        _processor = DataProcessor(uom_space_url,rm_category_type_url,em_location_url,av_equipment_url,
                           timetable_2020_url,floor_name_url,meeting_room_usage_url)
        _processor.load_data()
        self.space_data, self.employee_data, self.av_equipment_data, self.timetable_data, self.mr_usage_data = _processor.get_all_datasets()
        self.rm_category_type_df = _processor.rm_category_type_df
        self.feedback.pushInfo("--- DataExtractor Initialized Successfully ---")

    def get_meeting_rooms_data(self, campus_code = None):
        rm_category_type_df = self.rm_category_type_df
        space_data = self.space_data
        possible_rooms = rm_category_type_df[rm_category_type_df['Room Type'].str.contains("601|629")]
        meeting_room_types = possible_rooms['Room Type'].tolist()

        possible_meeting_rooms_df = space_data[space_data['Room Type'].isin(meeting_room_types)]
        if campus_code:
            return possible_meeting_rooms_df[possible_meeting_rooms_df['Campus Code'] == campus_code]
        return possible_meeting_rooms_df

    def get_toilets_data(self, campus_code = None):
        rm_category_type_df = self.rm_category_type_df
        space_data = self.space_data
        possible_rooms = rm_category_type_df[rm_category_type_df['Room Type Definition'].str.contains("toilet|washroom")]
        toilet_room_types = possible_rooms['Room Type'].tolist()
        possible_toilets_df = space_data[space_data['Room Type'].isin(toilet_room_types)]
        if campus_code:
            return possible_toilets_df[possible_toilets_df['Campus Code'] == campus_code]
        return possible_toilets_df

    def get_employees_data(self, campus_code = None):
        employee_data = self.employee_data
        if campus_code:
            return employee_data[employee_data['Campus Code']==campus_code]
        return employee_data

    def get_meeting_rooms_equipment_data(self, campus_code = None):
        av_equipment_data = self.av_equipment_data
        av_equipment_data = av_equipment_data[av_equipment_data['Room Type_x'].str.contains('601|629')]
        if campus_code:
            return av_equipment_data[av_equipment_data['Campus Code']==campus_code]
        return av_equipment_data

    def get_timetable_data(self, campus_code = None):
        timetable_data = self.timetable_data
        if campus_code:
            return timetable_data[timetable_data['Campus Code'] == campus_code]
        return timetable_data