from PyQt4.QtCore import QVariant, QFileInfo
import os
import processing
import networkx as nx
from networkx import connected_components
from qgis.core import *
import itertools
import csv
import math

def make_graph(network):
    pass

def make_dual_graph(graph):
    pass

def read_shp_to_multigraph(shapefile):
    pass

def make_Dict_(network):
    pass

def select_by_ids(network,ids):
    pass

def merge_lines(network_input):

    #create a copy of the input network as a memory layer
    crs=network_input.crs()
    network_input_filepath=network_input.dataProvider().dataSourceUri()
    network_input_dir=os.path.dirname(network_input_filepath)
    network_input_basename=QFileInfo(network_input_filepath).baseName()
    network_input_path= network_input_dir + "/"+ network_input_basename +".shp"
    networ_expl_path= network_input_dir + "/"+ network_input_basename +"_exploded.shp"
    network_input=QgsVectorLayer(network_input_path, "network_input", "ogr")
    temp_network=QgsVectorLayer('LineString?crs='+crs.toWkt(), "temporary_network", "memory")

    processing.runalg("qgis:explodelines",network_input,networ_expl_path)

    expl_network=QgsVectorLayer(networ_expl_path,"network_exploded","ogr")

    #add a column in the network_input file with feature ID
    expl_network.startEditing()
    expl_network.dataProvider().addAttributes([QgsField("feat_id_", QVariant.Int)])
    expl_network.commitChanges()

    fieldIdx = expl_network.dataProvider().fields().indexFromName("feat_id_")
    updateMap = {}

    for f in expl_network.getFeatures():
        fid=f.id()
        updateMap[fid] = { fieldIdx: fid}

    expl_network.dataProvider().changeAttributeValues( updateMap )

    QgsMapLayerRegistry.instance().addMapLayer(temp_network)

    #iface.mapCanvas().refresh()

    temp_network.dataProvider().addAttributes([y for y in expl_network.dataProvider().fields()])
    temp_network.updateFields()
    temp_network.startEditing()
    temp_network.addFeatures([x for x in expl_network.getFeatures()])
    temp_network.commitChanges()
    temp_network.removeSelection()

    """01: Merge lines from intersection to intersection"""
    #make a graph of the network_input_exploded layer
    G_shp = nx.read_shp(str(networ_expl_path))
    #parallel lines are excluded of the graph because it is not a multigraph, self loops are included
    G=G_shp.to_undirected(reciprocal=False)

    Dual_G=nx.MultiGraph()
    for e in G.edges_iter(data='feat_id_'):
        Dual_G.add_node(e[2])

    for i,j in G.adjacency_iter():
        if len(j)==2:
            values=[]
            for k,v in j.items():
                values.append(v['feat_id_'])
            #print values
            Dual_G.add_edge(values[0],values[1],data=None)

    #lines with three connections have been included, breaks at intresections
    #set also include single edges
    sets=[]
    for j in connected_components(Dual_G):
        sets.append(list(j))

    #make a dictionary of all feature ids and corresponding geometry
    D={}
    for f in temp_network.getFeatures():
        fid=f.attribute('feat_id_')
        #careful! you need AndOwnership otherwise you get a C++ error
        f_geom=f.geometryAndOwnership()
        D[fid]=f_geom

    #make a dictionary of sets of geometries to be combined and sets of ids to be combined
    Geom_sets={}
    for m in sets:
        Geom_sets[tuple(m)]=[]

    for k,v in Geom_sets.items():
        geoms=[]
        for i in k:
            #print i
            i_geom=D[i]
            #print i_geom
            geoms.append(i_geom)
        Geom_sets[k]=tuple(geoms)

    #make adjacency dictionary for nodes of Dual Graph (=edges)
    AdjD={}
    #returns an iterator of (node, adjacency dict) tuples for all nodes
    for (i, v) in Dual_G.adjacency_iter():
        AdjD[i]=v

    sets_in_order=[]
    for f in sets:
        ord_set=[]
        nodes_passed=[]
        if len(f)==2 or len(f)==1:
            ord_set=f
            sets_in_order.append(ord_set)
        else:
            for n in f:
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
    A={}
    for f in temp_network.getFeatures():
        fid=f.attribute('feat_id_')
        A[fid]=f.attributes()

    #include in sets ord the geometry of the feature
    for s in sets_in_order:
        for indx,i in enumerate(s):
            ind=indx
            line=i
            s[indx]= [line,D[line]]

    #combine geometries
    New_geoms=[]
    for h in sets_in_order:
        new_geom=None
        if len(h)==1:
            new_geom=h[0][1]
            new_attr=A[h[0][0]]
        elif len(h)==2 :
            line1_geom=h[0][1]
            line2_geom=h[1][1]
            new_geom=line1_geom.combine(line2_geom)
            new_attr=A[h[0][0]]
        else:
            new_attr=A[h[0][0]]
            for i,line in enumerate(h):
                ind=i
                l=line
                if ind==(len(h)-1):
                    pass
                else:
                    l_geom=h[ind][1]
                    next_l=h[(ind+1)%len(h)]
                    next_l_geom=h[(ind+1)%len(h)][1]
                    new_geom=l_geom.combine(next_l_geom)
                    h[(ind+1)%len(h)][1]=new_geom
        #print new_geom
        New_geoms.append([new_geom,new_attr])

    #delete all features and recreate memory layer with new geometries
    temp_network.removeSelection()
    temp_network.startEditing()
    temp_network.selectAll()
    temp_network.deleteSelectedFeatures()
    temp_network.commitChanges()

    New_feat=[]
    #reconstruct new geometries
    for i in New_geoms:
        feature = QgsFeature()
        feature.setGeometry(i[0])
        feature.setAttributes(i[1])
        New_feat.append(feature)

    temp_network.startEditing()
    temp_network.addFeatures(New_feat)
    temp_network.commitChanges()
    temp_network.removeSelection()

    #break lines if they are Multilines
    feat_to_del=[]
    New_feat=[]
    for f in temp_network.getFeatures():
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

    temp_network.startEditing()
    temp_network.dataProvider().deleteFeatures(feat_to_del)
    temp_network.addFeatures(New_feat)
    temp_network.commitChanges()
    temp_network.removeSelection()

    return temp_network

def PointEquality(vertex1,vertex2):
    return ((abs(vertex1[0] - vertex2[0]) < 0.000001) and
            (abs(vertex1[1] - vertex2[1]) < 0.000001))

def simplify_intersections(network,threshold_inter):
    #create a copy of the input network as a memory layer
    crs=network.crs()
    temp_network=QgsVectorLayer('LineString?crs='+crs.toWkt(), "temporary_network", "memory")
    QgsMapLayerRegistry.instance().addMapLayer(temp_network)
    temp_network.dataProvider().addAttributes([y for y in network.dataProvider().fields()])
    temp_network.updateFields()
    temp_network.startEditing()
    temp_network.addFeatures([x for x in network.getFeatures()])
    temp_network.commitChanges()
    temp_network.removeSelection()

    #make a new temporary point layer at intersections
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
    for i in temp_network.getFeatures():
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

    #make a dictionary with x,y coordinates of lines of the network layer and their id
    Id_D={}
    for f in temp_network.getFeatures():
        Id_D[(f.geometry().asPolyline()[0],f.geometry().asPolyline()[-1])]=f.id()

    feat_count=int(temp_network.featureCount())
    feat_count_init=int(temp_network.featureCount())

    new_attr=[]
    for i in range(0,len(temp_network.dataProvider().fields())):
        new_attr.append(NULL)

    New_feat_l=[]
    for t in New_edges:
        p1=P_D[t[0]]
        p2=P_D[t[1]]
        qp_1=QgsPoint(p1[0],p1[1])
        qp_2=QgsPoint(p2[0],p2[1])
        feat=QgsFeature()
        geom=QgsGeometry().fromPolyline([qp_1,qp_2])
        feat.setGeometry(geom)
        feat.setAttributes(new_attr)
        New_feat_l.append(feat)

    temp_network.startEditing()
    temp_network.addFeatures(New_feat_l)
    temp_network.commitChanges()

    #construct a normal graph from the merged netwrok
    G=nx.MultiGraph()
    for f in temp_network.getFeatures():
        f_geom=f.geometry()
        id=f.id()
        p0=f_geom.asPolyline()[0]
        p1=f_geom.asPolyline()[-1]
        G.add_edge(p0,p1,fid=id)

    #construct a dual graph with all connections
    Dual_G=nx.MultiGraph()
    for e in G.edges_iter(data='fid'):
        Dual_G.add_node(e[2])

    Dual_G_edges=[]
    for i,j in G.adjacency_iter():
        edges=[]
        if len(j)>1:
            for k,v in j.items():
                edges.append(v[0]['fid'])
            for elem in range(0,len(edges)+1):
                for subset in itertools.combinations(edges,elem):
                    if len(subset)==2:
                        Dual_G_edges.append(subset)

    for i in Dual_G_edges:
        Dual_G.add_edge(i[0],i[1],data=None)

    ids_short=[]
    for f in temp_network.getFeatures():
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
        temp_network.removeSelection()
        temp_network.select(comp)
        short_endpoints=[]
        for f in temp_network.selectedFeatures():
            p0=f.geometry().asPolyline()[0]
            p_1=f.geometry().asPolyline()[-1]
            short_endpoints.append(p0)
            short_endpoints.append(p_1)
        x=[p[0] for p in short_endpoints]
        y=[p[1] for p in short_endpoints]
        new_point=(float(sum(x))/float(len(short_endpoints)),float(sum(y))/float(len(short_endpoints)))
        all_new_points.append(new_point)
        neighbours=[]
        for i in comp:
            for j in Dual_G.neighbors_iter(i):
                if j not in neighbours and j not in ids_short:
                    neighbours.append(j)
        for i in neighbours:
            Neighbours.append(i)
        neighbours_to_rem=[]
        for i in neighbours:
            if i<=feat_count_init:
                temp_network.removeSelection()
                temp_network.select(i)
                f=temp_network.selectedFeatures()[0]
                if f.geometry().asPolyline()[0] in short_endpoints and f.geometry().asPolyline()[-1] in short_endpoints:
                    neighbours_to_rem.append(i)
                elif f.geometry().asPolyline()[0] in short_endpoints and not f.geometry().asPolyline()[-1] in short_endpoints:
                    lines_modified.append(f.id())
                    if len(f.geometry().asPolyline())<=2:
                        point_index=0
                        vertices_to_keep =[new_point]+[f.geometry().asPolyline()[-1]]
                    else:
                        vertices_to_keep =[new_point]+[x for ind,x in enumerate(f.geometry().asPolyline()) if ind>=1]
                    new_pl=[]
                    for vertex in vertices_to_keep:
                        p=QgsPoint(vertex[0],vertex[1])
                        new_pl.append(p)
                    new_geom=QgsGeometry().fromPolyline(new_pl)
                    temp_network.startEditing()
                    temp_network.changeGeometry(f.id(),new_geom)
                    temp_network.commitChanges()
                elif f.geometry().asPolyline()[0] not in short_endpoints and f.geometry().asPolyline()[-1] in short_endpoints:
                    lines_modified.append(f.id())
                    if len(f.geometry().asPolyline())<=2:
                        point_index=len(f.geometry().asPolyline())-1
                        vertices_to_keep=[f.geometry().asPolyline()[0]]+[new_point]
                    else:
                        vertices_to_keep= [x for ind,x in enumerate(f.geometry().asPolyline()) if ind<=len(f.geometry().asPolyline())-2] +[new_point]
                    new_pl=[]
                    for vertex in vertices_to_keep:
                        p=QgsPoint(vertex[0],vertex[1])
                        new_pl.append(p)
                    new_geom=QgsGeometry().fromPolyline(new_pl)
                    temp_network.startEditing()
                    temp_network.changeGeometry(f.id(),new_geom)
                    temp_network.commitChanges()
                for l in neighbours_to_rem:
                    ids_short.append(l)

    ids_unique=[]
    for i in ids_short:
        if i not in ids_unique:
            ids_unique.append(i)

    temp_network.startEditing()
    temp_network.dataProvider().deleteFeatures(ids_unique)
    temp_network.commitChanges()

    name_points=None
    for i, j in QgsMapLayerRegistry.instance().mapLayers().items():
        if Points==j:
            name_points=i

    #QgsMapLayerRegistry.instance().removeMapLayer(name_points)

    return temp_network,all_new_points

def clean_duplicates(network):

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

    ids_deleted=[]
    for i in ids_to_del:
        ids_deleted.append(i[0])

    network.startEditing()
    network.dataProvider().deleteFeatures(ids_deleted)
    network.commitChanges()

def clean_two_ends(network,distance_threshold):

    D={}

    for elem in network.getFeatures():
        id=elem.id()
        geom=elem.geometry()
        len_=geom.length()
        D[id]=[geom.asPolyline()[0],geom.asPolyline()[-1],len_]

    two_ends=[]

    for k,v in D.items():
        id=k
        p0=v[0]
        p1=v[1]
        l=v[2]
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

    network.removeSelection()
    network.select(two_ends_to_del)
    network.startEditing()
    network.deleteSelectedFeatures()
    network.commitChanges()

def find_parallel_lines(network,angle_threshold):
    """02. Find parallel lines"""
    D={} #D[id]=[(p0),(p1)]
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
        G.add_edge(p0,p1,fid=id)

    #find parallel lines below threshold
    parallel_lines=[]
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
            not_f.append(i.id())

    return f, not_f, self_loops_ids

def find_shortest_paths(network, all_new_points):

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

    endpoints_to_copy=[]
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
        else:
            for f in i:
                endpoints_to_copy.append(f)


    endpoints_to_keep=[]
    for path in unique_paths:
        for i in path:
            if i not in endpoints_to_keep:
                endpoints_to_keep.append(i)


    features_to_copy=[]
    features_to_keep=[]
    for i in network.getFeatures():
        p0=(i.geometry().asPolyline()[0][0], i.geometry().asPolyline()[0][1])
        p1=(i.geometry().asPolyline()[-1][0], i.geometry().asPolyline()[-1][1])
        b1=False
        b2=False
        b3=False
        b4=False
        for j in endpoints_to_keep:
            if PointEquality(p0,j):
                b1=True
        for k in endpoints_to_keep:
            if PointEquality(p1,k):
                b2=True
        if b1 and b2:
            features_to_keep.append(i.id())
        for t in endpoints_to_copy:
            if PointEquality(p0,t):
                b3=True
        for s in endpoints_to_copy:
            if PointEquality(p1,s):
                b4=True
        if b3 and b4:
            features_to_copy.append(i.id())


    return features_to_keep,features_to_copy

def clean_triangles(network,threshold_dif):
    D={}
    for i in network.getFeatures():
        p0=i.geometry().asPolyline()[0]
        p1=i.geometry().asPolyline()[-1]
        len_=i.geometry().length()
        D[i.id()]=[p0,p1,len_]

    one_common=[]
    for f in network.getFeatures():
        f_p0=D[f.id()][0]
        f_p1=D[f.id()][1]
        f_len=D[f.id()][2]
        for g in network.getFeatures():
            if g.id()!=f.id():
                g_p0=D[g.id()][0]
                g_p1=D[g.id()][1]
                g_len=D[g.id()][2]
                if f_p0==g_p0 and not f_p1==g_p1:
                    shortest=f
                    longest=g
                    shortest_endpoint=f_p1
                    other_endpoint=f_p0
                    if f_len>g_len:
                        shortest=g
                        longest=f
                        shortest_endpoint=g_p1
                        other_endpoint=g_p0
                    one_common.append([shortest.id(),longest.id(),shortest_endpoint,other_endpoint])
                elif f_p1==g_p1 and not f_p0==g_p0 :
                    shortest=f
                    longest=g
                    shortest_endpoint=f_p0
                    other_endpoint=f_p1
                    if f_len>g_len:
                        shortest=g
                        longest=f
                        shortest_endpoint=g_p0
                        other_endpoint=g_p1
                    one_common.append([shortest.id(),longest.id(),shortest_endpoint,other_endpoint])
                elif f_p0==g_p1 and not f_p1==g_p0:
                    shortest=f
                    longest=g
                    shortest_endpoint=f_p1
                    other_endpoint=f_p0
                    if f_len>g_len:
                        shortest=g
                        longest=f
                        shortest_endpoint=g_p0
                        other_endpoint=g_p1
                    one_common.append([shortest.id(),longest.id(),shortest_endpoint,other_endpoint])
                elif f_p1==g_p0 and not f_p0==g_p1:
                    shortest=f
                    longest=g
                    shortest_endpoint=f_p0
                    other_endpoint=f_p1
                    if f_len>g_len:
                        shortest=g
                        longest=f
                        shortest_endpoint=g_p1
                        other_endpoint=g_p0
                    one_common.append([shortest.id(),longest.id(),shortest_endpoint,other_endpoint])

    triangles=[]
    for i in one_common:
        for j in one_common:
            if i!=j:
                if i[1]==j[1] and i[2]==j[2]:
                    if not i[3]==j[3]:
                #short, short,long, peak_point,long_p0,long_p1)
                        triangles.append([i[0],j[0],j[1],i[2],D[j[1]][0],D[j[1]][1]])

    triangles_reduced=[]
    for i in triangles:
        AOK=math.asin(abs(i[4][0]-i[3][0])/abs(math.hypot(abs(i[4][0]-i[3][0]),abs(i[4][1]-i[3][1]))))
        BOL=math.asin(abs(i[5][0]-i[3][0])/abs(math.hypot(abs(i[5][0]-i[3][0]),abs(i[5][1]-i[3][1]))))
        angle=math.degrees(AOK) + math.degrees(BOL)
        if angle>120 and (D[i[0]][2]+D[i[1]][2])-D[i[2]][2]>0 and (D[i[0]][2]+D[i[1]][2])-D[i[2]][2]>0 <=threshold_dif:
            if i not in triangles_reduced and i[0]>i[1]:
                triangles_reduced.append([i[0],i[1],i[2]])

    long_features=[]
    for i in triangles_reduced:
        long_features.append(i[2])

    return long_features

def generate_unlinks(network,id_column):

    network_filepath=network.dataProvider().dataSourceUri()
    network_dir=os.path.dirname(network_filepath)
    network_basename=QFileInfo(network_filepath).baseName()
    output_path=network_dir + "/"+ network_basename +"_unlinks.shp"

    processing.runandload("qgis:lineintersections", network, network,id_column,id_column,output_path)

    Intersections = QgsVectorLayer(output_path,"Unlinks","ogr")
    QgsMapLayerRegistry.instance().addMapLayer(Intersections)

    mega_list=[]
    for f in network.getFeatures():
        Endpoints=f.geometry().asPolyline()
        for i in Endpoints:
            mega_list.append(i)

    #delete points if they are endpoints of lines
    #keep only unlinks
    points_to_del=[]
    for f in Intersections.getFeatures():
        point=f.geometry().asPoint()
        if point in mega_list:
            points_to_del.append(f.id())

    Intersections.startEditing()
    Intersections.dataProvider().deleteFeatures(points_to_del)
    Intersections.commitChanges()


def simplify_angle(network,angular_threshold,length_threshold):

    New={}
    Copy={}
    for feature in network.getFeatures():
        f=feature
        f_geom=f.geometry()
        if len(f_geom.asPolyline())>2:
            Dual_G=nx.Graph()
            indices_to_del=[]
            for index,point in enumerate(f_geom.asPolyline()):
                if index<len(f_geom.asPolyline())-2:
                    first=point
                    first_x=point[0]
                    first_y=point[1]
                    second=f_geom.asPolyline()[(index+1)%len(f_geom.asPolyline())]
                    second_x=second[0]
                    second_y=second[1]
                    third=f_geom.asPolyline()[(index+2)%len(f_geom.asPolyline())]
                    third_x=third[0]
                    third_y=third[1]
                    fi=math.degrees(math.asin((third_x-second_x)/math.hypot(third_x-second_x,third_y-second_y)))
                    omega=math.degrees(math.asin((second_x-first_x)/math.hypot(second_x-first_x,second_y-first_y)))
                    angle=180+fi-omega
                    if angle>180:
                        angle=360-angle
                    angle=180-angle
                    Dual_G.add_edge((index,index+1),(index+1,index+2), angular_change=angle)
            for i in Dual_G.edges(data=True):
                angle=i[2]['angular_change']
                if angle<angular_threshold:
                    intersection=set(i[0]).intersection(i[1])
                    indices_to_del.append(list(intersection)[0])
            del_count=0
            indices_to_keep=[x for x in range(len(f_geom.asPolyline())-1)]
            for i in indices_to_del:
                if i in indices_to_keep:
                    indices_to_keep.remove(i)
                    boolean=True
            if 0 not in indices_to_keep:
                indices_to_keep.append(0)
            if len(f_geom.asPolyline())-1 not in indices_to_keep:
                indices_to_keep.append(len(f_geom.asPolyline())-1)
            indices_to_keep.sort()
            new_pl=[]
            for i in indices_to_keep:
                p=QgsPoint(f_geom.asPolyline()[i])
                new_pl.append(p)
            new_geom=QgsGeometry().fromPolyline(new_pl)
            new_feat=QgsFeature()
            new_feat.setGeometry(new_geom)
            new_feat.setAttributes(feature.attributes())
            New[feature.id()]=new_feat
        else:
            Copy[feature.id()]=feature

    network.startEditing()
    network.removeSelection()
    network.select(New.keys()+Copy.keys())
    network.deleteSelectedFeatures()
    network.addFeatures(New.values()+Copy.values())
    network.commitChanges()


    """Simplification"""
    """2. delete vertices of segments that are short in length"""

    #try to repeat this until there is no length<threshold
    New={}
    Copy={}

    for feature in network.getFeatures():
        f=feature
        f_geom=f.geometry()
        indices_to_del=[]
        for index,point in enumerate(f_geom.asPolyline()):
            l=length_threshold
            if index<len(f_geom.asPolyline())-1:
                first=point
                next=f_geom.asPolyline()[(index+1)%len(f_geom.asPolyline())]
                l=math.hypot(first[0]-next[0],first[1]-next[1])
            if l< length_threshold:
                indices_to_del.append(index+1)
        indices_to_keep=[x for x in range(len(f_geom.asPolyline())-1)]
        for i in indices_to_del:
            if i in indices_to_keep:
                indices_to_keep.remove(i)
        if 0 not in indices_to_keep:
            indices_to_keep.append(0)
        if len(f_geom.asPolyline())-1 not in indices_to_keep:
            indices_to_keep.append(len(f_geom.asPolyline())-1)
        indices_to_keep.sort()
        if len(indices_to_del)==0:
            Copy[feature.id()]=feature
        else:
            for i in indices_to_del:
                if i in indices_to_keep:
                    indices_to_keep.remove(i)
            if 0 not in indices_to_keep:
                indices_to_keep.append(0)
            if len(f_geom.asPolyline())-1 not in indices_to_keep:
                indices_to_keep.append(len(f_geom.asPolyline())-1)
            indices_to_keep.sort()
            new_pl=[]
            for i in indices_to_keep:
                p=QgsPoint(f_geom.asPolyline()[i])
                new_pl.append(p)
            new_geom=QgsGeometry().fromPolyline(new_pl)
            new_feat=QgsFeature()
            new_feat.setGeometry(new_geom)
            new_feat.setAttributes(feature.attributes())
            New[feature.id()]=new_feat


    network.startEditing()
    network.removeSelection()
    network.select(New.keys()+Copy.keys())
    network.deleteSelectedFeatures()
    network.addFeatures(New.values()+Copy.values())
    network.commitChanges()

#this function has been replaced by merge_lines
def loadfile(self):

    # get input path
    input_layer=self.dlg.choose_input_layer.currentText()

    # get active layers
    active_layers = self.iface.legendInterface().layers()
    active_layer_names = []
    for layer in active_layers:
        active_layer_names.append(layer.name())
    # loading the network
    if input_layer in active_layer_names:
        Foreground_original = active_layers[active_layer_names.index(input_layer)]
    else:
        self.iface.messageBar().pushMessage(
            "Simplificator: ",
            "No network selected!",
            level=QgsMessageBar.WARNING,
            duration=5)

    #create a copy of the Foreground layer as a memory layer

    crs=Foreground_original.crs()
    #provider=Foreground_original.dataProvider()
    #Foreground_writer = QgsVectorFileWriter (input_path, provider.encoding(), provider.fields() ,provider.geometryType(), provider.crs() , "ESRI Shapefile")

    Foreground=QgsVectorLayer('LineString?crs='+crs.toWkt(), "temporary_foreground", "memory")
    QgsMapLayerRegistry.instance().addMapLayer(Foreground_original)
    Foreground_original.selectAll()

    pr=Foreground.dataProvider()
    QgsMapLayerRegistry.instance().addMapLayer(Foreground)
    #Foreground=self.iface.activeLayer()
    pr.addAttributes([y for y in Foreground_original.dataProvider().fields()])
    Foreground.updateFields()
    Foreground.startEditing()
    Foreground.addFeatures([x for x in Foreground_original.getFeatures()])
    Foreground.commitChanges()
    self.iface.mapCanvas().refresh()

    self.dlg.progress_bar.setValue(1)

    """PROCESS 1: Merge lines from intersection to intersection"""
    #add id column
    from PyQt4.QtCore import QVariant
    Foreground.startEditing()
    pr.addAttributes([QgsField("fid", QVariant.Int)])
    Foreground.commitChanges()

    #add unique ids to id column
    fieldIdx = pr.fields().indexFromName( 'fid' )
    updateMap = {}
    for f in Foreground.getFeatures():
        fid=f.id()
        updateMap[f.id()] = { fieldIdx: fid }

    pr.changeAttributeValues( updateMap )

    #make a graph of the memory layer
    import networkx as nx
    G=nx.Graph()

    for f in Foreground.getFeatures():
        f_geom=f.geometry()
        id=f.attribute('fid')
        #print id
        p0=f_geom.asPolyline()[0]
        p1=f_geom.asPolyline()[-1]
        G.add_edge(p0,p1,{'fid':id})

    #message: 'a graph with',%s,'nodes and', %s, 'edges has been created', (G.__len(),G.size())

    Dual_G=nx.MultiGraph()
    for e in G.edges_iter(data='fid'):
        #print e[2]
        Dual_G.add_node(e[2])

    for i,j in G.adjacency_iter():
        #print i,j
        if len(j)==2:
            values=[]
            for k,v in j.items():
                values.append(v['fid'])
            #print values
            Dual_G.add_edge(values[0],values[1],data=None)

    #a dual graph with',%s,'nodes and', %s, 'edges has been created', (Dual_G.__len(),Dual_G.size())
    #(node=edge's id, edge= (edge's id, edge's id) where there is a connection between edges)
    #deal with self loops
    #MultiGraph.selfloop_edges

    #find connected components of the Dual graph and make sets
    from networkx import connected_components

    #lines with three connections have been included, breaks at intresections
    #set also include single edges

    sets=[]
    for set in connected_components(Dual_G):
        sets.append(list(set))

    len(sets)

    #make a dictionary of all feature ids and corresponding geometry
    D={}

    for f in Foreground.getFeatures():
        fid=f.attribute('fid')
        f_geom=f.geometry()
        D[fid]=f_geom

    #make a dictionary of sets of geometries to be combined and sets of ids to be combined
    Geom_sets={}
    for set in sets:
        Geom_sets[tuple(set)]=[]

    len(Geom_sets)

    for k,v in Geom_sets.items():
        geoms=[]
        for i in k:
            #print i
            i_geom=D[i]
            #print i_geom
            geoms.append(i_geom)
        Geom_sets[k]=tuple(geoms)


    """write new vector layer with combined geom"""

    #make adjacency dictionary for nodes of Dual Graph (=edges)
    AdjD={}
    #returns an iterator of (node, adjacency dict) tuples for all nodes
    for (i, v) in Dual_G.adjacency_iter():
        #print i,v
        AdjD[i]=v

    sets_in_order=[]
    for set in sets:
        ord_set=[]
        nodes_passed=[]
        if len(set)==2 or len(set)==1:
            ord_set=set
            sets_in_order.append(ord_set)
        else:
            #print ord_set
            for n in set:
                #print n
                if len(AdjD[n])==1 or len(AdjD[n])>2:
                    first_line=n
                    #print n
                else:
                    pass
            #print "broken"
            ord_set=[]
            #print ord_set
            nodes_passed.append(first_line)
            #print nodes_passed
            ord_set.append(first_line)
            #print ord_set
            for n in ord_set:
                #print n
                nodes=AdjD[n].keys()
                #print nodes
                for node in nodes:
                    #print node
                    if node in nodes_passed:
                        pass
                    else:
                        nodes_passed.append(node)
                        ord_set.append(node)
            sets_in_order.append(ord_set)

    #make a dictionary of all feature ids and corresponding geometry
    D={}
    A={}
    for f in Foreground.getFeatures():
        fid=f.attribute('fid')
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
            new_attr=A[set[0][0]]
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
        #print new_geom
        New_geoms.append([new_geom,new_attr])

    #delete all features and recreate memory layer with new geometries
    Foreground.removeSelection()
    Foreground.startEditing()
    Foreground.selectAll()
    Foreground.deleteSelectedFeatures()
    Foreground.commitChanges()

    New_feat=[]
    #reconstruct new geometries
    for i in New_geoms:
        feature = QgsFeature()
        feature.setGeometry(i[0])
        feature.setAttributes(i[1])
        New_feat.append(feature)

    Foreground.startEditing()
    Foreground.addFeatures(New_feat)
    Foreground.commitChanges()

    self.dlg.progress_bar.setValue(2)

    """create new column with new feature's id (gid)"""
    pr=Foreground.dataProvider()

    Foreground.startEditing()
    pr.addAttributes([QgsField("gid", QVariant.Int)])
    Foreground.commitChanges()

    #get the index of the new field created
    fieldIdx = pr.fields().indexFromName( 'gid' )
    updateMap = {}

    for f in Foreground.getFeatures():
        gid=f.id()
        updateMap[f.id()] = { fieldIdx: gid }

    pr.changeAttributeValues( updateMap )

    """BREAK LINES"""

    feat_to_del=[]
    for f in Foreground.getFeatures():
        f_geom_type = f.geometry().wkbType()
        f_id = f.id()
        attr=f.attributes()
        if f_geom_type == 5:
            new_geoms = f.geometry().asGeometryCollection()
            #print "5", f_id
            for i in new_geoms:
                new_feat = QgsFeature()
                new_feat.setGeometry(i)
                new_feat.setAttributes(attr)
                Foreground.startEditing()
                Foreground.addFeature(new_feat, True)
                Foreground.commitChanges()
            feat_to_del.append(f_id)

    QgsMapLayerRegistry.instance().addMapLayer(Foreground)

    Foreground.removeSelection()
    Foreground.select(feat_to_del)
    Foreground.startEditing()
    Foreground.deleteSelectedFeatures()
    Foreground.commitChanges()

    from PyQt4.QtCore import QVariant

    pr=Foreground.dataProvider()

    Foreground.startEditing()
    pr.addAttributes([QgsField("zid", QVariant.Int)])
    Foreground.commitChanges()

    self.dlg.progress_bar.setValue(3)

    #get the index of the new field created
    fieldIdx = pr.fields().indexFromName( 'zid' )
    updateMap = {}

    for f in Foreground.getFeatures():
        zid=f.id()
        updateMap[f.id()] = { fieldIdx: zid }

    pr.changeAttributeValues( updateMap )

    """Condition 2 Break if they cross themselves"""

    Break_pairs = []

    for f in Foreground.getFeatures():
        f_geom_type = f.geometry().wkbType()
        f_geom_Pl = f.geometry().asPolyline()
        # print f_geom
        f_geom = f.geometry()
        f_endpoints = [f_geom_Pl[0], f_geom_Pl[-1]]
        f_id = f.attribute('zid')
        for g in Foreground.getFeatures():
            g_id = g.attribute('zid')
            if f_id == g_id:
                pass
            else:
                g_geom = g.geometry()
                g_geom_type = g.geometry().wkbType()
                if g_geom_type == 2:
                    g_geom_Pl = g.geometry().asPolyline()
                elif g_geom_type == 5:
                    g_geom_Pl = g.geometry().asMultiPolyline()
                if f_geom.intersects(g_geom):
                    Intersection = f_geom.intersection(g_geom)
                    if Intersection.wkbType() == 4:
                        for i in Intersection.asMultiPoint():
                            if i not in f_endpoints:
                                if i in f.geometry().asPolyline():
                                    index = f.geometry().asPolyline().index(i)
                                    break_pair = [f_id, index]
                                    Break_pairs.append(break_pair)
                    elif Intersection.wkbType() == 1:
                        if Intersection.asPoint() not in f_endpoints:
                            if Intersection.asPoint() in f.geometry().asPolyline():
                                index = f.geometry().asPolyline().index(Intersection.asPoint())
                                break_pair = [f_id, index]
                                Break_pairs.append(break_pair)

    len(Break_pairs)

    # make unique groups
    Break_pairs_unique = {}
    for i in Break_pairs:
        if i[0] not in Break_pairs_unique.keys():
            Break_pairs_unique[i[0]] = [i[1]]
        else:
            Break_pairs_unique[i[0]].append(i[1])

    for k, v in Break_pairs_unique.items():
        Foreground.select(k)
        f = Foreground.selectedFeatures()[0]
        Foreground.deselect(k)
        v.append(0)
        v.append(len(f.geometry().asPolyline()) - 1)

    for k, v in Break_pairs_unique.items():
        v.sort()

    # remove duplicates
    Break_pairs = {}
    for k, v in Break_pairs_unique.items():
        Break_pairs[k] = []
        for i in v:
            if i not in Break_pairs[k] and i != 0:
                Break_pairs[k].append(i)

    Break_pairs_new = {}
    for k, v in Break_pairs.items():
        Break_pairs_new[k] = []
        for i, j in enumerate(v):
            if i == 0:
                Break_pairs_new[k].append([0, j])
            else:
                before = v[(i - 1) % len(v)]
                Break_pairs_new[k].append([before, j])

    id = int(Foreground.featureCount())

    for k, v in Break_pairs_new.items():
        Foreground.select(k)
        f = Foreground.selectedFeatures()[0]
        Foreground.deselect(k)
        f_geom = f.geometry()
        Ind_D = {}
        for i, p in enumerate(f_geom.asPolyline()):
            Ind_D[i] = p
        for j in v:
            new_feat = QgsFeature()
            attr=f.attributes()
            id += 1
            new_ind_list = range(j[0], j[1] + 1, 1)
            new_vert_list = []
            for x in new_ind_list:
                #this is a point object
                p = Ind_D[x]
                new_vert_list.append(QgsGeometry().fromPoint(p))
            final_list = []
            for y in new_vert_list:
                final_list.append(y.asPoint())
            new_geom = QgsGeometry().fromPolyline(final_list)
            #new_geom.isGeosValid()
            #print "new_geom" , new_geom
            new_feat.setAttributes(attr)
            new_feat.setGeometry(new_geom)
            Foreground.startEditing()
            Foreground.addFeature(new_feat, True)
            Foreground.commitChanges()

    self.iface.mapCanvas().refresh()

    for k, v in Break_pairs_new.items():
        Foreground.select(k)
        #f = Foreground.selectedFeatures()[0]
        Foreground.deselect(k)
        Foreground.startEditing()
        Foreground.deleteFeature(k)
        Foreground.commitChanges()

    QgsMapLayerRegistry.instance().removeMapLayer(Foreground_original.name())

    self.dlg.progress_bar.setValue(4)

"""

Neighbours=[]
all_new_points=[]
Points=[]
for i in nx.connected_components(Short_G):
    comp=list(i)
    temp_network.removeSelection()
    temp_network.select(comp)
    short_endpoints=[]
    for f in temp_network.selectedFeatures():
        p0=f.geometry().asPolyline()[0]
        p_1=f.geometry().asPolyline()[-1]
        if p0 not in short_endpoints:
            short_endpoints.append(p0)
        if p_1 not in short_endpoints:
            short_endpoints.append(p_1)
    x=[p[0] for p in short_endpoints]
    y=[p[1] for p in short_endpoints]
    new_point=(float(sum(x))/float(len(short_endpoints)),float(sum(y))/float(len(short_endpoints)))
    all_new_points.append(new_point)
    Points.append([short_endpoints,new_point])
    neighbours=[]
    for i in comp:
        for j in Dual_G.neighbors_iter(i):
            if j not in neighbours and j not in ids_short:
                neighbours.append(j)
    for i in neighbours:
        if i not in Neighbours:
            Neighbours.append(i)

temp_network.select(Neighbours)

P_0={}
P_1={}
neighbours_to_rem=[]
for i in temp_network.selectedFeatures():
    p0=i.geometry().asPolyline()[0]
    p1=i.geometry().asPolyline()[-1]
    for j in Points:
        if p0 in j[0] and p1 in j[0]:
            neighbours_to_rem.append(i.id())
        else:
            if p0 in j[0]:
                new_p0=j[1]
                P_0[i.id()]=new_p0
            elif p1 in j[0]:
                new_p1=j[1]
                P_1[i.id()]=new_p1

New_feat=[]
for i in temp_network.selectedFeatures():
    i_geom=i.geometry()
    if i.id() in P_0.keys() and i.id() in P_1.keys():
        new_p0=P_0[i.id()]
        new_p1=P_1[i.id()]
        vertices_to_keep =[new_p0]+[x for ind,x in enumerate(f.geometry().asPolyline()) if ind>0 and ind<len(i.geometry().asPolyline())-1]+[new_p1]
        new_pl=[]
        for vertex in vertices_to_keep:
            p=QgsPoint(vertex[0],vertex[1])
            new_pl.append(p)
        new_geom=QgsGeometry().fromPolyline(new_pl)
        new_feat=QgsFeature()
        new_feat.setGeometry(new_geom)
        new_feat.setAttributes(i.attributes())
        New_feat.append(new_feat)
    else:
        if i.id() in P_0.keys():
            new_p0=P_0[i.id()]
            vertices_to_keep =[new_p0]+[x for ind,x in enumerate(f.geometry().asPolyline()) if ind>0]
            new_pl=[]
            for vertex in vertices_to_keep:
                p=QgsPoint(vertex[0],vertex[1])
                new_pl.append(p)
            new_geom=QgsGeometry().fromPolyline(new_pl)
            new_feat=QgsFeature()
            new_feat.setGeometry(new_geom)
            new_feat.setAttributes(i.attributes())
            New_feat.append(new_feat)
        if i.id() in P_1.keys():
            new_p1=P_1[i.id()]
            vertices_to_keep =[x for ind,x in enumerate(f.geometry().asPolyline()) if ind<len(i.geometry().asPolyline())-1]+[new_p1]
            new_pl=[]
            for vertex in vertices_to_keep:
                p=QgsPoint(vertex[0],vertex[1])
                new_pl.append(p)
            new_geom=QgsGeometry().fromPolyline(new_pl)
            new_feat=QgsFeature()
            new_feat.setGeometry(new_geom)
            new_feat.setAttributes(i.attributes())
            New_feat.append(new_feat)

temp_network.startEditing()
temp_network.deleteSelectedFeatures()
temp_network.addFeatures(New_feat)
temp_network.commitChanges()

"""