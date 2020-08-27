# -*- coding: utf-8 -*-
#
# This file is part of the  project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" Tangodevice AgilisAGP

"""

__all__ = ["AgilisAGP", "main"]

# PyTango imports
import tango
from tango import DebugIt, DeviceProxy
from tango.server import run
from tango.server import Device, DeviceMeta
from tango.server import attribute, command, pipe
from tango.server import class_property, device_property
from tango import AttrQuality,DispLevel, DevState
from tango import AttrWriteType, PipeWriteType
# Additional import
# PROTECTED REGION ID(AgilisAGP.additionnal_import) ENABLED START #
from time import sleep
import serial
# PROTECTED REGION END #    //  AgilisAGP.additionnal_import



class AgilisAGP(Device):
    """
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(AgilisAGP.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  AgilisAGP.class_variable
    # ----------------
    # Class Properties

    # ----------------

    # read name of serial port ('com1' .. (Windows) or '/dev/ttyUSB0' .. (Linux)) 
    # read the address of the device (1..31)

# -----------------
    # Device Properties
    # -----------------

    Address = device_property(
        dtype='DevLong',
    )
    Port = device_property(
        dtype='DevString',
    )


    # some Constants
    __EOL = '\r\n'


# time to wait after sending a command.
    COMMAND_WAIT_TIME_SEC = 0.06

# Errors from page 64 of the manual
    __ERROR_NEG_END_OF_RUN = 1
    __ERROR_POS_END_OF_RUN = 2
    __ERROR_OUT_OF_RANGE   = 'C'

# States from page 65 of the manual
    __STATE_NOT_REFERENCED = ('3C', '0A', '0B', '0c' ,'0D', '0E', '0F', '10')
    __STATE_READY   = ('32', '33', '34', '35')
    __STATE_MOVING  = ('28', '1E')

# some private variables
    __ser_port = None
    __agpID    = ''
    __port     = ''
    
    __agp_state    = ''
    __error        = ''
  
    
    # ----------
    # Attributes
    # ----------

    Position = attribute(
        dtype='DevDouble',
        access=AttrWriteType.READ_WRITE,
        label="angle",
        unit="degree",
        display_unit="degree",
        format="%8.3f",
        doc = 'absolute position in degrees'
    )
    Conversion = attribute(
        dtype='DevDouble',
        access=AttrWriteType.READ_WRITE,
        unit="hardwareUnit/setUnit",
        memorized=True,
        hw_memorized=True,
    )
    UnitLimitMin = attribute(
        dtype='DevDouble',
        access=AttrWriteType.READ_WRITE,
        unit="degree",
        memorized=True,
        hw_memorized=True,
    )
    UnitLimitMax = attribute(
        dtype='DevDouble',
        access=AttrWriteType.READ_WRITE,
        unit="degree",
        memorized=True,
        hw_memorized=True,
    )
    
    
    # -----
    # Pipes
    # -----

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        self.info_stream("init_device()")
        Device.init_device(self)
        self.set_state(DevState.INIT)
        
        # PROTECTED REGION ID(AgilisAGP.init_device) ENABLED START #
        self.__position = 0.0
        self.__unit_limit_min = 0.0
        self.__unit_limit_max = 0.0
        self.__conversion = 0.0
        
        self.proxy = DeviceProxy(self.get_name())
        self.__agpID = str(self.Address)
        self.__port  = self.Port
        
        self.debug_stream("Get_name: %s" % (self.get_name()))
        self.debug_stream("Connecting to AgilisAGP on %s" %(self.__port))
        self.debug_stream("Device address: %s" %(self.__agpID))
            
        self.__ser_port = serial.Serial(
            port = self.__port,
            baudrate = 921600,
            bytesize = 8,
            stopbits = 1,
            parity = 'N',
            xonxoff = True,
            timeout = 0.050)    
        
        
        if self.__ser_port.isOpen():
            self.__ser_port.close()
        self.__ser_port.open()
        
        if ("CONEX-AGP" in self.read_controller_info()):
            self.set_status("The device is in ON state")
            self.set_state(DevState.ON)  
        else:
            self.set_status("The device is in OFF state")
            self.set_state(DevState.OFF)
            
        # PROTECTED REGION END #    //  AgilisAGP.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(AgilisAGP.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  AgilisAGP.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(AgilisAGP.delete_device) ENABLED START #
        if self.__ser_port.isOpen():
            self.__ser_port.close()
            self.set_status("The device is in OFF state")
            self.set_state(DevState.OFF)
        # PROTECTED REGION END #    //  AgilisAGP.delete_device
    
    
    def send_cmd(self, cmd):
        # PROTECTED REGION ID(AgilisAGP.send_cmd) ENABLED START #
        snd_str = cmd + self.__EOL
        self.__ser_port.flushOutput()
        self.debug_stream("write command: {:s}".format(snd_str))
        self.__ser_port.write(snd_str.encode("utf-8"))
        self.__ser_port.flush()
        # PROTECTED REGION END #    //  AgilisAGP.send_cmd    

    def get_cmd_error_string(self):
        error = self.write_read('TE?')
        return error.strip()
        
        
    # ------------------
    # Attributes methods
    # ------------------

    def read_Position(self):
        # PROTECTED REGION ID(AgilisAGP.Position_read) ENABLED START #
        self.__position = float(self.write_read('TP?'))/self.__conversion
        return self.__position
        # PROTECTED REGION END #    //  AgilisAGP.Position_read

    def write_Position(self, value):
        # PROTECTED REGION ID(AgilisAGP.Position_write) ENABLED START #
        if value>=self.__unit_limit_min and value<=self.__unit_limit_max:
            value = value * self.__conversion
            self.write_read('PA' + str(value))
            if self.__ERROR_OUT_OF_RANGE == self.get_cmd_error_string():
                self.set_status("The device is in ALARM state. Target position OUT OF RANGE")
                self.error_stream("device state: ALARM (position OUT OF RANGE)")
                self.set_state(DevState.ALARM) 
        else:
            self.set_status("The device is in ALARM state. Target position OUT OF RANGE")
            self.error_stream("device state: ALARM (position OUT OF RANGE)")
            self.set_state(DevState.ALARM) 
        pass
        # PROTECTED REGION END #    //  AgilisAGP.Position_write
        
    def read_UnitLimitMin(self):
        # PROTECTED REGION ID(AgilisAGP.UnitLimitMin_read) ENABLED START #
        """Return the UnitLimitMin attribute."""
        return self.__unit_limit_min
        # PROTECTED REGION END #    //  AgilisAGP.UnitLimitMin_read

    def write_UnitLimitMin(self, value):
        # PROTECTED REGION ID(AgilisAGP.UnitLimitMin_write) ENABLED START #
        """Set the UnitLimitMin attribute."""
        self.__unit_limit_min = value
        pass
        # PROTECTED REGION END #    //  AgilisAGP.UnitLimitMin_write

    def read_UnitLimitMax(self):
        # PROTECTED REGION ID(AgilisAGP.UnitLimitMax_read) ENABLED START #
        """Return the UnitLimitMax attribute."""
        return self.__unit_limit_max
        # PROTECTED REGION END #    //  AgilisAGP.UnitLimitMax_read

    def write_UnitLimitMax(self, value):
        # PROTECTED REGION ID(AgilisAGP.UnitLimitMax_write) ENABLED START #
        """Set the UnitLimitMax attribute."""
        self.__unit_limit_max = value
        pass
        # PROTECTED REGION END #    //  AgilisAGP.UnitLimitMax_write

    def read_Conversion(self):
        # PROTECTED REGION ID(AgilisAGP.Conversion_read) ENABLED START #
        """Return the Conversion attribute."""
        return self.__conversion
        # PROTECTED REGION END #    //  AgilisAGP.Conversion_read

    def write_Conversion(self, value):
        # PROTECTED REGION ID(AgilisAGP.Conversion_write) ENABLED START #
        """Set the Conversion attribute."""
        self.__conversion = value
        pass
        # PROTECTED REGION END #    //  AgilisAGP.Conversion_write
        
    # -------------
    # Pipes methods
    # -------------

    # --------
    # Commands
    # --------
    
    def dev_state(self):
        # PROTECTED REGION ID(AgilisAGP.State) ENABLED START #
        resp = ''
        resp = self.write_read('TS?')
        if (resp != ''):
            self.__error = int(resp[:4],16)
            self.__agp_state = resp[4:].strip()
            if (self.__agp_state in self.__STATE_MOVING):
                self.set_status("The device is in MOVING state")
                self.debug_stream("device state: MOVING")
                return DevState.MOVING
            if self.__agp_state in self.__STATE_NOT_REFERENCED:
                self.set_status("The device is in ALARM state. Not referenced.")
                self.debug_stream("device state: ALARM (Not referenced)")
                return DevState.ALARM    
        self.set_status("The device is in ON state")
        return DevState.ON

        # PROTECTED REGION END #    //  AgilisAGP.State
    
    @command(dtype_in=str, 
    dtype_out=str, 
    )
    @DebugIt()
    def write_read(self, argin):
        # PROTECTED REGION ID(AgilisAGP.write_read) ENABLED START #
        # if argin ended with "?", then we expected an answer
        response = (argin[-1] == '?')
        if response:
            # cut the "?"
            prefix = self.__agpID + argin[:-1]
            send_str = self.__agpID + argin
            self.__ser_port.flushInput()
            self.send_cmd(send_str)
            tmp_answer = self.__ser_port.readline().decode("utf-8")
            self.debug_stream("read response: {:s}".format(tmp_answer))
            if tmp_answer.startswith(prefix):
                answer = tmp_answer[len(prefix):]
            else:
                answer = ''    
        else:    
            send_str = self.__agpID + argin
            self.send_cmd(send_str)
            answer = ''
        return answer
        # PROTECTED REGION END #    //  AgilisAGP.write_read
        

    @command(
    )
    def StopMove(self):
        # PROTECTED REGION ID(AgilisAGP.StopMove) ENABLED START #
        self.write_read('ST')
        pass
        # PROTECTED REGION END #    //  AgilisAGP.StopMove

    @command(
    )
    def Home(self):
        # PROTECTED REGION ID(AgilisAGP.Home) ENABLED START #
        self.write_read('OR')
        pass
        # PROTECTED REGION END #    //  AgilisAGP.Home
    
    @command(dtype_out=str)
    def ResetMotor(self):
        # PROTECTED REGION ID(AgilisAGP.ResetMotor) ENABLED START #
        self.write_read('RS')
        return ("Device reset, do homing now!")
        # PROTECTED REGION END #    //  AgilisAGP.ResetMotor
        
    @command(
    )
    def Calibrate(self):
        # PROTECTED REGION ID(AgilisAGP.Calibrate) ENABLED START #
        pass
        # PROTECTED REGION END #    //  AgilisAGP.Calibrate
    
    @command(dtype_out=str)
    def read_controller_info(self):
        return (self.write_read('VE?'))
    
    @command(dtype_out=str) 
    def read_controller_identifier(self):
        return (self.write_read('ID?'))
# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(AgilisAGP.main) ENABLED START #
    return run((AgilisAGP,), args=args, **kwargs)
    # PROTECTED REGION END #    //  AgilisAGP.main

if __name__ == '__main__':
    main()
