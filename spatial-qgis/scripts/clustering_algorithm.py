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
import pandas as pd
import matplotlib.pyplot as plt
from numpy import unique
from numpy import where
import numpy as np
from sklearn.cluster import KMeans
from qgis.core import QgsProject

class SoftHalt (Exception):
    def __init__ (self):
        sys.tracebacklimit = 0


class ClusteringAlgo(QgsProcessingAlgorithm):
    
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
    SEARCH_KEY = "search_key"
    CURRENT_BUILDING = "current_building"
    OBJECTIVE = "objective"
    WITH_EQUIPMENTS = "WITH_EQUIPMENTS"
    HIGH_CAPACITY = "HIGH_CAPACITY"
    COVID_LOCKDOWN = "COVID_LOCKDOWN"
    ROOM_CONDITION = "ROOM_CONDITION"
    REQUIRED_CAPACITY = "REQUIRED_CAPACITY"
    EASY_AVAILABILITY = "EASY_AVAILABILITY"
    SCATTER_PLOT = "SCATTER_PLOT"

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return ClusteringAlgo()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'clusteringScript'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('clustering Script')

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
        return 'clustering Script'

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr("")
        
    
    

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
        
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SCATTER_PLOT,
                'Enable Plot ?',
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
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
        
        scatter_plot_enabled = self.parameterAsBoolean(
            parameters,
            self.SCATTER_PLOT,
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
            
        # using provided layer - connected via reference
        layer = source
        stats = DataStats(layer)
        obj = Cluster(feedback)

        for feature in layer.getFeatures():
            if str(feature[search_key]) == str(current_building):
                feedback.pushInfo("-----" + '\n')
                feedback.pushInfo('Starting Building: ' +feature["NAME"] + '\n')
                startingFeature = feature
                break
        graph = []
        for feature in layer.getFeatures():
            if feature.id() != startingFeature.id():
                node = (startingFeature, feature)
                graph.append(node)
        df = pd.DataFrame()
        cost = []
        reward = []
        for node in graph:
            v_s, v_i = node
            cost.append(obj.get_cost(v_s, v_i))
            reward.append(obj.get_reward(v_i, objective, factors))
        df['COST']= cost
        df['REWARD'] = reward
        
        obj.KMEANS(df,scatter_plot_enabled)
        
        feedback.pushInfo("-----")
        feedback.pushInfo("STOPPING SCRIPT TO AVOID CREATING NEW LAYER")
        feedback.pushInfo("-----")
        raise Exception(" --- IGNORE ---")


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


class Cluster():
    def __init__(self, feedback):
        self.feedback = feedback

    def get_reward(self,node, objective, factors):
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
    
    
    def get_cost(self,node1, node2):
        return node2.geometry().distance(node1.geometry())
    
    def KMEANS(self,data,show_plot = False):
        X = data.to_numpy()
        model = KMeans(n_clusters=3,init='k-means++')
        model.fit(X)
        yhat = model.fit_predict(X)
        clusters = unique(yhat)
        self.get_building(model,X)
        if show_plot :
            for cluster in clusters:
                row_ix = where(yhat == cluster)
                plt.scatter(X[row_ix, 0], X[row_ix, 1])
            plt.title('KMEANS')
            plt.legend(clusters)
            plt.show()
        else:
            pass
    
    def get_building(self,model,data):
        cluster_info = {}
        points = {index: np.where(model.labels_ == index)[0] for index in range(model.n_clusters)}
        for index,key in enumerate(points):
            x  = [] 
            y = []
        for index,value in enumerate(points[key]):
            x.append(data[value,0])
            y.append(data[value,1])
          
        cluster_info[key] = {
            'ymin':np.round(min(y),4),
            'ymax':np.round(max(y),4),
            'xmin':np.round(min(x),4),
            'xmax':np.round(max(x),4),
            'avg' :np.average(y)
        }
        avg = -9999
        cluster = 9999
        for index,key in enumerate(cluster_info):
            if cluster_info[key]['avg'] > avg:
              avg = cluster_info[key]['avg']
              cluster = key
        if (cluster == 9999):
            pass
        else:
            self.feedback.pushInfo('Range for optimum building is : {min1} to {max1} meters with avegrage reward {re}.'.format(
            min1=str(cluster_info[cluster]['xmin']), max1 = str(cluster_info[cluster]['xmax']), re = str(np.round(cluster_info[cluster]['avg'],2)) ))
            self.feedback.pushInfo("-----" + '\n')
