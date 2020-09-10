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

        # parameters
        base_url = base_url.strip()
        campus_code = campus_code.strip().lower()
        search_key = search_key.strip()

        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        
        # extract required data
        _extractor = DataExtractor(feedback, base_url)
        filtered_meeting_rooms_data = _extractor.get_meeting_rooms_data(campus_code)
        filtered_toilets_data = _extractor.get_toilets_data(campus_code)
        filtered_employee_data = _extractor.get_employees_data(campus_code)
        mr_equipment_data = _extractor.get_meeting_rooms_equipment_data(campus_code)
        filtered_timetable_data = _extractor.get_timetable_data(campus_code)
        filtered_mr_usage_data = _extractor.get_meeting_room_usage_data(campus_code)

        # layer handlers
        layer = source
        features = layer.getFeatures()
        layer_provider = layer.dataProvider()

        # create layer manager
        layerManager = LayerManager(feedback)

        # clean + add attributes
        layerManager.add_attributes(layer, layer_provider)
        
        # get indexes of all attributes
        attr_indexes = layerManager.get_indexes_of_attributes(layer_provider)

        #### ---- Creating grouped data ----- #####
        feedback.pushInfo('Merging data for getting supply')   
        tr_data = filtered_toilets_data.groupby(by = ['Campus Code','Building Code','Building Name'],as_index = False).agg({'Room Code':pd.Series.nunique,'Room Capacity':sum})
        tr_data = tr_data.rename(columns = {"Room Code":"TR_COUNT", "Room Capacity": "TR_CAP"})
        
        mr_data = filtered_meeting_rooms_data.groupby(by=['Campus Code','Building Code','Building Name'], as_index=False).agg({'Room Code':pd.Series.nunique,'Room Capacity':sum})
        mr_data = mr_data.rename(columns={"Room Code": "MR_COUNT", "Room Capacity": "MR_CAP"})

        feedback.pushInfo('Merging data for getting demand')
        student_data = filtered_timetable_data.groupby(by=['Campus Code','Building Code','Building Name'], as_index=False).agg({'Planned Size':sum})
        student_data = student_data.rename(columns = {'Planned Size':'STU_COUNT'})
        
        emp_data = filtered_employee_data.groupby(by=['Campus Code','Building Code','Building Name'], as_index=False).agg({'Employee Sequential ID':pd.Series.nunique})
        emp_data = emp_data.rename(columns={'Employee Sequential ID':'EMP_COUNT'})
        
        cols = ['Campus Code','Building Code','Building Name']
        aggs = {'Equipment Code': pd.Series.nunique}
        names = {'Equipment Code': 'EQP_CNT'}
        mr_av_data = mr_equipment_data.groupby(by=cols, as_index=False).agg(aggs)
        mr_av_data = mr_av_data.rename(columns=names)

        ## New version - worked
        excellent_filtered_mr_data = filtered_meeting_rooms_data[filtered_meeting_rooms_data['Room Condition 2018'] == 'Excellent']
        verygood_filtered_mr_data = filtered_meeting_rooms_data[filtered_meeting_rooms_data['Room Condition 2018'] == 'Very Good']
        good_filtered_mr_data = filtered_meeting_rooms_data[filtered_meeting_rooms_data['Room Condition 2018'] == 'Good']
        cols = ['Campus Code','Building Code','Building Name']
        aggs = {'Room Code':pd.Series.nunique,'Room Capacity':sum}
        names = {"Room Code": "EX_MR_CNT", "Room Capacity": "EX_MR_CAP"}
        excellent_mr_data = excellent_filtered_mr_data.groupby(by=cols, as_index=False).agg(aggs)
        excellent_mr_data = excellent_mr_data.rename(columns=names)
        names = {"Room Code": "VG_MR_CNT", "Room Capacity": "VG_MR_CAP"}
        verygood_mr_data = verygood_filtered_mr_data.groupby(by=cols, as_index=False).agg(aggs)
        verygood_mr_data = verygood_mr_data.rename(columns=names)
        names = {"Room Code": "G_MR_CNT", "Room Capacity": "G_MR_CAP"}
        good_mr_data = good_filtered_mr_data.groupby(by=cols, as_index=False).agg(aggs)
        good_mr_data = good_mr_data.rename(columns=names)

        cols = ['Campus Code','Building Code','Building Name']
        names = {"Room Area m²": "AG_MR_SZ"}
        mr_data_area = filtered_meeting_rooms_data.groupby(by=cols, as_index=False)['Room Area m²'].mean()
        mr_data_area = mr_data_area.rename(columns=names)

        cols = ['Campus Code','Building Code','Building Name_x']
        names = {"Meetings": "TOTAL_M"}
        mr_usage = filtered_mr_usage_data.groupby(by=cols, as_index=False)["Meetings"].sum()
        mr_usage = mr_usage.rename(columns=names)

        ## New version TR - worked
        excellent_filtered_tr_data = filtered_toilets_data[filtered_toilets_data['Room Condition 2018'] == 'Excellent']
        verygood_filtered_tr_data = filtered_toilets_data[filtered_toilets_data['Room Condition 2018'] == 'Very Good']
        good_filtered_tr_data = filtered_toilets_data[filtered_toilets_data['Room Condition 2018'] == 'Good']
        cols = ['Campus Code','Building Code','Building Name']
        aggs = {'Room Code':pd.Series.nunique,'Room Capacity':sum}
        names = {"Room Code": "EX_TR_CNT", "Room Capacity": "EX_TR_CAP"}
        excellent_tr_data = excellent_filtered_tr_data.groupby(by=cols, as_index=False).agg(aggs)
        excellent_tr_data = excellent_tr_data.rename(columns=names)
        names = {"Room Code": "VG_TR_CNT", "Room Capacity": "VG_TR_CAP"}
        verygood_tr_data = verygood_filtered_tr_data.groupby(by=cols, as_index=False).agg(aggs)
        verygood_tr_data = verygood_tr_data.rename(columns=names)
        names = {"Room Code": "G_TR_CNT", "Room Capacity": "G_TR_CAP"}
        good_tr_data = good_filtered_tr_data.groupby(by=cols, as_index=False).agg(aggs)
        good_tr_data = good_tr_data.rename(columns=names)

        cols = ['Campus Code','Building Code','Building Name']
        names = {"Room Area m²": "AG_TR_SZ"}
        tr_data_area = filtered_toilets_data.groupby(by=cols, as_index=False)['Room Area m²'].mean()
        tr_data_area = tr_data_area.rename(columns=names)

        cols = ['Campus Code','Building Code','Building Name']
        names = {"Class Duration In Minutes": "AG_CL_DS"}
        cl_timetable = filtered_timetable_data.groupby(by=cols, as_index=False)["Class Duration In Minutes"].mean()
        cl_timetable = cl_timetable.rename(columns=names)

        ###### ---------------------------------- ######

        # create sink for new output layer
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

        # feature update logic
        for current, feature in enumerate(features):
            if feedback.isCanceled():
                break
            id = feature.id()
            
            # update calculated fields
            supply = _features.get_data_for_key(mr_data, feature[search_key], 'MR_CAP')
            demand = _features.get_data_for_key(emp_data, feature[search_key], 'EMP_COUNT')

            toilet_supply = _features.get_data_for_key(tr_data,feature[search_key], 'TR_CAP')
            toilet_demand = _features.get_data_for_key(student_data,feature[search_key], 'STU_COUNT')
            
            if supply and demand:
                weight = float(supply/demand)
            else:
                weight = QVariant()
            if toilet_supply and toilet_demand:
                tr_weight = float(toilet_supply/toilet_demand)
            else:
                tr_weight = QVariant()

            feature['MR_WEIGHTS'] = weight
            feature['TR_WEIGHTS'] = tr_weight        
            
            # update data fields
            mr_count = _features.get_data_for_key(mr_data, feature[search_key], 'MR_COUNT')
            if mr_count:
                feature['MR_CNT'] = int(mr_count)
            else:
                feature['MR_CNT'] = QVariant()

            if supply:
                feature['MR_CAP'] = int(supply)
            else:
                feature['MR_CAP'] = QVariant()
            
            tr_count = _features.get_data_for_key(tr_data,feature[search_key], 'TR_COUNT')
            if tr_count:
                feature['TR_CNT'] = int(tr_count)
            else:
                feature['TR_CNT'] = QVariant()

            if toilet_supply:
                feature['TR_CAP'] = int(toilet_supply)
            else:
                feature['TR_CAP'] = QVariant()

            if demand:
                feature['EMP_CNT'] = int(demand)
            else:
                feature['EMP_CNT'] = QVariant()

            eqp_count = _features.get_data_for_key(mr_av_data, feature[search_key], 'EQP_CNT')
            if eqp_count:
                feature['EQP_CNT'] = int(eqp_count)
            else:
                feature['EQP_CNT'] = QVariant()
            
            if toilet_demand:
                feature['STU_CNT'] = int(toilet_demand)
            else:
                feature['STU_CNT'] = QVariant()

            ex_mr_cap = _features.get_data_for_key(excellent_mr_data, feature[search_key], 'EX_MR_CAP')
            if ex_mr_cap:
                feature['EX_MR_CAP'] = int(ex_mr_cap)
            else:
                feature['EX_MR_CAP'] = QVariant()

            vg_mr_cap = _features.get_data_for_key(verygood_mr_data, feature[search_key], 'VG_MR_CAP')
            if vg_mr_cap:
                feature['VG_MR_CAP'] = int(vg_mr_cap)
            else:
                feature['VG_MR_CAP'] = QVariant()

            g_mr_cap = _features.get_data_for_key(good_mr_data, feature[search_key], 'G_MR_CAP')
            if g_mr_cap:
                feature['G_MR_CAP'] = int(g_mr_cap)
            else:
                feature['G_MR_CAP'] = QVariant()

            avg_mr_area = _features.get_data_for_key(mr_data_area, feature[search_key], 'AG_MR_SZ')
            if avg_mr_area:
                feature['AG_MR_SZ'] = float(avg_mr_area)
            else:
                feature['AG_MR_SZ'] = QVariant()

            total_m = _features.get_data_for_key(mr_usage, feature[search_key], 'TOTAL_M')
            if total_m:
                feature['TOTAL_M'] = int(total_m)
            else:
                feature['TOTAL_M'] = QVariant()

            ex_tr_cap = _features.get_data_for_key(excellent_tr_data, feature[search_key], 'EX_TR_CAP')
            if ex_tr_cap:
                feature['EX_TR_CAP'] = int(ex_tr_cap)
            else:
                feature['EX_TR_CAP'] = QVariant()

            vg_tr_cap = _features.get_data_for_key(verygood_tr_data, feature[search_key], 'VG_TR_CAP')
            if vg_mr_cap:
                feature['VG_TR_CAP'] = int(vg_tr_cap)
            else:
                feature['VG_TR_CAP'] = QVariant()

            g_tr_cap = _features.get_data_for_key(good_tr_data, feature[search_key], 'G_TR_CAP')
            if g_tr_cap:
                feature['G_TR_CAP'] = int(g_tr_cap)
            else:
                feature['G_TR_CAP'] = QVariant()

            avg_tr_area = _features.get_data_for_key(tr_data_area, feature[search_key], 'AG_TR_SZ')
            if avg_tr_area:
                feature['AG_TR_SZ'] = float(avg_tr_area)
            else:
                feature['AG_TR_SZ'] = QVariant()

            ag_cl_ds = _features.get_data_for_key(cl_timetable, feature[search_key], 'AG_CL_DS')
            if ag_cl_ds:
                feature['AG_CL_DS'] = float(ag_cl_ds)
            else:
                feature['AG_CL_DS'] = QVariant()

            # connect index with attributes
            attr_value={
                attr_indexes['MR_WEIGHTS']: feature['MR_WEIGHTS'],
                attr_indexes['TR_WEIGHTS']: feature['TR_WEIGHTS'],
                attr_indexes['MR_CNT']: feature['MR_CNT'],
                attr_indexes['MR_CAP']: feature['MR_CAP'],
                attr_indexes['TR_CNT']: feature['TR_CNT'],
                attr_indexes['TR_CAP']: feature['TR_CAP'],
                attr_indexes['EMP_CNT']: feature['EMP_CNT'],
                attr_indexes['EQP_CNT']: feature['EQP_CNT'],
                attr_indexes['STU_CNT']: feature['STU_CNT'],
                attr_indexes['EX_MR_CAP']: feature['EX_MR_CAP'],
                attr_indexes['VG_MR_CAP']: feature['VG_MR_CAP'],
                attr_indexes['G_MR_CAP']: feature['G_MR_CAP'],
                attr_indexes['AG_MR_SZ']: feature['AG_MR_SZ'],
                attr_indexes['TOTAL_M']: feature['TOTAL_M'],
                attr_indexes['EX_TR_CAP']: feature['EX_TR_CAP'],
                attr_indexes['VG_TR_CAP']: feature['VG_TR_CAP'],
                attr_indexes['G_TR_CAP']: feature['G_TR_CAP'],
                attr_indexes['AG_TR_SZ']: feature['AG_TR_SZ'],
                attr_indexes['AG_CL_DS']: feature['AG_CL_DS']
            }
            layer_provider.changeAttributeValues({id:attr_value})
            if (update == "false"):
                sink.addFeature(feature, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(current * total))

        if (update == "true"):
            feedback.pushInfo("-----")
            feedback.pushInfo("STOPPING SCRIPT TO AVOID CREATING NEW LAYER")
            feedback.pushInfo("-----")
            raise Exception("--- IGNORE THIS ---")   
        else:
            attribute_indexes = list(attr_indexes.values())
            layer_provider.deleteAttributes(attribute_indexes)
            layer.updateFields()
            layer.commitChanges()
        
        return {self.OUTPUT: dest_id}

######## ----------- CUSTOM TOOLS ----------------- #############
class DataFeatures():
    def __init__(self,feedback):
        self.feedback = feedback

    def get_data_for_key(self, data, val, key):
        row = data[data['Building Code']==val]
        if len(row) > 0:
            return row.iloc[0][key]
        else:
            return None

class LayerManager():

    def __init__(self, feedback):
        self.feedback = feedback
        
    def add_attributes(self, layer, layer_provider):
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

        idx = layer.fields().indexFromName('MR_CNT')
        if idx != -1:
            layer_provider.deleteAttributes([idx])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("MR_CNT",  QVariant.Int)])
        layer.updateFields()

        idx = layer.fields().indexFromName('MR_CAP')
        if idx != -1:
            layer_provider.deleteAttributes([idx])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("MR_CAP",  QVariant.Int)])
        layer.updateFields()

        idx = layer.fields().indexFromName('TR_CNT')
        if idx != -1:
            layer_provider.deleteAttributes([idx])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("TR_CNT",  QVariant.Int)])
        layer.updateFields()

        idx = layer.fields().indexFromName('TR_CAP')
        if idx != -1:
            layer_provider.deleteAttributes([idx])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("TR_CAP",  QVariant.Int)])
        layer.updateFields()

        idx = layer.fields().indexFromName('EMP_CNT')
        if idx != -1:
            layer_provider.deleteAttributes([idx])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("EMP_CNT",  QVariant.Int)])
        layer.updateFields()

        idx = layer.fields().indexFromName('EQP_CNT')
        if idx != -1:
            layer_provider.deleteAttributes([idx])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("EQP_CNT",  QVariant.Int)])
        layer.updateFields()

        idx = layer.fields().indexFromName('STU_CNT')
        if idx != -1:
            layer_provider.deleteAttributes([idx])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("STU_CNT",  QVariant.Int)])
        layer.updateFields()

        idx = layer.fields().indexFromName('EX_MR_CAP')
        if idx != -1:
            layer_provider.deleteAttributes([idx])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("EX_MR_CAP",  QVariant.Int)])
        layer.updateFields()

        idx = layer.fields().indexFromName('VG_MR_CAP')
        if idx != -1:
            layer_provider.deleteAttributes([idx])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("VG_MR_CAP",  QVariant.Int)])
        layer.updateFields()

        idx = layer.fields().indexFromName('G_MR_CAP')
        if idx != -1:
            layer_provider.deleteAttributes([idx])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("G_MR_CAP",  QVariant.Int)])
        layer.updateFields()

        idx = layer.fields().indexFromName('AG_MR_SZ')
        if idx != -1:
            layer_provider.deleteAttributes([idx])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("AG_MR_SZ",  QVariant.Double)])
        layer.updateFields()

        idx = layer.fields().indexFromName('TOTAL_M')
        if idx != -1:
            layer_provider.deleteAttributes([idx])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("TOTAL_M",  QVariant.Int)])
        layer.updateFields()

        idx = layer.fields().indexFromName('EX_TR_CAP')
        if idx != -1:
            layer_provider.deleteAttributes([idx])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("EX_TR_CAP",  QVariant.Int)])
        layer.updateFields()

        idx = layer.fields().indexFromName('VG_TR_CAP')
        if idx != -1:
            layer_provider.deleteAttributes([idx])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("VG_TR_CAP",  QVariant.Int)])
        layer.updateFields()

        idx = layer.fields().indexFromName('G_TR_CAP')
        if idx != -1:
            layer_provider.deleteAttributes([idx])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("G_TR_CAP",  QVariant.Int)])
        layer.updateFields()

        idx = layer.fields().indexFromName('AG_TR_SZ')
        if idx != -1:
            layer_provider.deleteAttributes([idx])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("AG_TR_SZ",  QVariant.Double)])
        layer.updateFields()

        idx = layer.fields().indexFromName('AG_CL_DS')
        if idx != -1:
            layer_provider.deleteAttributes([idx])
            layer.updateFields()
        layer_provider.addAttributes([QgsField("AG_CL_DS",  QVariant.Double)])
        layer.updateFields()

    def get_indexes_of_attributes(self, layer_provider):
        return {
            "MR_WEIGHTS": layer_provider.fieldNameIndex('MR_WEIGHTS'),
            "TR_WEIGHTS": layer_provider.fieldNameIndex('TR_WEIGHTS'),
            "MR_CNT": layer_provider.fieldNameIndex('MR_CNT'),
            "MR_CAP": layer_provider.fieldNameIndex('MR_CAP'),
            "TR_CNT": layer_provider.fieldNameIndex('TR_CNT'),
            "TR_CAP": layer_provider.fieldNameIndex('TR_CAP'),
            "EMP_CNT": layer_provider.fieldNameIndex('EMP_CNT'),
            "EQP_CNT": layer_provider.fieldNameIndex('EQP_CNT'),
            "STU_CNT": layer_provider.fieldNameIndex('STU_CNT'),
            "EX_MR_CAP": layer_provider.fieldNameIndex('EX_MR_CAP'),
            "VG_MR_CAP": layer_provider.fieldNameIndex('VG_MR_CAP'),
            "G_MR_CAP": layer_provider.fieldNameIndex('G_MR_CAP'),
            "AG_MR_SZ": layer_provider.fieldNameIndex('AG_MR_SZ'),
            "TOTAL_M": layer_provider.fieldNameIndex('TOTAL_M'),
            "EX_TR_CAP": layer_provider.fieldNameIndex('EX_TR_CAP'),
            "VG_TR_CAP": layer_provider.fieldNameIndex('VG_TR_CAP'),
            "G_TR_CAP": layer_provider.fieldNameIndex('G_TR_CAP'),
            "AG_TR_SZ": layer_provider.fieldNameIndex('AG_TR_SZ'),
            "AG_CL_DS": layer_provider.fieldNameIndex('AG_CL_DS')
        }

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

    def get_meeting_room_usage_data(self, campus_code = None):
        mr_usage_data = self.mr_usage_data
        if campus_code:
            return mr_usage_data[mr_usage_data['Campus Code'] == campus_code]
        return mr_usage_data


######### -------------------- HELPERS -------------- ################
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