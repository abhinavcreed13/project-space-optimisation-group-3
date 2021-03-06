##from pip._internal import main as pip
##pip(['install', '--user', 'scikit-learn'])

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
        
from qgis.core import QgsProject
import pandas as pd
import matplotlib.pyplot as plt
from numpy import unique
from numpy import where
import numpy as np
from sklearn.cluster import KMeans
from sklearn.cluster import Birch
from sklearn.cluster import MiniBatchKMeans
from sklearn.cluster import AgglomerativeClustering
from sklearn.mixture import GaussianMixture

campus_code = "PAR"
layer_name = "PAR_BUILDING_OUTLINE_WITH_DATA"
search_key = "BUILD_NO"
objective = 0
layer = QgsProject.instance().mapLayersByName(layer_name)[0]
features = layer.getFeatures()
layer_provider = layer.dataProvider()

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

stats = DataStats(layer)

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
    
    
def get_all_clustering_results(data):
    f = plt.figure()
    f, axes = plt.subplots(nrows = 3, ncols = 2,figsize=(5, 15))
    f.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=None, hspace=1)
    
    X = data.to_numpy()
    model = KMeans(n_clusters=3,init='k-means++')
    model.fit(X)
    yhat = model.fit_predict(X)
    clusters = unique(yhat)
    print('----------KMeans---------- \n')
    get_building(model,X)
    for cluster in clusters:
        row_ix = where(yhat == cluster)
        axes[0][0].scatter(X[row_ix, 0], X[row_ix, 1])
    axes[0][0].set_xlabel('Cost')
    axes[0][0].set_ylabel('Reward')
    axes[0][0].title.set_text('Kmeans')
    axes[0][0].legend(clusters,loc="upper right")
   
    model_B = Birch(threshold=0.01, n_clusters=3)
    model_B.fit(X)
    yhat = model_B.predict(X)
    clusters = unique(yhat)
    print('\n----------BIRCH---------- ')
    get_building(model_B,X)
    for cluster in clusters:
        row_ix = where(yhat == cluster)
        axes[0][1].scatter(X[row_ix, 0], X[row_ix, 1])
    axes[0][1].set_xlabel('Cost')
    axes[0][1].set_ylabel('Reward')
    axes[0][1].legend(clusters,loc="upper right")
    axes[0][1].title.set_text('Birch')
    
    model_A = AgglomerativeClustering(n_clusters=3,linkage="ward")
    yhat = model_A.fit_predict(X)
    clusters = unique(yhat)
    print('\n----------Agglomerative Clustering----------')
    get_building(model_A,X)
    
    for cluster in clusters:
        row_ix = where(yhat == cluster)
        axes[1][0].scatter(X[row_ix, 0], X[row_ix, 1])
    axes[1][0].set_xlabel('Cost')
    axes[1][0].set_ylabel('Reward')
    axes[1][0].legend(clusters,loc="upper right")
    axes[1][0].title.set_text('Agglomerative Clustering')
    
    
    model_G = GaussianMixture(n_components=3)
    model_G.fit(X)
    yhat = model_G.predict(X)
    clusters = unique(yhat)
    print('\n----------Gaussian Mixture Models----------')
    get_building_GMM(model_G,yhat,X)
    
    for cluster in clusters:
        row_ix = where(yhat == cluster)
        axes[1][1].scatter(X[row_ix, 0], X[row_ix, 1])
    axes[1][1].set_xlabel('Cost')
    axes[1][1].set_ylabel('Reward')
    axes[1][1].legend(clusters,loc="upper right")
    axes[1][1].title.set_text('Gaussian Mixture Models')
    
    
    model_M = MiniBatchKMeans(n_clusters=3)
    model_M.fit(X)
    yhat = model_M.predict(X)
    clusters = unique(yhat)
    print('\n----------Mini Kmeans----------')
    get_building(model_M,X)
    for cluster in clusters:
        row_ix = where(yhat == cluster)
        axes[2][0].scatter(X[row_ix, 0], X[row_ix, 1])
    axes[2][0].set_xlabel('Cost')
    axes[2][0].set_ylabel('Reward')
    axes[2][0].legend(clusters,loc="upper right")
    axes[2][0].title.set_text('Mini Kmeans')
    
    axes[2][1].axis('off')
  
    
    
    
    
    
    
    
    plt.show()

def get_building_GMM(model,yhat,data):
    cluster_info = {}
    points = {index: np.where(yhat == index)[0] for index in range(3)}
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
        min_distance = cluster_info[cluster]['xmin']
        max_distance = cluster_info[cluster]['xmin']+100
        max_reward = -99
        delta = -99
        for index,value in enumerate(points[cluster]):
            if data[value,0] <= max_distance and data[value,1] > max_reward:
                max_reward = data[value,1]
                delta = data[value,0] - min_distance
        print('delta',delta)
        
                
        print('Range for optimum building is : {min1} to {max1} meters with avegrage reward {re}.'.format(
            min1=str(cluster_info[cluster]['xmin']), max1 = str(cluster_info[cluster]['xmax']), re = str(np.round(cluster_info[cluster]['avg'],2)) ))


def get_building(model,data):
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
        min_distance = cluster_info[cluster]['xmin']
        max_distance = cluster_info[cluster]['xmin']+100
        max_reward = -99
        delta = -99
        for index,value in enumerate(points[cluster]):
            if data[value,0] <= max_distance and data[value,1] > max_reward:
                max_reward = data[value,1]
                delta = data[value,0] - min_distance
        print('delta',delta)
        
                
        print('Range for optimum building is : {min1} to {max1} meters with avegrage reward {re}.'.format(
            min1=str(cluster_info[cluster]['xmin']), max1 = str(cluster_info[cluster]['xmax']), re = str(np.round(cluster_info[cluster]['avg'],2)) ))

      
starting_node = '161'
for feature in layer.getFeatures():
    if str(feature[search_key]) == str(starting_node):
        print(feature["NAME"])
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
    cost.append(get_cost(v_s, v_i))
    reward.append(get_reward(v_i, objective, {}
#    {'COVID_LOCKDOWN': 'High'}
    ))
df['COST']= cost
df['REWARD'] = reward

get_all_clustering_results(df)
