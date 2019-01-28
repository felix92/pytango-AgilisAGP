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
import PyTango
from PyTango import DebugIt, DeviceProxy
from PyTango.server import run
from PyTango.server import Device, DeviceMeta
from PyTango.server import attribute, command, pipe
from PyTango.server import class_property, device_property
from PyTango import AttrQuality,DispLevel, DevState
from PyTango import AttrWriteType, PipeWriteType
# Additional import
# PROTECTED REGION ID(AgilisAGP.additionnal_import) ENABLED START #
from time import sleep
import serial
# PROTECTED REGION END #    //  AgilisAGP.additionnal_import

flagDebugIO = 0


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
        dtype='int16',
    )
    Port = device_property(
        dtype='str',
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
    
# private status variables, are are updated by "get_smc__state()"
    __Motor_Run   = False
    __Referenced  = False
    __Homing      = False
    __Out_Of_Range= False
    __Pos         = 0.000
    
    
    
    # ----------
    # Attributes
    # ----------

    
    range_error = attribute(
        dtype='bool',
        doc = 'if the new set position out of range\n when this flag is true'
    )
    moving = attribute(
        dtype='bool',
        doc = 'if motor in moving this flag is true'
    )
    position = attribute(
        min_value = 0.0,
        max_value = 340.0,
        dtype='float',
        access=AttrWriteType.READ_WRITE,
        label="angle",
        unit="degree",
        display_unit="degree",
        format="%8.3f",
        doc = 'absolute position in degrees'
    )
    homing = attribute(
        dtype='bool',
        doc = 'the position in degrees'
    )
    referenced = attribute(
        dtype='bool',
        doc = 'show the REFERENCED state'
    )
    
    
    # -----
    # Pipes
    # -----

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        Device.init_device(self)
        # PROTECTED REGION ID(AgilisAGP.init_device) ENABLED START #
        
        self.proxy = DeviceProxy(self.get_name())
        
        self.__agpID = str(self.Address)
        self.__port  = self.Port
        
        if flagDebugIO:
            print("Get_name: %s" % (self.get_name()))
            print("Connecting to AgilisAGP on %s" %(self.__port))
            print("Device address: %s" %(self.__agpID))
            
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
            self.get_agp_state()
            self.read_position()
            self.set_state(PyTango.DevState.ON)  
        else:
            self.set_state(PyTango.DevState.OFF)
        
        
        if flagDebugIO:
            print "Run: ",self.__Motor_Run
            print "Postion: ", self.__Pos    
            
        # PROTECTED REGION END #    //  AgilisAGP.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(AgilisAGP.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  AgilisAGP.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(AgilisAGP.delete_device) ENABLED START #
        if self.__ser_port.isOpen():
            self.__ser_port.close()
        # PROTECTED REGION END #    //  AgilisAGP.delete_device
    
    
    # def read_controller_info(self):
    #     return (self.write_read('VE?'))
    #     
    # def read_controller_identifier(self):
    #     return (self.write_read('ID?'))
    
    def send_cmd(self, cmd):
        # PROTECTED REGION ID(AgilisAGP.send_cmd) ENABLED START #
        snd_str = cmd + self.__EOL
        self.__ser_port.flushOutput()
        self.__ser_port.write(snd_str)
        self.__ser_port.flush()
        # PROTECTED REGION END #    //  AgilisAGP.send_cmd    

    def get_position(self):
        pos = self.write_read('TP?')
        if pos != '':
            self.__Pos = float(pos)   

    def get_cmd_error_string(self):
        error = self.write_read('TE?')
        return error.strip()
        
        
    # ------------------
    # Attributes methods
    # ------------------

    
    def read_range_error(self):
        # PROTECTED REGION ID(AgilisAGP.range_error) ENABLED START #
        return self.__Out_Of_Range
        # PROTECTED REGION END #    //  AgilisAGP.range_error

    def read_moving(self):
        # PROTECTED REGION ID(AgilisAGP.moving_read) ENABLED START #
        return self.__Motor_Run
        # PROTECTED REGION END #    //  AgilisAGP.moving_read

    def read_position(self):
        # PROTECTED REGION ID(AgilisAGP.position_read) ENABLED START #
        return self.__Pos
        # PROTECTED REGION END #    //  AgilisAGP.position_read

    def write_position(self, value):
        # PROTECTED REGION ID(AgilisAGP.position_write) ENABLED START #
        self.write_read('PA' + str(value))
        if self.__ERROR_OUT_OF_RANGE == self.get_cmd_error_string():
            self.__Out_Of_Range = True
        else:
            self.__Out_Of_Range = False 
            self.__Motor_Run = True    
        # PROTECTED REGION END #    //  AgilisAGP.position_write


    def read_homing(self):
        # PROTECTED REGION ID(AgilisAGP.homing_read) ENABLED START #
        return self.__Homing
        # PROTECTED REGION END #    //  AgilisAGP.homing_read

    def read_referenced(self):
        # PROTECTED REGION ID(AgilisAGP.homing_read) ENABLED START #
        return self.__Referenced
        # PROTECTED REGION END #    //  AgilisAGP.homing_read
    # -------------
    # Pipes methods
    # -------------

    # --------
    # Commands
    # --------
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
            tmp_answer = self.__ser_port.readline()
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
        

    @command
    @DebugIt()
    def stop_motion(self):
        # PROTECTED REGION ID(AgilisAGP.stop_motion) ENABLED START #
        self.write_read('ST')
        # PROTECTED REGION END #    //  AgilisAGP.stop_motion
    
    
    @command (
    dtype_out=str, polling_period= 100, doc_out='state of AgilisAGP' ) 
    @DebugIt()
    def get_agp_state(self):
        # PROTECTED REGION ID(AgilisAGP.get_agp_state) ENABLED START #
        self.get_position()
        resp = ''
        resp = self.write_read('TS?')
        if (resp != ''):
            self.__error = int(resp[:4],16)
            self.__agp_state = resp[4:].strip()
            if (self.__agp_state in self.__STATE_MOVING):
                self.__Motor_Run   = True
            else:
                self.__Motor_Run   = False
            if self.__agp_state in self.__STATE_NOT_REFERENCED:
                self.__Referenced  = False
            else:
                self.__Referenced  = True           
        return resp
        # PROTECTED REGION END #    //  AgilisAGP.get_agp_state

    @command
    @DebugIt()
    def homing(self):
        # PROTECTED REGION ID(AgilisAGP.homing) ENABLED START #
        self.write_read('OR')
        # PROTECTED REGION END #    //  AgilisAGP.homing
    
    @command(dtype_out=str)
    @DebugIt()
    def reset(self):
        # PROTECTED REGION ID(AgilisAGP.reset) ENABLED START #
        self.write_read('RS')
        return ("Device reset, do homing now!")
        # PROTECTED REGION END #    //  AgilisAGP.reset
    
    @command(dtype_out=str)
    @DebugIt()
    def read_controller_info(self):
        return (self.write_read('VE?'))
    
    @command(dtype_out=str)
    @DebugIt()    
    def read_controller_identifier(self):
        return (self.write_read('ID?'))
# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(AgilisAGP.main) ENABLED START #
    from PyTango.server import run
    return run((AgilisAGP,), args=args, **kwargs)
    # PROTECTED REGION END #    //  AgilisAGP.main

if __name__ == '__main__':
    main()
