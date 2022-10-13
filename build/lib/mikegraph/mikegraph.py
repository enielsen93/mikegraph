import networker
import networkx as nx
import os
import arcpy
import numpy as np
import warnings

class HParA:
    reduction_factor = None
    concentration_time = None

    def __init__(self, MUID):
        self.MUID = MUID

class Catchment:
    area = None
    persons = None

    imperviousness = None
    reduction_factor = None
    concentration_time = None
    connection = None
    nettypeno = None

    nodeID = None

    use_local_parameters = None

    def __init__(self, MUID):
        self.MUID = MUID

    @property
    def impervious_area(self):
        return self.area*self.imperviousness/1e2

    @property
    def reduced_area(self):
        return self.area*self.imperviousness/1e2*self.reduction_factor

class Graph:
    def __init__(self, MU_database, ignore_regulations = False, useMaxInFlow = False, remove_edges = False, map_only = "links"):
        self._is_mike_plus = True if ".sqlite" in MU_database else False
        
        MU_database = MU_database.replace(r"\mu_Geometry","")
        self.network = networker.NetworkLinks(MU_database, map_only = map_only)
        self._msm_Link = os.path.join(MU_database, "msm_Link")
        self._msm_Node = os.path.join(MU_database, "msm_Node")
        self._msm_Orifice = os.path.join(MU_database, "msm_Orifice")
        self._msm_Weir = os.path.join(MU_database, "msm_Weir")
        self._msm_Pump = os.path.join(MU_database, "msm_Pump")
        self._msm_CatchCon = os.path.join(MU_database, "msm_CatchCon")
        self._ms_Catchment = os.path.join(MU_database, "msm_Catchment") if self._is_mike_plus else os.path.join(MU_database, "ms_Catchment")
        self._msm_HParA = os.path.join(MU_database, "msm_HParA")
        self._ms_TabD = os.path.join(MU_database, "ms_TabD")
        self._msm_HModA = os.path.join(MU_database, "msm_HModA")
        self._msm_PasReg = os.path.join(MU_database, "msm_PasReg")
        self.ignore_regulations = ignore_regulations
        self.useMaxInFlow = useMaxInFlow
        self.remove_edges = remove_edges
        self.network_mapped = False
        self.maxInflow = {}

    def _read_catchments(self):
        self.catchments_dict = {}

        hParA_dict = {}
        with arcpy.da.SearchCursor(self._msm_HParA, ["MUID", "RedFactor", "ConcTime"]) as cursor:
            for row in cursor:
                hParA_dict[row[0]] = HParA(row[0])
                hParA_dict[row[0]].reduction_factor = row[1]
                hParA_dict[row[0]].concentration_time = row[2]

        self.msm_HModA_without_ms_Catchment = []

        if self._is_mike_plus:
            with arcpy.da.SearchCursor(self._ms_Catchment,
                                       ['MUID', 'SHAPE@AREA', 'Area', 'Persons', "NetTypeNo", "ModelAImpArea",
                                        "ModelAParAID", "ModelALocalNo", "ModelARFactor",
                                        "ModelAConcTime"]) as cursor:
                for row in cursor:
                    self.catchments_dict[row[0]] = Catchment(row[0])
                    self.catchments_dict[row[0]].persons = row[3] if row[3] is not None else 0
                    self.catchments_dict[row[0]].area = row[2] if row[2] is not None else abs(row[1])
                    self.catchments_dict[row[0]].nettypeno = row[4]
                    self.catchments_dict[row[0]].use_local_parameters = not bool(row[7])
                    self.catchments_dict[row[0]].imperviousness = row[5] * 1e2

                    try:
                        self.catchments_dict[row[0]].reduction_factor = (hParA_dict[row[6]].reduction_factor
                                                                         if not row[7] == 0 else row[8])
                        self.catchments_dict[row[0]].concentration_time = (hParA_dict[row[6]].concentration_time / 60.0
                                                                           if not row[7] == 0 else row[9] / 60.0)

                    except Exception as e:
                        self.catchments_dict[row[0]].concentration_time = 7
                        self.catchments_dict[row[0]].reduction_factor = 0
                        warnings.warn("%s not found in msm_HParA" % (row[6]))

            with arcpy.da.SearchCursor(self._msm_CatchCon, ["CatchID", "NodeID"]) as cursor:
                for row in cursor:
                    self.catchments_dict[row[0]].nodeID = row[1]

        else:
            with arcpy.da.SearchCursor(self._msm_HModA,
                                       ["CatchID", "ImpArea", "ParAID", "LocalNo", "RFactor", "ConcTime"]) as cursor:
                for row in cursor:
                    self.catchments_dict[row[0]] = Catchment(row[0])
                    self.catchments_dict[row[0]].imperviousness = row[1]

                    try:
                        self.catchments_dict[row[0]].reduction_factor = (hParA_dict[row[2]].reduction_factor
                                                                         if row[3] == 0 else row[4])
                        self.catchments_dict[row[0]].concentration_time = (hParA_dict[row[2]].concentration_time
                                                                       if row[3] == 0 else row[5])
                    except Exception as e:
                        self.catchments_dict[row[0]].concentration_time = 7
                        self.catchments_dict[row[0]].reduction_factor = 0
                        warnings.warn("%s not found in msm_HParA" % (row[2]))

            with arcpy.da.SearchCursor(self._msm_CatchCon, ["CatchID", "NodeID"]) as cursor:
                for row in cursor:
                    if row[0] in self.catchments_dict:
                        self.catchments_dict[row[0]].nodeID = row[1]

            with arcpy.da.SearchCursor(self._ms_Catchment, ['MUID', 'SHAPE@AREA', 'Area', 'Persons', "NetTypeNo"]) as cursor:
                for row in cursor:
                    if row[0] not in self.catchments_dict:
                        self.catchments_dict[row[0]] = Catchment(row[0])
                    self.catchments_dict[row[0]].persons = row[3] if row[3] is not None else 0
                    self.catchments_dict[row[0]].area = row[2] * 1e4 if row[2] is not None else row[1]
                    self.catchments_dict[row[0]].nettypeno = row[4]

    def map_network(self):
        self.graph = nx.DiGraph()
        for link in self.network.links.values():
            if link.fromnode and link.tonode:
                self.graph.add_edge(link.fromnode, link.tonode, weight = link.length)
            else:
                warnings.warn("Link %s is unconnected (%s-%s)" % (link.MUID, link.fromnode, link.tonode))
            
        if self.useMaxInFlow:
            with arcpy.da.SearchCursor(self._msm_Node, ["MUID", "InletControlNo", "MaxInlet"],
                                       where_clause="[MaxInlet] IS NOT NULL AND [InletControlNo] = 0") as cursor:
                for row in cursor:
                    self.maxInflow[row[0]] = row[2]

        self._read_catchments()

        if not self.ignore_regulations:
            ms_TabD_dict = {}
            with arcpy.da.SearchCursor(self._ms_TabD, ["TabID", "value2"],
                                       where_clause="active = 1" if self._is_mike_plus else "") as cursor:
                for row in cursor:
                    if row[0] not in ms_TabD_dict or row[1] > ms_TabD_dict[row[0]]:
                        ms_TabD_dict[row[0]] = row[1]

            if self._is_mike_plus:
                with arcpy.da.SearchCursor(self._msm_Link, ["MUID", "FunctionID"],
                           where_clause = "regulationtypeno = 1 AND FunctionID IS NOT NULL") as cursor:
                    for row in cursor:
                        if row[1] in ms_TabD_dict:
                            node = self.network.links[row[0]].tonode
                            self.maxInflow[node] = ms_TabD_dict[row[1]]
                            self.graph.remove_edge(self.network.links[row[0]].fromnode, self.network.links[row[0]].tonode)

            else:
                with arcpy.da.SearchCursor(self._msm_PasReg, ["LinkID", "FunctionID"], where_clause = "TypeNo = 1") as cursor:
                    for row in cursor:
                        if row[1] in ms_TabD_dict:
                            node = self.network.links[row[0]].tonode
                            self.maxInflow[node] = ms_TabD_dict[row[1]]
                            self.graph.remove_edge(self.network.links[row[0]].fromnode,
                                                   self.network.links[row[0]].tonode)
        if self.remove_edges:
            outlets = []
            junctions = []
            for node in list(self.network.nodes):
                if not self.network.out_edges(node):
                    outlets.append(node)
                if len(self.network.out_edges(node)) > 1:
                    junctions.append(node)

            for source in junctions:
                if source != None:
                    lengths = np.ones((len(outlets), 1)) * 1e6
                    for i, target in enumerate(outlets):
                        try:
                            if nx.has_path(self.network, source, target):
                                lengths[i] = (nx.bellman_ford_path_length(self.network, source, target, weight="weight"))
                        except:
                            arcpy.AddError("Failed upon tracing network from %s to %s" % (source, target))
                    try:
                        toNode = nx.bellman_ford_path(self.network, source, outlets[np.argmin(lengths)])[1]
                    except Exception as e:
                        arcpy.AddWarning(e.message)
                    for edge in self.network.out_edges(source):
                        if not edge[1] == toNode:
                            self.network.remove_edge(source, edge[1])
                            arcpy.AddMessage("Removed edge %s-%s so that node %s exclusively leads to outlet %s" % (
                            source, edge[1], source, outlets[np.argmin(lengths)]))
        self.network_mapped = True

    def find_upstream_nodes(self, nodes):
        if type(nodes) is str or type(nodes) is unicode:
            nodes = [nodes]
        if not self.network_mapped:
            self.map_network()

        upstream_nodes = [[]]*len(nodes)
        for target_i, target in enumerate(nodes):
            for source in self.graph.nodes:
                if source in self.graph and target in self.graph and nx.has_path(self.graph, source, target):
                    upstream_nodes[target_i].append(source)
        return upstream_nodes

    def find_connected_catchments(self, nodes):
        catchments = []
        for catchment in self.catchments_dict.values():
            if catchment.nodeID and catchment.nodeID in nodes:
                catchments.append(catchment)
        return catchments

    def travel_time(self, source, target):
        path = nx.shortest_path(self.graph, source, target)

        travel_time = 0

        for path_i in range(1, len(path)):
            travel_time += [link for link in self.network.links.values()
                            if link.fromnode == path[path_i - 1] and link.tonode == path[path_i]][0].travel_time
            link = [link for link in self.network.links.values()
                            if link.fromnode == path[path_i - 1] and link.tonode == path[path_i]][0]

        return travel_time

    def trace_between(self, nodes):
        links_in_path = set()
        nodes_in_path = set()
        for source in nodes:
            for target in nodes:
                if nx.has_path(self.graph, source, target):
                    path = nx.shortest_path(self.graph, source, target)
                elif nx.has_path(self.graph, target, source):
                    path = nx.shortest_path(self.graph, target, source)
                else:
                    path = None
                if path:
                    for path_i in range(1, len(path)):
                        links_in_path.add([link.MUID for link in self.network.links.values()
                         if link.fromnode == path[path_i - 1] and link.tonode == path[path_i]][0])
                        nodes_in_path.add(path[path_i - 1])
                        nodes_in_path.add(path[path_i])
        return nodes_in_path, links_in_path

if __name__ == "__main__":
    graf = Graph(r"C:\Users\ELNN\OneDrive - Ramboll\Documents\RWA2022N00174\Model\VOR_Plan_023\VOR_Plan_023.mdb")

    graf.map_network()

    # print(graf.trace_between(["O05930R", "O23910R"]))

    # print(graf.travel_time('O23119R',"O23114R"))
    targets = graf.find_upstream_nodes(["Node_163"])
    print(targets)
    # graph.find_connected_catchments(targets[0])
    # [catchment.MUID for catchment in graph.find_connected_catchments(targets[0])]

    # catchments = []
    # for catchment in graph.catchments_dict.values():
    #     if catchment.nodeID in targets[0]:
    #         catchments.append(catchment.MUID)