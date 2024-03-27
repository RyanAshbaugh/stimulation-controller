import pyqtgraph as pg
import numpy as np
import sys, time
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import ( Parameter, ParameterTree, ParameterItem,
    registerParameterType )
import pyqtgraph.configfile
from Arduino import Arduino
from sys import platform
import serial.tools.list_ports
import keyboard
import os

# takes care of high resolution multiple monitor dpi scaling issues
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
QtGui.QApplication.setHighDpiScaleFactorRoundingPolicy( \
        QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

class StimulationController(QtGui.QWidget):
    def __init__(self):

        # pin numbers for leds/stimulation
        self.active_pin = 11
        self.sham_pin = 10
        self.aux_pin = 9
        self.stim_on_pin = 8
        self.PWR_on_pin = 12
        self.aux_stim_1 = 7
        self.aux_stim_2 = 6

        # analog pins
        self.external_trigger_pin = 7

        # relay pins
        self.active_relay_1 = 2
        self.active_relay_2 = 5

        self.sham_relay_1 = 3
        self.sham_relay_2 = 4

        self.fan_pin = 13

        self.external_trigger_threshold = 300

        QtGui.QWidget.__init__(self)

        # parameters for stimulation
        self.params = [ 
            { 'name': 'Delay time', 'type': 'float', 'value': 1 },
            { 'name': 'Pulse width', 'type': 'float', 'value': 0.25 },
            { 'name': 'Pulse period', 'type': 'float', 'value': 0.5 },
            { 'name': 'No. of pulses', 'type': 'int', 'value': 2 },
            { 'name': 'Burst period', 'type': 'int', 'value': 1 },
            { 'name': 'No. of bursts', 'type': 'int', 'value': 2 },
            { 'name': 'Stimulations (trigger)', \
                    'type': 'int', 'value': 1 },
            { 'name': 'Save parameters', 'type': 'action'},
            { 'name': 'Load parameters', 'type': 'action'},
            ]
        self.p_tree = Parameter.create( name='params', type='group', 
            children=self.params )
        self.pt_widget = ParameterTree()
        self.pt_widget.setParameters( self.p_tree, showTop=False )
        self.pt_widget.setWindowTitle( 'Stimulation Controller' )

        # saving and loading stuff
        self.p_tree.param('Save parameters').sigActivated.connect( \
                self.saveParameters)
        self.p_tree.param('Load parameters').sigActivated.connect( \
                self.loadParameters)

        self.p_tree.param("Delay time").sigValueChanged.connect( \
                self.checkConditionLegality)
        self.p_tree.param("Pulse width").sigValueChanged.connect( \
                self.checkConditionLegality)
        self.p_tree.param("Pulse period").sigValueChanged.connect( \
                self.checkConditionLegality)
        self.p_tree.param("No. of pulses").sigValueChanged.connect( \
                self.checkConditionLegality)
        self.p_tree.param("Burst period").sigValueChanged.connect( \
                self.checkConditionLegality)
        self.p_tree.param("No. of bursts").sigValueChanged.connect( \
                self.checkConditionLegality)

        # create q widget and grid layout to be filled
        self.win = QtGui.QWidget()
        self.layout = QtGui.QGridLayout()
        self.win.setLayout( self.layout )
        self.layout.addWidget( self.pt_widget, 1, 0, 1, 4 )

        # plot of the stimulation parameters
        self.plot = pg.GraphicsLayoutWidget( show=True, title='Stimulation Graph' )
        self.layout.addWidget( self.plot, 1, 5, 3, 1 )
        self.p1 = self.plot.addPlot( title="Stimulation Graph" )
        self.plotStimulus()
        self.stimulate_button = QtGui.QPushButton( 'Stimulate' )
        self.layout.addWidget( self.stimulate_button, 5, 5, 1, 1 )
        self.stimulate_button.clicked.connect( self.triggerStimulus )

        # display whether a device has been connected
        self.connection_status_text = QtGui.QLabel( 'No device connected' )
        self.connection_status_text.setAlignment( QtCore.Qt.AlignCenter )
        self.layout.addWidget( self.connection_status_text, 4, 5, 1, 1 )

        # button for using the active mode
        self.active_button = QtGui.QPushButton( "Active" )
        self.active_button.setCheckable( True )
        self.active_button.clicked.connect( self.activeButtonClick )
        self.active_button.setStyleSheet( "background-color : lightgrey" )
        self.layout.addWidget( self.active_button, 5, 0, 1, 2 )

        # button for sham mode
        self.sham_button = QtGui.QPushButton( "Sham" )
        self.sham_button.setCheckable( True )
        self.sham_button.clicked.connect( self.shamButtonClick )
        self.sham_button.setStyleSheet( "background-color : lightgrey" )
        self.layout.addWidget( self.sham_button, 5, 2, 1, 2 )

        # Aux 1 and 2 label
        self.aux_1_label = QtGui.QLabel( 'Aux 1:' )
        self.aux_1_label.setAlignment( QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        self.layout.addWidget( self.aux_1_label, 3, 0, 1, 1 )
        self.aux_2_label = QtGui.QLabel( 'Aux 2:' )
        self.aux_2_label.setAlignment( QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        self.layout.addWidget( self.aux_2_label, 4, 0, 1, 1 )

        # radio buttons for auxiliary ports
        # aux 1 first
        layout = QtGui.QHBoxLayout()
        widget = QtGui.QWidget(self)
        widget.setLayout(layout)

        self.aux_1_number_group = QtGui.QButtonGroup(widget)
        self.aux_1_output_radio_button = QtGui.QRadioButton("output")
        self.aux_1_output_radio_button.mode = "output"
        self.aux_1_number_group.addButton( self.aux_1_output_radio_button )
        self.aux_1_output_radio_button.toggled.connect( \
                self.aux1ModeRadioButton )
        layout.addWidget( self.aux_1_output_radio_button )

        self.aux_1_input_radio_button = QtGui.QRadioButton("input")
        self.aux_1_input_radio_button.mode = "input" 
        self.aux_1_number_group.addButton( self.aux_1_input_radio_button )
        self.aux_1_input_radio_button.toggled.connect( \
                self.aux1ModeRadioButton )
        layout.addWidget( self.aux_1_input_radio_button )

        self.aux_1_off_radio_button = QtGui.QRadioButton("off")
        self.aux_1_off_radio_button.mode = "off"
        self.aux_1_number_group.addButton( self.aux_1_off_radio_button )
        self.aux_1_off_radio_button.setChecked(True)
        self.aux_1_off_radio_button.toggled.connect( \
                self.aux1ModeRadioButton )
        layout.addWidget( self.aux_1_off_radio_button )
        self.layout.addWidget( widget, 3, 1, 1, 3 )

        # aux 2
        aux_2_layout = QtGui.QHBoxLayout()
        aux_2_widget = QtGui.QWidget(self)
        aux_2_widget.setLayout(aux_2_layout)
        self.aux_2_number_group = QtGui.QButtonGroup(aux_2_widget)

        self.aux_2_output_radio_button = QtGui.QRadioButton("output")
        self.aux_2_output_radio_button.mode = "output"
        self.aux_2_number_group.addButton( self.aux_2_output_radio_button )
        self.aux_2_output_radio_button.toggled.connect( \
                self.aux2ModeRadioButton )
        aux_2_layout.addWidget( self.aux_2_output_radio_button )

        self.aux_2_input_radio_button = QtGui.QRadioButton("input")
        self.aux_2_input_radio_button.mode = "input"
        self.aux_2_number_group.addButton( self.aux_2_input_radio_button )
        self.aux_2_input_radio_button.toggled.connect( \
                self.aux2ModeRadioButton )
        aux_2_layout.addWidget( self.aux_2_input_radio_button )

        self.aux_2_off_radio_button = QtGui.QRadioButton("off")
        self.aux_2_off_radio_button.mode = "off"
        self.aux_2_number_group.addButton( self.aux_2_off_radio_button )
        self.aux_2_off_radio_button.setChecked(True)
        self.aux_2_off_radio_button.toggled.connect( \
                self.aux2ModeRadioButton )
        aux_2_layout.addWidget( self.aux_2_off_radio_button )
        self.layout.addWidget( aux_2_widget, 4, 1, 1, 3 )

        # radio button external trigger and manual mode
        self.manual_radio_button = QtGui.QRadioButton("Manual Trigger")
        self.manual_radio_button.setChecked(True)
        self.manual_radio_button.external_trigger_mode = False
        self.external_trigger = self.manual_radio_button.external_trigger_mode
        self.manual_radio_button.toggled.connect( self.triggerRadioButton )
        self.layout.addWidget( self.manual_radio_button, 2, 0, 1, 2 )

        self.external_radio_button = QtGui.QRadioButton("External Trigger")
        self.external_radio_button.external_trigger_mode = True
        self.external_radio_button.toggled.connect( self.triggerRadioButton )
        self.layout.addWidget( self.external_radio_button, 2, 2, 1, 2 )

        self.port_name = ""

        self.connectArduino() 

    def connectArduino(self):
        CH340_ports = []
        if platform == "linux" or platform == "linux2":
            #self.port_name = "/dev/ttyACM0"
            self.port_name = "/dev/ttyUSB0"
        elif platform == "win32":
            ports = list( serial.tools.list_ports.comports() )
            for p in ports:
                if "CH340" in p.description:
                    self.port_name = p.device
                    CH340_ports.append( self.port_name )

            CH340_ports.sort()
            for ii in range( len( CH340_ports ) ):
                try:
                    self.port_name = CH340_ports[ii]
                    self.board = Arduino( "115200", port=self.port_name )
                    self.connection_status_text.setText( 'Device connected to '\
                            'COM port: ' + str(self.port_name) )
                    break
                except (ValueError, serial.serialutil.SerialException):
                    self.connection_status_text.setText( 'No COM device found' )


        # set pin modes
        self.board.pinMode( self.PWR_on_pin, "OUTPUT" )
        self.board.pinMode( self.active_pin, "OUTPUT" )
        self.board.pinMode( self.sham_pin, "OUTPUT" )
        self.board.pinMode( self.aux_pin, "OUTPUT" )
        self.board.pinMode( self.stim_on_pin, "OUTPUT" )
        self.board.pinMode( self.active_relay_1, "OUTPUT" )
        self.board.pinMode( self.active_relay_2, "OUTPUT" )
        self.board.pinMode( self.sham_relay_1, "OUTPUT" )
        self.board.pinMode( self.sham_relay_2, "OUTPUT" )
        self.board.pinMode( self.fan_pin, "OUTPUT" )
        
        self.board.digitalWrite( self.PWR_on_pin, "HIGH" )
        self.board.digitalWrite( self.fan_pin, "HIGH" )

    def checkConditionLegality( self ):

        if self.p_tree.param("Pulse period").value() < \
                self.p_tree.param("Pulse width").value():
            self.p_tree.param("Pulse period").setValue( \
                    self.p_tree.param("Pulse width").value() + 1 )

        if self.p_tree.param("Burst period").value() < \
                ( self.p_tree.param("Pulse period").value() * \
                self.p_tree.param("No. of pulses").value() ):
            self.p_tree.param("Burst period").setValue( \
                (self.p_tree.param("Pulse period").value() * \
                self.p_tree.param("No. of pulses").value()) + 1 )

        self.plotStimulus()

    def plotStimulus(self):

        self.p1.clear()

        x_data = [ 0, self.p_tree.param("Delay time").value() ]
        y_data = [ 0, 0 ]
        for ii in range(self.p_tree.param("No. of bursts").value()):
            burst_offset = ii *self.p_tree.param( "Burst period" ).value()
            for jj in range(self.p_tree.param("No. of pulses").value()):
                pulse_offset = jj*self.p_tree.param("Pulse period").value()+\
                        burst_offset

                x_data.append( pulse_offset + \
                        self.p_tree.param("Delay time").value() )
                y_data.append( 1 )

                x_data.append( pulse_offset + \
                        self.p_tree.param("Pulse width").value() + \
                        self.p_tree.param("Delay time").value() )
                y_data.append( 1 )

                x_data.append( pulse_offset + \
                        self.p_tree.param("Pulse width").value()+0.000001 + \
                        self.p_tree.param("Delay time").value() )
                y_data.append( 0 )

                x_data.append( pulse_offset + \
                        self.p_tree.param("Pulse period").value() + \
                        self.p_tree.param("Delay time").value() )
                y_data.append( 0 )
            
            x_data.append(burst_offset + \
                    self.p_tree.param("Burst period").value() + \
                    self.p_tree.param("Delay time").value())
            y_data.append( 0 )

        self.p1.plot( x_data, y_data )

    def activeButtonClick(self):
        self.setModePinsLow()
        # if it got toggled on, turn off the others and change colors
        if self.active_button.isChecked():
            if self.sham_button.isChecked():
                self.sham_button.toggle()
            self.active_button.setStyleSheet( "background-color : lightgreen" )
            self.sham_button.setStyleSheet( "background-color : lightgrey" )
            self.board.digitalWrite( self.active_pin, "HIGH" )
        # if toggled off, just change colors
        else:
            self.active_button.setStyleSheet( "background-color : lightgrey" )
            self.sham_button.setStyleSheet( "background-color : lightgrey" )

    def shamButtonClick(self):
        self.setModePinsLow()
        # if it got toggled on, turn off the others and change colors
        if self.sham_button.isChecked():
            if self.active_button.isChecked():
                self.active_button.toggle()
            self.active_button.setStyleSheet( "background-color : lightgrey" )
            self.sham_button.setStyleSheet( "background-color : red" )
            self.board.digitalWrite( self.sham_pin, "HIGH" )
        # if toggled off, just change colors
        else:
            self.active_button.setStyleSheet( "background-color : lightgrey" )
            self.sham_button.setStyleSheet( "background-color : lightgrey" )

    def triggerRadioButton( self ):

        radio_button = self.sender()
        self.external_trigger = radio_button.external_trigger_mode

    def aux1ModeRadioButton( self ):

        aux_radio_button = self.sender()

        if aux_radio_button.mode == "output":
            self.board.pinMode( self.aux_stim_1, "OUTPUT" )
            self.board.digitalWrite( self.aux_pin, "HIGH" )
            self.external_trigger_pin = self.aux_stim_2
        elif aux_radio_button.mode == "input":
            self.board.pinMode( self.aux_stim_1, "INPUT" )
            self.board.digitalWrite( self.aux_stim_1, "LOW" )
            self.board.digitalWrite( self.aux_pin, "HIGH" )
            self.external_trigger_pin = self.aux_stim_1
        else:
            self.board.digitalWrite( self.aux_pin, "LOW" )

    def aux2ModeRadioButton( self ):

        aux_radio_button = self.sender()

        if aux_radio_button.mode == "output":
            self.board.pinMode( self.aux_stim_2, "OUTPUT" )
            self.board.digitalWrite( self.aux_pin, "HIGH" )
            self.external_trigger_pin = self.aux_stim_1
        elif aux_radio_button.mode == "input":
            self.board.pinMode( self.aux_stim_2, "INPUT" )
            self.board.digitalWrite( self.aux_stim_2, "LOW" )
            self.board.digitalWrite( self.aux_pin, "HIGH" )
            self.external_trigger_pin = self.aux_stim_2
        else:
            self.board.digitalWrite( self.aux_pin, "LOW" )

    def triggerStimulus(self): 

        if self.external_trigger == True:
            #while( not(keyboard.is_pressed('q')) ):
            for ii in range( 0, self.p_tree.param( \
                    "Stimulations (trigger)").value() ):
                while( self.board.digitalRead( self.external_trigger_pin )!=1):
                    pass
                self.stimulate()

        elif self.external_trigger == False:

            self.stimulate()

    def stimulate(self):

        time.sleep(self.p_tree.param('Delay time').value())

        # for every burst
        for ii in range( 0, self.p_tree.param( 'No. of bursts' ).value() ):

            # for each pulse
            for jj in range( 0, self.p_tree.param( 'No. of pulses' ).value() ):
                if self.active_button.isChecked():
                    self.board.digitalWrite( self.active_relay_1, "HIGH" )
                    self.board.digitalWrite( self.active_relay_2, "HIGH" )
                elif self.sham_button.isChecked():
                    self.board.digitalWrite( self.sham_relay_1, "HIGH" )
                    self.board.digitalWrite( self.sham_relay_2, "HIGH" )
                self.auxStimulate()

                self.board.digitalWrite( self.stim_on_pin, "HIGH" )
                time.sleep( self.p_tree.param( 'Pulse width' ).value() )
                self.board.digitalWrite( self.stim_on_pin, "LOW" )
                self.setStimulusLow()

                # end of period, pause for remainder of period
                time.sleep( self.p_tree.param( 'Pulse period' ).value() - \
                        self.p_tree.param( 'Pulse width' ).value() )

            # pause for the remainder of the burst
            time.sleep( self.p_tree.param( 'Burst period' ).value() - \
                self.p_tree.param( 'Pulse period' ).value() * \
                self.p_tree.param( 'No. of pulses' ).value() )

    def auxStimulate( self ):
        if self.aux_1_output_radio_button.isChecked():
            self.board.digitalWrite( self.aux_stim_1, "HIGH" )
        if self.aux_2_output_radio_button.isChecked():
            self.board.digitalWrite( self.aux_stim_2, "HIGH" )

    def setModePinsLow( self ):
        self.board.digitalWrite( self.active_pin, "LOW" )
        self.board.digitalWrite( self.sham_pin, "LOW" )
        self.board.digitalWrite( self.stim_on_pin, "LOW" )
        
    def setStimulusLow( self ):
        self.board.digitalWrite( self.active_relay_1, "LOW" )
        self.board.digitalWrite( self.active_relay_2, "LOW" )
        self.board.digitalWrite( self.sham_relay_1, "LOW" )
        self.board.digitalWrite( self.sham_relay_2, "LOW" )
        if self.aux_1_output_radio_button.isChecked():
            self.board.digitalWrite( self.aux_stim_1, "LOW" )
        if self.aux_2_output_radio_button.isChecked():
            self.board.digitalWrite( self.aux_stim_2, "LOW" )

    def saveParameters(self):
        filename = pg.QtGui.QFileDialog.getSaveFileName(self, \
                "Save parameters", "untitled.cfg", "Config Files (*.cfg)")
        if isinstance(filename, tuple):
            filename = filename[0]  # Qt4/5 API difference
        if filename == '':
            return
        state = self.p_tree.saveState()
        pg.configfile.writeConfigFile(state, str(filename)) 
        
    def loadParameters(self):
        filename = pg.QtGui.QFileDialog.getOpenFileName(self, \
                "Load parameters", "", "Config Files (*.cfg)")
        if isinstance(filename, tuple):
            filename = filename[0]  # Qt4/5 API difference
        if filename == '':
            return
        state = pg.configfile.readConfigFile(str(filename)) 
        self.loadState(state)

    def loadState(self, state):
        self.p_tree.restoreState(state, removeChildren=False)

if __name__ == '__main__':
    if ( sys.flags.interactive != 1 ) or not hasattr( QtCore, 'PYQT_VERSION'):

        app = QtGui.QApplication( sys.argv )
        window_1 = StimulationController()
        window_1.win.resize( 1200, 600 )
        window_1.win.show()

        QtGui.QApplication.instance().exec_()


