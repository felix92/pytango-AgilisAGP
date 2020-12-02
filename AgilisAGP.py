#!/usr/bin/python3 -u
from tango import AttrWriteType, DevState, DispLevel
from tango.server import Device, attribute, command, device_property
from time import sleep
import serial

class AgilisAGP(Device):
    """AgilisAGP

    This controls an Agilis Conex AGP actuator

    """
    
    Port = device_property(dtype='str', default_value='/dev/ttyUSB0')
    Address = device_property(dtype='int', default_value=1)

    # Errors from page 64 of the manual
    __ERROR_NEG_END_OF_RUN = 1
    __ERROR_POS_END_OF_RUN = 2
    __ERROR_OUT_OF_RANGE   = 'C'
    # States from page 65 of the manual
    __STATE_NOT_REFERENCED = ('3C', '0A', '0B', '0c' ,'0D', '0E', '0F', '10')
    __STATE_READY   = ('32', '33', '34', '35')
    __STATE_MOVING  = ('28', '1E')
    
    position = attribute(
        min_value = 0.0,
        max_value = 340.0,
        dtype='float',
        access=AttrWriteType.READ_WRITE,
        label="Position",
        unit="degree",
        format="%10.5f",
        doc = 'absolute position in degrees'
    )
    
    def init_device(self):
        Device.init_device(self)
        self.info_stream('Connecting to serial port {:s} ...'.format(self.Port))
        try:
            self.serial = serial.Serial(
                port = self.Port,
                baudrate = 921600,
                bytesize = 8,
                stopbits = 1,
                parity = 'N',
                xonxoff = True,
                timeout = 0.050
            )        
            
            if self.serial.isOpen():
                self.serial.close()
            self.serial.open()

            self.info_stream('Connection established:\n{:s}\n{:s}'.format(
                self.query('ID?'),
                self.query('VE?')
                ))
            self.set_state(DevState.ON)
        except:
            self.error_stream('Cannot connect!')
            self.set_state(DevState.OFF)

    def always_executed_hook(self):
        res = self.query('TS?')
        if (res != ''):
            self.__error = int(res[:4],16)
            state = res[4:]
            if (state in self.__STATE_MOVING):
                self.set_status('Device is MOVING')
                self.set_state(DevState.MOVING)
            elif (state in self.__STATE_NOT_REFERENCED):
                self.set_status('Device is NOT REFERENCED\nDo HOMING first!')
                self.set_state(DevState.OFF)
            elif (state in self.__STATE_READY):
                self.set_status('Device is ON')
                self.set_state(DevState.ON)
            else:
                self.set_status('Device is UNKOWN')
                self.set_state(DevState.UNKNOWN)

    def delete_device(self):
        if self.__ser_port.isOpen():
            self.__ser_port.close()    
        self.info_stream('Connection closed for port {:s}'.format(self.Port))

    def read_position(self):
        return float(self.query('TP?'))

    def write_position(self, value):
        if self.get_state() == DevState.OFF:
            self.error_stream('Home device first!')
        else:
            self.send_cmd('PA' + str(value))

    @command()
    def Stop(self):
        self.send_cmd('ST')
  
    @command()
    def Homing(self):        
        if self.get_state() == DevState.OFF:
            self.info_stream('Homing device ...')
            self.send_cmd('OR')
        else:
            self.error_stream('Reset device first to enable Homing!')
    
    @command()
    def Reset(self):
        self.send_cmd('RS')

    def query(self, cmd):
        prefix = str(self.Address) + cmd[:-1]
        self.send_cmd(cmd)
        answer = self.serial.readline().decode('utf-8')
        if answer.startswith(prefix):
           answer = answer[len(prefix):].strip()
        else:
           answer = ''
        return answer
    
    def send_cmd(self, cmd):
        cmd = str(self.Address) + cmd + '\r\n'
        self.serial.flushInput()
        self.serial.flushOutput()
        self.serial.write(cmd.encode('utf-8'))
        self.serial.flush()

# start the server
if __name__ == '__main__':
    AgilisAGP.run_server()
