import numpy as np
from qtpy import QtWidgets
from qtpy.QtCore import QThread

from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataFromPlugins, Axis, DataToExport
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter
from pymodaq_plugins_redpitaya.utils import Config

from pymeasure.instruments.redpitaya.redpitaya_scpi import RedPitayaScpi

plugin_config = Config()


class DAQ_1DViewer_RedPitayaSCPI(DAQ_Viewer_base):
    """ Instrument plugin class for a 1D viewer.
    
    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Viewer module through
    inheritance via DAQ_Viewer_base. It makes a bridge between the DAQ_Viewer module and the
    Python wrapper of a particular instrument.

    * Should be compatible with all redpitaya flavour using the SCPI communication protocol
    * Tested with the STEMlab 125-14 version
    * PyMoDAQ >= 4.1.0

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.

    """
    params = comon_parameters+[
        {'title': 'IP Address:', 'name': 'ip_address', 'type': 'str',
         'value': plugin_config('ip_address')},
        {'title': 'Port:', 'name': 'port', 'type': 'int', 'value': plugin_config('port')},
        {'title': 'Board name:', 'name': 'bname', 'type': 'str', 'readonly': True},
        {'title': 'Sampling:', 'name': 'sampling', 'type': 'group', 'children': [
            {'title': 'Decimation:', 'name': 'decimation', 'type': 'int', 'step': 2, 'max': 2**16},
            {'title': 'Sample rate:', 'name': 'sample_rate', 'type': 'int', 'readonly': True},
            {'title': 'Nsamples:', 'name': 'nsamples', 'type': 'int', },
            {'title': 'All samples:', 'name': 'all_samples', 'type': 'bool', 'value': False},
         ]},
        {'title': 'Triggering:', 'name': 'triggering', 'type': 'group', 'children': [
            {'title': 'Source:', 'name': 'source', 'type': 'list',
             'limits': RedPitayaScpi.TRIGGER_SOURCES},
            {'title': 'level (V):', 'name': 'level', 'type': 'float', },
        ]},
        ]

    def ini_attributes(self):
        self.controller: RedPitayaScpi = None
        self.x_axis: Axis = None

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        if param.name() == 'decimation':
            self.controller.decimation = param.value()
            self.settings.child('sampling', 'decimation').setValue(self.controller.decimation)
            self.settings.child('sampling', 'sample_rate').setValue(self.controller.CLOCK /
                                                        self.controller.decimation)

    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator/detector by controller
            (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        self.ini_detector_init(old_controller=controller,
                               new_controller=RedPitayaScpi(ip_address=self.settings['ip_address'],
                                                            port=self.settings['port']))
        bname = self.controller.name
        self.settings.child('bname').setValue(bname)
        self.settings.child('sampling', 'nsamples').setValue(self.controller.acq_size)
        self.settings.child('sampling', 'nsamples').setLimits((1, self.controller.acq_size))
        self.settings.child('sampling', 'sample_rate').setValue(self.controller.CLOCK /
                                                    self.controller.decimation)
        self.settings.child('sampling', 'decimation').setValue(self.controller.decimation)
        info = f"Succesfully connected to the Redpitaya {bname} board"
        initialized = True
        return info, initialized

    def close(self):
        """Terminate the communication protocol"""
        pass

    def grab_data(self, Naverage=1, **kwargs):
        """Start a grab from the detector

        Parameters
        ----------
        Naverage: int
            Number of hardware averaging (if hardware averaging is possible, self.hardware_averaging should be set to
            True in class preamble and you should code this implementation)
        kwargs: dict
            others optionals arguments
        """
        self.controller.acquisition_reset()
        self.controller.decimation = self.settings['sampling', 'decimation']
        self.controller.acq_format = 'ASCII'
        self.controller.acq_units = 'VOLTS'
        self.controller.acq_trigger_level = self.settings['triggering', 'level']
        self.controller.acquisition_start()
        QThread.msleep(1000)
        self.controller.acq_trigger_source = self.settings['triggering', 'source']

        while not self.controller.acq_trigger_status:
            QThread.msleep(10)
            QtWidgets.QApplication.processEvents()

        while not self.controller.acq_buffer_filled:
            QThread.msleep(10)
            QtWidgets.QApplication.processEvents()
        if self.settings['sampling', 'all_samples']:
            data_array = self.controller.analog_in[1].get_data_from_ascii()
        else:
            data_array = self.controller.analog_in[1].get_data_from_ascii(8192,
                npts=self.settings['sampling', 'nsamples'])
        axis = Axis('time', units='s', offset=self.controller.acq_trigger_delay_ns,
                    scaling=self.controller.decimation / self.controller.CLOCK,
                    size=len(data_array))
        self.dte_signal.emit(DataToExport('myplugin',
                                          data=[DataFromPlugins(name='RedPitaya', data=[data_array],
                                                                dim='Data1D', labels=['AI0'],
                                                                axes=[axis])]))

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        self.controller.acquisition_stop()
        return ''


if __name__ == '__main__':
    main(__file__)
