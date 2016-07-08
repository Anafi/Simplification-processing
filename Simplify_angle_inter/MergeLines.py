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

# import depedencies
from PyQt4.QtCore import *
#QSettings, QTranslator, qVersion, QCoreApplication,QgsProgressBar
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QDoubleSpinBox
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
import os.path
from qgis.core import *
from qgis.gui import *
import processing
import tools


# Initialize Qt resources from file resources.py
# Import the code for the dialog
from MergeLines_dialog import MergeLinesDialog
import os.path

# Import the debug library
# set is_debug to False in release version
is_debug = True
try:
    import pydevd
    has_pydevd = True
except ImportError, e:
    has_pydevd = False
    is_debug = False

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

        self.tools= tools

        #clear all lineEdits
        self.dlg.path_output.clear()
        self.dlg.path_output_2.clear()

        #set threshold menus precision and range
        self.dlg.angle_threshold.setDecimals(1)
        self.dlg.angle_threshold.setRange(0,25)
        self.dlg.angle_threshold.setSingleStep(0.1)
        self.dlg.length_threshold.setDecimals(4)
        self.dlg.length_threshold.setRange(0,100)
        self.dlg.length_threshold.setSingleStep(0.0001)
        self.dlg.inter_distance_threshold.setDecimals(4)
        self.dlg.inter_distance_threshold.setRange(0,100)
        self.dlg.inter_distance_threshold.setSingleStep(0.0001)
        self.dlg.two_ends_threshold.setDecimals(4)
        self.dlg.two_ends_threshold.setRange(0,1000)
        self.dlg.two_ends_threshold.setSingleStep(0.0001)
        self.dlg.angle_threshold.setDecimals(0)
        self.dlg.angle_threshold.setRange(0,90)
        self.dlg.angle_threshold.setSingleStep(1)
        self.dlg.triangles_threshold.setDecimals(4)
        self.dlg.triangles_threshold.setRange(0,1000)
        self.dlg.triangles_threshold.setSingleStep(0.0001)

        #connect browse button
        self.dlg.path_output.setPlaceholderText("Save as temporary layer...")
        self.dlg.path_output_2.setPlaceholderText("Save as temporary layer...")
        self.dlg.path_output_3.setPlaceholderText("Save as temporary layer...")

        # connect drop-down layer menu
        self.dlg.choose_input_layer.activated.connect(self.choose_input_layer)
        self.dlg.choose_input_layer_2.activated.connect(self.choose_input_layer)

        #connect save button
        self.dlg.save_output.clicked.connect(self.save_output)
        self.dlg.save_output_2.clicked.connect(self.save_output_2)
        self.dlg.save_output_3.clicked.connect(self.save_output_3)

        #connect run button
        self.dlg.analysis.clicked.connect(self.minimise_angle)
        self.dlg.analysis_2.clicked.connect(self.minimise_resolution)

        #connect close button
        self.dlg.close_button.clicked.connect(self.closeEvent)
        self.dlg.close_button_2.clicked.connect(self.closeEvent)

        #setup progress bar
        self.dlg.progress_bar.setMinimum(0)
        self.dlg.progress_bar.setMaximum(4)
        self.dlg.progress_bar_2.setMinimum(0)
        self.dlg.progress_bar_2.setMaximum(4)

        # Add at the end of __init__ function of main plugin class
        if has_pydevd and is_debug:
            pydevd.settrace('localhost', port=53100, stdoutToServer=True, stderrToServer=True,
                            suspend=False)


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


    #def save_output(self):
    #    filename = QFileDialog.getOpenFileName(self.dlg, "Select output file ","", '*.shp')
    #    self.dlg.path_input.setText(filename)

    def choose_input_layer(self):
        layers = QgsMapLayerRegistry.instance().mapLayers().values()
        layer_name = self.dlg.choose_input_layer.currentText()
        layer_index = self.dlg.choose_input_layer.currentIndex()
        network = layers[layer_index]
        if not network.isValid():
            self.iface.messageBar().pushMessage(
                "Simplicator: ",
                "Invalid network file!",
                level=QgsMessageBar.WARNING,
                duration=5)

    def save_output(self):
        filename = QFileDialog.getSaveFileName(self.dlg, "Select output file ","", '*.shp')
        self.dlg.path_output.setText(filename)

    def save_output_2(self):
        filename = QFileDialog.getSaveFileName(self.dlg, "Select output file ","", '*.shp')
        self.dlg.path_output_2.setText(filename)

    def save_output_3(self):
        filename = QFileDialog.getSaveFileName(self.dlg, "Select output file ","", '*.shp')
        self.dlg.path_output_3.setText(filename)

    def minimise_angle(self):

        self.dlg.progress_bar.reset()

        #get thresholds' values
        ang_threshold=self.dlg.angle_threshold.value()
        len_threshold=self.dlg.length_threshold.value()

        # get input path
        input_layer=self.dlg.choose_input_layer.currentText()

        # get active layers
        active_layers = self.iface.legendInterface().layers()
        active_layer_names = []
        for layer in active_layers:
            active_layer_names.append(layer.name())
        # loading the network
        if input_layer in active_layer_names:
            network = active_layers[active_layer_names.index(input_layer)]
        else:
            self.iface.messageBar().pushMessage(
                "Simplificator: ",
                "No network selected!",
                level=QgsMessageBar.WARNING,
                duration=5)

        self.dlg.progress_bar.setValue(1)
        #merge lines of network to polylines
        #network_merged=temp_network
        network_merged = tools.merge_lines(network)

        self.dlg.progress_bar.setValue(2)

        tools.simplify_angle(network_merged, ang_threshold, len_threshold)

        self.dlg.progress_bar.setValue(3)

        #get output path
        if not self.dlg.path_output.text():
            pass
        else:
            output_path = self.dlg.path_output.text()
            #add a writer
            provider = network_merged.dataProvider()
            output_network_writer = QgsVectorFileWriter(output_path, provider.encoding(), provider.fields() ,provider.geometryType(), provider.crs() , "ESRI Shapefile")
            if output_network_writer.hasError() != QgsVectorFileWriter.NoError:
                print "Error when creating shapefile: ",  output_network_writer.errorMessage()
            output_network=QgsVectorLayer(output_path,"Simplified","ogr")
            QgsMapLayerRegistry.instance().addMapLayer(output_network)
            output_network.updateFields()
            output_network.startEditing()
            output_network.addFeatures([x for x in network_merged.getFeatures()])
            output_network.commitChanges()
            output_network.removeSelection()
            self.iface.mapCanvas().refresh()

        self.dlg.progress_bar.setValue(4)

    def minimise_resolution(self):

        self.dlg.progress_bar_2.reset()

        #get thresholds' values
        threshold_inter=self.dlg.inter_distance_threshold.value()
        distance_threshold_two=self.dlg.two_ends_threshold.value()
        angle_thres=self.dlg.angle_threshold_2.value()
        thres_triangle=self.dlg.triangles_threshold.value()

        # get input path
        input_layer=self.dlg.choose_input_layer_2.currentText()

        # get active layers
        active_layers_2 = self.iface.legendInterface().layers()
        active_layer_names = []
        for layer in active_layers_2:
            active_layer_names.append(layer.name())
        # loading the network
        if input_layer in active_layer_names:
            network = active_layers_2[active_layer_names.index(input_layer)]
        else:
            self.iface.messageBar().pushMessage(
                "Simplificator: ",
                "No network selected!",
                level=QgsMessageBar.WARNING,
                duration=5)

        output,points_inter = self.tools.simplify_intersections(network,threshold_inter)

        #QgsMapLayerRegistry.instance().addMapLayer(output)

        #make a copy of the memory layer output
        #add a writer
        network_filepath=network.dataProvider().dataSourceUri()
        network_dir=os.path.dirname(network_filepath)
        network_basename=QFileInfo(network_filepath).baseName()
        provider = network.dataProvider()
        output_path=network_dir + "/"+ network_basename +"_sim_inter_1.shp"
        output_network_writer = QgsVectorFileWriter(output_path, provider.encoding(), provider.fields() ,provider.geometryType(), provider.crs() , "ESRI Shapefile")
        if output_network_writer.hasError() != QgsVectorFileWriter.NoError:
            print "Error when creating shapefile: ", output_network_writer.errorMessage()
        del output_network_writer
        output_network=QgsVectorLayer(output_path,"output_copied","ogr")
        QgsMapLayerRegistry.instance().addMapLayer(output_network)
        output_network.startEditing()
        output_network.addFeatures([x for x in output.getFeatures()])
        output_network.commitChanges()
        output_network.removeSelection()

        self.iface.mapCanvas().refresh()

        self.dlg.progress_bar_2.setValue(1)

        tools.clean_duplicates(output_network)
        tools.clean_two_ends(output_network, distance_threshold_two)

        network_merged=self.tools.merge_lines(output_network)

        tools.clean_two_ends(network_merged, distance_threshold_two)

        self.dlg.progress_bar_2.setValue(2)
        # TO DO: add clean triangles

    def active_layers(self):
        # list of active layers for the comboxes
        self.dlg.choose_input_layer.clear()
        layers = self.iface.legendInterface().layers()
        layers_list = []
        for layer in layers:
            if (layer.wkbType() == 2 or layer.wkbType() == 5):
                layers_list.append(layer.name())
        # adding layers to the comboboxes
        if not len(layers_list) == 0:
            self.dlg.choose_input_layer.addItems(layers_list)

    def active_layers_2(self):
        # list of active layers for the comboxes
        self.dlg.choose_input_layer_2.clear()
        layers_2 = self.iface.legendInterface().layers()
        layers_2_list=[]
        for layer in layers_2:
            if (layer.wkbType() == 2 or layer.wkbType() == 5):
                layers_2_list.append(layer.name())
        # adding layers to the comboboxes
        if not len(layers_2_list) == 0:
            self.dlg.choose_input_layer_2.addItems(layers_2_list)

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.active_layers()
        self.active_layers_2()
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    def refresh(self):
        self.active_layers()
        self.active_layers_2()
        self.dlg.path_output.setPlaceholderText("Save as temporary layer...")
        self.dlg.path_output_2.setPlaceholderText("Save as temporary layer...")
        self.dlg.progress_bar.reset()
        self.dlg.progress_bar_2.reset()

    def closeEvent(self,event):
        self.refresh()
        #self.dialogClosed.emit()
        return self.dlg.close()