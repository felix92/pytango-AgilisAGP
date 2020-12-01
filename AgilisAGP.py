#!/usr/bin/python3 -u
from tango import AttrWriteType, DevState, DispLevel
from tango.server import Device, attribute, command, device_property
from time import sleep
import serial

class AgilisAGP(Device):
    """AgilisAGP

    This controls an Agilis Conex AGP actuator

    """

    Address = device_property(
        dtype='int16',
    )
    
    Port = device_property(
        dtype='str',
    )

    # end-of-line character
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
    
    def init_device(self):
        Device.init_device(self)
                
        self.__agpID = str(self.Address)
        self.__port  = self.Port
                    
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
            self.set_state(DevState.ON)  
        else:
            self.set_state(DevState.OFF)

    def always_executed_hook(self):
        pass

    def delete_device(self):
        if self.__ser_port.isOpen():
            self.__ser_port.close()    
    
    # def read_controller_info(self):
    #     return (self.write_read('VE?'))
    #     
    # def read_controller_identifier(self):
    #     return (self.write_read('ID?'))
    
    def send_cmd(self, cmd):
        snd_str = cmd + self.__EOL
        self.__ser_port.flushOutput()
        self.__ser_port.write(snd_str)
        self.__ser_port.flush()

    def get_position(self):
        pos = self.write_read('TP?')
        if pos != '':
            self.__Pos = float(pos)   

    def get_cmd_error_string(self):
        error = self.write_read('TE?')
        return error.strip()
        
    def read_range_error(self):
        return self.__Out_Of_Range

    def read_moving(self):
        return self.__Motor_Run

    def read_position(self):
        return self.__Pos

    def write_position(self, value):
        self.write_read('PA' + str(value))
        if self.__ERROR_OUT_OF_RANGE == self.get_cmd_error_string():
            self.__Out_Of_Range = True
        else:
            self.__Out_Of_Range = False 
            self.__Motor_Run = True

    def read_homing(self):
        return self.__Homing

    def read_referenced(self):
        return self.__Referenced

    @command(dtype_in=str, dtype_out=str)
    def write_read(self, argin):
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

    @command()
    def stop_motion(self):
        self.write_read('ST')
    
    @command (dtype_out=str, polling_period= 100, doc_out='state of AgilisAGP') 
    def get_agp_state(self):
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

    @command()
    def homing(self):
        self.write_read('OR')
    
    @command(dtype_out=str)
    def reset(self):
        self.write_read('RS')
        return ("Device reset, do homing now!")
    
    @command(dtype_out=str)
    def read_controller_info(self):
        return (self.write_read('VE?'))
    
    @command(dtype_out=str)
    def read_controller_identifier(self):
        return (self.write_read('ID?'))

# start the server
if __name__ == '__main__':
    AgilisAGP.run_server()
