# -*- coding: utf-8 -*-
'''
    pysimplebgc.device
    ------------------

    Allows data query of Basecam SimpleBGC Controller boards

    :copyright: Copyright 2015 Lionel Darras and contributors, see AUTHORS.
    :license: GNU GPL v3.

'''
from __future__ import division, unicode_literals
import struct
import copy
from datetime import datetime, timedelta
from pylink import link_from_url
from array import array

from .logger import LOGGER
from .utils import (cached_property, retry, bytes_to_hex, hex_to_bytes,
                    ListDict, is_bytes)
from .compat import stdout


class NoDeviceException(Exception):
    '''Can not access device.'''
    value = __doc__


class BadCmdException(Exception):
    '''No valid command.'''
    value = __doc__


class BadAckException(Exception):
    '''No valid acknowledgement.'''
    def __str__(self):
        return self.__doc__


class BadCRCException(Exception):
    '''No valid checksum.'''
    def __str__(self):
        return self.__doc__


class BadDataException(Exception):
    '''No valid data.'''
    def __str__(self):
        return self.__doc__


class SimpleBGC32(object):
    '''Communicates with the board by sending commands, reads the binary
    data and parsing it into usable scalar values.

    :param link: A `PyLink` connection.
    '''
    
    # Command ID definitions
    CMDTYPEDEF = {
        'CMD_BOARD_INFO':
        {'id': 86, 'cmdbodysize': 0, 'cmdfmt': '', 'respbodysize': 18,
         'respfields': [ {'name': 'BOARD_VER', 'valuefmt': '%d', 'framefmt': 'B'}, {'name': 'FIRMWARE_VER', 'valuefmt': '%d', 'framefmt': 'H'},
           {'name': 'DEBUG_MODE', 'valuefmt': '%d', 'framefmt': 'B'}, {'name': 'BOARD_FEATURES', 'valuefmt': '%d', 'framefmt': 'H'},
           {'name': 'CONNECTION_FLAGS', 'valuefmt': '%d', 'framefmt': 'B'}, {'name': 'FRW_EXTRA_ID', 'valuefmt': '%d', 'framefmt': 'I'},
           {'name': 'reserved', 'valuefmt': '%s', 'framefmt': '7s'}]},
        # Board v3.x only
        'CMD_BOARD_INFO_3':
        {'id': 20, 'cmdbodysize': 0, 'cmdfmt': '', 'respbodysize':69,
         'respfields': [{'name': 'deviceID', 'valuefmt': '%s', 'framefmt': '9s'}, {'name': 'mcuID', 'valuefmt': '%s', 'framefmt': '12s'},
          {'name': 'EEPROM_SIZE', 'valuefmt': '%d', 'framefmt': 'I'}, {'name': 'SCRIPT_SLOT1_SIZE', 'valuefmt': '%d', 'framefmt': 'H'},
          {'name': 'SCRIPT_SLOT2_SIZE', 'valuefmt': '%d', 'framefmt': 'H'}, {'name': 'SCRIPT_SLOT3_SIZE', 'valuefmt': '%d', 'framefmt': 'H'},
          {'name': 'SCRIPT_SLOT4_SIZE', 'valuefmt': '%d', 'framefmt': 'H'}, {'name': 'SCRIPT_SLOT5_SIZE', 'valuefmt': '%d', 'framefmt': 'H'},
          {'name': 'reserved', 'valuefmt': '%s', 'framefmt': '34s'}]},
        'CMD_REALTIME_DATA_3':
        {'id': 23, 'cmdbodysize': 0, 'cmdfmt':'', 'respbodysize': 63, 
         'respfields': [{'name': 'ACC_ROLL', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'GYRO_ROLL', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'ACC_PITCH', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'GYRO_PITCH', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'ACC_YAW', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'GYRO_YAW', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'DEBUG1', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'DEBUG2', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'DEBUG3', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'DEBUG4', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'RC_ROLL', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'RC_PITCH', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'RC_YAW', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'RC_CMD', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'EXT_FC_ROLL', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'EXT_FC_PITCH', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'ANGLE_ROLL', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'ANGLE_PITCH', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'ANGLE_YAW', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'FRAME_IMU_ANGLE_ROLL', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'FRAME_IMU_ANGLE_PITCH', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'FRAME_IMU_ANGLE_YAW', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'RC_ANGLE_ROLL', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'RC_ANGLE_PITCH', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'ANGLE_YAW', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'CYCLE_TIME', 'valuefmt': '%d', 'framefmt': 'H'},
          {'name': 'I2C_ERROR_COUNT', 'valuefmt': '%d', 'framefmt': 'H'}, {'name': 'ERROR_CODE', 'valuefmt': '%d', 'framefmt': 'B'},
          {'name': 'BAT_LEVEL', 'valuefmt': '%d', 'framefmt': 'H'}, {'name': 'OTHER_FLAGS', 'valuefmt': '%d', 'framefmt': 'B'},
          {'name': 'CUR_IMU', 'valuefmt': '%d', 'framefmt': 'B'}, {'name': 'CUR_PROFILE', 'valuefmt': '%d', 'framefmt': 'B'},
          {'name': 'MOTOR_POWER_ROLL', 'valuefmt': '%d', 'framefmt': 'B'}, {'name': 'MOTOR_POWER_PITCH', 'valuefmt': '%d', 'framefmt': 'B'},
          {'name': 'MOTOR_POWER_YAW', 'valuefmt': '%d', 'framefmt': 'B'}]},
        'CMD_REALTIME_DATA_4':
        {'id': 25, 'cmdbodysize': 0, 'cmdfmt':'', 'respbodysize': 124, 
         'respfields': [{'name': 'ACC_ROLL', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'GYRO_ROLL', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'ACC_PITCH', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'GYRO_PITCH', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'ACC_YAW', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'GYRO_YAW', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'DEBUG1', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'DEBUG2', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'DEBUG3', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'DEBUG4', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'RC_ROLL', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'RC_PITCH', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'RC_YAW', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'RC_CMD', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'EXT_FC_ROLL', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'EXT_FC_PITCH', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'ANGLE_ROLL', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'ANGLE_PITCH', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'ANGLE_YAW', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'FRAME_IMU_ANGLE_ROLL', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'FRAME_IMU_ANGLE_PITCH', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'FRAME_IMU_ANGLE_YAW', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'RC_ANGLE_ROLL', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'RC_ANGLE_PITCH', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'ANGLE_YAW', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'CYCLE_TIME', 'valuefmt': '%d', 'framefmt': 'H'},
          {'name': 'I2C_ERROR_COUNT', 'valuefmt': '%d', 'framefmt': 'H'}, {'name': 'ERROR_CODE', 'valuefmt': '%d', 'framefmt': 'B'},
          {'name': 'BAT_LEVEL', 'valuefmt': '%d', 'framefmt': 'H'}, {'name': 'OTHER_FLAGS', 'valuefmt': '%d', 'framefmt': 'B'},
          {'name': 'CUR_IMU', 'valuefmt': '%d', 'framefmt': 'B'}, {'name': 'CUR_PROFILE', 'valuefmt': '%d', 'framefmt': 'B'},
          {'name': 'MOTOR_POWER_ROLL', 'valuefmt': '%d', 'framefmt': 'B'}, {'name': 'MOTOR_POWER_PITCH', 'valuefmt': '%d', 'framefmt': 'B'},
          {'name': 'MOTOR_POWER_YAW', 'valuefmt': '%d', 'framefmt': 'B'}, {'name': 'ROTOR_ANGLE_ROLL', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'ROTOR_ANGLE_PITCH', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'ROTOR_ANGLE_YAW', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'reserved', 'valuefmt': '%d', 'framefmt': 'B'}, {'name': 'BALANCE_ERROR_ROLL', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'BALANCE_ERROR_PITCH', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'BALANCE_ERROR_YAW', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'CURRENT', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'MAG_DATA_ROLL', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'MAG_DATA_PITCH', 'valuefmt': '%d', 'framefmt': 'h'}, {'name': 'MAG_DATA_YAW', 'valuefmt': '%d', 'framefmt': 'h'},
          {'name': 'IMU_TEMPERATURE', 'valuefmt': '%d', 'framefmt': 'b'}, {'name': 'FRAME_IMU_TEMPERATURE', 'valuefmt': '%d', 'framefmt': 'b'},
          {'name': 'reserved', 'valuefmt': '%s', 'framefmt': '38s'}]}
        }
    
    HEADER_SIZE = 4    

    def __init__(self, link):
        self.link = link
        self.link.open()
        self.cmdtypelist = self.CMDTYPEDEF

    @classmethod
    def from_url(cls, url, timeout=10):
        ''' Get device from url.

        :param url: A `PyLink` connection URL.
        :param timeout: Set a read timeout value.
        '''
        link = link_from_url(url)
        link.settimeout(timeout)
        return cls(link)

    @retry(tries=3, delay=0.5)
    def send(self, data, wait_ack=None, timeout=None):
        '''Sends data to station.

         :param data: Can be a byte array or an ASCII command. If this is
            the case for an ascii command, a <LF> will be added.

         :param wait_ack: If `wait_ack` is not None, the function must check
            that acknowledgement is the one expected.
         :param timeout: Define timeout when reading ACK from link
         '''
        if is_bytes(data):
            LOGGER.info("try send : %s" % bytes_to_hex(data))
            self.link.write(data)
        else:
            LOGGER.info("try send : %s" % data)
            self.link.write("%s" % data)
        if wait_ack is None:
            return True
        ack = self.link.read(len(wait_ack), timeout=timeout)
        if wait_ack == ack:
            LOGGER.info("Check ACK: OK (%s)" % (repr(ack)))
            return True
        LOGGER.error("Check ACK: BAD (%s != %s)" % (repr(wait_ack), repr(ack)))
        raise BadAckException()


    def setcmd(self, cmdtype, cmddata=""):
        ''' Send commands and returns response received as a list of dictionnaries
        
        :param cmdtype: command type,'CMD_BOARD_INFO', etc...
        :param cmddata: command data, array of char
        '''
        if self.iscmdvalid(cmdtype):
            cmdid, pack_cmd = self._pack_command(cmdtype, cmddata)
            self.send(pack_cmd)
            respsize = 1 + self.HEADER_SIZE + self.cmdtypelist[cmdtype]['respbodysize']
            respdata = self.link.read(respsize)
            unpack_data = self._unpack_response(cmdid, respdata)
            LOGGER.info("unpacked data: %s" % (unpack_data))
            framefmt = self.torespfieldsframeformat(cmdtype)
            data = struct.unpack(framefmt, unpack_data)
            for i in range(len(data)):
                self.cmdtypelist[cmdtype]['respfields'][i]['value'] = data[i]                
        else:
            raise BadCmdException()
        return self.cmdtypelist[cmdtype]['respfields']
        
        
    def setcollectcmd(self, cmdtype, output, delim, stdoutdisplay, measuresnb, storingperiod, samplingperiod):
        ''' Send data collect command

        :param cmdtype: command type,'CMD_BOARD_INFO', etc...
        :param output: Filename where output is written (default: standard out)
        :param delim: CSV char delimiter (default: ";")
        :param stdoutdisplay: Display on the standard out if defined output is a file
        :param measuresnb: number of measures to realize, 0 if continue until break (Ctrl-C)        
        :param storingperiod: period of storing, 10ms, (default: 10)
        :param samplingperiod: period of sampling, 10ms, (default: 10)
        '''
        measuresnbtodo = measuresnb
        if (samplingperiod > storingperiod):
            samplingperiod = storingperiod
        firstpassage = True
        samplesnb = 0
        storingdtprevious = datetime.utcnow()
        samplingdtprevious = storingdtprevious
        while ((measuresnb==0) or (measuresnbtodo>0)) :
            try:
                dt = datetime.utcnow()
                storingdeltamillisec = (dt - storingdtprevious).seconds*1000 + ((dt - storingdtprevious).microseconds/1000)
                samplingdeltamillisec = (dt - samplingdtprevious).seconds*1000 + ((dt - samplingdtprevious).microseconds/1000)
        
                if (firstpassage or (samplingdeltamillisec > (samplingperiod*10))):  # if it is time to acquire sample
                    fields = self.setcmd(cmdtype)
                    if (firstpassage):
                        data = "DATETIME"
                        for i in range(len(fields)):
                            if fields[i]['name'] != 'reserved':
                                data += (delim + fields[i]['name'])
                        data +='\n'            
                        output.write(data)
                        if (output != stdout):                             # if file as ouput
                            if (stdoutdisplay):                                 # if stdoutflag = True
                                stdout.write(data)                              # display data on the standard output too
                        firstpassage = False
                    if (samplesnb == 0):
                        sumfields = copy.deepcopy(fields)
                    else:
                        _addmeasure(sumfields, fields)
                    samplesnb +=1
                    samplingdtprevious = dt

                if (storingdeltamillisec > (storingperiod*10)):                 # if it is time to store data
                    data = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]             # date format, "2015-12-20 05:25:40.145" 
                    for i in range(len(sumfields)):
                        if sumfields[i]['name'] != 'reserved':
                            data += (delim + (sumfields[i]['valuefmt'])%(sumfields[i]['value']/samplesnb))
                    data +='\n'
                    output.write(data)
                    if (output != stdout):                                 # if file as ouput
                        if (stdoutdisplay):                                     # if stdoutflag = True
                            stdout.write(data)                                  # display data on the standard output too
                        
                    measuresnbtodo -= 1
                    samplesnb = 0
                    storingdtprevious = dt
            except KeyboardInterrupt:                                           # 'Ctrl' + 'C' detected
                break            

        
    def getcmdlist(self):
        '''Returns list of commands availables'''
        list = []
        for key in self.cmdtypelist.keys():
            list.append(key)
        return list
    

    def iscmdvalid(self, cmdtype):
        '''Returns True if cmdtype valid'''
        iscmdvalid = (cmdtype in self.cmdtypelist)
        if iscmdvalid:
            LOGGER.info("check validity of command type: OK %s" % (cmdtype))
        else:
            LOGGER.info("check validity of command type: BAD %s" % (cmdtype))            
        return (iscmdvalid)


    def _pack_command(self, cmdtype, cmddata=""):
        ''' builds the command with '>' header and the checksum
        :param cmdtype : command type,'CMD_BOARD_INFO', etc...
        :param cmddata : command data, array of char
        '''
        
        LOGGER.info("try pack command : %s" % cmdtype)
        try :
            cmdid = self.cmdtypelist[cmdtype]['id']
            cmdbodysize = self.cmdtypelist[cmdtype]['cmdbodysize']
            LOGGER.info("Check CMDID: OK (%s,%d,%d)" % (cmdtype, cmdid, cmdbodysize))
        except :
            LOGGER.info("Check CMDID: BAD (%s)" % (cmdtype))
            raise BadCmdException()            
            
        body_realsize = len(cmddata)
        # verify if body size is correct
        if (body_realsize == cmdbodysize):
            LOGGER.info("Check CMDBODY: OK (%d)" % (cmdbodysize))
        else:
            LOGGER.info("Check CMDBODY: BAD (%d,%d)" % (cmdbodysize, body_realsize))
            raise BadCmdException()            
            
        fullcmd = chr(cmdid) + chr(cmdbodysize)
        packed_cmd = '>' + chr(cmdid) + chr(cmdbodysize) + chr(self._checksum8bytes(fullcmd)) + cmddata + chr(self._checksum8bytes(cmddata))
        return cmdid, packed_cmd


    def torespfieldsframeformat(self, cmdtype):
        ''' '''
        frameformat = "<"
        for field in self.cmdtypelist[cmdtype]['respfields']:
            frameformat += field['framefmt']
        return frameformat
    

    def _unpack_response(self, cmdid, packed_resp):
        ''' unpacks the responce received after sending a command '''

        LOGGER.info("try unpack response : %s" % packed_resp)
        # verify if size of packed_resp is higher than the minimal accepted,
        # 4 bytes for the header + 1 byte for the body checkum
        resp_size = len(packed_resp)
        if (resp_size > self.HEADER_SIZE):
            LOGGER.info("Check MINRESPSIZE: OK (%d)" % resp_size)
        else:
            LOGGER.info("Check MINRESPSIZE: BAD (%d)" % resp_size)
            raise BadCmdException()            

        # verify if 2 first bytes od header are '>' and cmdid
        if (chr(packed_resp[0]) == '>') and (packed_resp[1] == cmdid):
            LOGGER.info("Check ACK: OK (%s)" % (packed_resp[:2]))
        else:
            LOGGER.info("Check ACK: BAD (%s,'>',%s)" % (packed_resp[:2], cmdid))
            raise BadCmdException()

        data_size = packed_resp[2]
        # verify header checksum
        header_checksum = packed_resp[3]
        header_realchecksum = self._checksum8bytes(packed_resp[1:3])
        if (header_checksum == header_realchecksum):
            LOGGER.info("Check HEADERCRC: OK (%s)" % (header_checksum))
        else:
            LOGGER.info("Check HEADERCRC: BAD (%s,%s)" % (header_checksum, header_realchecksum))
            raise BadCRCException()

        # verify data size
        data_realsize = resp_size - self.HEADER_SIZE - 1
        if (data_realsize == data_size):
            LOGGER.info("Check DATASIZE: OK (%s)" % data_size)
        else:
            LOGGER.info("Check DATASIZE: BAD (%s,%s)" % (data_size, data_realsize))
            raise BadDataException()

        # verify data checksum
        data_checksum = int(packed_resp[resp_size-1])
        if (data_size == 0):
            data_realchecksum = 0
        else:
            data = packed_resp[self.HEADER_SIZE:resp_size-1]
            data_realchecksum = self._checksum8bytes(data)
            if (data_checksum == data_realchecksum):
                LOGGER.info("Check DATACRC: OK (%x)" % data_checksum)
            else:
                LOGGER.info("Check DATACRC: BAD (%x,%x)" % (data_checksum, data_realchecksum))
                raise BadCRCException()
            
        return data                


    def _checksum8bytes(self, string):
        '''Returns checksum  value from string.'''
        checksum = 0
        # for each char in the string
        for ch in string:
            try:
                c = ord(ch)
            except:
                c = ch
            checksum = (checksum + c) & 0xFF
        return checksum



def _addmeasure(sumfields, fields):
    for i in range(len(fields)):
        if fields[i]['name'] != 'reserved':
            sumfields[i]['value'] += fields[i]['value']

            
