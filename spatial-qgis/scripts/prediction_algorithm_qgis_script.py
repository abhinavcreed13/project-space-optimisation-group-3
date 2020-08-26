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

from qgis.PyQt.QtCore import QCoreApplication
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
import numpy as np
from qgis.utils import iface
from PyQt5.QtGui import QColor
from scipy.special import softmax
import sys

class PredictionAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to find most optimal building 
    based on different parameters
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    SEARCH_KEY = "search_key"
    CURRENT_BUILDING = "current_building"
    RADIUS = "radius"
    OBJECTIVE = "objective"
    PENALTY = "penalty"

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return PredictionAlgorithm()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Prediction Algorithm'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Prediction Algorithm Script')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('Scripts')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Scripts'

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr("Algorithm to find most optimal building based on different parameters")

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
           QgsProcessingParameterMapLayer(
               self.INPUT,
               self.tr('Input layer'),
               [QgsProcessing.TypeVectorAnyGeometry]
           )
        )
        
        # self.addParameter(
        #     QgsProcessingParameterString(
        #         self.INPUT,
        #         'Enter Layer Name',
        #         defaultValue="Output Layer"
        #     )
        # )

        self.addParameter(
            QgsProcessingParameterString(
                self.SEARCH_KEY,
                'Enter Search Key',
                defaultValue="BUILD_NO"
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.CURRENT_BUILDING,
                'Enter current building code',
                defaultValue="104"
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.RADIUS,
                'Enter radius in meters',
                defaultValue="200"
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.OBJECTIVE,
                'Enter objective (0 - meeting rooms, 1 - toilet facilities)',
                defaultValue="0"
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.PENALTY,
                'Enter penalty',
                defaultValue="0.05"
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
        # input = self.parameterAsString(
        #     parameters,
        #     self.INPUT,
        #     context
        # )
        
        source = self.parameterAsLayer(
            parameters,
            self.INPUT,
            context
        )

        search_key = self.parameterAsString(
            parameters,
            self.SEARCH_KEY,
            context
        )

        current_building = self.parameterAsString(
            parameters,
            self.CURRENT_BUILDING,
            context
        )

        radius = self.parameterAsString(
            parameters,
            self.RADIUS,
            context
        )

        objective = self.parameterAsString(
            parameters,
            self.OBJECTIVE,
            context
        )

        penalty = self.parameterAsString(
            parameters,
            self.PENALTY,
            context
        )
        
        # using provided layer - connected via reference
        layer = source
        
        # create logic object
        _runner = PredictionAlgorithmLogic(feedback, layer, search_key)

        # run algo
        top_3_buildings = _runner.find_building_algorithm(
                        int(current_building), 
                        int(radius), 
                        int(objective), 
                        float(penalty))
        
        iface.mapCanvas().setSelectionColor(QColor("green"))
        selected_fids = []
        layer.removeSelection()
        feedback.pushInfo("")
        feedback.pushInfo("-- Top 3 Buildings Found --")
        for idx, building in enumerate(top_3_buildings):
            #feedback.pushInfo(str(building))
            feedback.pushInfo('#{0} - {2}, {1}, {3:.2f} meters'.format(idx+1, building['building_name'], building['building_id'], building['distance']))
            selected_fids.append(building['feature_obj'].id())
            
        layer.select(selected_fids)
        feedback.pushInfo("-----")
        feedback.pushInfo("STOPPING SCRIPT TO AVOID CREATING NEW LAYER")
        feedback.pushInfo("-----")
        raise Exception("--- IGNORE THIS ---")

        # If source was not found, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSourceError method to return a standard
        # helper text for when a source cannot be evaluated
        # if source is None:
        #     raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        # # (sink, dest_id) = self.parameterAsSink(
        # #     parameters,
        # #     self.OUTPUT,
        # #     context,
        # #     source.fields(),
        # #     source.wkbType(),
        # #     source.sourceCrs()
        # # )

        # # Send some information to the user
        # feedback.pushInfo('CRS is {}'.format(source.sourceCrs().authid()))

        # # If sink was not created, throw an exception to indicate that the algorithm
        # # encountered a fatal error. The exception text can be any string, but in this
        # # case we use the pre-built invalidSinkError method to return a standard
        # # helper text for when a sink cannot be evaluated
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

        # # To run another Processing algorithm as part of this algorithm, you can use
        # # processing.run(...). Make sure you pass the current context and feedback
        # # to processing.run to ensure that all temporary layer outputs are available
        # # to the executed algorithm, and that the executed algorithm can send feedback
        # # reports to the user (and correctly handle cancellation and progress reports!)
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

        # # Return the results of the algorithm. In this case our only result is
        # # the feature sink which contains the processed features, but some
        # # algorithms may return multiple feature sinks, calculated numeric
        # # statistics, etc. These should all be included in the returned
        # # dictionary, with keys matching the feature corresponding parameter
        # # or output names.
        # return {self.OUTPUT: dest_id}
        #return {}

class PredictionAlgorithmLogic():

    def __init__(self, feedback, layer, search_key):
        self.feedback = feedback
        self.layer = layer
        self.search_key = search_key

    def normalize_data(self, data):
        return (data - np.min(data)) / (np.max(data) - np.min(data))

    def find_building_algorithm(self, 
        current_building, radius,
        objective, penalty):
        """
        Find the most optimal nearest building

        Parameters:
        layer: QGIS layer object
        search_key: layer building number search attribute
        current_building (int)
        radius (int) : meters
        objective: 0 - meeting rooms, 1 - toilet facilites
        penalty (real number) > 0
        """
        layer = self.layer
        search_key = self.search_key

        # Step-0: Find target building geometry
        targetGeometry = None
        for feature in layer.getFeatures():
            if str(feature[search_key]) == str(current_building):
                self.feedback.pushInfo(str("Current Building : "+ feature["NAME"]))
                targetGeometry = feature.geometry()
                #x = targetGeometry.asMultiPolygon()
                #print("MultiPolygon: ", x, "Area: ", targetGeometry.area())
                break
                
        #print(type(targetGeometry))
        
        # Step-1: get buildings within specified radius
        # Step-2: calculate weights of these buildings
        nearest_buildings_info = []
        select_buildings = []
        weights = [] # ordered weights
        distances = [] # ordered distances
        for feature in layer.getFeatures():
            if str(feature[search_key]) != str(current_building):
                dist = feature.geometry().distance(targetGeometry)
                if dist <= radius:
                    data_obj = {
                        'building_id': str(feature[search_key]),
                        'building_name': feature["NAME"],
                        'distance': dist,
                        'feature_obj': feature
                    }
                    # Meeting rooms objective
                    if objective == 0:
                        # add buildings for which weights exists
                        if feature['MR_WEIGHTS'] != 'NULL':
                            data_obj['weight'] = feature['MR_WEIGHTS']
                            weights.append(data_obj['weight'])
                            distances.append(data_obj['distance'])
                            select_buildings.append(feature.id())
                            nearest_buildings_info.append(data_obj)
                        
        
        # Step-3: data correlations - TODO
    
        # Step-4: calculate probabilities
        # convert weights into probability distribution
        np_weights = np.array(weights)
        np_weights_probs = softmax(np_weights)
        #print(np_weights[0])
        #print(np_weights_probs)
        #print(np_weights_probs.shape)
        #print(np_weights_probs[0])
        
        np_dist = np.array(distances)
        np_dist_adjusted = self.normalize_data(np_dist)
        #print(np_dist[0])
        #print(np_dist_adjusted[0])
        penalities = np_dist_adjusted * penalty
        #print(penalities[0])
        
        # Step-5: Penalize probabilities
        # as per their physical distance from current building 
        # and using penalty.
        adjusted_weights = [] # ordered adjusted weights
        for idx, building in enumerate(nearest_buildings_info):
            prob = np_weights_probs[idx]
            penalty = penalities[idx]
            adjusted_weight = prob * penalty
            building["adjusted_weight"] = adjusted_weight
            adjusted_weights.append(adjusted_weight)
            
        # Step 6: Optimal nearest building
        # top 3 buildings
        adjusted_weights = np.array(adjusted_weights)
        b_indexes = adjusted_weights.argsort()[-3:][::-1]
        final_buildings = []
        
        for b_idx in b_indexes:
            final_buildings.append(nearest_buildings_info[b_idx])
            
        return final_buildings