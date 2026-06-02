#!/usr/bin/env python3
"""
Standalone ZMODEM file receiver (rz).
Merged from PyZMODEM codebase.
"""
import os
import sys
import time
import argparse
import termios
import select
import logging
import struct
import datetime
import zlib
import pty
import re
import signal
import fcntl
from pathlib import Path
from collections.abc import Iterable
from gettext import gettext as _
from zlib import crc32 as _crc32

# --- Begin modem/const.py ---
'''
XMODEM Protocol bytes
=====================

.. data:: SOH

   Indicates a packet length of 128 (X/Y)

.. data:: STX

   Indicates a packet length of 1024 (X/Y)

.. data:: EOT

   End of transmission (X/Y)

.. data:: ACK

   Acknowledgement (X/Y)

.. data:: XON

   Enable out of band flow control (Z)

.. data:: XOFF

   Disable out of band flow control (Z)

.. data:: NAK

   Negative acknowledgement (X/Y)

.. data:: CAN

   Cancel (X/Y)

.. data:: CRC

   Cyclic redundancy check (X/Y)


ZMODEM Protocol bytes
=====================

.. data:: TIMEOUT

   Timeout or invalid data.

.. data:: ZPAD

   Pad character; frame begins

.. data:: ZDLE

   Escape sequence

.. data:: ZDLEE

   Escaped ``ZDLE``

.. data:: ZBIN, ZVBIN

   Binary frame indicator (using CRC16)

.. data:: ZHEX, ZVHEX

   Hex frame indicator (using CRC16)

.. data:: ZBIN32, ZVBIN32

   Binary frame indicator (using CRC32)

.. data:: ZBINR32, ZVBINR32

   Run length encoded binary frame (using CRC32)

.. data:: ZRESC

   Run length encoding flag or escape character


ZMODEM Frame types
==================

.. data:: ZRQINIT

   Request receive init (s->r)

.. data:: ZRINIT

   Receive init (r->s)

.. data:: ZSINIT

   Send init sequence (optional) (s->r)

.. data:: ZACK

   Ack to ZRQINIT ZRINIT or ZSINIT (s<->r)

.. data:: ZFILE

   File name (s->r)

.. data:: ZSKIP

   Skip this file (r->s)

.. data:: ZNAK

   Last packet was corrupted (?)

.. data:: ZABORT

   Abort batch transfers (?)

.. data:: ZFIN

   Finish session (s<->r)

.. data:: ZRPOS

   Resume data transmission here (r->s)

.. data:: ZDATA

   Data packet(s) follow (s->r)

.. data:: ZEOF

   End of file reached (s->r)

.. data:: ZFERR

   Fatal read or write error detected (?)

.. data:: ZCRC

   Request for file CRC and response (?)

.. data:: ZCHALLENGE

   Security challenge (r->s)

.. data:: ZCOMPL

   Request is complete (?)

.. data:: ZCAN

   Pseudo frame; other end cancelled session with 5* CAN

.. data:: ZFREECNT

   Request free bytes on file system (s->r)

.. data:: ZCOMMAND

   Issue command (s->r)

.. data:: ZSTDERR

   Output data to stderr (??)


ZMODEM ZDLE sequences
=====================

.. data:: ZCRCE

   CRC next, frame ends, header packet follows

.. data:: ZCRCG

   CRC next, frame continues nonstop

.. data:: ZCRCQ

   CRC next, frame continuous, ZACK expected

.. data:: ZCRCW

   CRC next, ZACK expected, end of frame

.. data:: ZRUB0

   Translate to rubout 0x7f

.. data:: ZRUB1

   Translate to rubout 0xff


ZMODEM receiver capability flags
================================

.. data:: CANFDX

   Receiver can send and receive true full duplex

.. data:: CANOVIO

   Receiver can receive data during disk I/O

.. data:: CANBRK

   Receiver can send a break signal

.. data:: CANCRY

   Receiver can decrypt

.. data:: CANLZW

   Receiver can uncompress

.. data:: CANFC32

   Receiver can use 32 bit Frame Check

.. data:: ESCCTL

   Receiver expects ctl chars to be escaped

.. data:: ESC8

   Receiver expects 8th bit to be escaped


ZMODEM ZRINIT frame
===================

.. data:: ZF0_CANFDX

   Receiver can send and receive true full duplex

.. data:: ZF0_CANOVIO

   Receiver can receive data during disk I/O

.. data:: ZF0_CANBRK

   Receiver can send a break signal

.. data:: ZF0_CANCRY

   Receiver can decrypt DONT USE

.. data:: ZF0_CANLZW

   Receiver can uncompress DONT USE

.. data:: ZF0_CANFC32

   Receiver can use 32 bit Frame Check

.. data:: ZF0_ESCCTL

   Receiver expects ctl chars to be escaped

.. data:: ZF0_ESC8

   Receiver expects 8th bit to be escaped

.. data:: ZF1_CANVHDR

   Variable headers OK

ZMODEM ZSINIT frame
===================

.. data:: ZF0_TESCCTL

   Transmitter expects ctl chars to be escaped

.. data:: ZF0_TESC8

   Transmitter expects 8th bit to be escaped

'''

SOH = b'\x01'
STX = b'\x02'
EOT = b'\x04'
ACK = b'\x06'
XON = b'\x11'
XOFF = b'\x13'
NAK = b'\x15'
CAN = b'\x18'
CRC = b'\x43'

TIMEOUT = None
ZPAD = 0x2a
ZDLE = 0x18
ZDLEE = 0x58
ZBIN = 0x41
ZHEX = 0x42
ZBIN32 = 0x43
ZBINR32 = 0x44
ZVBIN = 0x61
ZVHEX = 0x62
ZVBIN32 = 0x63
ZVBINR32 = 0x64
ZRESC = 0x7e

# ZMODEM Frame types
ZRQINIT = 0x00
ZRINIT = 0x01
ZSINIT = 0x02
ZACK = 0x03
ZFILE = 0x04
ZSKIP = 0x05
ZNAK = 0x06
ZABORT = 0x07
ZFIN = 0x08
ZRPOS = 0x09
ZDATA = 0x0a
ZEOF = 0x0b
ZFERR = 0x0c
ZCRC = 0x0d
ZCHALLENGE = 0x0e
ZCOMPL = 0x0f
ZCAN = 0x10
ZFREECNT = 0x11
ZCOMMAND = 0x12
ZSTDERR = 0x13

# ZMODEM ZDLE sequences
ZCRCE = 0x68
ZCRCG = 0x69
ZCRCQ = 0x6a
ZCRCW = 0x6b
ZRUB0 = 0x6c
ZRUB1 = 0x6d

# ZMODEM Receiver capability flags
CANFDX = 0x01
CANOVIO = 0x02
CANBRK = 0x04
CANCRY = 0x08
CANLZW = 0x10
CANFC32 = 0x20
ESCCTL = 0x40
ESC8 = 0x80

# ZMODEM ZRINIT frame
ZF0_CANFDX = 0x01
ZF0_CANOVIO = 0x02
ZF0_CANBRK = 0x04
ZF0_CANCRY = 0x08
ZF0_CANLZW = 0x10
ZF0_CANFC32 = 0x20
ZF0_ESCCTL = 0x40
ZF0_ESC8 = 0x80
ZF1_CANVHDR = 0x01

# ZMODEM ZSINIT frame
ZF0_TESCCTL = 0x40
ZF0_TESC8 = 0x80

# ZMODEM Byte positions within header array
ZF0, ZF1, ZF2, ZF3 = range(4, 0, -1)
ZP0, ZP1, ZP2, ZP3 = range(1, 5)

# ZMODEM Frame contents
ENDOFFRAME = 2
FRAMEOK = 1
TIMEOUT = -1      # Rx routine did not receive a character within timeout
INVHDR = -2       # Invalid header received; but within timeout
INVDATA = -3      # Invalid data subpacket received
ZDLEESC = 0x8000  # One of ZCRCE/ZCRCG/ZCRCQ/ZCRCW was ZDLE escaped

# MODEM Protocol types
PROTOCOL_XMODEM = 0x00
PROTOCOL_XMODEMCRC = 0x01
PROTOCOL_XMODEM1K = 0x02
PROTOCOL_YMODEM = 0x03
PROTOCOL_ZMODEM = 0x04

PACKET_SIZE = {
    PROTOCOL_XMODEM: 128,
    PROTOCOL_XMODEMCRC: 128,
    PROTOCOL_XMODEM1K: 1024,
    PROTOCOL_YMODEM: 1024,
    PROTOCOL_ZMODEM: 1024,
}

# CRC tab calculated by Mark G. Mendel, Network Systems Corporation
CRC16_MAP = [
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
    0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
    0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
    0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
    0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
    0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
    0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
    0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
    0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
    0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
    0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
    0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
    0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
    0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
    0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
    0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
    0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
    0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
    0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
    0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
    0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
    0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
    0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0,
]

# CRC tab calculated by Gary S. Brown
CRC32_MAP = [
    0x00000000, 0x77073096, 0xee0e612c, 0x990951ba, 0x076dc419, 0x706af48f,
    0xe963a535, 0x9e6495a3, 0x0edb8832, 0x79dcb8a4, 0xe0d5e91e, 0x97d2d988,
    0x09b64c2b, 0x7eb17cbd, 0xe7b82d07, 0x90bf1d91, 0x1db71064, 0x6ab020f2,
    0xf3b97148, 0x84be41de, 0x1adad47d, 0x6ddde4eb, 0xf4d4b551, 0x83d385c7,
    0x136c9856, 0x646ba8c0, 0xfd62f97a, 0x8a65c9ec, 0x14015c4f, 0x63066cd9,
    0xfa0f3d63, 0x8d080df5, 0x3b6e20c8, 0x4c69105e, 0xd56041e4, 0xa2677172,
    0x3c03e4d1, 0x4b04d447, 0xd20d85fd, 0xa50ab56b, 0x35b5a8fa, 0x42b2986c,
    0xdbbbc9d6, 0xacbcf940, 0x32d86ce3, 0x45df5c75, 0xdcd60dcf, 0xabd13d59,
    0x26d930ac, 0x51de003a, 0xc8d75180, 0xbfd06116, 0x21b4f4b5, 0x56b3c423,
    0xcfba9599, 0xb8bda50f, 0x2802b89e, 0x5f058808, 0xc60cd9b2, 0xb10be924,
    0x2f6f7c87, 0x58684c11, 0xc1611dab, 0xb6662d3d, 0x76dc4190, 0x01db7106,
    0x98d220bc, 0xefd5102a, 0x71b18589, 0x06b6b51f, 0x9fbfe4a5, 0xe8b8d433,
    0x7807c9a2, 0x0f00f934, 0x9609a88e, 0xe10e9818, 0x7f6a0dbb, 0x086d3d2d,
    0x91646c97, 0xe6635c01, 0x6b6b51f4, 0x1c6c6162, 0x856530d8, 0xf262004e,
    0x6c0695ed, 0x1b01a57b, 0x8208f4c1, 0xf50fc457, 0x65b0d9c6, 0x12b7e950,
    0x8bbeb8ea, 0xfcb9887c, 0x62dd1ddf, 0x15da2d49, 0x8cd37cf3, 0xfbd44c65,
    0x4db26158, 0x3ab551ce, 0xa3bc0074, 0xd4bb30e2, 0x4adfa541, 0x3dd895d7,
    0xa4d1c46d, 0xd3d6f4fb, 0x4369e96a, 0x346ed9fc, 0xad678846, 0xda60b8d0,
    0x44042d73, 0x33031de5, 0xaa0a4c5f, 0xdd0d7cc9, 0x5005713c, 0x270241aa,
    0xbe0b1010, 0xc90c2086, 0x5768b525, 0x206f85b3, 0xb966d409, 0xce61e49f,
    0x5edef90e, 0x29d9c998, 0xb0d09822, 0xc7d7a8b4, 0x59b33d17, 0x2eb40d81,
    0xb7bd5c3b, 0xc0ba6cad, 0xedb88320, 0x9abfb3b6, 0x03b6e20c, 0x74b1d29a,
    0xead54739, 0x9dd277af, 0x04db2615, 0x73dc1683, 0xe3630b12, 0x94643b84,
    0x0d6d6a3e, 0x7a6a5aa8, 0xe40ecf0b, 0x9309ff9d, 0x0a00ae27, 0x7d079eb1,
    0xf00f9344, 0x8708a3d2, 0x1e01f268, 0x6906c2fe, 0xf762575d, 0x806567cb,
    0x196c3671, 0x6e6b06e7, 0xfed41b76, 0x89d32be0, 0x10da7a5a, 0x67dd4acc,
    0xf9b9df6f, 0x8ebeeff9, 0x17b7be43, 0x60b08ed5, 0xd6d6a3e8, 0xa1d1937e,
    0x38d8c2c4, 0x4fdff252, 0xd1bb67f1, 0xa6bc5767, 0x3fb506dd, 0x48b2364b,
    0xd80d2bda, 0xaf0a1b4c, 0x36034af6, 0x41047a60, 0xdf60efc3, 0xa867df55,
    0x316e8eef, 0x4669be79, 0xcb61b38c, 0xbc66831a, 0x256fd2a0, 0x5268e236,
    0xcc0c7795, 0xbb0b4703, 0x220216b9, 0x5505262f, 0xc5ba3bbe, 0xb2bd0b28,
    0x2bb45a92, 0x5cb36a04, 0xc2d7ffa7, 0xb5d0cf31, 0x2cd99e8b, 0x5bdeae1d,
    0x9b64c2b0, 0xec63f226, 0x756aa39c, 0x026d930a, 0x9c0906a9, 0xeb0e363f,
    0x72076785, 0x05005713, 0x95bf4a82, 0xe2b87a14, 0x7bb12bae, 0x0cb61b38,
    0x92d28e9b, 0xe5d5be0d, 0x7cdcefb7, 0x0bdbdf21, 0x86d3d2d4, 0xf1d4e242,
    0x68ddb3f8, 0x1fda836e, 0x81be16cd, 0xf6b9265b, 0x6fb077e1, 0x18b74777,
    0x88085ae6, 0xff0f6a70, 0x66063bca, 0x11010b5c, 0x8f659eff, 0xf862ae69,
    0x616bffd3, 0x166ccf45, 0xa00ae278, 0xd70dd2ee, 0x4e048354, 0x3903b3c2,
    0xa7672661, 0xd06016f7, 0x4969474d, 0x3e6e77db, 0xaed16a4a, 0xd9d65adc,
    0x40df0b66, 0x37d83bf0, 0xa9bcae53, 0xdebb9ec5, 0x47b2cf7f, 0x30b5ffe9,
    0xbdbdf21c, 0xcabac28a, 0x53b39330, 0x24b4a3a6, 0xbad03605, 0xcdd70693,
    0x54de5729, 0x23d967bf, 0xb3667a2e, 0xc4614ab8, 0x5d681b02, 0x2a6f2b94,
    0xb40bbe37, 0xc30c8ea1, 0x5a05df1b, 0x2d02ef8d
]

# Standard ZMODEM Management Options (ZFILE ZF1)
ZF1_ZMCLOB = 0x04   # Replace existing destination file (Overwrite)

# PyZMODEM custom ZLIB feature flags
ZF1_CANZLIB = 0x08  # Receiver capability flag in ZRINIT ZF1 (0x08 avoids 0x02 TIMESYNC)
ZF3_ZLIB = 0x01     # Sender file flag in ZFILE ZF3 (Extended Options)

# --- End modem/const.py ---

# --- Begin modem/error.py ---

ABORT = _('Aborting transfer')
ABORT_WHY = _('Aborting transfer; %s')
ERROR = _('Error')
ERROR_WHY = _('Error; %s')
WARNS = _('Warning')
WARNS_WHY = _('Warnings; %s')

ABORT_ERROR_LIMIT = ABORT_WHY % _('error limit reached')
ABORT_EXPECT_NAK_CRC = ABORT_WHY % _('expected <NAK>/<CRC>, got "%02x"')
ABORT_EXPECT_SOH_EOT = ABORT_WHY % _('expected <SOH>/<EOT>, got "%02x"')
ABORT_INIT_NEXT = ABORT_WHY % _('initialisation of next failed')
ABORT_OPEN_FILE = ABORT_WHY % _('error opening file')
ABORT_PACKET_SIZE = ABORT_WHY % _('incompatible packet size')
ABORT_PROTOCOL = ABORT_WHY % _('protocol error')
ABORT_RECV_CAN_CAN = ABORT_WHY % _('second <CAN> received')
ABORT_RECV_PACKET = ABORT_WHY % _('packet recv failed')
ABORT_RECV_STREAM = ABORT_WHY % _('stream recv failed')
ABORT_SEND_PACKET = ABORT_WHY % _('packet send failed')
ABORT_SEND_STREAM = ABORT_WHY % _('stream send failed')

DEBUG_RECV_CAN = _('First <CAN> received')
DEBUG_SEND_CAN = _('First <CAN> sent')
DEBUG_START_FILENAME = _('Start sending "%s"')
DEBUG_TRY_CRC = _('Try CRC mode')
DEBUG_TRY_CHECKSUM = _('Try check sum mode')
DEBUG_SEND_EOT = _('Send <EOT>')
DEBUG_FILENAME_SENT = _('File name {} sent')
DEBUG_FILE_SENT = _('File {} sent')
DEBUG_SEND_PROGRESS = _('Progress: |{}>{:3.0f}%{}|')

ERROR_EXPECT_NAK_CRC = ERROR_WHY % _('expected <NAK>/<CRC>, got "%02x"')
ERROR_EXPECT_SOH_EOT = ERROR_WHY % _('expected <SOH>/<EOT>, got "%02x"')
ERROR_PROTOCOL = ERROR_WHY % _('protocol error')
ERROR_SEND_EOT = ERROR_WHY % _('failed sending <EOT>')
ERROR_SEND_PACKET = ERROR_WHY % _('failed to send packet')

WARNS_SEQUENCE = WARNS_WHY % \
    _('invalid sequence; expected %02x got %02x/%02x')

# --- End modem/error.py ---

# --- Begin modem/tools.py ---


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(process)d %(asctime)s [%(levelname)s] %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p'
)

log = logging.getLogger('modem')


def crc16(data, crc=0):
    '''
    Calculates the (unsigned) 16 bit cyclic redundancy check of a byte
    sequence::

        >>> crc = crc16('Hello ')
        >>> crc = crc16('world!', crc)
        >>> print hex(crc)
        0x39db

    '''
    def calc(byte, crc=0):
        if isinstance(byte, bytes):
            b = struct.unpack('B', byte)[0]
        elif isinstance(byte, str):
            b = ord(byte)
        else:
            b = byte

        crc = (crc << 8) ^ CRC16_MAP[((crc >> 0x08) ^ b) & 0xff]
        return crc

    if isinstance(data, Iterable):
        for byte in data:
            crc = calc(byte, crc)
    else:
        crc = calc(data, crc)
    return crc & 0xffff


def crc32(data, crc=0):
    '''
    Calculates the (unsigned) 32 bit cyclic redundancy check of a byte
    sequence::

        >>> crc = crc32('Hello ')
        >>> crc = crc32('world!', crc)
        >>> print hex(crc)
        0x1b851995

    '''
    return _crc32(data, crc) & 0xffffffff

# --- End modem/tools.py ---

# --- Begin modem/base.py ---


class Modem(object):
    '''
    Base modem class.
    '''

    def __init__(self, getc, putc):
        self.getc = getc
        self.putc = putc

    def calc_checksum(self, data, checksum=0):
        '''
        Calculate the checksum for a given block of data, can also be used to
        update a checksum.

            >>> csum = modem.calc_checksum('hello')
            >>> csum = modem.calc_checksum('world', csum)
            >>> hex(csum)
            '0x3c'

        '''
        return (sum(map(ord, data)) + checksum) % 256

    def calc_crc16(self, data, crc=0):
        '''
        Calculate the 16 bit Cyclic Redundancy Check for a given block of data,
        can also be used to update a CRC.

            >>> crc = modem.calc_crc16(b'hello')
            >>> crc = modem.calc_crc16(b'world', crc)
            >>> hex(crc)
            '0xd5e3'

        '''
        for byte in data:
            crc = crc16(byte, crc)
        return crc

    def calc_crc32(self, data, crc=0):
        '''
        Calculate the 32 bit Cyclic Redundancy Check for a given block of data,
        can also be used to update a CRC.

            >>> crc = modem.calc_crc32('hello')
            >>> crc = modem.calc_crc32('world', crc)
            >>> hex(crc)
            '0x20ad'

        '''
        for byte in data:
            crc = crc32(byte, crc)
        return crc

    def _check_crc(self, data, crc_mode):
        '''
        Depending on crc_mode check CRC or checksum on data.

            >>> data = self._check_crc(data,crc_mode,quiet=quiet,debug=debug)
            >>> if data:
            >>>    income_size += len(data)
            >>>    stream.write(data)
            ...

        In case the control code is valid returns data without checksum/CRC,
        or returns False in case of invalid checksum/CRC
        '''
        if crc_mode:
            csum = (data[-2] << 8) + data[-1]
            data = data[:-2]
            mine = self.calc_crc16(data)
            if csum == mine:
                return data
        else:
            csum = data[-3]
            data = data[:-1]
            mine = self.calc_checksum(data)
            if csum == mine:
                return data
        return False

# --- End modem/base.py ---

# --- Begin modem/utf8.py ---
class QPStreamEncoder:
    def __init__(self, putc):
        self._putc = putc

    def putc(self, data: bytes, timeout=1):
        out = bytearray()
        for b in data:
            if b == 0x3d: # '='
                out.extend(b'=3D')
            elif 0x20 <= b <= 0x7e:
                out.append(b)
            elif b == 0x0d or b == 0x0a:
                out.append(b)
            else:
                out.extend(f"={b:02X}".encode('ascii'))
        if out:
            self._putc(bytes(out), timeout)

class QPStreamDecoder:
    def __init__(self, getc):
        self._getc = getc
        self.buf = bytearray()

    def getc(self, size, timeout=1):
        out = bytearray()
        while len(out) < size:
            if self.buf:
                out.append(self.buf.pop(0))
                continue
                
            chunk = self._getc(1, timeout)
            if not chunk:
                break
                
            b = chunk[0]
            if b == 0x3d: # '='
                hex_str = bytearray()
                c1 = self._getc(1, timeout)
                if not c1:
                    out.append(b)
                    break
                hex_str.extend(c1)
                
                c2 = self._getc(1, timeout)
                if not c2:
                    out.append(b)
                    self.buf.extend(hex_str)
                    break
                hex_str.extend(c2)
                
                try:
                    out.append(int(hex_str, 16))
                except ValueError:
                    out.append(b)
                    self.buf.extend(hex_str)
            else:
                out.append(b)
                
        return bytes(out)

# --- End modem/utf8.py ---

# --- Begin modem/protocol/zmodem.py ---



class ZMODEM(Modem):
    '''
    ZMODEM protocol implementation.
    '''

    def __init__(self, getc, putc, progress_callback=None, compress=False, escape_all=False, utf8=False):
        if utf8:
            putc = QPStreamEncoder(putc).putc
            getc = QPStreamDecoder(getc).getc
        super().__init__(getc, putc)
        self.progress_callback = progress_callback
        self.compress_enabled = compress
        self.escape_all = escape_all
        self.utf8 = utf8


    def abort(self, timeout=1):
        """Send standard ZMODEM abort sequence (5 CAN bytes)."""
        try:
            for _ in range(5):
                self.putc(bytes([0x18]), timeout)
            self.putc(bytes([0x08, 0x08, 0x08, 0x08, 0x08]), timeout)
        except Exception:
            pass

    def send(self, files, retry=16, timeout=60, overwrite=False):
        '''
        Send one or more files using ZMODEM protocol.
        files is a list of file paths.
        '''
        
        # 1. Send ZRQINIT
        # Many terminal emulators (SecureCRT, iTerm2, etc.) require "rz\r" before the ZRQINIT 
        # signature to auto-trigger the local ZMODEM receiver.
        self.putc(b'rz\r', timeout)
        self._send_hex_header([ZRQINIT, 0, 0, 0, 0], timeout)
        
        # 2. Wait for ZRINIT
        kind, header = None, None
        peer_zf1 = 0
        while True:
            res = self._recv_header(timeout)
            if res is TIMEOUT:
                log.error("Timeout waiting for ZRINIT")
                return False
            if res and res[0] == ZRINIT:
                header = res
                peer_zf1 = header[ZP2]
                peer_zf0 = header[ZP3]
                if peer_zf0 & ZF0_ESCCTL:
                    log.info("Receiver requested control character escaping (ESCCTL)")
                    self.escape_all = True
                break
                
        can_zlib = (peer_zf1 & ZF1_CANZLIB) != 0 and self.compress_enabled
        if can_zlib:
            log.info("Receiver supports inline ZLIB compression")
        
        # 3. For each file
        sent_count = 0
        for filepath in files:
            try:
                size = os.path.getsize(filepath)
                filename = os.path.basename(filepath)
            except Exception as e:
                log.error("Cannot read file %s: %s", filepath, e)
                print(f"\r\n[ERROR] Cannot read file {filepath}: {e}\r\n", file=sys.stderr)
                continue
            
            # Send ZFILE header (Hex is fine, or BIN)
            zf1 = ZF1_ZMCLOB if overwrite else 0
            zf3 = ZF3_ZLIB if can_zlib else 0
            # Note: _send_hex_header expects [type, f3, f2, f1, f0] order because ZFILE header is ZP0=ZF3...ZP3=ZF0
            # Wait, no. Standard says ZF3 is at index 0 (which is zfile_header[1] since 0 is frame type).
            # zfile_header[1] = ZF3, [2] = ZF2, [3] = ZF1, [4] = ZF0.
            self._send_hex_header([ZFILE, zf3, 0, zf1, 0], timeout)
            
            # Send ZFILE data
            # Format: filename \x00 filesize \x00
            file_info = filename.encode('utf-8') + b'\x00' + str(size).encode('utf-8') + b' 0 0 0\x00'
            self._send_16_data(file_info, ZCRCW, timeout)
            
            # Wait for ZRPOS
            offset = 0
            while True:
                res = self._recv_header(timeout)
                if res is TIMEOUT:
                    log.error("Timeout waiting for ZRPOS")
                    return False
                if res and res[0] == ZRPOS:
                    offset = res[ZP0] | (res[ZP1] << 8) | (res[ZP2] << 16) | (res[ZP3] << 24)
                    break
                elif res and res[0] == ZSKIP:
                    offset = -1
                    break
                    
            if offset == -1:
                log.info("Receiver skipped file")
                continue
                
            # Send ZDATA header
            self._send_hex_header([ZDATA, offset & 0xff, (offset >> 8) & 0xff, (offset >> 16) & 0xff, (offset >> 24) & 0xff], timeout)
            
            # Stream data
            total_sent = offset
            with open(filepath, 'rb') as f:
                f.seek(offset)
                compressor = zlib.compressobj() if can_zlib else None
                
                while True:
                    chunk = f.read(4096 if can_zlib else 1024)
                    if not chunk:
                        if compressor:
                            comp_chunk = compressor.flush()
                            if comp_chunk:
                                for i in range(0, len(comp_chunk), 1024):
                                    sub = comp_chunk[i:i+1024]
                                    self._send_16_data(sub, ZCRCG, timeout)
                        self._send_16_data(b'', ZCRCE, timeout)
                        break
                    
                    if compressor:
                        comp_chunk = compressor.compress(chunk)
                        if comp_chunk:
                            for i in range(0, len(comp_chunk), 1024):
                                sub = comp_chunk[i:i+1024]
                                self._send_16_data(sub, ZCRCG, timeout)
                    else:
                        self._send_16_data(chunk, ZCRCG, timeout)
                        
                    total_sent += len(chunk)
                    if self.progress_callback:
                        self.progress_callback(filename, size, total_sent)
                        
                    # Non-blocking check for receiver abort (CAN) or other interruptions
                    char = self.getc(1, 0)
                    if char:
                        if char == bytes([ZDLE]):
                            self._can_count = getattr(self, '_can_count', 0) + 1
                            if self._can_count >= 5:
                                log.info("Received 5 consecutive CAN (Ctrl+X), aborting")
                                raise KeyboardInterrupt("Transfer cancelled by peer")
                        else:
                            self._can_count = 0
            
            # Send ZEOF
            self._send_hex_header([ZEOF, size & 0xff, (size >> 8) & 0xff, (size >> 16) & 0xff, (size >> 24) & 0xff], timeout)
            
            # Wait for ZRINIT
            while True:
                res = self._recv_header(timeout)
                if res is TIMEOUT:
                    return False
                if res and res[0] == ZRINIT:
                    break
                    
            sent_count += 1

        # Send ZFIN
        self._send_hex_header([ZFIN, 0, 0, 0, 0], timeout)
        
        # Wait for ZFIN
        while True:
            res = self._recv_header(timeout)
            if res is TIMEOUT:
                break
            if res and res[0] == ZFIN:
                break
        
        # Send OO
        self.putc(b'O', timeout)
        self.putc(b'O', timeout)
        return sent_count > 0

    def _send_16_data(self, data, frameend, timeout):
        mine = 0
        for byte in data:
            char = byte if isinstance(byte, int) else ord(byte)
            mine = self.calc_crc16(chr(char), mine)
            self._send(char, timeout)
        
        self.putc(bytes([ZDLE]), timeout)
        self.putc(bytes([frameend]), timeout)
        mine = self.calc_crc16(chr(frameend), mine)
        
        self._send(mine >> 8, timeout)
        self._send(mine & 0xff, timeout)
    def recv(self, basedir, retry=16, timeout=60, delay=1):
        '''
        Receive some files via the ZMODEM protocol and place them under
        ``basedir``::

            >>> print modem.recv(basedir)
            3

        Returns the number of files received on success or ``None`` in case of
        failure.

        N.B.: currently there are no control on the existence of files, so they
        will be silently overwritten.
        '''
        
        # Loop until we established a connection, we expect to receive a
        # different packet than ZRQINIT
        kind = TIMEOUT
        header = None
        while kind in [TIMEOUT, ZRQINIT]:
            self._send_zrinit(timeout)
            res = self._recv_header(timeout)
            if res is TIMEOUT or res is False:
                kind = TIMEOUT
            else:
                header = res
                kind = res[0]

        log.info('ZMODEM connection established')

        file_count = 0
        # Receive files
        while kind != ZFIN:
            if kind == ZFILE:
                if self._recv_file(header, basedir, timeout, retry) is not False:
                    file_count += 1
                kind = TIMEOUT
            elif kind == ZFIN:
                continue
            else:
                log.info('Did not get a file offer? Sending position header')
                self._send_pos_header(ZCOMPL, 0, timeout)
                kind = TIMEOUT

            while kind is TIMEOUT:
                self._send_zrinit(timeout)
                res = self._recv_header(timeout)
                if res is TIMEOUT or res is False:
                    kind = TIMEOUT
                else:
                    header = res
                    kind = res[0]

        # Acknowledge the ZFIN
        log.info('Received ZFIN, done receiving files')
        self._send_hex_header([ZFIN, 0, 0, 0, 0], timeout)

        # Wait for the over and out sequence
        kind = self._recv(timeout)
        while kind not in [ord('O'), TIMEOUT]:
            kind = self._recv(timeout)

        if kind is not TIMEOUT:
            # We got the first 'O', wait for the second 'O'
            kind = self._recv(timeout)
            while kind not in [ord('O'), TIMEOUT]:
                kind = self._recv(timeout)

        return file_count

    def _recv(self, timeout):
        # Outer loop
        while True:
            while True:
                char = self._recv_raw(timeout)
                if char is TIMEOUT:
                    return TIMEOUT

                if char == ZDLE:
                    break
                elif char in [0x11, 0x91, 0x13, 0x93]:
                    continue
                else:
                    # Regular character
                    return char

            # ZDLE encoded sequence or session abort
            char = self._recv_raw(timeout)
            if char is TIMEOUT:
                return TIMEOUT

            if char in [0x11, 0x91, 0x13, 0x93, ZDLE]:
                # Drop
                continue

            # Special cases
            if char in [ZCRCE, ZCRCG, ZCRCQ, ZCRCW]:
                return char | ZDLEESC
            elif char == ZRUB0:
                return 0x7f
            elif char == ZRUB1:
                return 0xff
            else:
                # Escape sequence
                return char ^ 0x40

    def _recv_raw(self, timeout):
        char = self.getc(1, timeout)
        if char == b'':
            return TIMEOUT
        if char is not TIMEOUT:
            char_val = char[0] if isinstance(char, bytes) else ord(char)
            if char_val == 0x18:
                self._can_count = getattr(self, '_can_count', 0) + 1
                if self._can_count >= 5:
                    log.info("Received 5 consecutive CAN (Ctrl+X), aborting")
                    raise KeyboardInterrupt("Transfer cancelled by peer")
            else:
                self._can_count = 0
                
            return char_val
        return char

    def _recv_data(self, ack_file_pos, timeout, ack=True):
        # zack_header = [ZACK, 0, 0, 0, 0]
        pos = ack_file_pos

        if self._recv_bits == 16:
            sub_frame_kind, data = self._recv_16_data(timeout)
        elif self._recv_bits == 32:
            sub_frame_kind, data = self._recv_32_data(timeout)
        else:
            raise TypeError('Invalid _recv_bits size')

        # Update file positions
        if sub_frame_kind is TIMEOUT:
            return TIMEOUT, None
        else:
            pos += len(data)

        # Frame continues non-stop
        if sub_frame_kind == ZCRCG:
            return FRAMEOK, data
        # Frame ends
        elif sub_frame_kind == ZCRCE:
            return ENDOFFRAME, data
        # Frame continues; ZACK expected
        elif sub_frame_kind == ZCRCQ:
            if ack: self._send_pos_header(ZACK, pos, timeout)
            return FRAMEOK, data
        # Frame ends; ZACK expected
        elif sub_frame_kind == ZCRCW:
            if ack: self._send_pos_header(ZACK, pos, timeout)
            return ENDOFFRAME, data
        else:
            return False, data

    def _recv_16_data(self, timeout):
        char = 0
        data = bytearray()
        mine = 0
        log.debug("Entering _recv_16_data")
        while char < 0x100:
            char = self._recv(timeout)
            if char is TIMEOUT:
                log.debug("_recv_16_data timeout!")
                return TIMEOUT, b''
            elif char < 0x100:
                mine = self.calc_crc16(bytes([char & 0xff]), mine)
                data.append(char)

        # Calculate our crc, unescape the sub_frame_kind
        sub_frame_kind = char ^ ZDLEESC
        mine = self.calc_crc16(bytes([sub_frame_kind]), mine)

        # Read their crc
        rcrc = self._recv(timeout) << 0x08
        rcrc |= self._recv(timeout)

        log.debug('My CRC16 = %08x, theirs = %08x' % (mine, rcrc))
        if mine != rcrc:
            log.error('Invalid CRC16')
            return timeout, b''
        else:
            return sub_frame_kind, bytes(data)

    def _recv_32_data(self, timeout):
        mine = 0
        data = bytearray()
        while True:
            char = self._recv(timeout)
            if char is TIMEOUT:
                return TIMEOUT, b''
            elif char < 0x100:
                mine = self.calc_crc32(bytes([char & 0xff]), mine)
                data.append(char)
            else:
                break

        # Calculate our crc, unescape the sub_frame_kind
        sub_frame_kind = char ^ ZDLEESC
        mine = self.calc_crc32(bytes([sub_frame_kind]), mine)

        # Read their crc
        rcrc = self._recv(timeout) << 0x00
        rcrc |= self._recv(timeout) << 0x08
        rcrc |= self._recv(timeout) << 0x10
        rcrc |= self._recv(timeout) << 0x18

        log.debug('My CRC32 = %08x, theirs = %08x' % (mine, rcrc))
        if mine != rcrc:
            log.error('Invalid CRC32')
            return timeout, b''
        else:
            return sub_frame_kind, bytes(data)

    def _recv_header(self, timeout, errors=10):
        header_length = 0
        error_count = 0
        char = None
        while header_length == 0:
            # Frist ZPAD
            while char != ZPAD:
                char = self._recv_raw(timeout)
                if char is TIMEOUT:
                    return TIMEOUT

            # Second ZPAD
            char = self._recv_raw(timeout)
            if char == ZPAD:
                # Get raw character
                char = self._recv_raw(timeout)
                if char is TIMEOUT:
                    return TIMEOUT

            # Spurious ZPAD check
            if char != ZDLE:
                continue

            # Read header style
            char = self._recv_raw(timeout)
            if char is TIMEOUT:
                return TIMEOUT

            if char == ZBIN:
                header_length, header = self._recv_bin16_header(timeout)
                self._recv_bits = 16
            elif char == ZHEX:
                header_length, header = self._recv_hex_header(timeout)
                self._recv_bits = 16
            elif char == ZBIN32:
                header_length, header = self._recv_bin32_header(timeout)
                self._recv_bits = 32
            else:
                error_count += 1
                if error_count > errors:
                    return TIMEOUT
                continue

        # We received a valid header
        # if header[0] == ZDATA:
        #     ack_file_pos = \
        #         header[ZP0] | \
        #         header[ZP1] << 0x08 | \
        #         header[ZP2] << 0x10 | \
        #         header[ZP3] << 0x20

        # elif header[0] == ZFILE:
        #     # ack_file_pos = 0
        #     pass

        return header

    def _recv_bin16_header(self, timeout):
        '''
        Recieve a header with 16 bit CRC.
        '''
        header = []
        mine = 0
        for x in range(0, 5):
            char = self._recv(timeout)
            if char is TIMEOUT:
                return 0, False
            else:
                mine = self.calc_crc16(chr(char), mine)
                header.append(char)

        rcrc = self._recv(timeout) << 0x08
        rcrc |= self._recv(timeout)

        if mine != rcrc:
            log.error('Invalid CRC16 in header')
            return 0, False
        else:
            return 5, header

    def _recv_bin32_header(self, timeout):
        header = []
        mine = 0

        for x in range(0, 5):
            char = self._recv(timeout)
            if char is TIMEOUT:
                return 0, False
            else:
                mine = self.calc_crc32(bytes([char]), mine)
                header.append(char)

        # Read their crc
        rcrc = self._recv(timeout) << 0x00
        rcrc |= self._recv(timeout) << 0x08
        rcrc |= self._recv(timeout) << 0x10
        rcrc |= self._recv(timeout) << 0x18

        log.debug('My CRC32 = %08x, theirs = %08x' % (mine, rcrc))
        if mine != rcrc:
            log.error('Invalid CRC32 in header')
            return 0, False
        else:
            return 5, header

    def _recv_hex_header(self, timeout):
        '''
        Receive a header with HEX encoding.
        '''
        header = []
        mine = 0
        for x in range(0, 5):
            char = self._recv_hex(timeout)
            if char is TIMEOUT:
                return 0, False
            mine = self.calc_crc16(chr(char), mine)
            header.append(char)

        # Read their crc
        char = self._recv_hex(timeout)
        if char is TIMEOUT:
            return 0, False
        rcrc = char << 0x08
        char = self._recv_hex(timeout)
        if char is TIMEOUT:
            return 0, False
        rcrc |= char

        log.debug('My CRC = %04x, theirs = %04x' % (mine, rcrc))
        if mine != rcrc:
            log.error('Invalid CRC16 in receiving HEX header')
            return 0, False

        # Read to see if we receive a carriage return
        char = self.getc(1, timeout)
        if char == b'\r' or char == b'\x8d' or char == b'\n' or char == b'\x8a':
            # Expect a second one (which we discard)
            self.getc(1, timeout)
            
        # Many senders (including us) append XON after \r\n, optionally consume it
        # Actually it's safer to just do a quick non-blocking read
        char = self.getc(1, 0.1)
        if char != b'\x11' and char != b'':
            # It wasn't XON, but we consumed it. In a robust implementation we'd unget it,
            # but we can just ignore it or log it.
            pass

        return 5, header

    def _recv_hex(self, timeout):
        n1 = self._recv_hex_nibble(timeout)
        if n1 is TIMEOUT:
            return TIMEOUT
        n0 = self._recv_hex_nibble(timeout)
        if n0 is TIMEOUT:
            return TIMEOUT
        return (n1 << 0x04) | n0

    def _recv_hex_nibble(self, timeout):
        char = self.getc(1, timeout)
        if char is TIMEOUT:
            return TIMEOUT

        if isinstance(char, bytes) and len(char) > 0:
            char = char[0]
        elif isinstance(char, str) and len(char) > 0:
            char = ord(char[0])
        else:
            return TIMEOUT
            
        if char > 57: # '9'
            if char < 97 or char > 102: # 'a' to 'f'
                if char >= 65 and char <= 70: # 'A' to 'F'
                    return char - 65 + 10
                # Illegal character
                return TIMEOUT
            return char - 97 + 10
        else:
            if char < 48: # '0'
                # Illegal character
                return TIMEOUT
            return char - 48

    def _recv_file(self, zfile_header, basedir, timeout, retry):
        log.info('Abort to receive a file in %s' % (basedir,))
        pos = 0

        is_zlib = (zfile_header[ZP0] & ZF3_ZLIB) != 0 if len(zfile_header) > ZP0 else False
        if is_zlib:
            log.info("ZLIB inline decompression enabled for this file")

        force_overwrite = (zfile_header[ZP2] & ZF1_ZMCLOB) != 0 if len(zfile_header) > ZP2 else False
        if force_overwrite:
            log.info("Sender requested forced overwrite for this file")

        # Read the data subpacket containing the file information
        kind, data = self._recv_data(pos, timeout, ack=False)
        pos += len(data)
        if kind not in [FRAMEOK, ENDOFFRAME]:
            if kind is not TIMEOUT:
                # File info metadata corrupted
                self._send_znak(pos, timeout)
            return False

        # We got the file name
        part = data.split(b'\x00')
        filename = part[0].decode('utf-8', 'replace')
        filepath = os.path.join(basedir, os.path.basename(filename))
        
        file_size_on_disk = 0
        if os.path.exists(filepath) and not force_overwrite:
            file_size_on_disk = os.path.getsize(filepath)
            fp = open(filepath, 'ab')
            log.info('File exists, resuming from offset %d' % file_size_on_disk)
        else:
            if force_overwrite and os.path.exists(filepath):
                log.info('File exists, but overwrite requested')
            fp = open(filepath, 'wb')
            
        part = part[1].split(b' ')
        log.info('Meta %r' % (part,))
        size = int(part[0])
        # Date is octal (!?)
        if len(part) > 1 and part[1]:
            date = datetime.datetime.fromtimestamp(int(part[1], 8))
        else:
            date = datetime.datetime.now()
        # We ignore mode and serial number, whatever, dude :-)

        log.info('Receiving file "%s" with size %d, mtime %s' %
                 (filename, size, date))

        # Receive contents
        start = time.time()
        kind = None
        total_size = file_size_on_disk
        
        # Send initial ZRPOS
        self._send_pos_header(ZRPOS, file_size_on_disk, timeout)
        
        while True:
            header = self._recv_header(timeout)
            if header is TIMEOUT or header is False:
                break
            kind = header[0]
            
            if kind == ZDATA:
                decompressor = zlib.decompressobj() if is_zlib else None
                # Read data subpackets
                frame_kind = FRAMEOK
                while frame_kind == FRAMEOK:
                    frame_kind, chunk = self._recv_data(fp.tell(), timeout)
                    if frame_kind in [ENDOFFRAME, FRAMEOK]:
                        if decompressor:
                            try:
                                chunk = decompressor.decompress(chunk)
                            except zlib.error as e:
                                log.error(f"Zlib decompression failed: {e}")
                                self._send_pos_header(ZRPOS, fp.tell(), timeout)
                                break
                        fp.write(chunk)
                        total_size += len(chunk)
                        if self.progress_callback:
                            self.progress_callback(filename, size, total_size)
            elif kind == ZEOF:
                # File EOF reached
                break
            elif kind == ZNAK:
                # Resend ZRPOS? Or wait?
                pass
            else:
                log.info(f"Unexpected header during file transfer: {kind}")
                pass

        # End of file
        speed = (total_size / (time.time() - start))
        log.info('Receiving file "%s" done at %.02f bps' % (filename, speed))

        # Truncate to exact size specified in ZFILE header to strip any trailing ZMODEM frame padding
        fp.truncate(size)
        fp.close()
        
        # Update file metadata
        mtime = time.mktime(date.timetuple())
        os.utime(filepath, (mtime, mtime))

    def _recv_file_data(self, pos, fp, timeout):
        self._send_pos_header(ZRPOS, pos, timeout)
        kind = 0
        dpos = -1
        while dpos != pos:
            while kind != ZDATA:
                if kind is TIMEOUT:
                    return TIMEOUT, 0
                else:
                    header = self._recv_header(timeout)
                    if header is TIMEOUT:
                        return TIMEOUT, 0
                    kind = header[0]

            # Read until we are at the correct block
            dpos = \
                header[ZP0] | \
                header[ZP1] << 0x08 | \
                header[ZP2] << 0x10 | \
                header[ZP3] << 0x18

        # TODO: stream to file handle directly
        kind = FRAMEOK
        size = 0
        while kind == FRAMEOK:
            kind, chunk = self._recv_data(pos, timeout)
            if kind in [ENDOFFRAME, FRAMEOK]:
                fp.write(chunk)
                size += len(chunk)

        return kind, size

    def _send(self, char, timeout, esc=True):
        if char == ZDLE:
            self._send_esc(char, timeout)
        elif char in [0x10, 0x90, 0x11, 0x91, 0x13, 0x93]:
            self._send_esc(char, timeout)
        elif char in [0x0d, 0x0a]:
            # ALWAYS escape CR and LF to survive PTY translations (ONLCR, ICRNL, IGNCR)
            self._send_esc(char, timeout)
        elif getattr(self, 'escape_all', False) and (char < 0x20 or char == 0x7f):
            self._send_esc(char, timeout)
        elif char in [0x8d] or not esc:
            self.putc(bytes([char]), timeout)
        else:
            self.putc(bytes([char]), timeout)

    def _send_esc(self, char, timeout):
        self.putc(bytes([ZDLE]), timeout)
        if char == 0x7f:
            self.putc(bytes([ZRUB0]), timeout)
        elif char == 0xff:
            self.putc(bytes([ZRUB1]), timeout)
        else:
            self.putc(bytes([char ^ 0x40]), timeout)

    def _send_znak(self, pos, timeout):
        self._send_pos_header(ZNAK, pos, timeout)

    def _send_pos_header(self, kind, pos, timeout):
        header = []
        header.append(kind)
        header.append(pos & 0xff)
        header.append((pos >> 0x08) & 0xff)
        header.append((pos >> 0x10) & 0xff)
        header.append((pos >> 0x20) & 0xff)
        self._send_hex_header(header, timeout)

    def _send_hex(self, char, timeout):
        char = char & 0xff
        self._send_hex_nibble(char >> 0x04, timeout)
        self._send_hex_nibble(char >> 0x00, timeout)

    def _send_hex_nibble(self, nibble, timeout):
        nibble &= 0x0f
        self.putc(('%x' % nibble).encode('ascii'), timeout)

    def _send_hex_header(self, header, timeout):
        log.debug(f'Sending hex header: {header}')
        buf = bytearray([ZPAD, ZPAD, ZDLE, ZHEX])
        mine = 0

        # Update CRC
        for char in header:
            mine = self.calc_crc16(chr(char), mine)
            buf.extend(('%x' % (char >> 0x04)).encode('ascii'))
            buf.extend(('%x' % (char & 0x0f)).encode('ascii'))

        # Transmit the CRC
        crc1 = mine >> 0x08
        buf.extend(('%x' % (crc1 >> 0x04)).encode('ascii'))
        buf.extend(('%x' % (crc1 & 0x0f)).encode('ascii'))
        
        crc2 = mine & 0xff
        buf.extend(('%x' % (crc2 >> 0x04)).encode('ascii'))
        buf.extend(('%x' % (crc2 & 0x0f)).encode('ascii'))

        buf.extend(b'\r\n')
        buf.extend(XON)
            
        self.putc(bytes(buf), timeout)

    def _send_zrinit(self, timeout):
        log.debug('Sending ZRINIT header')
        zf1 = ZF1_CANZLIB if self.compress_enabled else 0
        header = [ZRINIT, 0, 0, zf1, 4 | ZF0_CANFDX |
                  ZF0_CANOVIO | ZF0_CANFC32 | ZF0_ESCCTL]
        self._send_hex_header(header, timeout)

# --- End modem/protocol/zmodem.py ---

# --- Begin rz.py ---

"""
rz.py - A ZMODEM file receiver.
"""


# Add the current directory to the Python path

def getc(size, timeout=1):
    
    # If using sys.stdin.buffer, select() will wait on the FD even if the buffer has data.
    # To fix this, we read directly from the raw file descriptor.
    fd = sys.stdin.fileno()
    
    # Wait for data
    r, _, _ = select.select([fd], [], [], timeout)
    if r:
        b = os.read(fd, size)
        if b:
            return b
    return b''

def putc(data, timeout=1):
    import os, sys
    os.write(sys.stdout.fileno(), data)


def main():
    parser = argparse.ArgumentParser(
        description="Receive files with ZMODEM protocol (rz)."
    )
    parser.add_argument(
        '--directory',
        type=str,
        default='.',
        help="The directory to save received files into. Defaults to current directory."
    )
    
    parser.add_argument(
        '--request',
        type=str,
        help="Request the local wrapper to upload a specific file."
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help="Enable debug logging"
    )
    
    parser.add_argument(
        '-c', '--compress',
        action='store_true',
        help="Advertise inline ZLIB compression support and use it if sender agrees"
    )
    
    parser.add_argument(
        '-e', '--escape',
        action='store_true',
        help="Escape all control characters (safe for sudo/use_pty wrappers)"
    )
    
    parser.add_argument(
        '-u', '--utf8',
        action='store_true',
        help="Quoted-Printable encode the stream to survive Bastion UTF-8 proxies"
    )
    
    parser.add_argument(
        '--zdle',
        type=str,
        help="Override ZDLE byte (hex string, e.g. 1d). Useful if Bastion/SSH strips 0x18."
    )
    
    parser.add_argument(
        'command',
        nargs=argparse.REMAINDER,
        help="Optional command to run in a PTY wrapper (e.g. ssh user@host)"
    )
    
    args = parser.parse_args()
    
    if args.zdle:
        global ZDLE
        ZDLE = int(args.zdle, 16)
        ZDLE = int(args.zdle, 16)
    
    log_level = logging.DEBUG if args.debug else logging.ERROR
    logging.basicConfig(level=log_level, format='RZ: %(asctime)s [%(levelname)s] %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', force=True)
    
    if args.debug:
        # In debug mode, log to a file so it doesn't mess up the terminal
        file_handler = logging.FileHandler('/tmp/pyzmodem_rz_debug.log')
        file_handler.setFormatter(logging.Formatter('RZ: %(asctime)s [%(levelname)s] %(message)s'))
        # Clear existing handlers from root logger
        logging.getLogger().handlers = []
        logging.getLogger().addHandler(file_handler)
        sys.stderr.write("\r\n[PyZMODEM] Debug logging enabled. See /tmp/pyzmodem_rz_debug.log on local machine.\r\n")
    
    if args.command:
        # PTY Wrapper mode
        
        # Remove '--' if it's the first argument in command
        cmd = args.command
        if cmd[0] == '--':
            cmd = cmd[1:]
            
        pid, master_fd = pty.fork()
        if pid == 0:
            # Child
            os.execvp(cmd[0], cmd)
            
        # Parent
        fd = sys.stdin.fileno()
        
        def set_winsize(signum, frame):
            try:
                # Get the window size from the actual terminal (stdin)
                winsize = fcntl.ioctl(fd, termios.TIOCGWINSZ, b'0000')
                # Propagate the window size to the pseudo-terminal (master_fd)
                fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
            except OSError:
                pass

        # Set initial window size
        set_winsize(None, None)
        # Catch window resize events
        signal.signal(signal.SIGWINCH, set_winsize)

        try:
            old_settings = termios.tcgetattr(fd)
        except termios.error:
            old_settings = None
        try:
            import tty
            tty.setraw(fd)
            
            snoop_buffer = bytearray()
            stdout_fd = sys.stdout.fileno()
            
            while True:
                try:
                    r, _, _ = select.select([fd, master_fd], [], [])
                except KeyboardInterrupt:
                    # In environments like MSYS2/Git Bash, Ctrl+C may still raise
                    # KeyboardInterrupt even in raw mode. Forward it to the child.
                    try:
                        os.write(master_fd, b'\x03')
                    except OSError:
                        pass
                    continue
                
                if fd in r:
                    try:
                        data = os.read(fd, 4096)
                    except OSError:
                        break
                    if not data:
                        break
                    os.write(master_fd, data)
                    
                if master_fd in r:
                    try:
                        data = os.read(master_fd, 4096)
                    except OSError:
                        break
                    if not data:
                        break
                        
                    if args.debug:
                        logging.debug(f"PTY READ: {repr(data)}")
                    
                    snoop_buffer.extend(data)
                    if len(snoop_buffer) > 4096:
                        snoop_buffer = snoop_buffer[-4096:]
                        
                    # Check for ZMODEM signature
                    # lsz sends "rz\r**\x18B00"
                    idx = -1
                    is_upload = False
                    upload_filename = ""
                    
                    zdle_char = bytes([ZDLE])
                    zrqinit_sig = b'**' + zdle_char + b'B00'
                    zrinit_sig  = b'**' + zdle_char + b'B01'
                    
                    req_pattern = b'rz-request:([^\r\n]+)\r*\n.*?\\*\\*' + re.escape(zdle_char) + b'B0[01]'
                    req_match = re.search(req_pattern, snoop_buffer, re.DOTALL)
                    
                    if req_match:
                        is_upload = True
                        upload_filename = req_match.group(1).decode('utf-8')
                        # Find where this started in data
                        req_str = b'rz-request:' + req_match.group(1)
                        if req_str in data:
                            idx = data.find(req_str)
                        else:
                            # It straddled a chunk boundary, just use the end
                            idx_00 = data.find(zrqinit_sig)
                            idx_01 = data.find(zrinit_sig)
                            idx = max(idx_00, idx_01)
                            if idx == -1:
                                idx = 0
                    elif zrqinit_sig in snoop_buffer or zrinit_sig in snoop_buffer:
                        if zrqinit_sig in data:
                            idx = data.find(zrqinit_sig)
                            if args.debug:
                                logging.debug(f"Found **\\x{ZDLE:02x}B00 at index {idx}")
                        elif zrinit_sig in data:
                            idx = data.find(zrinit_sig)
                            if args.debug:
                                logging.debug(f"Found **\\x{ZDLE:02x}B01 at index {idx}")
                        else:
                            idx = 0
                            
                    if idx != -1:
                        # We found it! Now we need to start intercepting.
                        
                        # First, if the signature was split across a chunk boundary, 
                        # ensure we pass the correct initial buffer to the protocol.
                        sig_str = zrinit_sig if (is_upload or zrinit_sig in snoop_buffer) else zrqinit_sig
                        
                        if not is_upload:
                            sig_idx = snoop_buffer.find(zrqinit_sig)
                            if sig_idx != -1:
                                zmodem_buffer = snoop_buffer[sig_idx:]
                            else:
                                zmodem_buffer = data[idx:]
                        else:
                            # Skip the request string and get to the **\x1dB01
                            zmodem_buffer = snoop_buffer[snoop_buffer.find(zrinit_sig):]
                            
                        def wrapper_getc(size, timeout=1):
                            nonlocal zmodem_buffer
                            if zmodem_buffer:
                                chunk = zmodem_buffer[:size]
                                zmodem_buffer = zmodem_buffer[size:]
                                return chunk
                            rr, _, _ = select.select([master_fd], [], [], timeout)
                            if rr:
                                try:
                                    return os.read(master_fd, size)
                                except OSError:
                                    return b''
                            return b''
                            
                        def wrapper_putc(d, timeout=1):
                            try:
                                os.write(master_fd, d)
                            except OSError:
                                pass
                                
                        if is_upload:
                            # If it's a relative path and not in the current dir, check the --directory fallback
                            upload_path = upload_filename
                            if not os.path.isabs(upload_path) and not os.path.exists(upload_path):
                                potential_path = os.path.join(args.directory, upload_filename)
                                if os.path.exists(potential_path):
                                    upload_path = potential_path
                                    
                            sys.stderr.write(f"\r\n\033[K[PyZMODEM] Local wrapper requested to upload {upload_path}...\r\n")
                            sys.stderr.write("[PyZMODEM] Tip: Press Ctrl+C to abort the transfer.\r\n")
                            
                            def upload_progress(filename, total_size, uploaded):
                                if total_size > 0:
                                    pct = int((uploaded / total_size) * 100)
                                    sys.stderr.write(f"\r[PyZMODEM] Sending {filename}: {pct}% ({uploaded}/{total_size} bytes)\033[K")
                                else:
                                    sys.stderr.write(f"\r[PyZMODEM] Sending {filename}: {uploaded} bytes\033[K")
                                sys.stderr.flush()

                            # Temporarily restore normal terminal mode so Ctrl+C works to interrupt
                            if old_settings is not None:
                                try:
                                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                                except termios.error:
                                    pass
                            z = ZMODEM(wrapper_getc, wrapper_putc, progress_callback=upload_progress, compress=args.compress, escape_all=args.escape, utf8=args.utf8)
                            try:
                                success = z.send([upload_path], overwrite=True)
                            except KeyboardInterrupt:
                                sys.stderr.write(f"\r\n[PyZMODEM] Transfer interrupted by user.\r\n")
                                # Send 5 CAN bytes to tell remote to abort
                                try:
                                    z.abort()
                                except Exception:
                                    pass
                                success = False
                            except Exception as e:
                                sys.stderr.write(f"\r\n[PyZMODEM] Transfer failed with error: {e}\r\n")
                                try:
                                    z.abort()
                                except Exception:
                                    pass
                                success = False
                            finally:
                                # Put back into raw mode
                                try:
                                    tty.setraw(fd)
                                except termios.error:
                                    pass
                                
                            if success:
                                sys.stderr.write(f"\r\n[PyZMODEM] Successfully uploaded {upload_path}.\r\n")
                                flush_needed = False
                            else:
                                sys.stderr.write(f"\r\n[PyZMODEM] Upload failed.\r\n")
                                flush_needed = True
                                
                            # If we were interrupted on the remote side, flush garbage out of the pipe
                            if flush_needed:
                                while True:
                                    try:
                                        rr, _, _ = select.select([master_fd], [], [], 0.1)
                                    except KeyboardInterrupt:
                                        continue
                                    if not rr:
                                        break
                                    try:
                                        os.read(master_fd, 4096)
                                    except OSError:
                                        break
                        else:
                            def progress(filename, total_size, downloaded):
                                if total_size > 0:
                                    pct = int((downloaded / total_size) * 100)
                                    sys.stderr.write(f"\r[PyZMODEM] Receiving {filename}: {pct}% ({downloaded}/{total_size} bytes)\033[K")
                                else:
                                    sys.stderr.write(f"\r[PyZMODEM] Receiving {filename}: {downloaded} bytes\033[K")
                                sys.stderr.flush()
    
                            # Temporarily restore normal terminal mode so Ctrl+C works to interrupt
                            if old_settings is not None:
                                try:
                                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                                except termios.error:
                                    pass
                            sys.stderr.write("[PyZMODEM] Tip: Press Ctrl+C to abort the transfer.\r\n")
                            z = ZMODEM(wrapper_getc, wrapper_putc, progress_callback=progress, compress=args.compress, escape_all=args.escape, utf8=args.utf8)
                            try:
                                count = z.recv(args.directory)
                            except KeyboardInterrupt:
                                sys.stderr.write(f"\r\n[PyZMODEM] Transfer interrupted by user.\r\n")
                                # Send 5 CAN bytes to tell remote to abort
                                try:
                                    z.abort()
                                except Exception:
                                    pass
                                count = 0
                            except Exception as e:
                                sys.stderr.write(f"\r\n[PyZMODEM] Transfer failed with error: {e}\r\n")
                                try:
                                    z.abort()
                                except Exception:
                                    pass
                                count = 0
                            finally:
                                # Put back into raw mode
                                try:
                                    tty.setraw(fd)
                                except termios.error:
                                    pass
                            
                            if count:
                                sys.stderr.write(f"\r\n[PyZMODEM] Successfully received {count} file(s).\r\n")
                                flush_needed = False
                            else:
                                sys.stderr.write("\r\n[PyZMODEM] Transfer failed.\r\n")
                                flush_needed = True
                                
                            # If we were interrupted or failed, flush any garbage out of the pipe
                            if flush_needed:
                                while True:
                                    try:
                                        rr, _, _ = select.select([master_fd], [], [], 0.1)
                                    except KeyboardInterrupt:
                                        continue
                                    if not rr:
                                        break
                                    try:
                                        os.read(master_fd, 4096)
                                    except OSError:
                                        break
                        
                        # Transfer finished, resume pass-through
                        snoop_buffer.clear()
                    else:
                        os.write(stdout_fd, data)
                        
        finally:
            try:
                if old_settings:
                    termios.tcsetattr(fd, termios.TCSANOW, old_settings)
            except termios.error:
                pass
            
    else:
        # Standalone mode
        fd = sys.stdin.fileno()
        try:
            old_settings = termios.tcgetattr(fd)
        except termios.error:
            old_settings = None
        
        if args.request:
            # Emit our special request signature before starting ZMODEM receiver
            sys.stdout.write(f"rz-request:{args.request}\r\n")
            sys.stdout.flush()
            
        print("\r\n[PyZMODEM] Tip: Press Ctrl+X 5 times to abort the transfer at any time.\r\n", file=sys.stderr)
            
        try:
            # Set raw mode
            import tty
            try:
                tty.setraw(fd)
            except termios.error:
                pass
            
            z = ZMODEM(getc, putc, compress=args.compress, escape_all=args.escape, utf8=args.utf8)
            
            # Start receiver loop
            # The recv() method in xyzmodem returns the number of files received.
            try:
                count = z.recv(args.directory)
            except KeyboardInterrupt:
                print("\r\n[PyZMODEM] Transfer interrupted by user.\r\n", file=sys.stderr)
                try:
                    putc(bytes([ZDLE]) * 5, 1)
                except Exception:
                    pass
                count = 0
            except Exception as e:
                print(f"\r\n[PyZMODEM] Transfer failed with error: {e}\r\n", file=sys.stderr)
                try:
                    putc(bytes([ZDLE]) * 5, 1)
                except Exception:
                    pass
                count = 0
            
            if count:
                sys.stderr.write(f"\r\nReceived {count} files.\r\n")
            else:
                sys.stderr.write("\r\nTransfer failed or no files received.\r\n")
        finally:
            try:
                if old_settings:
                    termios.tcsetattr(fd, termios.TCSANOW, old_settings)
            except termios.error:
                pass

if __name__ == "__main__":
    main()

# --- End rz.py ---
