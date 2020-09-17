## -- Spatial Prediction Algorithm --

from PyQt5.QtGui import QColor
import numpy as np
from scipy.special import softmax
from heapq import nlargest
from random import randint
import heapq

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

def normalize_data(data):
    return (data - np.min(data)) / (np.max(data) - np.min(data))

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
                
def non_randomized_AoR(layer, search_key, 
    current_building, radius,
    objective, k=3, factors = {}, stats = None):
    
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
    
    # build graph
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
                
            # factors adjustments
            if "WITH_EQUIPMENTS" in factors:
                if factors["WITH_EQUIPMENTS"]:
                    if node["EQP_CNT"]:
                        total_eqp = stats.total_equipments
                        adj = node["EQP_CNT"]/total_eqp
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
        return randint(1,99)
    
    # <reward, node>
    budget_nodes_queue = PriorityQueue()
    best_k = []
    for node in graph:
        # sample a node
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

def find_building_algorithm(layer, search_key, 
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
    # Step-0: Find target building geometry
    targetGeometry = None
    for feature in layer.getFeatures():
        if str(feature[search_key]) == str(current_building):
            print(feature["NAME"])
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
                elif objective == 1:
                    # add buildings for which weights exists
                    if feature['TR_WEIGHTS'] != QVariant():
                        data_obj['weight'] = feature['TR_WEIGHTS']
                        weights.append(data_obj['weight'])
                        distances.append(data_obj['distance'])
                        select_buildings.append(feature.id())
                        nearest_buildings_info.append(data_obj)
    
    # Step-3: data correlations - TODO
    #print(nearest_buildings_info)
    for b in nearest_buildings_info:
        print(b['building_id'])
        print(b['weight'])
        print(b['distance'])
    print("---")
    # Step-4: calculate probabilities
    # convert weights into probability distribution
    np_weights = np.array(weights)
    np_weights_probs = softmax(np_weights)
    #print(np_weights[0])
    #print(np_weights_probs)
    #print(np_weights_probs.shape)
    #print(np_weights_probs[0])
    
    np_dist = np.array(distances)
    np_dist_adjusted = normalize_data(np_dist)
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