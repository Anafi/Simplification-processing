from qgis.core import *
from PyQt4.QtCore import QVariant
import processing
import csv
import os
import networkx as nx
import itertools

threshold_inter=0.0006
network=iface.mapCanvas().currentLayer()

#construct a normal graph from the merged netwrok
#you need to make a multi_graph(include self loops and paralel lines)
G=nx.MultiGraph()
for f in network.getFeatures():
    f_geom=f.geometry()
    id=f.id()
    p0=f_geom.asPolyline()[0]
    p1=f_geom.asPolyline()[-1]
    G.add_edge(p0,p1,fid=id)

#construct a dual graph with all connections
Dual_G=nx.MultiGraph()
for e in G.edges_iter(data='fid'):
    Dual_G.add_node(e[2]['fid'])

Dual_G_edges=[]
for i,j in G.adjacency_iter():
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
                    Dual_G_edges.append(subset)

for i in Dual_G_edges:
    Dual_G.add_edge(i[0],i[1],data=None)

#make a new temporary point layer at intersections

crs=network.crs()
Points=QgsVectorLayer('Point?crs='+crs.toWkt(),"temporary_points","memory")
QgsMapLayerRegistry.instance().addMapLayer(Points)
pr=Points.dataProvider()
Points.startEditing()
pr.addAttributes([QgsField("fid", QVariant.Int),
                      QgsField("x", QVariant.Double),
                      QgsField("y", QVariant.Double)])
Points.commitChanges()

#add point features at intersections of the network
nodes_passed=[]
features=[]
id=1
for i in network.getFeatures():
    g=[i.geometry().asPolyline()[0],i.geometry().asPolyline()[-1]]
    for i in g:
        if i not in nodes_passed:
            feat=QgsFeature()
            p=QgsPoint(i[0],i[1])
            feat.setGeometry(QgsGeometry().fromPoint(p))
            feat.setAttributes ([id,i[0],i[1]])
            features.append(feat)
            nodes_passed.append(i)
            id+=1

Points.startEditing()
pr.addFeatures(features)
Points.commitChanges()

#make a distance matrix of all points for the 10 closest neighbours
#get the path of the Points layer and make the path of th csv matrix
network_filepath= network.dataProvider().dataSourceUri()
(myDirectory,nameFile) = os.path.split(network_filepath)
csv_path=myDirectory+"/Matrix.csv"

processing.runalg("qgis:distancematrix", Points, "fid", Points,"fid",0, 10, csv_path)

#specify new short lines as new edges
New_edges=[]

with open(csv_path,'rb') as f:
    reader = csv.reader(f)
    your_list = list(reader)

#remove header
your_list.remove(['InputID', 'TargetID', 'Distance'])

for i in your_list:
    if float(i[2])<=threshold_inter and float(i[2])>0:
        if i[0]>=i[1]:
            New_edges.append([int(i[0]),int(i[1])])

#make a dictionary of point id and x,y coordinates
P_D={}
for i in Points.getFeatures():
    fid=i.id()
    x=i.attribute('x')
    y=i.attribute('y')
    P_D[fid]=(x,y)

#ATTENTION (*** from Merge lines plugin)
# First: GEOM does not check for duplicate vertices or intersecting lines.
# Second: QGis does, and simply uses '==' when comparing coordinates.
# However, if we use '==' here too (likewise when using the '==' operator
# for vertices), it will sometimes return "false" when the validity check
# in QGis would return "true". That's the reason for this function.

#make a dictionary with x,y coordinates of lines of the network layer and their id
Id_D={}
for f in network.getFeatures():
    Id_D[(f.geometry().asPolyline()[0],f.geometry().asPolyline()[-1])]=f.id()

feat_count=int(network.featureCount())
feat_count_init=int(network.featureCount())

new_attr=[]
for i in range(0,len(network.dataProvider().fields())):
    new_attr.append(NULL)

for t in New_edges:
    p1=P_D[t[0]]
    p2=P_D[t[1]]
    qp_1=QgsPoint(p1[0],p1[1])
    qp_2=QgsPoint(p2[0],p2[1])
    #if not((qp_1,qp_2) not in Id_D.keys()and (qp_2,qp_1) not in Id_D.keys()):
    #    print t[0],t[1]
    feat=QgsFeature()
    geom=QgsGeometry().fromPolyline([qp_1,qp_2])
    network.startEditing()
    feat.setGeometry(geom)
    feat.setAttributes(new_attr)
    network.addFeature(feat,True)
    network.commitChanges()
    #print i[0],i[1]

#clean duplicate geometries
geometries = {}
for f in network.getFeatures():
    geometries[f.id()]=f.geometry().asPolyline()

ids_to_del=[]
com_geom_pairs=[]
for i,j in geometries.items():
    if j!= None:
        for x,y in geometries.items():
            if j == y and i>x:
                ids_to_del.append(x)
            elif j==list(reversed(y)) and i>x:
                ids_to_del.append(x)

network.select(ids_to_del)

network.startEditing()
network.dataProvider().deleteFeatures(ids_to_del)
network.commitChanges()


#construct a normal graph from the merged netwrok
#you need to make a multi_graph(include self loops and paralel lines)
G=nx.MultiGraph()
for f in network.getFeatures():
    f_geom=f.geometry()
    id=f.id()
    p0=f_geom.asPolyline()[0]
    p1=f_geom.asPolyline()[-1]
    #G.add_edge(p0,p1,{'fid':id})
    G.add_edge(p0,p1,fid=id)

#construct a dual graph with all connections
Dual_G=nx.MultiGraph()
for e in G.edges_iter(data='fid'):
    #print e[2]
    Dual_G.add_node(e[2])

Dual_G_edges=[]
for i,j in G.adjacency_iter():
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
                    Dual_G_edges.append(subset)

for i in Dual_G_edges:
    Dual_G.add_edge(i[0],i[1],data=None)

ids_short=[]
for f in network.getFeatures():
    f_geom=f.geometry()
    l=f.geometry().length()
    id=f.id()
    if l<threshold_inter:
        ids_short.append(id)

Short_G=Dual_G.subgraph(ids_short)

Neighbours=[]
all_new_points=[]
lines_modified=[]
for i in nx.connected_components(Short_G):
    comp=list(i)
    Inter_G=Short_G.subgraph(list(i))
    nodes_passed=[]
    network.removeSelection()
    network.select(comp)
    short_endpoints=[]
    for f in network.selectedFeatures():
        p0=f.geometry().asPolyline()[0]
        p_1=f.geometry().asPolyline()[-1]
        #print f, p0,p_1
        short_endpoints.append(p0)
        short_endpoints.append(p_1)
        max_con=0
    #new point= centroid of points
    x=[p[0] for p in short_endpoints]
    y=[p[1] for p in short_endpoints]
    new_point=(float(sum(x))/float(len(short_endpoints)),float(sum(y))/float(len(short_endpoints)))
    all_new_points.append(new_point)
        #if len(G.neighbors(p0))>max_con:
        #    new_point=p0
        #    max_con=len(G.neighbors(p0))
        #if len(G.neighbors(p_1))>max_con:
        #    new_point=p_1
        #    max_con=len(G.neighbors(p_1))
    #print short_endpoints
    neighbours=[]
    for i in comp:
        for j in Dual_G.neighbors_iter(i):
            if j not in neighbours and j not in ids_short:
                #print j
                neighbours.append(j)
    for i in neighbours:
        Neighbours.append(i)
    neighbours_to_rem=[]
    for i in neighbours:
        if i<=feat_count_init:
            #print i
            network.removeSelection()
            network.select(i)
            f=network.selectedFeatures()[0]
            lines_modified.append(f.id())
            if f.geometry().asPolyline()[0] in short_endpoints and f.geometry().asPolyline()[-1] in short_endpoints:
                neighbours_to_rem.append(i)
                #print "excluded", i
            elif f.geometry().asPolyline()[0] in short_endpoints and not f.geometry().asPolyline()[-1] in short_endpoints:
                #print "index to keep 0, to modify 0 , length 2", i
                if len(f.geometry().asPolyline())==2:
                    #print "index=0","2", l
                    point_index=0
                    f.geometry().moveVertex(new_point[0],new_point[1],point_index)
                    if f.geometry().isGeosValid():
                        #print "valid"
                        network.startEditing()
                        network.changeGeometry(i, f.geometry())
                        network.commitChanges()
                    else:
                        #print "invalid"
                        pass
                else:
                    #print "index to keep 0, to modify 0 , length >2", i
                    f.geometry().moveVertex(new_point[0],new_point[1],0)
                    if f.geometry().isGeosValid():
                        #print "valid"
                        network.startEditing()
                        network.changeGeometry(i, f.geometry())
                        network.commitChanges()
                    else:
                        pass
                        #print "la"
            elif f.geometry().asPolyline()[0] not in short_endpoints and f.geometry().asPolyline()[-1] in short_endpoints:
                if len(f.geometry().asPolyline())==2:
                    #print "index=-1","2", l
                    point_index=len(f.geometry().asPolyline())-1
                    f.geometry().moveVertex(new_point[0],new_point[1],point_index)
                    if f.geometry().isGeosValid():
                        #print "valid"
                        network.startEditing()
                        network.changeGeometry(i, f.geometry())
                        network.commitChanges()
                    else:
                        #print "invalid"
                        pass
                else:
                    #print "index=-1","alliws", l
                    f.geometry().moveVertex(new_point[0],new_point[1],(len(f.geometry().asPolyline()))-1)
                    if f.geometry().isGeosValid():
                        #print "valid"
                        network.startEditing()
                        network.changeGeometry(i, f.geometry())
                        network.commitChanges()
                    else:
                        pass
                        #print "invalid"
            for i in neighbours_to_rem:
                ids_short.append(i)

ids_unique=[]
for i in ids_short:
    if i not in ids_unique:
        ids_unique.append(i)

network.startEditing()
network.dataProvider().deleteFeatures(ids_unique)
network.commitChanges()

"""CLEAN DUPLICATE GEOMETRIES"""

geometries = {}
for f in network.getFeatures():
    geometries[f.id()]=f.geometry().asPolyline()

ids_to_del=[]
for i,j in geometries.items():
    if j!= None:
        for x,y in geometries.items():
            if j == y and i>x:
                ids_to_del.append([i,x])
            elif j==list(reversed(y)) and i>x:
                ids_to_del.append([i,x])

ids_to_be_excl=[]
for i in ids_to_del:
    ids_to_be_excl.append(i[1])

ids_deleted=[]
for i in ids_to_del:
    ids_deleted.append(i[0])

network.startEditing()
network.dataProvider().deleteFeatures(ids_deleted)
network.commitChanges()

name_points=None
for i, j in QgsMapLayerRegistry.instance().mapLayers().items():
    if Points==j:
        name_points=i

QgsMapLayerRegistry.instance().removeMapLayer(name_points)


"""CLEAN LINES WITH TWO_COMMON ENDPOINTS"""
D={}

distance_threshold= 0.0001

for elem in network.getFeatures():
    #get f.id()
    id=elem.id()
    geom=elem.geometry()
    len_=geom.length()
    #get endpoints
    D[id]=[geom.asPolyline()[0],geom.asPolyline()[-1],len_]

two_ends=[]

for k,v in D.items():
    id=k
    p0=v[0]
    p1=v[1]
    l=v[2]
    #print id,p0,p1
    for i,j in D.items():
        if k>i:
            id_s=i
            p0_s=j[0]
            p1_s=j[1]
            l_s=j[2]
            #a condition for not having double pairs eg [a,b] and [b,a]
            if p0==p0_s and p1==p1_s:
                #lines that will be paired should have approximately the same length
                if abs(l-l_s)<= distance_threshold:
                    two_ends.append([id,id_s])
            elif p0==p1_s and p1==p0_s:
                #lines that will be paired should have approximately the same length
                if abs(l-l_s)<= distance_threshold :
                    two_ends.append([id,id_s])

#unless average angular change is very different

two_ends_to_del=[]
for i in two_ends:
    two_ends_to_del.append(i[0])

two_ends_to_exclude=[]
for i in two_ends:
    two_ends_to_exclude.append(i[1])

network.removeSelection()
network.select(ids_to_be_excl)
#network.select(ids_deleted)
network.removeSelection()
network.select(two_ends_to_exclude)
network.removeSelection()
network.select(two_ends_to_del)
network.startEditing()
network.deleteSelectedFeatures()
network.commitChanges()

edges_not_to_check=ids_to_be_excl+two_ends_to_exclude
edges_to_check=lines_modified




