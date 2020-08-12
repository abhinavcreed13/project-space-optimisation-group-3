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
                       QgsFields)
from qgis import processing
import pandas as pd

class CustomProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    BASE_URL = "base_url"
    CAMPUS_CODE = "campus_code"
    SEARCH_KEY = "search_key"
    COVID_ENABLED = "covid"

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return CustomProcessingAlgorithm()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Optimization script'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Optimization script')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('scripts')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'scripts'

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr("Creates custom layers according to the requirment")

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
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
                'Enter Building Code'
            )
        )
        
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.COVID_ENABLED,
                'Enable COVID',
            )
        )
        

        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Output layer')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        source = self.parameterAsSource(
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
        
        building_code = self.parameterAsString(
            parameters,
            self.SEARCH_KEY,
            context
        )
        
       # covid_enabled = self.parameterAsBool(
        #    parameters,
        #    self.COVID_ENABLED,
        #    context
        #)
       
        fields = QgsFields()
        fields.append(QgsField(base_url, QVariant.String))
        fields.append(QgsField(campus_code,QVariant.String))
        fields.append(QgsField(building_code,QVariant.String))
        #fields.append(QgsField(covid_enabled,QVariant.Bool))
        

        # If source was not found, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSourceError method to return a standard
        # helper text for when a source cannot be evaluated
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            source.wkbType(),
            source.sourceCrs()
        )

        # Send some information to the user
        uom_space_url = base_url+'uom-space.xlsx'
        rm_category_type_url = base_url+'rm-category-type-cleaned.xlsx'
        em_location_url = base_url+'em-location.xlsx'
        av_equipment_url = base_url+'av-equipment.xlsx'
        timetable_2020_url = base_url+'2020-timetable-v2.xlsx'
        floor_name_url = base_url+'fl-name-cleaned.xlsx'
        meeting_room_usage_url = base_url+'meeting-room-usage.xlsx'
        _processor = DataProcessor(uom_space_url,rm_category_type_url,em_location_url,av_equipment_url,
                           timetable_2020_url,floor_name_url,meeting_room_usage_url,feedback)
        _processor.load_data()
        space_data, employee_data, av_equipment_data, timetable_data, mr_usage_data = _processor.get_all_datasets()
        _extractor = DataExtractor(feedback)
        possible_meeting_rooms_data = _extractor.get_meeting_rooms_data(_processor.rm_category_type_df, space_data)
        possible_toilets_data = _extractor.get_toilets_data(_processor.rm_category_type_df, space_data)
        feedback.pushInfo('END')

        # If sink was not created, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSinkError method to return a standard
        # helper text for when a sink cannot be evaluated
        # if sink is None:
        #     raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        # # Compute the number of steps to display within the progress bar and
        # # get features from source
        # total = 100.0 / source.featureCount() if source.featureCount() else 0
        # features = source.getFeatures()

        # for current, feature in enumerate(features):
        #     # Stop the algorithm if cancel button has been clicked
        #     if feedback.isCanceled():
        #         break

        #     # Add a feature in the sink
        #     sink.addFeature(feature, QgsFeatureSink.FastInsert)

        #     # Update the progress bar
        #     feedback.setProgress(int(current * total))

        # To run another Processing algorithm as part of this algorithm, you can use
        # processing.run(...). Make sure you pass the current context and feedback
        # to processing.run to ensure that all temporary layer outputs are available
        # to the executed algorithm, and that the executed algorithm can send feedback
        # reports to the user (and correctly handle cancellation and progress reports!)
        # if False:
        #     buffered_layer = processing.run("native:buffer", {
        #         'INPUT': dest_id,
        #         'DISTANCE': 1.5,
        #         'SEGMENTS': 5,
        #         'END_CAP_STYLE': 0,
        #         'JOIN_STYLE': 0,
        #         'MITER_LIMIT': 2,
        #         'DISSOLVE': False,
        #         'OUTPUT': 'memory:'
        #     }, context=context, feedback=feedback)['OUTPUT']

        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        return {self.OUTPUT: dest_id}





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
        # output data shapes on the console
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
    def __init__(self,feedback):
        self.feedback = feedback

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

    def __init__(self,feedback):
        self.feedback = feedback


    def get_merged_space_data(self,uom_space_df,rm_category_type_df, floor_df):
        uom_space_df_enhanced = pd.merge(uom_space_df,floor_df,on=['Building Code','Floor Code'])
        self.feedback.pushInfo("# Merge - uom_space + floor_data")
        # self.feedback.pushInfo(uom_space_df_enhanced.shape)
        # self.feedback.pushInfo('Unable to merge records:',uom_space_df.shape[0]-uom_space_df_enhanced.shape[0])
        merged_space_data_df = pd.merge(uom_space_df_enhanced,rm_category_type_df,on=['Room Category','Room Type'])
        self.feedback.pushInfo("# Merge - enhanced_uom_space + rm_category_type")
        # self.feedback.pushInfo((uom_space_df_enhanced.shape, merged_space_data_df.shape))
        # self.feedback.pushInfo('Unable to merge records:',uom_space_df_enhanced.shape[0]-merged_space_data_df.shape[0])
        return merged_space_data_df

    def get_merged_em_location_data(self,em_location_df,merged_space_data_df):
        self.feedback.pushInfo("# merge - space_data + em_location")
        merged_em_location_df = pd.merge(em_location_df,merged_space_data_df,on=['Building Code','Floor Code','Room Code'])
        # self.feedback.pushInfo((em_location_df.shape, merged_em_location_df.shape))
        # self.feedback.pushInfo('Unable to merge records:',em_location_df.shape[0]-merged_em_location_df.shape[0])
        return merged_em_location_df

    def get_merged_av_equipment_data(self,av_equipment_df,merged_space_data_df):
        self.feedback.pushInfo("# merge - space_data + av_equipment")
        merged_av_equipment_df = pd.merge(av_equipment_df,merged_space_data_df,on=['Campus Code','Building Code','Floor Code','Room Code'])
        # self.feedback.pushInfo((av_equipment_df.shape, merged_av_equipment_df.shape))
        # self.feedback.pushInfo('Unable to merge records:',av_equipment_df.shape[0]-merged_av_equipment_df.shape[0])
        return merged_av_equipment_df

    def get_merged_timetable_data(self,timetable_df,merged_space_data_df):
        self.feedback.pushInfo("# merge - space_data + timetable_data")
        merged_timetable_df = pd.merge(timetable_df,merged_space_data_df,on=['Campus Code','Building Code','Room Code'])
        # self.feedback.pushInfo((timetable_df.shape, merged_timetable_df.shape))
        # self.feedback.pushInfo('Unable to merge records:',timetable_df.shape[0]-merged_timetable_df.shape[0])
        return merged_timetable_df

    def get_merged_meeting_room_usage_data(self,meeting_room_usage_df,merged_space_data_df):
        self.feedback.pushInfo("# merge - space_data + meeting_room_usage")
        merged_meeting_room_usage_df = pd.merge(meeting_room_usage_df,merged_space_data_df,on=['Campus Code','Building Code','Floor Code','Room Code'])
        # self.feedback.pushInfo((meeting_room_usage_df.shape, merged_meeting_room_usage_df.shape))
        # self.feedback.pushInfo('Unable to merge records:',meeting_room_usage_df.shape[0]-merged_meeting_room_usage_df.shape[0])
        return merged_meeting_room_usage_df

class DataExtractor():
    def __init__(self,feedback):
        self.feedback = feedback

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