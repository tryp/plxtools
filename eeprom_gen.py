#	 Utility to generate a PEX8734 EEPROM binary

# From Pex8734 Datasheet

# Byte	0x00	0x5a		Validation Signature
# 	0x01	Set Bi 7 to enable CRC checking
#	0x02	Config reg Byte Count (LSB)
#	0x03	Config reg Byte Count (MSB)
#	0x04	RegAddr(LSB)
#	0x05	RegAddr(MSB)
#	0x06	RegData[0]
#	0x07	RegData[1]
#	0x08	RegData[2]
#	0x09	RegData[3]
#	0x0a	RegAddr(LSB)
#	0x0b	RegAddr(MSB)
#	0x0c	RegData[0]
#	0x0d	RegData[1]
#	0x0e	RegData[2]
#	0x0f	RegData[3]
#	...
#	(ByteCount +3)	RegData[3]
#	(ByteCount +4)	CRC[0]
#	(ByteCount +5)	CRC[1]
#	(ByteCount +6)	CRC[2]
#	(ByteCount +7)	CRC[3]
#


import struct
import codecs

PLX_port = {0: 0x0,
	1: 0x1,
	2: 0x2,
	3: 0x3,
	4: 0x08 | 0x00,
	5: 0x08 | 0x01,
	6: 0x08 | 0x02,
	7: 0x08 | 0x03,
	'A-LUT RAM0': 0x2c | 0x00,
	'A-LUT RAM1': 0x2c | 0x01,
	'A-LUT RAM2': 0x2c | 0x02,
	'A-LUT RAM3': 0x2c | 0x03,
	'VS0': 0x30 | 0x00,
	'VS1': 0x30 | 0x01,
	'NT0 Link': 0x38 | 0x00,
	'NT0 Virtual': 0x38 | 0x01,
	'NT1 Link': 0x38 | 0x02,
	'NT1 Virtual': 0x38 | 0x03,
	}

def PLX_RegAddr(port, addr):
	val = port << 10
	val |= (addr >> 2) & 0x3ff
	return val


def PLX_RegEntry(port, addr, value):
	RegAddr = PLX_RegAddr(port, addr)
	return struct.pack('<HI', RegAddr, value)




class PLX_RegStream(list):
	def __init__(self):
		list.__init__(self)

	def serialize(self):
		buf = bytearray()
		buf += struct.pack('b', 0x5a)
		buf += struct.pack('b', 0x00)
		buf += struct.pack('<H', len(self) * 6)
		for e in self:
			buf += e
		crcval = 0
		buf += struct.pack('<I', crcval)
		return buf


rs = PLX_RegStream()

# Enable x4x4x8 Port Config + defaults for port 4
correct_station_2_lane_reversal = True
if (correct_station_2_lane_reversal):
	rs.append(PLX_RegEntry(PLX_port[4], 0x220, # Port 4 to select station 1 (ports 4-7)
			(1 << 8) 
			| (1 << 12)
			| (1 << 13)
			| (1 << 14)
			| (1 << 30))) # enable x4x4x8 Port Config

# Disable Port 1
# Used on VPX1142 carrier in NG chassis to 
# disable port designated for NT bridge
# between processor domains
disable_port_1 = False
if (disable_port_1):
	rs.append(PLX_RegEntry(PLX_port[0], 0x208,
		(1 << 1) # Port 1 Disable
		)) 
	rs.append(PLX_RegEntry(PLX_port[0], 0x30c, # Port 0
		0x010000ff # Default POR value
		& ~(1 << 1) # Port 1 Disable clock
		)) 

# Disable Port 4
# Used on VPX7664 CPU B in NG Chassis
# disable port designated for NT bridge
# between processor domains
disable_port_4 = False
if (disable_port_4):
	rs.append(PLX_RegEntry(PLX_port[4], 0x208, # Port 4 to select station 1 (ports 4-7)
		(1 << 0) # Port 0 Disable RX termination
		)) 
	rs.append(PLX_RegEntry(PLX_port[0], 0x30c, # Port 0
		0x010000ff # 
		& ~(1 << 4) # Port 4 Disable clock
		)) 


upstream_port_1 = True
if (upstream_port_1):
	rs.append(PLX_RegEntry(PLX_port[0], 0x360,
		(0x1 << 0) # Upstream Port
		| (0x1a << 8) # NT0 port (0x1a = disabled)
		& ~(1 << 13) # NT0 1 = Enable
		| (0x1a << 16) # NT1 port (0x1a = disabled)
		& ~(1 << 21) # NT1 1 = Enable
		))

NT_port_1 = False
if (NT_port_1):
	rs.append(PLX_RegEntry(PLX_port[0], 0x360,
		(0x0 << 0) # Upstream Port
		| (0x1 << 8) # NT0 port (0x1a = disabled)
		| (1 << 13) # NT0 1 = Enable
		| (0x1a << 16) # NT1 port (0x1a = disabled)
		& ~(1 << 21) # NT1 1 = Enable
		))

NT_port_4 = False
if (NT_port_4):
	rs.append(PLX_RegEntry(PLX_port[0], 0x360,
		((0 << 0) & 0xf) # Upstream Port
		| (0x4 << 8) # NT0 port (0x1a = disabled)
		| (1 << 13) # NT0 1 = Enable
		| (0x1a << 16) # NT1 port (0x1a = disabled)
		& ~(1 << 21) # NT1 1 = Enable
		))

# If an NT port is configured, setup the Link and Virtual interfaces
if False and (NT_port_1 or NT_port_4):
	rs.append(PLX_RegEntry(PLX_port['NT0 Link'], 0x04, # NT Link Interface BAR0/1 Setup
		(1 << 1) # Memory Access Enable
		| (1 << 10) # Disable INTx from NT Link Interface
		))
	rs.append(PLX_RegEntry(PLX_port['NT0 Virtual'], 0x04, # NT Virtual Interface BAR0/1 Setup
		(1 << 1) # Memory Access Enable
		| (1 << 10) # Disable INTx from NT Virtual Interface
		))



PortCfg = {'x16': 0x1,
	'x8x8': 0x2,
	'x8x4x4': 0x3,
	'x4x4x4x4': 0x4 }
PortCfg_x4x4x4x4 = False
if (PortCfg_x4x4x4x4):
	rs.append(PLX_RegEntry(PLX_port[0], 0x300,
		(PortCfg['x4x4x4x4'] << 0)
		| (PortCfg['x8x4x4'] << 3)
		))

PortCfg_x8x8 = True
if (PortCfg_x8x8):
	rs.append(PLX_RegEntry(PLX_port[0], 0x300,
		(PortCfg['x8x8'] << 0)
		| (PortCfg['x8x4x4'] << 3)
		))

print("Data:")
print(codecs.encode(rs.serialize(), "hex_codec"))

filename = "plx8732"
if (correct_station_2_lane_reversal): filename += "_stn2rev"
if (PortCfg_x4x4x4x4): filename += "_x4x4x4x4"
if (PortCfg_x8x8): filename += "_x8x8"
if (disable_port_1): filename += "_port1dis"
if (disable_port_4): filename += "_port4dis"
if (NT_port_1): filename += "_port1NT"
if (NT_port_4): filename += "_port4NT"
if (upstream_port_1): filename += "_port1Upst"

filename += ".bin"
with open(filename, mode="wb") as f:
	print("to File {}".format(filename))
	f.write(rs.serialize())


