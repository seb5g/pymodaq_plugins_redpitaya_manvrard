
from typing import Union, List, Dict
from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, comon_parameters_fun,
                                                          main, DataActuatorType, DataActuator)

from pymodaq_utils.utils import ThreadCommand  # object used to send info back to the main thread
from pymodaq_gui.parameter import Parameter

from pymeasure.instruments.redpitaya.redpitaya_scpi import RedPitayaScpi, AnalogOutputFastChannel


from pymodaq_data import Q_

from pymodaq_plugins_redpitaya.utils import Config

plugin_config = Config()


# TODO:
# (1) change the name of the following class to DAQ_Move_TheNameOfYourChoice X
# (2) change the name of this file to daq_move_TheNameOfYourChoice ("TheNameOfYourChoice" should be the SAME
#     for the class name and the file name.) X
# (3) this file should then be put into the right folder, namely IN THE FOLDER OF THE PLUGIN YOU ARE DEVELOPING:
#     pymodaq_plugins_my_plugin/daq_move_plugins X
class DAQ_Move_RedpitayaSCPI(DAQ_Move_base):
    """ Instrument plugin class for Red Pitaya

       This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Move module through
       inheritance via DAQ_Move_base. It makes a bridge between the DAQ_Move module and the
       Python wrapper of a particular instrument.

       * Should be compatible with all redpitaya flavours using the SCPI communication protocol
       * Tested with the STEMlab 125-14 version
       * PyMoDAQ >= 4.1.0
       * Linux Ubuntu
       *
       """

    """ Instrument plugin class for an actuator.
    
    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Move module through inheritance via
    DAQ_Move_base. It makes a bridge between the DAQ_Move module and the Python wrapper of a particular instrument.

    TODO Complete the docstring of your plugin with:
        * The set of controllers and actuators that should be compatible with this instrument plugin. X
        * With which instrument and controller it has been tested. X
        * The version of PyMoDAQ during the test. X
        * The version of the operating system. <--
        * Installation instructions: what manufacturer’s drivers should be installed to make it run? <--

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.
         
    # TODO add your particular attributes here if any

    """
    is_multiaxes = True
    _axis_names: Union[List[str], Dict[str, int]] = ['amplitude', 'frequency']
    _controller_units: Union[str, List[str]] = ['V','Hz']
    # TODO  a single str (the same one is applied to all axes) or a list of str (as much as the number of axes)
    _epsilon: Union[float, List[float]] = 0.1  # TODO replace this by a value that is correct depending on your controller
    # TODO it could be a single float of a list of float (as much as the number of axes)
    data_actuator_type = DataActuatorType.DataActuator  # wether you use the new data style for actuator otherwise set this
    # as  DataActuatorType.float  (or entirely remove the line)

    plugin_config = Config()

    params = [   # TODO for your custom plugin: elements to be added here as dicts in order to control your custom stage
                 {'title': 'IP Address:', 'name': 'ip_address', 'type': 'str',
                  'value': plugin_config('ip_address')},
                 {'title': 'Port:', 'name': 'port', 'type': 'int', 'value': plugin_config('port')},
                 {'title': 'Board name:', 'name': 'bname', 'type': 'str', 'readonly': True},
                 {'title': 'Channel', 'name': 'channel', 'type': 'list', 'limits':{'1': 1, '2': 2},
                  'value': plugin_config('generator', 'channel')},
                 {'title': 'Enable', 'name': 'enable', 'type': 'list',
                  'limits': AnalogOutputFastChannel.STATE, 'value': plugin_config('generator', 'state')},
                 #{'title': 'Triggering:', 'name': 'triggering', 'type': 'group', 'children': [
                     #{'title': 'Source:', 'name': 'source', 'type': 'list',
                      #'limits': AnalogOutputFastChannel.GEN_TRIGGER_SOURCES, 'value': plugin_config('trigger', 'source')},
                 #]},
                {'title': 'Shape', 'name': 'shape', 'type': 'list',
                      'limits': AnalogOutputFastChannel.SHAPES, 'value': plugin_config('generator', 'shape')},
                 {'title': 'Offset', 'name': 'offset', 'type': 'float', 'limits' : AnalogOutputFastChannel.OFFSETS,
                  'value': plugin_config('generator', 'offset')},
                {'title': 'Phase', 'name': 'phase', 'type': 'float', 'limits' : AnalogOutputFastChannel.PHASES,
                      'value': plugin_config('generator', 'phase')},
                {'title': 'Dutycycle', 'name': 'dutycycle', 'type': 'float', 'limits' : AnalogOutputFastChannel.CYCLES,
                      'value': plugin_config('generator', 'cycle')},
                ] + comon_parameters_fun(is_multiaxes, axis_names=_axis_names, epsilon=_epsilon)
    # _epsilon is the initial default value for the epsilon parameter allowing pymodaq to know if the controller reached
    # the target value. It is the developer responsibility to put here a meaningful value

    def ini_attributes(self):
        #  TODO declare the type of the wrapper (and assign it to self.controller) you're going to use for easy
        #  autocompletion
        self.controller: RedPitayaScpi = None

        #TODO declare here attributes you want/need to init with a default value
        pass

    def get_actuator_value(self):
        """Get the current value from the hardware with scaling conversion.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """
        pos = DataActuator(data=getattr(self.aout, self.axis_name),
                           units=self.axis_unit)  # when writing your own plugin replace this line
        pos = self.get_position_with_scaling(pos)

        return pos

    def user_condition_to_reach_target(self) -> bool:
        """ Implement a condition for exiting the polling mechanism and specifying that the
        target value has been reached

       Returns
        -------
        bool: if True, PyMoDAQ considers the target value has been reached
        """
        # TODO either delete this method if the usual polling is fine with you, but if need you can
        #  add here some other condition to be fullfilled either a completely new one or
        #  using or/and operations between the epsilon_bool and some other custom booleans
        #  for a usage example see DAQ_Move_brushlessMotor from the Thorlabs plugin
        return True

    def close(self):
        """Terminate the communication protocol"""
        self.enable(False)

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        if param.name() == 'axis':

            if param.value() =='frequency':
                self.settings.child('bounds', 'min_bound').setValue(1e-6)
                self.settings.child('bounds', 'max_bound').setValue(50e6)
            elif param.value == 'amplitude':
                self.settings.child('bounds', 'min_bound').setValue(0)
                self.settings.child('bounds', 'max_bound').setValue(1)

            #self.settings['bounds', 'is_bounds']
            self.settings.child('bounds', 'is_bounds').value()
            self.settings.child('bounds', 'is_bounds').setValue(True)
        elif param.name() == 'enable':
            self.aout.enable = param.value()
        elif param.name() == 'shape':
            self.aout.shape = param.value()
        elif param.name() == 'offset':
            self.aout.offset = param.value()
        elif param.name() == 'phase':
            self.aout.phase = param.value()
        elif param.name() == 'dutycycle':
            self.aout.dutycycle = param.value()

    def is_enabled(self) -> bool:
        return self.settings['enable'] == 'ON'

    def enable(self, status = True):
        self.aout.enable = 'ON' if status else 'OFF'

    @property
    def aout(self):
        """ It defines what output channel the user chose"""
        return self.controller.analog_out[self.settings['channel']]

    def ini_stage(self, controller=None):
        """Actuator communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator by controller (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """

        if self.is_master:  # is needed when controller is master
            self.controller = RedPitayaScpi(ip_address=plugin_config('ip_address')) #  arguments for instantiation!)
        else:
            self.controller = controller

        self.aout.shape = self.settings['shape'] #plugin_config('generator', 'shape')

        self.settings.child('bounds', 'is_bounds').setOpts(readonly=True)

        self.aout.enable = self.settings['enable']
        self.aout.run()

        info = "Whatever info you want to log"
        initialized = True
        return info, initialized

    def move_abs(self, value: DataActuator):
        """ Move the actuator to the absolute target defined by value

        Parameters
        ----------
        value: (float) value of the absolute target positioning
        """
        if not self.is_enabled():
            self.enable()
        value = self.check_bound(value)  #if user checked bounds, the defined bounds are applied here
        self.target_value = value
        value = self.set_position_with_scaling(value)  # apply scaling if the user specified one

        setattr(self.controller.analog_out[self.settings['channel']], self.axis_name, value.value(self.axis_unit))

    def move_rel(self, value: DataActuator):
        """ Move the actuator to the relative target actuator value defined by value

        Parameters
        ----------
        value: (float) value of the relative target positioning
        """
        value = self.check_bound(self.current_position + value) - self.current_position
        self.target_value = value + self.current_position
        self.move_abs(self.target_value)

    def move_home(self):
        """Call the reference method of the controller"""
        pass

    def stop_motion(self):
      """Stop the actuator and emits move_done signal"""
    pass


if __name__ == '__main__':
    main(__file__)
