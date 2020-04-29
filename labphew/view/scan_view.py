"""
labphew.view.scan_window.py
===========
The main purpose of the scan_window and its derivatives is to view the progress of one-time operations
called by an operator that is already initialized in the monitor_window.
It implements a form where the user can change the input port,
and delay between measurements. It has control also over the output port and range.

TODO:
    - build the UI without a design file
    - think about and add a default operation

"""
import os
import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt, QThread, QTimer
from PyQt5.QtWidgets import QMainWindow, QWidget, QPushButton, QVBoxLayout, QApplication, QSlider, QLabel
from PyQt5.QtGui import QFont, QIcon

from labphew import Q_
from .general_worker import WorkThread


class ScanWindow(QtWidgets.QMainWindow):
    def __init__(self, operator, parent=None):

        super().__init__(parent)
        self.operator = operator
        p = os.path.dirname(__file__)
        self.directory = p
        uic.loadUi(os.path.join(p, 'design/UI/scan_window.ui'), self)

        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_scan)

        self.main_plot = pg.PlotWidget()
        layout = self.centralwidget.layout()
        layout.addWidget(self.main_plot)
        self.ydata = np.zeros((0))
        self.xdata = np.zeros((0))
        self.p = self.main_plot.plot(self.xdata, self.ydata)

        self.startButton.clicked.connect(self.start_scan)
        self.stopButton.clicked.connect(self.stop_scan)

        self.outChannelLine.setText('{}'.format(self.operator.properties['Scan']['channel_out']))
        self.outStartLine.setText('{:~}'.format(Q_(self.operator.properties['Scan']['start'])))
        self.outStopLine.setText('{:~}'.format(Q_(self.operator.properties['Scan']['stop'])))
        self.outStepLine.setText('{:~}'.format(Q_(self.operator.properties['Scan']['step'])))

        self.inChannelLine.setText('{}'.format(self.operator.properties['Scan']['channel_in']))
        self.inDelayLine.setText('{:~}'.format(Q_(self.operator.properties['Scan']['delay'])))

        self.running_scan = False

        self.action_Save.triggered.connect(self.save_data)

        menubar = self.menuBar()
        self.scanMenu = menubar.addMenu('&Scan')
        self.start_scan_action = QtWidgets.QAction("Start Scan", self)
        self.start_scan_action.setShortcut('Ctrl+Shift+S')
        self.start_scan_action.setStatusTip('Start the scan')
        self.start_scan_action.triggered.connect(self.start_scan)
        self.scanMenu.addAction(self.start_scan_action)


    def start_scan(self):
        """Starts the scan as defined in the Experiment model. Gets the parameters from the GUI, i.e.:
        it gets the input port and delay, the output port and range.
        It updates the plot with the proper units and ranges and creates a worker thread for running the
        scan.
        A timer will be responsible for updating the values into the plot.
        """
        if self.running_scan:
            print('Scan already running')
            return

        self.running_scan = True
        self.operator.properties['Scan'].update({
            'channel_out': int(self.outChannelLine.text()),
            'start': Q_(self.outStartLine.text()),
            'stop': Q_(self.outStopLine.text()),
            'step': Q_(self.outStepLine.text()),
            'channel_in': int(self.inChannelLine.text()),
            'delay': Q_(self.inDelayLine.text()),
        })
        xlabel = self.operator.properties['Scan']['channel_out']
        units = self.operator.properties['Scan']['start'].u
        ylabel = self.operator.properties['Scan']['channel_in']

        self.main_plot.setLabel('bottom', 'Port: {}'.format(xlabel),
                                units=units)
        self.main_plot.setLabel('left', 'Port: {}'.format(ylabel), units='V')

        self.worker_thread = WorkThread(self.operator.do_scan)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.finished.connect(self.stop_scan)
        self.worker_thread.start()
        refresh_time = Q_(self.operator.properties['GUI']['refresh_time'])
        self.update_timer.start(refresh_time.m_as('ms'))

    def update_scan(self):
        """Updates the plot with the available data in the application model. This method is triggered
        through a timer that starts with the start_scan method.
        The method also monitors whether the scan is still running or not. If it has stopped it will update
        the GUI in order to know it.
        """
        self.xdata = self.operator.xdata_scan
        self.ydata = self.operator.ydata_scan

        self.p.setData(self.xdata, self.ydata)

        if not self.operator.running_scan:
            self.stop_scan()

    def stop_scan(self):
        """Stops the scan if it is running. It sets the proper variable to the application model in order
        to finish it in an elegant way. It stops the update timer and calls the update plot one last time
        in order to display the very last available data.
        """
        if not self.running_scan:
            return

        print('Stopping Scan')
        self.running_scan = False
        self.operator.stop_scan = True
        self.update_timer.stop()
        self.xdata = self.operator.xdata_scan
        self.ydata = self.operator.ydata_scan

        self.p.setData(self.xdata, self.ydata)

    def save_data(self):
        """Saves the data to disk. It opens a Dialog for selecting the directory. The default filename for
        the data is 'scan_data.dat'. The application model takes care of handling the saving itself.
        """
        self.directory = str(QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory", self.directory))
        filename = 'scan_data.dat'
        file = os.path.join(self.directory, filename)

        self.operator.save_scan_data(file)

    def closeEvent(self, event):
        print('Closing')
        super().closeEvent(event)


if __name__ == "__main__":
    """
    The scan_window is generally called as a child of the monitor_window. 
    In case, for testing or for fun, the scan_window if executed as standalone, it will by default call the 
    labphew blink operator.
    >>> REVISIT AFTER FINISHIN THE BLINK APPLICATION 
    """
    import sys
    from PyQt5.QtWidgets import QApplication
    from labphew.model.blink_model import Operator

    e = Operator()
    session = {'port_monitor': 1,
               'time_resolution': Q_('1ms'),
               'refresh_time': Q_('100ms'),
               'total_time': Q_('15s'),
               'scan_port_out': 1,
               'scan_start': Q_('0.1V'),
               'scan_stop': Q_('0.7V'),
               'scan_step': Q_('0.1V'),
               'scan_port_in': 2,
               'scan_delay': Q_('10ms'),
               }
    e.properties = session

    app = QApplication(sys.argv)
    s = ScanWindow(e)
    s.show()
    app.exit(app.exec_())