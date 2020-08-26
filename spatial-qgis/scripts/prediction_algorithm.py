## -- Spatial Prediction Algorithm --

from PyQt5.QtGui import QColor
import numpy as np
from scipy.special import softmax

def normalize_data(data):
    return (data - np.min(data)) / (np.max(data) - np.min(data))

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
    
    
def find_building_algorithm_2(layer, search_key, 
    current_building, radius,
    objective):
    
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
        
        
        