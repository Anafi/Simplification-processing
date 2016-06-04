# -*- coding: utf-8 -*-
"""
/***************************************************************************
 demo
                                 A QGIS plugin
 demo
                              -------------------
        begin                : 2016-02-12
        git sha              : $Format:%H$
        copyright            : (C) 2016 by AA
        email                : a.acharya@spacesyntax.com
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
from demo_dialog import demoDialog
import os.path
from qgis.core import *
from qgis.gui import *


class demo:
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
            'demo_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = demoDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&demo')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'demo')
        self.toolbar.setObjectName(u'demo')

        self.dlg.lineEdit.clear()
        self.dlg.lineEdit_2.clear()
        self.dlg.lineEdit_3.clear()
        self.dlg.pushButton.clicked.connect(self.select_output_file)
        self.dlg.pushButton_2.clicked.connect(self.Loadfile)
        self.dlg.pushButton_4.clicked.connect(self.backgroundsave)
        self.dlg.pushButton_5.clicked.connect(self.foregroundsave)
        self.dlg.pushButton_3.clicked.connect(self.seperatelayer)

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
        return QCoreApplication.translate('demo', message)


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

        icon_path = ':/plugins/demo/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&demo'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def select_output_file(self):
        filename = QFileDialog.getOpenFileName(self.dlg, "Select output file ","", '*.shp')
        self.dlg.lineEdit.setText(filename)

    def backgroundsave(self):
        filename = QFileDialog.getSaveFileName(self.dlg, "Select output file ","", '*.shp')
        self.dlg.lineEdit_2.setText(filename)

    def foregroundsave(self):
        filename = QFileDialog.getSaveFileName(self.dlg, "Select output file ","", '*.shp')
        self.dlg.lineEdit_3.setText(filename)

    def Loadfile(self):
        location1 = self.dlg.lineEdit.text()
        input5 = self.iface.addVectorLayer(location1, "Seperate", "ogr")

        input5.startEditing()

    def seperatelayer(self):
        """Step 1: separate foreground from background network"""

#select current layer (you can also try to load a Vector layer by its path)
        Athens_allRoads =  self.iface.activeLayer()

        location2 = self.dlg.lineEdit_2.text()
        location3 = self.dlg.lineEdit_3.text()

        #two expressions for Foreground and Background
        expr_Foreground = QgsExpression("type= 'primary' OR type='primary_link' OR type = 'motorway' OR type= 'motorway_link' OR type= 'secondary' OR type= 'secondary_link' OR type= 'trunk' OR type= 'trunk_link'")
        expr_Background = QgsExpression("type='tertiary' or type='tertiary_link' or type= 'bridge' OR type='footway' OR type = 'living_street' OR type= 'path' OR type= 'pedestrian' OR type= 'residential' OR type= 'road' OR type= 'service' OR type= 'steps' OR type= 'track' OR type= 'unclassified' OR type='abandonded' OR type='bridleway' OR type='bus_stop' OR type='construction' OR type='elevator' OR type='proposed' OR type='raceway' OR type='rest_area'")

        #create two writers to write the new vector layers
        provider = Athens_allRoads.dataProvider()
        Foreground_writer = QgsVectorFileWriter (location2, provider.encoding(), provider.fields() ,provider.geometryType(), provider.crs() , "ESRI Shapefile")
        Background_writer = QgsVectorFileWriter (location3, provider.encoding(), provider.fields() ,provider.geometryType(), provider.crs() , "ESRI Shapefile")

        if Foreground_writer.hasError() != QgsVectorFileWriter.NoError:
            print "Error when creating shapefile: ",  Foreground_writer.errorMessage()
        if Background_writer.hasError() != QgsVectorFileWriter.NoError:
            print "Error when creating shapefile: ",  Background_writer.errorMessage()

        #get features based on the queries and add them to the new layers
        #avoid printing True (processing time)
        Foreground_elem= QgsFeature()

        for elem in Athens_allRoads.getFeatures (QgsFeatureRequest(expr_Foreground)):
            Foreground_elem.setGeometry(elem.geometry())
            Foreground_elem.setAttributes(elem.attributes())
            Foreground_writer.addFeature(Foreground_elem)

        del Foreground_writer

        Background_elem= QgsFeature()

        for elem in Athens_allRoads.getFeatures (QgsFeatureRequest(expr_Background)):
            Background_elem.setGeometry(elem.geometry())
            Background_elem.setAttributes(elem.attributes())
            Background_writer.addFeature(Background_elem)

        del Background_writer

        
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
