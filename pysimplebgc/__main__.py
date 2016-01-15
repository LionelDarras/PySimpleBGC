# -*- coding: utf-8 -*-
'''
    pysimplebgc
    -----------

    The public API and command-line interface to PySimpleBGC package.

    :copyright: Copyright 2015 Lionel Darras and contributors, see AUTHORS.
    :license: GNU GPL v3.

'''
import os
import argparse
import time
import copy
from datetime import datetime

# Make sure the logger is configured early:
from . import VERSION
from .logger import active_logger
from .device import SimpleBGC32
from .compat import stdout


def setstdcmd(cmdtype, device):
    '''set standard command'''
    fields = device.setcmd(cmdtype)
    for i in range(len(fields)):
        if fields[i]['name'] != 'reserved':
            stdout.write(("%s : " + fields[i]['valuefmt'] + "\n")%(fields[i]['name'],fields[i]['value']))


def getboardinfo_cmd(args, device):
    '''Getboardinfo command.'''
    setstdcmd('CMD_BOARD_INFO', device)


def getboardinfo3_cmd(args, device):
    '''Getboardinfo3 command.'''
    setstdcmd('CMD_BOARD_INFO_3', device)


def getrealtimedata3_cmd(args, device):
    '''Getrealtimedata3 command.'''
    setstdcmd('CMD_REALTIME_DATA_3', device)


def collectdata3_cmd(args, device):
    '''Collectdata3 command.'''
    device.setcollectcmd('CMD_REALTIME_DATA_3', args.output, args.delim, args.stdoutdisplay, args.measuresnb, args.storingperiod, args.samplingperiod)
        

def collectdata4_cmd(args, device):
    '''Collectdata4 command.'''
    device.setcollectcmd('CMD_REALTIME_DATA_4', args.output, args.delim, args.stdoutdisplay, args.measuresnb, args.storingperiod, args.samplingperiod)
        

def get_cmd_parser(cmd, subparsers, help, func):
    '''Make a subparser command.'''
    parser = subparsers.add_parser(cmd, help=help, description=help)
    parser.add_argument('--timeout', default=10.0, type=float,
                        help="Connection link timeout")
    parser.add_argument('--debug', action="store_true", default=False,
                        help='Display log')
    parser.add_argument('url', action="store",
                        help="Specify URL for connection link. "
                             "E.g. tcp:iphost:port "
                             "or serial:/dev/ttyUSB0:19200:8N1")
    parser.set_defaults(func=func)
    return parser


def main():
    '''Parse command-line arguments and execute SimpleBGC32 command.'''

    parser = argparse.ArgumentParser(prog='pysimplebgc',
                                     description='Communication tools for '
                                                 'Basecam SimpleBGC '
                                                 'Controller boards')
    parser.add_argument('--version', action='version',
                         version='PySimpleBGC version %s' % VERSION,
                         help='Print PySimpleBGC version number and exit.')

    subparsers = parser.add_subparsers(title='The PySimpleBGC commands')
    # getboardinfo command
    subparser = get_cmd_parser('getboardinfo', subparsers,
                               help='Get board and software information.',
                               func=getboardinfo_cmd)
    
    # getboardinfo3 command
    subparser = get_cmd_parser('getboardinfo3', subparsers,
                               help='Get additionnal board information.',
                               func=getboardinfo3_cmd)
    
    # getrealtimedata3 command
    subparser = get_cmd_parser('getrealtimedata3', subparsers,
                               help='Get current real-time data.',
                               func=getrealtimedata3_cmd)
    
    # collectdata3 command
    subparser = get_cmd_parser('collectdata3', subparsers,
                               help='Collect real-time data and save in a file.',
                               func=collectdata3_cmd)
    subparser.add_argument('--output', action="store", default=stdout,
                           type=argparse.FileType('w'),
                           help='Filename where output is written (default: standard out')
    subparser.add_argument('--delim', action="store", default=";",
                           help='CSV char delimiter (default: ";"')
    subparser.add_argument('--stdoutdisplay', action="store_true", default=False,
                           help='Display on the standard out if defined output is a file')
    subparser.add_argument('--measuresnb', default=0, type=int,
                           help='number of measures to realize, 0 if continue until break (Ctrl-C)')
    subparser.add_argument('--samplingperiod', default=10, type=int,
                           help='period of sampling, 100ms, (default: 10)')
    subparser.add_argument('--storingperiod', default=10, type=int,
                           help='period of storing, 100ms, (default: 10)')

    # collectdata4 command
    subparser = get_cmd_parser('collectdata4', subparsers,
                               help='Collect extended real-time data and save in a file.',
                               func=collectdata4_cmd)
    subparser.add_argument('--output', action="store", default=stdout,
                           type=argparse.FileType('w'),
                           help='Filename where output is written (default: standard out)')
    subparser.add_argument('--delim', action="store", default=";",
                           help='CSV char delimiter (default: ";")')
    subparser.add_argument('--stdoutdisplay', action="store_true", default=False,
                           help='Display on the standard out if defined output is a file')
    subparser.add_argument('--measuresnb', default=0, type=int,
                           help='number of measures to realize, 0 if continue until break (Ctrl-C)')
    subparser.add_argument('--samplingperiod', default=10, type=int,
                           help='period of sampling, 100ms, (default: 10)')
    subparser.add_argument('--storingperiod', default=10, type=int,
                           help='period of storing, 100ms, (default: 10)')

    # Parse argv arguments
    try:
        args = parser.parse_args()
        try:            
            if args.func:
                isfunc = True
        except:
            isfunc = False

        if (isfunc == True):
            if args.debug:
                active_logger()
                device = SimpleBGC32.from_url(args.url, args.timeout)
                args.func(args, device)
            else:
                try:                
                    device = SimpleBGC32.from_url(args.url, args.timeout)
                    args.func(args, device)
                except Exception as e:
                    parser.error('%s' % e)
        else:
            parser.error("No command")

                    
    except Exception as e:
        parser.error('%s' % e)
        

if __name__ == '__main__':
    main()
