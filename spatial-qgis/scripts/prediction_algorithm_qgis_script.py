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

from qgis.PyQt.QtCore import QCoreApplication, QVariant
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

# ------------------------------------------------------------------
# Reset so get full traceback next time you run the script and a "real"
# exception occurs
if hasattr (sys, 'tracebacklimit'):
    del sys.tracebacklimit

# ------------------------------------------------------------------
# Raise this class for "soft halt" with minimum traceback.
class SoftHalt (Exception):
    def __init__ (self):
        sys.tracebacklimit = 0

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

        # self.addParameter(
        #     QgsProcessingParameterString(
        #         self.PENALTY,
        #         'Enter penalty',
        #         defaultValue="0.05"
        #     )
        # )

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

        # penalty = self.parameterAsString(
        #     parameters,
        #     self.PENALTY,
        #     context
        # )
        
        # using provided layer - connected via reference
        layer = source
        
        # create logic object
        _runner = PredictionAlgorithmLogic(feedback, layer, search_key)

        # run algo
        # top_3_buildings = _runner.find_building_algorithm(
        #                 int(current_building), 
        #                 int(radius), 
        #                 int(objective), 
        #                 float(penalty))

        top_3_nodes = _runner.find_building_algorithm_AOr(
                        int(current_building), 
                        int(radius), 
                        int(objective))
        
        iface.mapCanvas().setSelectionColor(QColor("green"))
        selected_fids = []
        layer.removeSelection()
        feedback.pushInfo("")
        feedback.pushInfo("-- Top 3 Buildings Found --")
        
        # for idx, building in enumerate(top_3_buildings):
        #     #feedback.pushInfo(str(building))
        #     feedback.pushInfo('#{0} - {2}, {1}, {3:.2f} meters'.format(idx+1, building['building_name'], building['building_id'], building['distance']))
        #     selected_fids.append(building['feature_obj'].id())

        for idx, node in enumerate(top_3_nodes):
            #feedback.pushInfo(str(building))
            feedback.pushInfo('#{0} - {2}, {1}, cost={3:.2f}, reward={4:.3f}'.format(idx+1, 
                                node[1]['NAME'], node[1]['BUILD_NO'], node[2], node[3]))
            selected_fids.append(node[1].id())
            
        layer.select(selected_fids)
        feedback.pushInfo("-----")
        feedback.pushInfo("STOPPING SCRIPT TO AVOID CREATING NEW LAYER")
        feedback.pushInfo("-----")
        raise SoftHalt()
        
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
                        if feature['MR_WEIGHTS'] != QVariant():
                            data_obj['weight'] = feature['MR_WEIGHTS']
                            weights.append(data_obj['weight'])
                            distances.append(data_obj['distance'])
                            select_buildings.append(feature.id())
                            nearest_buildings_info.append(data_obj)
                    # Toilet facilities objective
                    elif objective == 1:
                        # add buildings for which weights exists
                        if feature['TR_WEIGHTS'] != QVariant():
                            data_obj['weight'] = feature['TR_WEIGHTS']
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

    # CSP using anytime orienteering
    def find_building_algorithm_AOr(self, 
                                    current_building, radius,
                                    objective):
        
        layer = self.layer
        search_key = self.search_key
        
        # budget
        B = radius
        
        # Find target building geometry
        startingFeature = None
        for feature in layer.getFeatures():
            if str(feature[search_key]) == str(current_building):
                print(feature["NAME"])
                startingFeature = feature
                #x = targetGeometry.asMultiPolygon()
                #print("MultiPolygon: ", x, "Area: ", targetGeometry.area())
                break
        
        if objective == 0:
            targetRewardKey = "MR_WEIGHTS"
        elif objective == 1:
            targetRewardKey = "TR_WEIGHTS"
            
        # build graph
        # < startingNode, nextbuilding, distance, reward >
        graph = []
        startingFeatureGEOM = startingFeature.geometry()
        for feature in layer.getFeatures():
            if feature.id() != startingFeature.id():
                dist = feature.geometry().distance(startingFeatureGEOM)
                reward = feature[targetRewardKey]
                if feature[targetRewardKey] == None:
                    reward = 0
                node = (startingFeature, feature, dist, reward)
                graph.append(node)
        
        # CST - simple algo
        
        best_3_nodes = []
        
        while len(best_3_nodes) < 3:
            r_best = 0
            r_node = ()
            for node in graph:
                # sample a node
                v_s, v_e, routeLength, reward = node
                #if routeLength <= B:
                    #print(v_e['BUILD_NO'], v_e['NAME'], routeLength, reward)
                if routeLength <= B and reward > r_best and node not in best_3_nodes:
                    r_best = reward
                    r_node = node
            #print(r_node)
            best_3_nodes.append(r_node)
            #break
        
        #for node in best_3_nodes:
            #print(node[1]['NAME'])
            #print(node[1]['BUILD_NO'])
                
        return best_3_nodes