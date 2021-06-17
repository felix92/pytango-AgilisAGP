#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
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
from time import sleep
import serial

class AgilisAGP(Device):
    """
    """
    __metaclass__ = DeviceMeta

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
    
    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        self.info_stream("init_device()")
        Device.init_device(self)
        self.set_state(DevState.INIT)
        
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

    def always_executed_hook(self):
        pass

    def delete_device(self):
        if self.__ser_port.isOpen():
            self.__ser_port.close()
            self.set_status("The device is in OFF state")
            self.set_state(DevState.OFF)    
    
    def send_cmd(self, cmd):
        snd_str = cmd + self.__EOL
        self.__ser_port.flushOutput()
        self.debug_stream("write command: {:s}".format(snd_str))
        self.__ser_port.write(snd_str.encode("utf-8"))
        self.__ser_port.flush()

    def get_cmd_error_string(self):
        error = self.write_read('TE?')
        return error.strip()
        
        
    # ------------------
    # Attributes methods
    # ------------------

    def read_Position(self):
        self.__position = float(self.write_read('TP?'))/self.__conversion
        return self.__position

    def write_Position(self, value):
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
        
    def read_UnitLimitMin(self):
        return self.__unit_limit_min

    def write_UnitLimitMin(self, value):
        self.__unit_limit_min = value
        pass

    def read_UnitLimitMax(self):
        return self.__unit_limit_max

    def write_UnitLimitMax(self, value):
        self.__unit_limit_max = value
        pass

    def read_Conversion(self):
        return self.__conversion

    def write_Conversion(self, value):
        self.__conversion = value
        pass

    # --------
    # Commands
    # --------
    
    def dev_state(self):
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
    
    @command(dtype_in=str, 
    dtype_out=str, 
    )
    @DebugIt()
    def write_read(self, argin):
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

    @command(
    )
    def StopMove(self):
        self.write_read('ST')
        pass

    @command(
    )
    def Home(self):
        self.write_read('OR')
        pass
    
    @command(dtype_out=str)
    def ResetMotor(self):
        self.write_read('RS')
        return ("Device reset, do homing now!")
        
    @command(dtype_in='DevDouble')
    def Calibrate(self,argin):
        pass
    
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
    return run((AgilisAGP,), args=args, **kwargs)

if __name__ == '__main__':
    main()
