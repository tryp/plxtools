# Utility to generate a PEX8734 EEPROM binary


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


entry0 = PLX_RegEntry(1, 0x7c, 0x01234567)
entry1 = PLX_RegEntry(4, 0x220,
		  (1 << 8) 
		| (1 << 12)
		| (1 << 13)
		| (1 << 14)
		| (1 << 30))

rs = PLX_RegStream()
rs.append(entry0)
rs.append(entry1)

print(codecs.encode(entry0, "hex_codec"))
print(codecs.encode(rs.serialize(), "hex_codec"))

with open("plx8734.bin", mode="wb") as f:
	f.write(rs.serialize())


