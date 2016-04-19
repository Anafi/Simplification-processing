#general imports
import networkx as nx
from qgis.core import *
import os
from PyQt4.QtCore import QVariant
import processing

#general inputs
all_new_points=[] #pseudo variable
lines_modified=[] #pseudo variable
network=iface.mapCanvas().currentLayer()

"""00. Simplify intersections"""
#output all_new_points (<network points)=[p1,p2,p3] tuples
#output lines_modified

"""01. Create a copy of the vector layer with merged lines into polylines"""
#Add column modified/not modified lines because lines will be merged
network.startEditing()
pr = network.dataProvider()
pr.addAttributes([QgsField("modified", QVariant.String)])
network.commitChanges()

fieldIdx = pr.fields().indexFromName("modified")
updateMap = {}
lines_not_modified=[f.id() for f in network.getFeatures() if f.id() not in lines_modified]

network.removeSelection()
network.select(lines_modified)
for f in network.selectedFeatures():
    fid=f.id()
    updateMap[fid] = { fieldIdx: "modified"}

network.removeSelection()
network.select(lines_not_modified)
for f in network.selectedFeatures():
    fid=f.id()
    updateMap[fid] = { fieldIdx: "not_modified"}

pr.changeAttributeValues( updateMap )
network.removeSelection()

#create a copy of the network as a new vector layer
crs=network.crs()
network_filepath = network.dataProvider().dataSourceUri()
(myDirectory,nameFile) = os.path.split(network_filepath)
new_path = myDirectory+"/Foregr_s_inter_subgraphs2.shp"

pr = network.dataProvider()
Foregr_s_inter_subgraphs2_writer= QgsVectorFileWriter(new_path, "UTF-8", pr.fields() ,pr.geometryType(), pr.crs() , "ESRI Shapefile")

if Foregr_s_inter_subgraphs2_writer.hasError() != QgsVectorFileWriter.NoError:
    print "Error when creating shapefile: ", Foregr_s_inter_subgraphs2_writer.errorMessage()

del Foregr_s_inter_subgraphs2_writer

Foregr_s_inter_subgraphs2 = iface.addVectorLayer(new_path, "Foregr_s_inter_subgraphs2", "ogr")
if not Foregr_s_inter_subgraphs2:
  print "Layer failed to load!"

Foregr_s_inter_subgraphs2.startEditing()
Foregr_s_inter_subgraphs2.addFeatures([x for x in network.getFeatures()])
Foregr_s_inter_subgraphs2.commitChanges()
Foregr_s_inter_subgraphs2.removeSelection()

network.startEditing()
network.deleteAttributes([fieldIdx])
network.commitChanges()

#Merge lines from intersection to intersection
#make a graph of the memory layer
G=nx.Graph()
for f in Foregr_s_inter_subgraphs2.getFeatures():
    f_geom=f.geometry()
    id=f.id()
    p0=f_geom.asPolyline()[0]
    p1=f_geom.asPolyline()[-1]
    G.add_edge(p0,p1,{'fid':id})

Dual_G=nx.MultiGraph()
for e in G.edges_iter(data='fid'):
    Dual_G.add_node(e[2])

for i,j in G.adjacency_iter():
    if len(j)==2:
        values=[]
        for k,v in j.items():
            values.append(v['fid'])
        Dual_G.add_edge(values[0],values[1],data=None)

#find connected components of the Dual graph and make sets
from networkx import connected_components
#lines with three connections have been included, breaks at intresections
#set also include single edges
sets=[]
for set in connected_components(Dual_G):
    sets.append(list(set))

#make a dictionary of all feature ids and corresponding geometry
D={}
for f in Foregr_s_inter_subgraphs2.getFeatures():
    fid=f.id()
    f_geom=f.geometry()
    D[fid]=f_geom

#make a dictionary of sets of geometries to be combined and sets of ids to be combined
Geom_sets={}
for set in sets:
    Geom_sets[tuple(set)]=[]

for k,v in Geom_sets.items():
    geoms=[]
    for i in k:
        i_geom=D[i]
        geoms.append(i_geom)
    Geom_sets[k]=tuple(geoms)

"""write new vector layer with combined geom"""

AdjD={}
for (i, v) in Dual_G.adjacency_iter():
    AdjD[i]=v

sets_in_order=[]
for set in sets:
    ord_set=[]
    nodes_passed=[]
    if len(set)==2 or len(set)==1:
        ord_set=set
        sets_in_order.append(ord_set)
    else:
        for n in set:
            if len(AdjD[n])==1 or len(AdjD[n])>2:
                first_line=n
            else:
                pass
        ord_set=[]
        nodes_passed.append(first_line)
        ord_set.append(first_line)
        for n in ord_set:
            nodes=AdjD[n].keys()
            for node in nodes:
                if node in nodes_passed:
                    pass
                else:
                    nodes_passed.append(node)
                    ord_set.append(node)
        sets_in_order.append(ord_set)

#make a dictionary of all feature ids and corresponding geometry
D={}
A={}
for f in Foregr_s_inter_subgraphs2.getFeatures():
    fid=f.id()
    f_geom=f.geometryAndOwnership()
    D[fid]=f_geom
    A[fid]=f.attributes()

#include in sets ord the geometry of the feature
for set in sets_in_order:
    for indx,i in enumerate(set):
        ind=indx
        line=i
        set[indx]= [line,D[line]]

#combine geometries
New_geoms=[]
for set in sets_in_order:
    new_geom=None
    if len(set)==1:
        new_geom=set[0][1]
        new_attr=A[set[0][0]]
    elif len(set)==2:
        line1_geom=set[0][1]
        line2_geom=set[1][1]
        new_geom=line1_geom.combine(line2_geom)
        if A[set[0][0]][-1]=="modified":
            new_attr=A[set[0][0]]
        elif A[set[1][0]][-1]=="modified":
            new_attr=A[set[1][0]]
        else:
            new_attr=A[set[0][0]]
    else:
        new_attr=A[set[0][0]]
        for ind,z in enumerate(set):
            if any(A[z[0]][-1]=="modified" for t in set[0]):
                new_attr=A[set[ind][0]]
            else:
                new_attr=A[set[0][0]]
        for i,line in enumerate(set):
            ind=i
            l=line
            if ind==(len(set)-1):
                pass
            else:
                l_geom=set[ind][1]
                next_l=set[(ind+1)%len(set)]
                next_l_geom=set[(ind+1)%len(set)][1]
                new_geom=l_geom.combine(next_l_geom)
                set[(ind+1)%len(set)][1]=new_geom
    New_geoms.append([new_geom,new_attr])

#delete all features and recreate memory layer with new geometries
Foregr_s_inter_subgraphs2.removeSelection()
Foregr_s_inter_subgraphs2.startEditing()
Foregr_s_inter_subgraphs2.selectAll()
Foregr_s_inter_subgraphs2.deleteSelectedFeatures()
Foregr_s_inter_subgraphs2.commitChanges()

New_feat=[]
#reconstruct new geometries
for i in New_geoms:
    feature = QgsFeature()
    feature.setGeometry(i[0])
    feature.setAttributes(i[1])
    New_feat.append(feature)

Foregr_s_inter_subgraphs2.startEditing()
Foregr_s_inter_subgraphs2.addFeatures(New_feat)
Foregr_s_inter_subgraphs2.commitChanges()
Foregr_s_inter_subgraphs2.removeSelection()

feat_to_del=[]
New_feat=[]
for f in Foregr_s_inter_subgraphs2.getFeatures():
    f_geom_type = f.geometry().wkbType()
    f_id = f.id()
    attr=f.attributes()
    if f_geom_type == 5:
        new_geoms = f.geometry().asGeometryCollection()
        for i in new_geoms:
            new_feat = QgsFeature()
            new_feat.setGeometry(i)
            new_feat.setAttributes(attr)
            New_feat.append(new_feat)
        feat_to_del.append(f_id)

Foregr_s_inter_subgraphs2.removeSelection()
Foregr_s_inter_subgraphs2.select(feat_to_del)
Foregr_s_inter_subgraphs2.startEditing()
Foregr_s_inter_subgraphs2.deleteSelectedFeatures()
Foregr_s_inter_subgraphs2.commitChanges()
Foregr_s_inter_subgraphs2.startEditing()
Foregr_s_inter_subgraphs2.addFeatures(New_feat)
Foregr_s_inter_subgraphs2.commitChanges()


request = QgsFeatureRequest().setFilterExpression(u'"modified" = \'modified\'')
lines_modified_merged=[x.id() for x in Foregr_s_inter_subgraphs2.getFeatures(request)]

network=Foregr_s_inter_subgraphs2

"""02. Find parallel lines"""
#D[id]=[(p0),(p1)]
D={}
for feat in network.getFeatures():
    D[feat.id()]=[(feat.geometry().asPolyline()[0][0],feat.geometry().asPolyline()[0][1]),
                  (feat.geometry().asPolyline()[-1][0], feat.geometry().asPolyline()[-1][1])]

#find self_loops
self_loops_ids=[]
for k,v in D.items():
    if v[0]==v[1]:
        self_loops_ids.append(k)

#find edges of the system
#make a graph (add edges as tuple-tuple)
G=nx.MultiGraph()
for f in network.getFeatures():
    f_geom=f.geometry()
    id=f.id()
    p0=(f_geom.asPolyline()[0][0],f_geom.asPolyline()[0][1])
    p1=(f_geom.asPolyline()[-1][0],f_geom.asPolyline()[-1][1])
    #G.add_edge(p0,p1,{'fid':id})
    G.add_edge(p0,p1,fid=id)

#find parallel lines below threshold
import math
import itertools
parallel_lines=[]
angle_threshold=30
for k,v in G.adjacency_iter():
    if len(v)>1:
        point=k
        star_edges=[]
        Dual_G_edges=[]
        for i,j in v.items():
            star_edges.append(j[0]['fid'])
        for elem in range(0,len(star_edges)+1):
            for subset in itertools.combinations(star_edges,elem):
                if len(subset)==2:
                    Dual_G_edges.append(subset)
        for pair in Dual_G_edges:
            for f in D[pair[0]]:
                if f!=point:
                    line_1_p=f
            for t in D[pair[1]]:
                if t!=point:
                    line_2_p= t
            if (line_1_p[0]>point[0] and line_2_p[0]<point[0]) or (line_1_p[0]<point[0] and line_2_p[0]>point[0]):
                pass
            elif line_1_p==line_2_p :
                parallel_lines.append(pair[0])
                parallel_lines.append(pair[1])
            else:
                #find angle between two_lines
                if abs(line_1_p[1])>abs(line_2_p[1]):
                    A=line_1_p
                    B=line_2_p
                else:
                    A=line_2_p
                    B=line_1_p
                O=point
                AOK=math.asin(abs(A[1]-O[1])/abs(math.hypot(abs(O[0]-A[0]),abs(O[1]-A[1]))))
                BOL=math.asin(abs(B[1]-O[1])/abs(math.hypot(abs(O[0]-B[0]),abs(O[1]-B[1]))))
                if A[1]>O[1] and B[1]<O[1]:
                    angle=math.degrees(AOK)+math.degrees(BOL)
                else:
                    angle=math.degrees(AOK)-math.degrees(BOL)
                if angle<=angle_threshold:
                    parallel_lines.append(pair[0])
                    parallel_lines.append(pair[1])


network.removeSelection()
network.select(parallel_lines)

"""03. Filter edges to subgraph and filter points to subgraph"""
Sub_parallel=nx.MultiGraph()
Sub_parallel_edges=[]
#make a copy of the graph
#TO DO: try G_copy.remove_edges_from([])
for i in G.edges(data=True):
    if i[2]['fid'] in parallel_lines:
        Sub_parallel_edges.append((i[0],i[1],i[2]['fid']))

for i in Sub_parallel_edges:
    Sub_parallel.add_edge(i[0],i[1],fid=i[2])

nodes_subgraph=[]
for i in Sub_parallel.nodes():
    nodes_subgraph.append(i)

#make Dual_G of Sub_parallel
Sub_parallel_dual=nx.MultiGraph()

Sub_Dual_G_edges=[]
for i,j in Sub_parallel.adjacency_iter():
    edges=[]
    if len(j)>1:
        #print j
        for k,v in j.items():
            edges.append(v[0]['fid'])
            #print edges
        for elem in range(0,len(edges)+1):
            for subset in itertools.combinations(edges,elem):
                if len(subset)==2:
                    #print subset
                    Sub_Dual_G_edges.append(subset)

for i in Sub_Dual_G_edges:
    Sub_parallel_dual.add_edge(i[0],i[1],data=None)

sets=[]
for i in connected_components(Sub_parallel_dual):
    sets.append(list(i))

full_sets=[]
for i in sets:
    endpoints=[]
    for j in i:
        if D[j][0] not in endpoints:
            endpoints.append(D[j][0])
        if D[j][1] not in endpoints:
            endpoints.append(D[j][1])
    connected_lines=[]
    for feat in network.getFeatures():
        if (feat.geometry().asPolyline()[0][0],feat.geometry().asPolyline()[0][1]) in endpoints and (feat.geometry().asPolyline()[-1][0],feat.geometry().asPolyline()[-1][1]) in endpoints and feat.id() not in i:
            connected_lines.append(feat.id())
    full_sets.append(i+connected_lines)

f=[]
for i in full_sets:
    for j in i:
        if j not in f:
            f.append(j)

not_f=[]
for i in network.getFeatures():
    if i.id() not in f and i.id() not in self_loops_ids:
        not_f=i.id()

"""04. Make a new vector layer with edges_subgraph and network exploded"""
#explode selection
#processing.alghelp("qgis:explodelines")
#ALGORITHM: Explode lines
#    INPUT <ParameterVector>
#    OUTPUT <OutputVector>

network_filepath = network.dataProvider().dataSourceUri()
(myDirectory,nameFile) = os.path.split(network_filepath)
new_path = myDirectory+"/Parallel_lines"
new_path_expl= myDirectory+"/Parallel_lines_expl"

pr = network.dataProvider()
Parallel_lines_writer= QgsVectorFileWriter(new_path, "UTF-8", pr.fields() ,pr.geometryType(), pr.crs() , "ESRI Shapefile")

if Parallel_lines_writer.hasError() != QgsVectorFileWriter.NoError:
    print "Error when creating shapefile: ", Parallel_lines_writer.errorMessage()

short_paths = QgsVectorLayer(new_path, "short_paths_expl" , "ogr")
QgsMapLayerRegistry.instance().addMapLayer(short_paths)

network.removeSelection()
network.select(f)

New_feat=[]
for f in network.selectedFeatures():
    fet = QgsFeature()
    fet.setGeometry(QgsGeometry().fromPoint(QgsPoint(i[0],i[1])))
    fet.setAttributes (f.attributes())
    New_feat.append(fet)

pr=short_paths.dataProvider()
short_paths.addFeatures(New_feat)

processing.runandload("qgis:explodelines",network,new_path_expl)

"""Make groups to subgraph"""
network=iface.mapCanvas().currentLayer()

G=nx.Graph()
for f in network.getFeatures():
    f_geom=f.geometry()
    id=f.id()
    p0=f_geom.asPolyline()[0]
    p1=f_geom.asPolyline()[-1]
    G.add_edge(p0,p1,{'fid':id})

groups=[]
for i in connected_components(G):
    groups.append(list(i))

def PointEquality(vertex1,vertex2):
    return ((abs(vertex1[0] - vertex2[0]) < 0.000001) and
            (abs(vertex1[1] - vertex2[1]) < 0.000001))
unique_paths=[]
for i in groups:
    sub_graph=G.subgraph(i)
    paths=[]
    new_point_nodes=[]
    for n in sub_graph.nodes():
        for k in all_new_points:
            if PointEquality(k,n):
                if n not in new_point_nodes:
                    new_point_nodes.append(n)
        if sub_graph.degree(n)==1:
            if n not in new_point_nodes:
                new_point_nodes.append(n)
    if len(new_point_nodes)>1:
        for j in itertools.combinations(new_point_nodes,2):
            if nx.has_path(sub_graph,source=j[0],target=j[1]):
            #find shortest_path
                paths.append(nx.shortest_path(sub_graph,source=j[0], target=j[1]))
        for path in paths:
            times=0
            for p in path:
                if p in new_point_nodes:
                    times+=1
            if times<3:
                unique_paths.append(path)


endpoints_to_keep=[]
for path in unique_paths:
    for i in path:
        if i not in endpoints_to_keep:
            endpoints_to_keep.append(i)


features_to_keep=[]
for i in network.getFeatures():
    p0=(i.geometry().asPolyline()[0][0], i.geometry().asPolyline()[0][1])
    p1=(i.geometry().asPolyline()[-1][0], i.geometry().asPolyline()[-1][1])
    b1=False
    b2=False
    for j in endpoints_to_keep:
        if PointEquality(p0,j):
            b1=True
    for k in endpoints_to_keep:
        if PointEquality(p1,k):
            b2=True
    if b1 and b2:
        features_to_keep.append(i.id())

network.removeSelection()
network.select(features_to_keep)