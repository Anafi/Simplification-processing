from PyQt4.QtCore import *
from qgis.core import *
import math

"""inputs"""
all_new_points=[(0,1),(2,0)] #pseudo input
network=iface.mapCanvas().currentLayer()
#set length threshold
threshold=0.0005

"""00. Create new_points layer"""
crs=network.crs()
new_points = QgsVectorLayer('Point?crs='+crs.toWkt(), "new_points", "memory")
QgsMapLayerRegistry.instance().addMapLayer(new_points)

pr = new_points.dataProvider()
new_points.startEditing()
pr.addAttributes( [ QgsField("id", QVariant.Int),
                QgsField("x",  QVariant.Double),
                QgsField("y", QVariant.Double) ] )

New_feat=[]
for i in all_new_points:
    fet = QgsFeature()
    fet.setGeometry(QgsGeometry().fromPoint(QgsPoint(i[0],i[1])))
    fet.setAttributes ([id,i[0],i[1]])
    New_feat.append(fet)

pr.addFeatures( New_feat )
new_points.commitChanges()

"""inputs"""
new_points=iface.mapCanvas().currentLayer()

"""00: Delete new point that connect only two lines"""

D={}
for feat in network.getFeatures():
    D[feat.id()]=[(feat.geometry().asPolyline()[0][0],feat.geometry().asPolyline()[0][1]),
                  (feat.geometry().asPolyline()[-1][0], feat.geometry().asPolyline()[-1][1])]

P={}
for feat in new_points.getFeatures():
    P[(feat.geometry().asPoint()[0],feat.geometry().asPoint()[1])]= feat.id()

#P_rev={}
#for feat in new_points.getFeatures():
#    P_rev[feat.id()]=(feat.geometry().asPoint()[0],feat.geometry().asPoint()[1])

new_points_to_del=[]
for i in all_new_points:
    connections=[]
    for k,v in D.items():
        if (v[0]==i or v[1]==i):
            connections.append(k)
    if len(connections)==2:
        new_points_to_del.append(P[i])

new_points.select(new_points_to_del)
new_points.startEditing()
new_points.deleteSelectedFeatures()
new_points.commitChanges()

"""01: Clean two lines that have common endpoints, which are also new_points or one of them is new_point. Delete longest feature"""
#first do that and then step0 of erasing points, because you may have a new_point as an endpoint of two parallel lines

two_new_points=[]
for k_1,v_1 in D.items():
    if (v_1[0][0],v_1[0][1]) in all_new_points and (v_1[1][0],v_1[1][1]) in all_new_points:
        two_new_points.append(k_1)
    elif (v_1[0][0],v_1[0][1]) in all_new_points and not (v_1[1][0],v_1[1][1]) in all_new_points:
        two_new_points.append(k_1)
    elif (v_1[0][0],v_1[0][1]) not in all_new_points and (v_1[1][0],v_1[1][1]) in all_new_points:
        two_new_points.append(k_1)

D2={}
for i in two_new_points:
    D2[i]=D[i]

twos=[]
for k,v in D2.items():
    for i,j in D2.items():
        if k>i and v==j:
           twos.append([k,i])
        elif k>i and v==list(reversed(j)):
            twos.append([k,i])

twos_unique=[]
for i in twos:
    len_1=math.hypot(abs(D[i[0]][0][0]-D[i[0]][1][0]),abs(D[i[0]][0][1]-D[i[0]][1][1]))
    len_2=math.hypot(abs(D[i[1]][0][0]-D[i[1]][1][0]),abs(D[i[1]][0][1]-D[i[1]][1][1]))
    if len_2<=len_1+threshold:
        twos_unique.append(i[1])
    elif len_1<=len_2+threshold:
        twos_unique.append(i[0])

network.removeSelection()
network.select(twos_unique)
network.startEditing()
network.deleteSelectedFeatures()
network.commitChanges()

"""02.A: Clean three lines that have three endpoints, all of which are new_points"""
"""02.B: Clean three lines that have three endpoints, from which two are new_points"""
threes=[]

D={}
for feat in network.getFeatures():
    D[feat.id()]=[(feat.geometry().asPolyline()[0][0],feat.geometry().asPolyline()[0][1]),
                  (feat.geometry().asPolyline()[-1][0], feat.geometry().asPolyline()[-1][1])]

two_new_points=[]
for k_1,v_1 in D.items():
    if (v_1[0][0],v_1[0][1]) in all_new_points and (v_1[1][0],v_1[1][1]) in all_new_points:
        two_new_points.append(k_1)

one_new_point=[]
for k_1,v_1 in D.items():
    if (v_1[0][0],v_1[0][1]) in all_new_points and not((v_1[1][0],v_1[1][1]) in all_new_points):
        one_new_point.append(k_1)
    elif not((v_1[0][0],v_1[0][1])) in all_new_points and ((v_1[1][0],v_1[1][1]) in all_new_points):
        one_new_point.append(k_1)

two_new_points_inter=[]
for i_1 in two_new_points:
    for i_2 in two_new_points:
        points_1=D[i_1]
        points_2=D[i_2]
        if len(set(points_1).intersection(points_2))==1:
            if i_1>i_2:
                two_new_points_inter.append([i_1,i_2])

G={}
for i in network.getFeatures():
    if i.geometry() is None:
        print True
    else:
        G[i.id()]=i.geometry()

for i_3 in two_new_points:
    p_3_0=D[i_3][0]
    p_3_1=D[i_3][1]
    len_3=G[i_3].length()
    for i in two_new_points_inter:
        i_f=i[0]
        i_s=i[1]
        len_f=G[i_f].length()
        len_s=G[i_s].length()
        #this is also to avoid tripple features
        if len_3>len_f and len_f>len_s:
            points=[(D[i_f][0][0], D[i_f][0][1]),(D[i_f][1][0], D[i_f][1][1]),(D[i_s][0][0], D[i_s][0][1]),(D[i_s][1][0], D[i_s][1][1])]
            points_unique=[]
            for i in points:
                if i not in points_unique:
                    points_unique.append(i)
            if p_3_0 in points and p_3_1 in points and len_3<=len_f+len_s+threshold:
                threes.append([i_3,i_f,i_s])

#select threes with three new_points 02.A
#they include lines that had the original new_points
for i in threes:
    for j in i:
        network.select(j)

two_points_inter=[]
for i_1 in one_new_point:
    for i_2 in one_new_point:
        points_1=D[i_1]
        points_2=D[i_2]
        if len(set(points_1).intersection(points_2))==1 and not set(points_1).intersection(points_2) in all_new_points:
            if i_1>i_2:
                two_points_inter.append([i_1,i_2])

network.removeSelection()
for i in two_points_inter:
    for j in i:
        network.select(j)

#if AK kai KB
threes.append()







