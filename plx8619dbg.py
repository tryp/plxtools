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


def plx_validate_read(count, data_in):
    if (count < 0):
        print "error: %s" % aa_status_string(count)
        return -1
    elif (count == 0):
        print "error: no bytes read"
        print "  are you sure you have the right slave address?"
        return -2 
    elif (count != 4):
        print "error: read %d bytes (expected %d)" % (count, length)
        return -3
    
    return 0


def plx_read4 (handle, device, port, addr):
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

def plx_read_qword (handle, device, port, addr):
        (count, data_in) = plx_read4(handle, device, port, addr)

        errval = plx_validate_read(count, data_in)
        if(errval < 0):
            return errval

        qword = data_in[3] + (data_in[2] << 8) + (data_in[1] << 16) + (data_in[0] << 24) 

        return qword

def plx_get_portconfig(handle, device):
    val = plx_read_qword(handle, device, 0, 0x574)
    portcfg = val & 0xf
    return portcfg

def plx_8619_get_portmap(portcfg):
    if portcfg == 0:
        portmap = 16 * [1]
    elif portcfg == 1:
        portmap = 16 * [1]
        portmap[0] = 4
        portmap[4] = 0
        portmap[6] = 0
        portmap[8] = 0

    elif portcfg == 2:
        portmap = [4, 4, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1]

    elif portcfg == 3:
        portmap = [4, 4, 4, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1]

    elif portcfg == 4:
        portmap = (4 * [4]) + (12 * [0])
    
    elif portcfg == 5:
        portmap = [8, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]

    elif portcfg == 6:
        portmap = [8, 4, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1]

    elif portcfg == 7:
        portmap = 16 * [0]
        portmap[0] = 8
        portmap[1] = 4
        portmap[3] = 1
        portmap[11] = 1
        portmap[13] = 1
        portmap[15] = 1

    elif portcfg == 7:
        portmap = 16 * [0]
        portmap[0] = 8
        portmap[1] = 4
        portmap[3] = 4

    elif portcfg == 8:
        portmap = 16 * [0]
        portmap[0] = 8
        portmap[1] = 8

    return portmap

def plx_get_recv_errcounts(handle, device):
    even_0246_counts = plx_read_qword(handle, device, 0, 0xb88)
    odd_1357_counts = plx_read_qword(handle, device, 0, 0xb8c)
    even_8ace_counts = plx_read_qword(handle, device, 0, 0xb90)
    odd_9bdf_counts = plx_read_qword(handle, device, 0, 0xb94)

    recv_errcounts = 16 * [0]
    recv_errcounts[0] = (even_0246_counts >> 0) & 0xff
    recv_errcounts[1] = (odd_1357_counts >> 0) & 0xff
    recv_errcounts[2] = (even_0246_counts >> 8) & 0xff
    recv_errcounts[3] = (odd_1357_counts >> 8) & 0xff
    recv_errcounts[4] = (even_0246_counts >> 16) & 0xff
    recv_errcounts[5] = (odd_1357_counts >> 16) & 0xff
    recv_errcounts[6] = (even_0246_counts >> 24) & 0xff
    recv_errcounts[7] = (odd_1357_counts >> 24) & 0xff
    recv_errcounts[8] = (even_8ace_counts >> 0) & 0xff
    recv_errcounts[9] = (odd_9bdf_counts >> 0) & 0xff
    recv_errcounts[10] = (even_8ace_counts >> 8) & 0xff
    recv_errcounts[11] = (odd_9bdf_counts >> 8) & 0xff
    recv_errcounts[12] = (even_8ace_counts >> 16) & 0xff
    recv_errcounts[13] = (odd_9bdf_counts >> 16) & 0xff
    recv_errcounts[14] = (even_8ace_counts >> 24) & 0xff
    recv_errcounts[15] = (odd_9bdf_counts >> 24) & 0xff

    return recv_errcounts

def plx_get_ports_enabled(handle, device):
    val = plx_read_qword(handle, device, 0, 0x668)
    en = 16 * [0]
    for i in range(16):
        if val & 1 << i:
            en[i] = 1
    return en

def plx_get_receiver_detected(handle, device):
    rd_low = plx_read_qword(handle, device, 0, 0x200)
    rd_high = plx_read_qword(handle, device, 0, 0x204)

    rd = 16 * [0]
    for i in range(8):
        rd[i] = (rd_low >> (24 + 1)) & 0x1
        
    for i in range(8):
        rd[8 + i] = (rd_high >> (24 + 1)) & 0x1

    return rd

def plx_get_lanes_up(handle, device):
    val = plx_read_qword(handle, device, 0, 0x1f4)
    lanes_up = 16 * [0]
    for i in range(16):
        lanes_up[i] = (val >> i) & 0x1

    return lanes_up

def plx_get_linkandspeed(handle, device):
    widths_low = plx_read_qword(handle, device, 0, 0x66c)
    widths_high = plx_read_qword(handle, device, 0, 0x670)
    widths = 16 * [0]
    speeds = 16 * [0]

    w_map = [1, 2, 4, 8]
    s_map = [2.5, 5.0]

    for i in range(8):
        ws = widths_low >> (6 * i)
        w = ws & 0x7
        s = (ws >> 3) & 0x1
        widths[i] = w_map[w]
        speeds[i] = s_map[s]
    for i in range(8):
        ws = widths_high >> (6 * i)
        w = ws & 0x7
        s = (ws >> 3) & 0x1
        widths[8 + i] = w_map[w]
        speeds[8 + i] = s_map[s]
    return (widths, speeds)

def plx_get_debug_control(handle, device):
    val = plx_read_qword(handle, device, 0, 0x1dc)
    debug_control = {}
    debug_control["UPCFG Timer Enable"] = (val >> 4) & 0x1
    debug_control["SMBus Enable"] = (val >> 5) & 0x1
    debug_control["NT P2P Enable"] = (val >> 6) & 0x1
    debug_control["Upstream Port ID"] = (val >> 8) & 0xf
    debug_control["Interrupt Fencing Mode"] = (val >> 12) & 0x3
    debug_control["Hardware/Software Configuration Mode Control"] = (val >> 15) & 0x1
    debug_control["Upstream Hot Reset Control"] = (val >> 16) & 0x1
    debug_control["Disable Serial EEPROM Load on Hot Reset"] = (val >> 17) & 0x1
    debug_control["NT Mode Enable"] = (val >> 18) & 0x1
    debug_control["NT Port DL_Down Porpagation Disable"] = (val >> 19) & 0x01
    debug_control["Upstream Port DL_Down Porpagation Disable"] = (val >> 20) & 0x01
    debug_control["Cut-Thru Enable"] = (val >> 21) & 0x1
    debug_control["NT Port Number"] = (val >> 24) & 0xf
    debug_control["Virtual Interface Access Enable"] = (val >> 28) & 0x1
    debug_control["Link Interface Access Enable"] = (val >> 29) & 0x1
    debug_control["Inhibit EEPROM NT-Link Load on Hot Reset"] = (val >> 30) & 0x1
    debug_control["Load Only EEPROM NT-Link on Hot Reset"] = (val >> 31) & 0x1

    return debug_control

def plx_get_link_status(handle, device, port):
    val = plx_read_qword(handle, device, port, 0x78)
    s_map=[0, 2.5, 5.0]
    ls = {}
    ls["Port"] = port
    ls["ASPM"] = (val >> 0) & 0x3
    ls["Link Disable"] = (val >> 4) & 0x1
    ls["Common Clock Configuration"] = (val >> 6) & 0x1
    ls["Extended Sync"] = (val >> 7) & 0x1
    ls["Clock Power Management Enable"] = (val >> 8) & 0x1
    ls["Link Bandwidth Management Interrupt Enable"] = (val >> 10) & 0x1
    ls["Link Autonomous Bandwidth Interrupt Enable"] = (val >> 11) & 0x1
    ls["Current Link Speed"] = s_map[(val >> 16) & 0xf]
    ls["Negotiated Link Width"] = (val >> 20) & 0x3f
    ls["Link Training"] = (val >> 27) & 0x1
    ls["Slot Clock Configuration"] = (val >> 28) & 0x1
    ls["Data Link Layer Link Active"] = (val >> 29) & 0x1
    ls["Link Bandwidth Management Status"] = (val >> 30) & 0x1
    ls["Link Autonomous Bandwidth Status"] = (val >> 31) & 0x1
    return ls

def plx_get_vc0_negotiation_pending(handle, device, port):
    val = plx_read_qword(handle, device, port, 0x160)
    return (val >> 17) & 0x1

def dict_pprint(d, title):
    print(title)
    for k, v in d.iteritems():
        print("  {0}: {1}".format(str(k), str(v)))

def plx_for_all_ports(handle, device, plx_func):
    ''' Applies func to all ports on device and returns a list of all results '''
    params = 16 * [0]
    for i in range(16):
        params[i] = plx_func(handle, device, i)
    return params

def plx_for_all_enabled_ports(handle, device, enabled, plx_func):
    ''' Applies func to all enabled ports on device and returns a list of all results '''
    params = []
    for i in range(16):
        if enabled[i]:
            params.append(plx_func(handle, device, i))
    return params

def plx_get_bad_tlp_count(handle, device, port):
    val = plx_read_qword(handle, device, port, 0x1e8)
    return val

def plx_get_bad_dllp_count(handle, device, port):
    val = plx_read_qword(handle, device, port, 0x1ec)
    return val

def plx_get_bad_tlp_counts(handle, device):
    return plx_for_all_ports(handle, device, plx_get_bad_tlp_count)

def plx_get_bad_dllp_counts(handle, device):
    return plx_for_all_ports(handle, device, plx_get_bad_dllp_count)

def plx_get_links_status(handle, device, enabled):
    return plx_for_all_enabled_ports(handle, device, enabled, plx_get_link_status)

def plx_get_vc0_negotiations_pending(handle, device, enabled):
    return plx_for_all_enabled_ports(handle, device, enabled, plx_get_vc0_negotiation_pending)

#==========================================================================
# MAIN PROGRAM
#==========================================================================
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
#print "Bitrate set to %d kHz" % bitrate

# Set the bus lock timeout
bus_timeout = aa_i2c_bus_timeout(handle, BUS_TIMEOUT)
#print "Bus lock timeout set to %d ms" % bus_timeout

portcfg = plx_get_portconfig(handle, device)
portmap = plx_8619_get_portmap(portcfg) 
print("Port Configuration: {0} - {1}".format(portcfg, str(portmap)))

ports_enabled = plx_get_ports_enabled(handle, device)
print("Ports Enabled: {0}".format(str(ports_enabled)))

receivers_detected = plx_get_receiver_detected(handle, device)
print("Receivers Detected: {0}".format(str(receivers_detected)))

vc0_negotiations_pending = plx_get_vc0_negotiations_pending(handle, device, ports_enabled)
print("VC0 Negotiations Pending: {0}".format(str(receivers_detected)))

lanes_up = plx_get_lanes_up(handle, device)
print("Lanes Up: {0}".format(str(lanes_up)))

(link_widths, port_speeds) = plx_get_linkandspeed(handle, device)
print("Negotiated Link Widths: {0}".format(str(link_widths)))
print("Negotiated Link Speeds: {0}".format(str(port_speeds)))

recv_errcounts = plx_get_recv_errcounts(handle, device)
print("Receive Error Counts: {0}".format(str(recv_errcounts)))

bad_tlp_counts = plx_get_bad_tlp_counts(handle, device)
print("Bad TLP Counts: {0}".format(str(bad_tlp_counts)))
bad_dllp_counts = plx_get_bad_tlp_counts(handle, device)
print("Bad DLLP Counts: {0}".format(str(bad_dllp_counts)))

#links_status = plx_get_links_status(handle, device, ports_enabled)
#for s in links_status:
#    dict_pprint(s, "Port {0} PCIe Link Status".format(s["Port"]))


#debug_control = plx_get_debug_control(handle, device)
#dict_pprint(debug_control, "Debug Control Register")


# Close the device
aa_close(handle)


# modeline...
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
