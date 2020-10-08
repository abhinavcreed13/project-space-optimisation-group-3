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
                       QgsProcessingParameterMapLayer,
                       QgsProcessingParameterEnum)
from qgis import processing
import numpy as np
from qgis.utils import iface
from PyQt5.QtGui import QColor
from scipy.special import softmax
import sys
from random import randint
import heapq

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
    DELTA = "delta"
    OBJECTIVE = "objective"

    K = "K"
    WITH_EQUIPMENTS = "WITH_EQUIPMENTS"
    HIGH_CAPACITY = "HIGH_CAPACITY"
    COVID_LOCKDOWN = "COVID_LOCKDOWN"
    ROOM_CONDITION = "ROOM_CONDITION"
    REQUIRED_CAPACITY = "REQUIRED_CAPACITY"
    EASY_AVAILABILITY = "EASY_AVAILABILITY"

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
        return self.tr("Algorithm to find k-most optimal buildings based on different parameters and objectives")

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

        self.addParameter(
            QgsProcessingParameterEnum(
                self.OBJECTIVE,
                'Select objective',
                options=['Meeting Rooms','Toilet Facilities'],
                defaultValue=0)
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.SEARCH_KEY,
                'Enter building code column name',
                defaultValue="BUILD_NO"
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.CURRENT_BUILDING,
                'Enter building code from where you want predictions',
                defaultValue="104"
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.RADIUS,
                'Enter preferred radius in meters',
                defaultValue="200"
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.DELTA,
                'How much are you willing to relax your budget?',
                defaultValue="0"
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.K,
                'How many buildings to select?',
                defaultValue="5"
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.HIGH_CAPACITY,
                'Prioritize high capacity',
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.EASY_AVAILABILITY,
                'Prioritize easy availability',
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.WITH_EQUIPMENTS,
                'Prioritize meeting rooms with equipments',
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.COVID_LOCKDOWN,
                'COVID Lockdown Situation',
                options=['NA','Strict (0% - demand)','Medium (25% - demand)','Low (50% - demand)'],
                defaultValue=0)
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.ROOM_CONDITION,
                'Specific Room Condition',
                options=['NA','Excellent','Very Good','Good'],
                defaultValue=0)
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.REQUIRED_CAPACITY,
                'Do you have any specific capacity requirement?',
                defaultValue="NA"
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

        k = self.parameterAsString(
            parameters,
            self.K,
            context
        )

        radius = self.parameterAsString(
            parameters,
            self.RADIUS,
            context
        )

        delta = self.parameterAsString(
            parameters,
            self.DELTA,
            context
        )

        objective = self.parameterAsEnum(
            parameters,
            self.OBJECTIVE,
            context
        )

        with_equipments = self.parameterAsBoolean(
            parameters,
            self.WITH_EQUIPMENTS,
            context
        )

        high_capacity = self.parameterAsBoolean(
            parameters,
            self.HIGH_CAPACITY,
            context
        )

        easy_availability = self.parameterAsBoolean(
            parameters,
            self.EASY_AVAILABILITY,
            context
        )

        covid_lockdown = self.parameterAsEnum(
            parameters,
            self.COVID_LOCKDOWN,
            context
        )

        room_condition = self.parameterAsEnum(
            parameters,
            self.ROOM_CONDITION,
            context
        )

        required_capacity = self.parameterAsString(
            parameters,
            self.REQUIRED_CAPACITY,
            context
        )

        factors = {
            "HIGH_CAPACITY": high_capacity,
            "WITH_EQUIPMENTS": with_equipments,
            "EASY_AVAILABILITY": easy_availability
        }

        if covid_lockdown == 1:
            factors["COVID_LOCKDOWN"] = "High"
        elif covid_lockdown == 2:
            factors["COVID_LOCKDOWN"] = "Medium"
        elif covid_lockdown == 3:    
            factors["COVID_LOCKDOWN"] = "Low"

        if room_condition == 1:
            factors["ROOM_CONDITION"] = "Excellent"
        elif room_condition == 2:
            factors["ROOM_CONDITION"] = "Very Good"
        elif room_condition == 3:    
            factors["ROOM_CONDITION"] = "Good"

        if required_capacity != "NA":
            factors["REQUIRED_CAPACITY"] = int(required_capacity)

        feedback.pushInfo(str(factors))

        # using provided layer - connected via reference
        layer = source
        
        # create logic object
        _runner = PredictionAlgorithmLogic(feedback, layer, search_key)

        stats = DataStats(layer)

        top_k_nodes = _runner.find_building_algorithm_AOr(
                        int(current_building), 
                        int(radius), 
                        int(objective),
                        delta = int(delta),
                        k = int(k),
                        factors = factors, stats = stats)
        
        iface.mapCanvas().setSelectionColor(QColor("green"))
        selected_fids = []
        layer.removeSelection()
        feedback.pushInfo("")
        feedback.pushInfo("-- Top "+k+" Buildings Found --")
        
        # for idx, building in enumerate(top_3_buildings):
        #     #feedback.pushInfo(str(building))
        #     feedback.pushInfo('#{0} - {2}, {1}, {3:.2f} meters'.format(idx+1, building['building_name'], building['building_id'], building['distance']))
        #     selected_fids.append(building['feature_obj'].id())

        for idx, node_tuple in enumerate(top_k_nodes):
            #feedback.pushInfo(str(building))
            reward, cost, node = node_tuple
            feedback.pushInfo('#{0} - {2}, {1}, cost={3:.2f}, reward={4:.7f}'.format(idx+1, 
                                node['NAME'], node['BUILD_NO'], cost, reward))
            selected_fids.append(node.id())
            
        layer.select(selected_fids)
        feedback.pushInfo("-----")
        feedback.pushInfo("STOPPING SCRIPT TO AVOID CREATING NEW LAYER")
        feedback.pushInfo("-----")
        raise Exception(" --- IGNORE ---")

class PriorityQueue:
    """
      Implements a priority queue data structure. Each inserted item
      has a priority associated with it and the client is usually interested
      in quick retrieval of the lowest-priority item in the queue. This
      data structure allows O(1) access to the lowest-priority item.
    """
    def  __init__(self):
        self.heap = []
        self.count = 0

    def push(self, item, priority):
        entry = (priority, self.count, item)
        heapq.heappush(self.heap, entry)
        self.count += 1

    def pop(self):
        (_, _, item) = heapq.heappop(self.heap)
        return item

    def isEmpty(self):
        return len(self.heap) == 0

    def update(self, item, priority):
        # If item already in priority queue with higher priority, update its priority and rebuild the heap.
        # If item already in priority queue with equal or lower priority, do nothing.
        # If item not in priority queue, do the same thing as self.push.
        for index, (p, c, i) in enumerate(self.heap):
            if i == item:
                if p <= priority:
                    break
                del self.heap[index]
                self.heap.append((priority, c, item))
                heapq.heapify(self.heap)
                break
        else:
            self.push(item, priority)

class DataStats():
    
    def __init__(self, layer):
        # collect stats
        self.total_equipments = 0
        self.total_excellent_mr_cap = 0
        self.total_verygood_mr_cap = 0
        self.total_good_mr_cap = 0
        self.total_average_room_size = 0
        self.total_meetings = 0

        self.total_excellent_tr_cap = 0
        self.total_verygood_tr_cap = 0
        self.total_good_tr_cap = 0
        self.total_tr_average_room_size = 0
        self.total_duration_mins = 0

        for feature in layer.getFeatures():
            if feature["EQP_CNT"]:
                self.total_equipments += feature["EQP_CNT"]
            if feature["EX_MR_CAP"]:
                self.total_excellent_mr_cap += feature["EX_MR_CAP"]
            if feature["VG_MR_CAP"]:
                self.total_verygood_mr_cap += feature["VG_MR_CAP"]
            if feature["G_MR_CAP"]:
                self.total_good_mr_cap += feature["G_MR_CAP"]
            if feature["AG_MR_SZ"]:
                self.total_average_room_size += feature["AG_MR_SZ"]
            if feature["TOTAL_M"]:
                self.total_meetings += feature["TOTAL_M"]

            if feature["EX_TR_CAP"]:
                self.total_excellent_tr_cap += feature["EX_TR_CAP"]
            if feature["VG_TR_CAP"]:
                self.total_verygood_tr_cap += feature["VG_TR_CAP"]
            if feature["G_TR_CAP"]:
                self.total_good_tr_cap += feature["G_TR_CAP"]
            if feature["AG_TR_SZ"]:
                self.total_tr_average_room_size += feature["AG_TR_SZ"]
            if feature["AG_CL_DS"]:
                self.total_duration_mins += feature["AG_CL_DS"]
        
class PredictionAlgorithmLogic():

    def __init__(self, feedback, layer, search_key):
        self.feedback = feedback
        self.layer = layer
        self.search_key = search_key

    def normalize_data(self, data):
        return (data - np.min(data)) / (np.max(data) - np.min(data))

    # CSP using anytime orienteering
    def find_building_algorithm_AOr(self, 
                                    current_building, 
                                    radius,
                                    objective, 
                                    k=3, 
                                    factors = {}, 
                                    stats = None,
                                    delta=0):
        
        layer = self.layer
        search_key = self.search_key
        
        # budget
        B = radius
        
        # Find target building geometry
        startingFeature = None
        for feature in layer.getFeatures():
            if str(feature[search_key]) == str(current_building):
                #print(feature["NAME"])
                startingFeature = feature
                #x = targetGeometry.asMultiPolygon()
                #print("MultiPolygon: ", x, "Area: ", targetGeometry.area())
                break
        
        # build specialized graph
        # < startingNode, nextbuilding >
        graph = []
        for feature in layer.getFeatures():
            if feature.id() != startingFeature.id():
                node = (startingFeature, feature)
                #print(node[1]['TR_WEIGHTS'])
                graph.append(node)
        
        # Reward Function
        # Objective = 0
        # {
        #   REQUIRED_CAPACITY: <number>,
        #   COVID_LOCKDOWN: High/Medium/Low,
        #   HIGH_CAPACITY: True/False,
        #   EASY_AVAILABILITY: True/False,
        #   WITH_EQUIPMENTS: True/False,
        #   ROOM_CONDITION: Excellent/Very Good/Good
        # }
        # Objective = 1
        # {
        #   REQUIRED_CAPACITY: <number>,
        #   COVID_LOCKDOWN: High/Medium/Low,
        #   HIGH_CAPACITY: True/False,
        #   ROOM_CONDITION: Excellent/Very Good/Good
        # }
        def get_reward(node, objective, factors):
            if objective == 0:
                targetRewardKey = "MR_WEIGHTS"
                reward = node[targetRewardKey]
                if node[targetRewardKey] == None:
                    return 0

                if "REQUIRED_CAPACITY" in factors:
                    capacity = float(node["MR_CAP"])
                    if capacity < float(factors["REQUIRED_CAPACITY"]):
                        return 0

                if "COVID_LOCKDOWN" in factors:
                    situation = factors["COVID_LOCKDOWN"].lower()
                    if situation == "high":
                        # demand is 0
                        reward = float(node["MR_CAP"])
                    elif situation == "medium":
                        # demand is 25%
                        demand = node["EMP_CNT"] * 0.25
                        reward = float(node["MR_CAP"]/demand)
                    else:
                        # demand is 50%
                        demand = node["EMP_CNT"] * 0.50
                        reward = float(node["MR_CAP"]/demand)
                        
                if "HIGH_CAPACITY" in factors:
                    if factors["HIGH_CAPACITY"]:
                        if node["AG_MR_SZ"]:
                            adj = node["AG_MR_SZ"]/stats.total_average_room_size
                            reward = reward * adj
                        else:
                            reward = reward * 0
                            
                if "EASY_AVAILABILITY" in factors:
                    if factors["EASY_AVAILABILITY"]:
                        if node["TOTAL_M"]:
                            adj = node["TOTAL_M"]/stats.total_meetings
                            reward = reward * (1-adj)
                        else:
                            reward = reward * 0

                # factors adjustments
                if "WITH_EQUIPMENTS" in factors:
                    if factors["WITH_EQUIPMENTS"]:
                        if node["EQP_CNT"]:
                            total_eqp = stats.total_equipments
                            adj = node["EQP_CNT"]/total_eqp
                            reward = reward * adj
                        else:
                            reward = reward * 0

                # adjustments
                if "ROOM_CONDITION" in factors:
                    condition = factors["ROOM_CONDITION"].lower()
                    if condition == "excellent":
                        if node["EX_MR_CAP"]:
                            adj = node["EX_MR_CAP"]/stats.total_excellent_mr_cap
                            reward = reward * adj
                        else:
                            reward = reward * 0
                    elif condition == "verygood":
                        if node["VG_MR_CAP"]:
                            adj = node["VG_MR_CAP"]/stats.total_verygood_mr_cap
                            reward = reward * adj
                        else:
                            reward = reward * 0
                    elif condition == "good":
                        if node["G_MR_CAP"]:
                            adj = node["G_MR_CAP"]/stats.total_good_mr_cap
                            reward = reward * adj
                        else:
                            reward = reward * 0
                
                return reward
            
            elif objective == 1:
                targetRewardKey = "TR_WEIGHTS"
                reward = node[targetRewardKey]
                if node[targetRewardKey] == None:
                    return 0

                if "REQUIRED_CAPACITY" in factors:
                    capacity = float(node["TR_CAP"])
                    if capacity < float(factors["REQUIRED_CAPACITY"]):
                        return 0
                    
                if "COVID_LOCKDOWN" in factors:
                    situation = factors["COVID_LOCKDOWN"].lower()
                    if situation == "high":
                        # demand is 0
                        reward = float(node["TR_CAP"])
                    elif situation == "medium":
                        # demand is 25%
                        demand = node["STU_CNT"] * 0.05
                        reward = float(node["TR_CAP"]/demand)
                    else:
                        # demand is 50%
                        demand = node["STU_CNT"] * 0.50
                        reward = float(node["TR_CAP"]/demand)

                if "HIGH_CAPACITY" in factors:
                    if factors["HIGH_CAPACITY"]:
                        if node["AG_TR_SZ"]:
                            adj = node["AG_TR_SZ"]/stats.total_tr_average_room_size
                            reward = reward * adj
                        else:
                            reward = reward * 0

                if "EASY_AVAILABILITY" in factors:
                    if factors["EASY_AVAILABILITY"]:
                        if node["AG_CL_DS"]:
                            adj = node["AG_CL_DS"]/stats.total_duration_mins
                            reward = reward * (1-adj)
                        else:
                            reward = reward * 0

                if "ROOM_CONDITION" in factors:
                    condition = factors["ROOM_CONDITION"].lower()
                    if condition == "excellent":
                        if node["EX_TR_CAP"]:
                            adj = node["EX_TR_CAP"]/stats.total_excellent_tr_cap
                            reward = reward * adj
                        else:
                            reward = reward * 0
                    elif condition == "verygood":
                        if node["VG_TR_CAP"]:
                            adj = node["VG_TR_CAP"]/stats.total_verygood_tr_cap
                            reward = reward * adj
                        else:
                            reward = reward * 0
                    elif condition == "good":
                        if node["G_TR_CAP"]:
                            adj = node["G_TR_CAP"]/stats.total_good_tr_cap
                            reward = reward * adj
                        else:
                            reward = reward * 0
                    
                return reward
            
        def get_cost(node1, node2):
            return node2.geometry().distance(node1.geometry())
        
        def get_delta():
            return delta
        
        # <reward, cost, node>
        budget_nodes_queue = PriorityQueue()
        best_k = []
        for node in graph:
            v_s, v_i = node
            cost = get_cost(v_s, v_i)
            reward = get_reward(v_i, objective, factors)
            delta = get_delta()
            if cost <= B + delta:
                priority = -1 * reward
                budget_nodes_queue.push((reward, cost, v_i), priority)
            
        # get k-optimal nodes
        while not budget_nodes_queue.isEmpty():
            if len(best_k) == k:
                break
            best_k.append(budget_nodes_queue.pop())

        return best_k