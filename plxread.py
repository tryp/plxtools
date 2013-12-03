#!/bin/env python
#
# plx debug
# Chris Douglass <cdouglass@oriontechnologies.com>
# 
# Connects to a PLX PCIe switch I2C port and reads
# registers for debug.
#
#==========================================================================
# (c) 2004  Total Phase, Inc.
#--------------------------------------------------------------------------
# Project : Aardvark Sample Code
# File    : aai2c_eeprom.py
#--------------------------------------------------------------------------
# Perform simple read and write operations to an I2C EEPROM device.
#--------------------------------------------------------------------------
# Redistribution and use of this file in source and binary forms, with
# or without modification, are permitted.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#==========================================================================

#==========================================================================
# IMPORTS
#==========================================================================
import sys

from aardvark_py import *


#==========================================================================
# CONSTANTS
#==========================================================================
PAGE_SIZE   = 8
BUS_TIMEOUT = 150  # ms

aaport = 0
bitrate = 100
# The default i2c address for the device is 0x38. 
# on the Orion VPX765x boards, the address is strapped to 0x3c
device  = 0x3c

#==========================================================================
# FUNCTIONS
#==========================================================================
def _writeMemory (handle, device, addr, length, zero):
    # Write to the I2C EEPROM
    #
    # The AT24C02 EEPROM has 8 byte pages.  Data can written
    # in pages, to reduce the number of overall I2C transactions
    # executed through the Aardvark adapter.
    n = 0
    while (n < length):
        data_out = array('B', [ 0 for i in range(1+PAGE_SIZE) ])

        # Fill the packet with data
        data_out[0] = addr & 0xff
        
        # Assemble a page of data
        i = 1
        while 1:
            if not (zero): data_out[i] = n & 0xff

            addr = addr + 1
            n = n +1
            i = i+1

            if not (n < length and (addr & (PAGE_SIZE-1)) ): break
        
        # Truncate the array to the exact data size
        del data_out[i:]

        # Write the address and data
        aa_i2c_write(handle, device, AA_I2C_NO_FLAGS, data_out)
        aa_sleep_ms(10)


PLX_CMD_WRITE = int('00000011', 2)
PLX_CMD_READ = int('00000100', 2)

PLX_PORTSEL_NT_PORT_LINK = 0x10
PLX_PORTSEL_NT_P2P_BRIDGE = 0x11
PLX_PORTSEL_DMA = 0x12
PLX_PORTSEL_DMA_DESCRIPTORS = 0x13


def plxread_qword (handle, device, port, addr):
    cmd = PLX_CMD_READ

    command = array('B', [
        cmd,
        (port >> 1) & 0xf,
	((port & 0x01) << 7) | ((addr >> 10) & 0x3),
	(addr >> 2) & 0xff
	])
	
	
    #print("writing {0:s}]n".format(str(command)))

    # Write the address
    aa_i2c_write(handle, device, AA_I2C_NO_STOP, command)

    (count, data_in) = aa_i2c_read(handle, device, AA_I2C_NO_FLAGS, 4)

    #print("read {0}: {1}".format(count, data_in))
    return (count, data_in)

def plxread (handle, device, port, addr, length):
    # PLX register access is by qword
    for i in range(0,length,4):
        reg = addr + i
        (count, data_in) = plxread_qword(handle, device, port, reg)

        if (count < 0):
            print "error: %s" % aa_status_string(count)
            return
        elif (count == 0):
            print "error: no bytes read"
            print "  are you sure you have the right slave address?"
            return
        elif (count != 4):
            print "error: read %d bytes (expected %d)" % (count, length)

        qword = data_in[0] \
            + data_in[1] << 8 \
            + data_in[2] << 16 \
            + data_in[3] << 24 

        sys.stdout.write("0x{0:0>4x}: {1[0]:0>2x} {1[1]:0>2x} {1[2]:0>2x} {1[3]:0>2x}\n".format(reg, data_in))




#==========================================================================
# MAIN PROGRAM
#==========================================================================
if (len(sys.argv) < 2):
    print "usage: plxread port reg [length]"
    print ""
    print "example: plxread 0xa 0x240 106"
    sys.exit()

port = int(sys.argv[1], base=0)
addr    = int(sys.argv[2], base=0)
length  = int(sys.argv[3], base=0)

handle = aa_open(aaport)
if (handle <= 0):
    print "Unable to open Aardvark device on port %d" % port
    print "Error code = %d" % handle
    sys.exit()
    
# Ensure that the I2C subsystem is enabled
aa_configure(handle,  AA_CONFIG_SPI_I2C)
    
# Enable the I2C bus pullup resistors (2.2k resistors).
# This command is only effective on v2.0 hardware or greater.
# The pullup resistors on the v1.02 hardware are enabled by default.
aa_i2c_pullup(handle, AA_I2C_PULLUP_BOTH)

# Don't turn on aardvark power pin
aa_target_power(handle, AA_TARGET_POWER_NONE)

# Set the bitrate
bitrate = aa_i2c_bitrate(handle, bitrate)
print "Bitrate set to %d kHz" % bitrate

# Set the bus lock timeout
bus_timeout = aa_i2c_bus_timeout(handle, BUS_TIMEOUT)
print "Bus lock timeout set to %d ms" % bus_timeout

plxread(handle, device, port, addr, length)

    
# Close the device
aa_close(handle)




# modeline...
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
