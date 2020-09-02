# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from qgis.PyQt.QtCore import QCoreApplication,QVariant
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterField,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterString,
                       QgsField, 
                       QgsFields,
                       QgsProject,
                       QgsFeature,
                       QgsVectorLayer,
                       QgsProcessingParameterMapLayer)
from qgis import processing
import pandas as pd


class DataEnhancer(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    BASE_URL = "base_url"
    CAMPUS_CODE = "campus_code"
    SEARCH_KEY = "search_key"
    UPDATE = "update"

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return DataEnhancer()

    def name(self):
        return 'Data Loader'

    def displayName(self):
        return self.tr('Data Loader Script')

    def group(self):
        return self.tr('Scripts')

    def groupId(self):
        return 'Scripts'

    def shortHelpString(self):
        return self.tr("Loading data into QGIS environment")

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterMapLayer(
                self.INPUT,
                self.tr('Input layer'),
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.BASE_URL,
                'Enter Base URL'
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.CAMPUS_CODE,
                'Enter Campus Code'
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.SEARCH_KEY,
                'Enter Search Key'
            )

        )
         
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.UPDATE,
                'Update base layer and Do not create new layer'
            )

        )
            # 

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Output layer')
            )
        )


    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsLayer(
            parameters,
            self.INPUT,
            context
        )
        base_url = self.parameterAsString(
            parameters,
            self.BASE_URL,
            context
        )

        campus_code = self.parameterAsString(
            parameters,
            self.CAMPUS_CODE,
            context
        )

        search_key = self.parameterAsString(
            parameters,
            self.SEARCH_KEY,
            context
        )

        update = self.parameterAsString(
            parameters,
            self.UPDATE,
            context
        )

        base_url = base_url.strip()
        campus_code = campus_code.strip().lower()
        search_key = search_key.strip()

        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        #_manager = LayerManager(source, feedback)

        # add all attributes to the layer
        #_manager.add_attributes()
        
        # extract required data
        _extractor = DataExtractor(feedback, base_url)
        filtered_meeting_rooms_data = _extractor.get_meeting_rooms_data(campus_code)
        filtered_toilets_data = _extractor.get_toilets_data(campus_code)
        filtered_employee_data = _extractor.get_employees_data(campus_code)
        mr_equipment_data = _extractor.get_meeting_rooms_equipment_data(campus_code)
        timetable_data = _extractor.timetable_data
        timetable_data_toi = _extractor.get_timetable_data(campus_code)
        
        #layer = _manager.get_layer()
        layer = source

        features = layer.getFeatures()
        layer_provider = layer.dataProvider()

        weightFieldIndex = layer.fields().indexFromName('MR_WEIGHTS')
        if weightFieldIndex != -1:
            layer_provider.deleteAttributes([weightFieldIndex])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("MR_WEIGHTS",  QVariant.Double)])
        
        weightFieldIndex_toilets = layer.fields().indexFromName('TR_WEIGHTS')
        if weightFieldIndex_toilets != -1:
            layer_provider.deleteAttributes([weightFieldIndex_toilets])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("TR_WEIGHTS",  QVariant.Double)])
        layer.updateFields() 

        # idx = layer.fields().indexFromName('MR_CNT')
        # if idx != -1:
        #     layer_provider.deleteAttributes([idx])
        #     layer.updateFields()
        # layer_provider.addAttributes([QgsField("MR_CNT",  QVariant.Double)])
        # layer.updateFields()

        # idx = layer.fields().indexFromName('MR_CAP')
        # if idx != -1:
        #     layer_provider.deleteAttributes([idx])
        #     layer.updateFields()
        # layer_provider.addAttributes([QgsField("MR_CAP",  QVariant.Double)])
        # layer.updateFields()

        # idx = layer.fields().indexFromName('TR_CNT')
        # if idx != -1:
        #     layer_provider.deleteAttributes([idx])
        #     layer.updateFields()
        # layer_provider.addAttributes([QgsField("TR_CNT",  QVariant.Double)])
        # layer.updateFields()

        # idx = layer.fields().indexFromName('TR_CAP')
        # if idx != -1:
        #     layer_provider.deleteAttributes([idx])
        #     layer.updateFields()
        # layer_provider.addAttributes([QgsField("TR_CAP",  QVariant.Double)])
        # layer.updateFields()

        # idx = layer.fields().indexFromName('EMP_CNT')
        # if idx != -1:
        #     layer_provider.deleteAttributes([idx])
        #     layer.updateFields()
        # layer_provider.addAttributes([QgsField("EMP_CNT",  QVariant.Double)])
        # layer.updateFields()

        # idx = layer.fields().indexFromName('EQP_CNT')
        # if idx != -1:
        #     layer_provider.deleteAttributes([idx])
        #     layer.updateFields()
        # layer_provider.addAttributes([QgsField("EQP_CNT",  QVariant.Double)])
        # layer.updateFields()

        # idx = layer.fields().indexFromName('STU_CNT')
        # if idx != -1:
        #     layer_provider.deleteAttributes([idx])
        #     layer.updateFields()
        # layer_provider.addAttributes([QgsField("STU_CNT",  QVariant.Double)])
        # layer.updateFields()
        
        #idx1 = layer_provider.fieldNameIndex('MR_CNT')
        weightFieldIndex = layer_provider.fieldNameIndex('MR_WEIGHTS')
        weightFieldIndex_toilets = layer_provider.fieldNameIndex('TR_WEIGHTS')
        # idx1 = layer_provider.fieldNameIndex('MR_CNT')
        # idx2 = layer_provider.fieldNameIndex('MR_CAP')
        # idx3 = layer_provider.fieldNameIndex('TR_CNT')
        # idx4 = layer_provider.fieldNameIndex('TR_CAP')
        # idx5 = layer_provider.fieldNameIndex('EMP_CNT')
        # idx6 = layer_provider.fieldNameIndex('EQP_CNT')
        # idx7 = layer_provider.fieldNameIndex('STU_CNT')

        # uom_space_url = base_url+'uom-space.xlsx'
        # rm_category_type_url = base_url+'rm-category-type-cleaned.xlsx'
        # em_location_url = base_url+'em-location.xlsx'
        # av_equipment_url = base_url+'av-equipment.xlsx'
        # timetable_2020_url = base_url+'2020-timetable-v2.xlsx'
        # floor_name_url = base_url+'fl-name-cleaned.xlsx'
        # meeting_room_usage_url = base_url+'meeting-room-usage.xlsx'
        # _processor = DataProcessor(uom_space_url,rm_category_type_url,em_location_url,av_equipment_url,
        #                    timetable_2020_url,floor_name_url,meeting_room_usage_url,feedback)
        # _processor.load_data()
        # space_data, employee_data, av_equipment_data, timetable_data, mr_usage_data = _processor.get_all_datasets()
        # _extractor = DataExtractor(feedback)

        # possible_meeting_rooms_data = _extractor.get_meeting_rooms_data(_processor.rm_category_type_df, space_data)
        # possible_toilets_data = _extractor.get_toilets_data(_processor.rm_category_type_df, space_data)
        # timetable_data_toi = timetable_data[timetable_data['Campus Code'] == campus_code]
        # filtered_meeting_rooms_data = possible_meeting_rooms_data[possible_meeting_rooms_data['Campus Code'] == campus_code]
        # filtered_employee_data = employee_data[employee_data['Campus Code']==campus_code]
        # filtered_toilets_data = possible_toilets_data[possible_toilets_data['Campus Code'] == campus_code]
        # _manager.create_grouped_data(filtered_meeting_rooms_data, 
        #                             filtered_toilets_data,
        #                             filtered_employee_data,
        #                             mr_equipment_data,
        #                             timetable_data_toi)

        feedback.pushInfo(str(len(filtered_toilets_data)))
        feedback.pushInfo(str(len(filtered_meeting_rooms_data)))
        feedback.pushInfo(str(len(filtered_employee_data)))
        feedback.pushInfo(str(len(timetable_data_toi)))

        feedback.pushInfo('Merging data for getting supply')
        tr_data = filtered_toilets_data.groupby(by = ['Campus Code','Building Code','Building Name'],as_index = False).agg({'Room Code':pd.Series.nunique,'Room Capacity':sum})
        tr_data = tr_data.rename(columns = {"Room Code":"TR_COUNT", "Room Capacity": "TR_CAP"})
        mr_data = filtered_meeting_rooms_data.groupby(by=['Campus Code','Building Code','Building Name'], as_index=False).agg({'Room Code':pd.Series.nunique,'Room Capacity':sum})
        mr_data = mr_data.rename(columns={"Room Code": "MR_COUNT", "Room Capacity": "MR_CAP"})
        
        feedback.pushInfo('Merging data for getting demand')
        student_data = timetable_data.groupby(by=['Campus Code','Building Code','Building Name'], as_index=False).agg({'Planned Size':sum})
        student_data = student_data.rename(columns = {'Planned Size':'STU_COUNT'})
        feedback.pushInfo(str(len(student_data)))
        
        emp_data = filtered_employee_data.groupby(by=['Campus Code','Building Code','Building Name'], as_index=False).agg({'Employee Sequential ID':pd.Series.nunique})
        emp_data = emp_data.rename(columns={'Employee Sequential ID':'EMP_COUNT'})
        feedback.pushInfo(str(len(emp_data)))
        
        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            layer.fields(),
            layer.wkbType(),
            layer.sourceCrs()
        )
        feedback.pushInfo('CRS is {}'.format(layer.sourceCrs().authid()))
        
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))
        
        total = 100.0 / layer.featureCount() if layer.featureCount() else 0
        features = layer.getFeatures()
        _features = DataFeatures(feedback)

        for current, feature in enumerate(features):
            if feedback.isCanceled():
                break
            id = feature.id()
            supply = _features.get_meeting_room_capacity(mr_data, feature[search_key])
            demand = _features.get_employee_count(emp_data, feature[search_key])
            toilet_supply = _features.get_toilet_room_capacity(tr_data,feature[search_key])
            toilet_demand = _features.get_student_count(student_data,feature[search_key])
            if supply and demand:
                weight = float(supply/demand)
            else:
                weight = QVariant()
            if toilet_supply and toilet_demand:
                tr_weight = float(toilet_supply/toilet_demand)
            else:
                tr_weight = QVariant()          
            feature['TR_WEIGHTS'] = weight        
            feature['MR_WEIGHTS'] = tr_weight
            # feature['MR_CNT'] = QVariant()
            # feature['MR_CAP'] = QVariant()
            # feature['TR_CNT'] = QVariant()
            # feature['TR_CAP'] = QVariant()
            # feature['EMP_CNT'] = QVariant()
            # feature['EQP_CNT'] = QVariant()
            # feature['STU_CNT'] = QVariant()
            attr_value={
                weightFieldIndex: QVariant(),
                weightFieldIndex_toilets: QVariant()
                # idx1: QVariant(),
                # idx2: QVariant(),
                # idx3: QVariant(),
                # idx4: QVariant(),
                # idx5: QVariant(),
                # idx6: QVariant(),
                # idx7: QVariant()
            }
            #attr_value = _manager.update_feature(feature, attr_value)
            layer_provider.changeAttributeValues({id:attr_value})
            if(update == "false"):
                sink.addFeature(feature, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(current * total))

        if (update == "true"):
            feedback.pushInfo("-----")
            feedback.pushInfo("STOPPING SCRIPT TO AVOID CREATING NEW LAYER")
            feedback.pushInfo("-----")
            raise Exception("--- IGNORE THIS ---")   
        else:
            # layer_provider.deleteAttributes([idx1, idx2, idx3, idx4, idx5, idx6, idx7, weightFieldIndex_toilets,weightFieldIndex])
            layer_provider.deleteAttributes([weightFieldIndex_toilets,weightFieldIndex])
            layer.updateFields()
            layer.commitChanges()
        
        return {self.OUTPUT: dest_id}

class LayerManager():

    def __init__(self, layer, feedback):
        self.layer = layer
        self.feedback = feedback
        self.features = layer.getFeatures()
        self.layer_provider = layer.dataProvider()
        self.attributes = {
            'MR_CNT': QVariant.Double,
            'MR_CAP': QVariant.Double,
            'TR_CNT': QVariant.Double,
            'TR_CAP': QVariant.Double,
            'EMP_CNT': QVariant.Double,
            'EQP_CNT': QVariant.Double,
            'STU_CNT': QVariant.Double,
            'MR_WEIGHTS': QVariant.Double,
            'TR_WEIGHTS': QVariant.Double      
        }
        self.grouped_mr_data = None
        self.grouped_to_data = None
        self.grouped_av_data = None
        self.grouped_emp_data = None
        self.grouped_stu_data = None
        self.data_attributes = {}

    def get_layer(self):
        return self.layer
        
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

    def update_feature(self, feature, attr):
        for attribute, data in self.data_attributes.items():
            feature[attribute] = QVariant()
            attribute_index = self.layer_provider.fieldNameIndex(attribute)
            attr[attribute_index] = QVariant()
        return attr
            
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
                           timetable_2020_url,floor_name_url,meeting_room_usage_url, feedback)
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


class DataProcessor():
    def __init__(self,uom_space_url,rm_category_type_url,
                 em_location_url,av_equipment_url,
                 timetable_2020_url,floor_name_url,
                 meeting_room_usage_url,
                 feedback):
        self.uom_space_url = uom_space_url
        self.rm_category_type_url = rm_category_type_url
        self.em_location_url = em_location_url
        self.av_equipment_url = av_equipment_url
        self.timetable_2020_url = timetable_2020_url
        self.floor_name_url = floor_name_url
        self.meeting_room_usage_url = meeting_room_usage_url
        self.feedback = feedback

    def load_data(self):
       
        self.feedback.pushInfo("Data Loading Initialized")
        self.uom_space_df = pd.read_excel(self.uom_space_url)
        self.rm_category_type_df = pd.read_excel(self.rm_category_type_url)
        self.em_location_df = pd.read_excel(self.em_location_url)
        self.av_equipment_df = pd.read_excel(self.av_equipment_url)
        self.timetable_df = pd.read_excel(self.timetable_2020_url, delim_whitespace=True)
        self.floor_df = pd.read_excel(self.floor_name_url)
        self.meeting_room_usage_df = pd.read_excel(self.meeting_room_usage_url)
        
        self.feedback.pushInfo('Data loaded successfully!')
        self.feedback.pushInfo("UOM space shape:"+str(self.uom_space_df.shape))
        self.feedback.pushInfo("RM category:"+str(self.rm_category_type_df.shape))
        self.feedback.pushInfo("EM location:"+str(self.em_location_df.shape))
        self.feedback.pushInfo("AV equipment:"+str(self.av_equipment_df.shape))
        self.feedback.pushInfo("2020 timetable:"+str(self.timetable_df.shape))
        self.feedback.pushInfo("Floor data shape:"+str(self.floor_df.shape))
        self.feedback.pushInfo("Meeting room usage shape:"+str(self.meeting_room_usage_df.shape))
    

    def get_all_datasets(self):

        self.feedback.pushInfo("Data Cleaning Initialized")
        _cleaner = DataCleaner(self.feedback)
        self.uom_space_df = _cleaner.clean_uom_space(self.uom_space_df)
        self.rm_category_type_df = _cleaner.clean_rm_category_type(self.rm_category_type_df)
        self.floor_df = _cleaner.clean_floor_data(self.floor_df)
        self.em_location_df = _cleaner.clean_em_location(self.em_location_df)
        self.av_equipment_df = _cleaner.clean_av_equipment(self.av_equipment_df)
        self.timetable_df = _cleaner.clean_timetable_data(self.timetable_df)
        self.meeting_room_usage_df = _cleaner.clean_meeting_room_usage(self.meeting_room_usage_df)
        self.feedback.pushInfo("Data Cleaning Successful!")

        self.feedback.pushInfo("Data Mutating Initialized for Timetable and Employee location")
        _mutator = DataMutator(self.feedback)
        self.em_location_df = _mutator.mutate_em_location(self.em_location_df)
        self.timetable_df = _mutator.mutate_timetable_data(self.timetable_df)
        self.feedback.pushInfo("Data Mutating Successful for Timetable and Employee location")


        self.feedback.pushInfo("Data Merging Initialized")
        _merger = DataMerger(self.feedback)
        self.merged_space_data = _merger.get_merged_space_data(self.uom_space_df, self.rm_category_type_df, self.floor_df)
        self.merged_em_location_data = _merger.get_merged_em_location_data(self.em_location_df,self.merged_space_data)
        self.merged_av_equipment_data = _merger.get_merged_av_equipment_data(self.av_equipment_df,self.merged_space_data)
        self.merged_timetable_data = _merger.get_merged_timetable_data(self.timetable_df,self.merged_space_data)

        self.merged_meeting_room_usage_data = _merger.get_merged_meeting_room_usage_data(self.meeting_room_usage_df,self.merged_space_data)
        self.feedback.pushInfo("Data Merging Successful!")

        return self.merged_space_data, self.merged_em_location_data, self.merged_av_equipment_data, self.merged_timetable_data, self.merged_meeting_room_usage_data


class DataCleaner():
    def __init__(self,feedback):
        self.feedback = feedback
    
    def clean_uom_space(self,uom_space_df):
        uom_space_df['Campus Code']=uom_space_df['Campus Code'].astype(str).str.strip().str.lower()
        uom_space_df['Building Code']=uom_space_df['Building Code'].astype(str).str.strip().str.lower()
        uom_space_df['Building Name']=uom_space_df['Building Name'].astype(str).str.strip().str.lower()
        uom_space_df['Room Type']=uom_space_df['Room Type'].astype(str).str.strip().str.lower()
        uom_space_df['Room Category']=uom_space_df['Room Category'].astype(str).str.strip().str.lower()
        uom_space_df['Floor Code']=uom_space_df['Floor Code'].astype(str).str.strip().str.lower()
        uom_space_df['Room Code']=uom_space_df['Room Code'].astype(str).str.strip().str.lower()
        return uom_space_df

    def clean_rm_category_type(self,rm_category_type_df):
        rm_category_type_df['Room Type']=rm_category_type_df['Room Type'].astype(str).str.strip().str.lower()
        rm_category_type_df['Room Category']=rm_category_type_df['Room Category'].astype(str).str.strip().str.lower()
        rm_category_type_df['Room Type Abbreviation']=rm_category_type_df['Room Type Abbreviation'].str.lower().str.strip()
        rm_category_type_df['Description']=rm_category_type_df['Description'].str.lower().str.strip()
        rm_category_type_df['Room Type Definition']=rm_category_type_df['Room Type Definition'].str.lower().str.strip()
        return rm_category_type_df

    def clean_floor_data(self,floor_df):
        floor_df['Building Code'] = floor_df['Building Code'].astype(str).str.strip().str.lower()
        floor_df['Floor Code'] = floor_df['Floor Code'].astype(str).str.strip().str.lower()
        floor_df['Floor Name'] = floor_df['Floor Name'].astype(str).str.strip().str.lower()
        return floor_df

    def clean_em_location(self,em_location_df):
        em_location_df['Floor Code'] = em_location_df['Floor Code'].astype(int)
        em_location_df['Floor Code'] = em_location_df['Floor Code'].astype(str).str.strip().str.lower()
        return em_location_df

    def clean_av_equipment(self,av_equipment_df):
        av_equipment_df['Room Type'] = av_equipment_df['Room Type'].astype(str).str.strip().str.lower()
        av_equipment_df['Room Code'] = av_equipment_df['Room Code'].astype(str).str.strip().str.lower()
        av_equipment_df['Building Code'] = av_equipment_df['Building Code'].astype(str).str.strip().str.lower()
        av_equipment_df['Campus Code'] = av_equipment_df['Campus Code'].astype(str).str.strip().str.lower()
        av_equipment_df['Equip. Status'] = av_equipment_df['Equip. Status'].astype(str).str.strip().str.lower()
        av_equipment_df['Floor Code'] = av_equipment_df['Floor Code'].astype(int).astype(str).str.strip().str.lower()
        return av_equipment_df

    def clean_timetable_data(self,timetable_df):
        timetable_df = timetable_df.dropna(how='all')
        timetable_df = timetable_df.drop_duplicates()
        timetable_df = timetable_df[timetable_df['Host Key of Allocated Locations'].notna()]
        timetable_df = timetable_df[timetable_df['Host Key of Allocated Locations']!='Online option.']
        timetable_df = timetable_df[timetable_df['Name of Zone of Allocated Locations']!='Off-Site']
        return timetable_df

    def clean_meeting_room_usage(self,meeting_room_usage_df):
        meeting_room_usage_df = meeting_room_usage_df[meeting_room_usage_df['Campus Code'].notna()]
        meeting_room_usage_df = meeting_room_usage_df[meeting_room_usage_df['Building Code'].notna()]
        meeting_room_usage_df = meeting_room_usage_df[meeting_room_usage_df['Floor Code'].notna()]
        meeting_room_usage_df = meeting_room_usage_df[meeting_room_usage_df['Room Code'].notna()]

        meeting_room_usage_df['Campus Code'] = meeting_room_usage_df['Campus Code'].astype(str).str.strip().str.lower()
        meeting_room_usage_df['Building Code'] = meeting_room_usage_df['Building Code'].astype(str).str.strip().str.lower()
        meeting_room_usage_df['Building Name'] = meeting_room_usage_df['Building Name'].astype(str).str.strip().str.lower()
        meeting_room_usage_df['Floor Code'] = meeting_room_usage_df['Floor Code'].astype(int).astype(str).str.strip()
        meeting_room_usage_df['Room Code'] = meeting_room_usage_df['Room Code'].astype(str).str.strip().str.lower()
        return meeting_room_usage_df

    
class DataMutator():
    def __init__(self,feedback):
        self.feedback = feedback

    def mutate_em_location(self,em_location_df):
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
            building_codes.append(s[0].strip().lower())
            room_codes.append(s[1].strip().lower())
            c = row['Name of Allocated Locations'].split('-')[0]
            if c == 'zzzPAR':
                c = 'PAR'
            campus_codes.append(c.strip().lower())
            d = row['Duration as duration']
            class_duration_minutes.append(d.hour * 60 + d.minute)
        timetable_df['Building Code'] = building_codes
        timetable_df['Room Code'] = room_codes
        timetable_df['Campus Code'] = campus_codes
        timetable_df['Class Duration In Minutes'] = class_duration_minutes
        return timetable_df


class DataMerger():

    def __init__(self,feedback):
        self.feedback = feedback

    def get_merged_space_data(self,uom_space_df,rm_category_type_df, floor_df):
        uom_space_df_enhanced = pd.merge(uom_space_df,floor_df,on=['Building Code','Floor Code'])
        self.feedback.pushInfo("Merge - uom_space + floor_data")
        merged_space_data_df = pd.merge(uom_space_df_enhanced,rm_category_type_df,on=['Room Category','Room Type'])
        self.feedback.pushInfo("Merge - enhanced_uom_space + rm_category_type")
        return merged_space_data_df

    def get_merged_em_location_data(self,em_location_df,merged_space_data_df):
        self.feedback.pushInfo("Merge - space_data + em_location")
        merged_em_location_df = pd.merge(em_location_df,merged_space_data_df,on=['Building Code','Floor Code','Room Code'])
        return merged_em_location_df

    def get_merged_av_equipment_data(self,av_equipment_df,merged_space_data_df):
        self.feedback.pushInfo("Merge - space_data + av_equipment")
        merged_av_equipment_df = pd.merge(av_equipment_df,merged_space_data_df,on=['Campus Code','Building Code','Floor Code','Room Code'])
        return merged_av_equipment_df

    def get_merged_timetable_data(self,timetable_df,merged_space_data_df):
        self.feedback.pushInfo("Merge - space_data + timetable_data")
        merged_timetable_df = pd.merge(timetable_df,merged_space_data_df,on=['Campus Code','Building Code','Room Code'])
        return merged_timetable_df

    def get_merged_meeting_room_usage_data(self,meeting_room_usage_df,merged_space_data_df):
        self.feedback.pushInfo("Merge - space_data + meeting_room_usage")
        merged_meeting_room_usage_df = pd.merge(meeting_room_usage_df,merged_space_data_df,on=['Campus Code','Building Code','Floor Code','Room Code'])
        return merged_meeting_room_usage_df

# class DataExtractor():
#     def __init__(self,feedback):
#         self.feedback = feedback

#     def get_meeting_rooms_data(self,rm_category_type_df,space_data):
#         possible_rooms = rm_category_type_df[rm_category_type_df['Room Type'].str.contains("601|629")]
#         meeting_room_types = possible_rooms['Room Type'].tolist()

#         possible_meeting_rooms_df = space_data[space_data['Room Type'].isin(meeting_room_types)]
#         return possible_meeting_rooms_df

#     def get_toilets_data(self,rm_category_type_df,space_data):
#         possible_rooms = rm_category_type_df[rm_category_type_df['Room Type Definition'].str.contains("toilet|washroom")]
#         toilet_room_types = possible_rooms['Room Type'].tolist()

#         possible_toilets_df = space_data[space_data['Room Type'].isin(toilet_room_types)]
#         return possible_toilets_df


class DataFeatures():
    def __init__(self,feedback):
        self.feedback = feedback

    def get_meeting_room_capacity(self,data, val):
        row = data[data['Building Code']==val]
        if len(row) > 0:
            return row.iloc[0]['MR_COUNT']
        else:
            return None

    def get_toilet_room_capacity(self,data, val):
        row = data[data['Building Code']==val]
        if len(row) > 0:
            return row.iloc[0]['TR_COUNT']
        else:
            return None

    def get_student_count(self,data, val):
        row = data[data['Building Code']==val]
        if len(row) > 0:
            return row.iloc[0]['STU_COUNT']
        else:
            return None

    def get_employee_count(self,data, val):
        row = data[data['Building Code']==val]
        if len(row) > 0:
            return row.iloc[0]['EMP_COUNT']
        else:
            return None