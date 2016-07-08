# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MergeLines
                                 A QGIS plugin
 MergeLines
                              -------------------
        begin                : 2016-02-17
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Ioanna Kolovou
        email                : I.Kolovou@spacesyntax.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
import os.path
from qgis.core import *

from qgis.gui import *

# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from MergeLines_dialog import MergeLinesDialog
import os.path


class MergeLines:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'MergeLines_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = MergeLinesDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&MergeLines')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'MergeLines')
        self.toolbar.setObjectName(u'MergeLines')

        self.dlg.lineEdit.clear()
        self.dlg.lineEdit_2.clear()
        self.dlg.pushButton.clicked.connect(self.select_output_file)
        self.dlg.pushButton_2.clicked.connect(self.Loadfile)
        self.dlg.pushButton_4.clicked.connect(self.mergedsave)
        self.dlg.pushButton_5.clicked.connect(self.MergeLines)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('MergeLines', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/MergeLines/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'MergeLines'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&MergeLines'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def select_output_file(self):
        filename = QFileDialog.getOpenFileName(self.dlg, "Select output file ","", '*.shp')
        self.dlg.lineEdit.setText(filename)


    def Loadfile(self):
        location1 = self.dlg.lineEdit.text()
        input5 = self.iface.addVectorLayer(location1, "Merge", "ogr")

        #input 5 is a variable in order to start editing the file

        input5.startEditing()

    def mergedsave(self):
        filename = QFileDialog.getSaveFileName(self.dlg, "Select output file ","", '*.shp')
        self.dlg.lineEdit_2.setText(filename)

    def MergeLines(self):

        from PyQt4.QtCore import QVariant

        Foreground =  self.iface.activeLayer()

        location = self.dlg.lineEdit_2.text()

        pr=Foreground.dataProvider()

        Foreground.startEditing()
        pr.addAttributes([QgsField("fid", QVariant.Int)])
        Foreground.commitChanges()

        #get the index of the new field created
        fieldIdx = pr.fields().indexFromName( 'fid' )
        updateMap = {}

        for f in Foreground.getFeatures():
            fid=f.id()
            updateMap[f.id()] = { fieldIdx: fid }

        pr.changeAttributeValues( updateMap )

        """3. Make a graph out of the Main network (nodes=endpoints of lines, edges=lines)"""
        """why do you need to explode it first? processing time increases significantly"""
        import networkx as nx

        G=nx.Graph()
        nodes=[]

        for f in Foreground.getFeatures():
            f_geom=f.geometry()
            id=f.attribute('fid')
            #print id
            p0=f_geom.asPolyline()[0]
            p1=f_geom.asPolyline()[-1]
            G.add_edge(p0,p1,{'fid':id})


        #check number of nodes and number of edges
        G.__len__()
        G.size()

        #print list of edges
        #list(G.edges_iter(data='fid'))

        """4. Make a dual graph out of the graph of the Foreground network based on ids (node=edge's id, edge= (edge's id, edge's id) where there is a connection between edges"""
        Dual_G=nx.Graph()
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

        #list(Dual_G.edges_iter())

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

        len(Geom_sets)

        #print Geom_sets

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


        #add a writer to write new features
        provider=Foreground.dataProvider()
        merged_writer = QgsVectorFileWriter (location, "UTF-8" , provider.fields() ,provider.geometryType(), provider.crs() , "ESRI Shapefile")

        if merged_writer.hasError() != QgsVectorFileWriter.NoError:
            print "Error when creating shapefile: ",  merged_writer.errorMessage()

        del merged_writer
        Merged_FNet_w_attr=QgsVectorLayer (location, 'Merged_FNet_w_attr', 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(Merged_FNet_w_attr)

        """delete other columns and keep only id column"""

        for i in New_geoms:
          # add a feature
          #print i
          feature = QgsFeature()
          #print feature
          feature.setGeometry(i[0])
          feature.setAttributes(i[1])
          Merged_FNet_w_attr.startEditing()
          Merged_FNet_w_attr.addFeature(feature, True)
          Merged_FNet_w_attr.commitChanges()

        """create new column with new feature's id (gid)"""
        pr=Merged_FNet_w_attr.dataProvider()

        Merged_FNet_w_attr.startEditing()
        pr.addAttributes([QgsField("gid", QVariant.Int)])
        Merged_FNet_w_attr.commitChanges()

        #get the index of the new field created
        fieldIdx = pr.fields().indexFromName( 'gid' )
        updateMap = {}

        gid=0
        for f in Merged_FNet_w_attr.getFeatures():
            updateMap[f.id()] = { fieldIdx: gid }
            gid+=1

        pr.changeAttributeValues( updateMap )

        """"""""""""""""""""""""""""""""""""""""""""""""""""""""
        """BREAK LINES"""
        """"""""""""""""""""""""""""""""""""""""""""""""""""""""

        """Conditions: Break if there are multiPolylines with loops"""

        Merged_FNet_w_attr=QgsVectorLayer (location, 'Merged_FNet_w_attr', 'ogr')

        # get last id of the feature
        #id = int(Foreground.featureCount())

        for f in Merged_FNet_w_attr.getFeatures():
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
                    Merged_FNet_w_attr.startEditing()
                    Merged_FNet_w_attr.addFeature(new_feat, True)
                    Merged_FNet_w_attr.commitChanges()
                Merged_FNet_w_attr.startEditing()
                Merged_FNet_w_attr.deleteFeature(f_id)
                Merged_FNet_w_attr.commitChanges()

        """create new column with new features' id (zid)"""
        from PyQt4.QtCore import QVariant

        pr=Merged_FNet_w_attr.dataProvider()

        Merged_FNet_w_attr.startEditing()
        pr.addAttributes([QgsField("zid", QVariant.Int)])
        Merged_FNet_w_attr.commitChanges()

        #get the index of the new field created
        fieldIdx = pr.fields().indexFromName( 'zid' )
        updateMap = {}

        zid=0
        for f in Foreground.getFeatures():
            updateMap[f.id()] = { fieldIdx: zid }
            zid+=1

        pr.changeAttributeValues( updateMap )

        """Condition 2 Break if they cross themselves"""

        Foreground=QgsVectorLayer (location, 'Merged_FNet_w_attr', 'ogr')

        Break_pairs = []

        for f in Foreground.getFeatures():
            f_geom_type = f.geometry().wkbType()
            f_geom_Pl = f.geometry().asPolyline()
            # print f_geom
            f_geom = f.geometry()
            f_endpoints = [f_geom_Pl[0], f_geom_Pl[-1]]
            f_id = f.attribute('fid')
            for g in Foreground.getFeatures():
                g_id = g.attribute('fid')
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
                attr = [id]
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


        for k, v in Break_pairs_new.items():
            Foreground.select(k)
            f = Foreground.selectedFeatures()[0]
            Foreground.deselect(k)
            Foreground.startEditing()
            Foreground.deleteFeature(k)
            Foreground.commitChanges()



    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
