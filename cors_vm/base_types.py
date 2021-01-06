class uint8_t:

    def __init__(self, value):
        self._uint8 = value & 0xff

    def __repr__(self):

        return f"uint8_t({hex(self.uint8)})"

    def __str__(self):

        return f"{hex(self.uint8)}"

    @property
    def uint8(self):
        return self._uint8 & 0xff

    @property
    def val(self):
        return self.uint8 & 0xff
    
class uint16_t:

    def __init__(self, value):
        self._lo_byte = (value & 0xff)
        self._ho_byte = (value & 0xff00) >> 8

    def __repr__(self):

        return f"uint16_t({hex(self.uint16)})"

    def __str__(self):

        return f"{hex(self.uint16)}"


    def __add__(self, other):
        val = self.uint16 + other

        return uint16_t(val)

    def __sub__(self, other):

        if isinstance(other, uint16_t):
            val = self.uint16 - other.uint16
        else:
            val = self.uint16 - other

        return uint16_t(val)

    @property
    def lo_byte(self):
        return self._lo_byte
    
    @property
    def ho_byte(self):
        return self._ho_byte
    

    @property
    def uint16(self):
        return (self._ho_byte << 8) + self._lo_byte
    
    @uint16.setter
    def uint16(self, value):

        self._lo_byte = value & 0xff
        self._ho_byte = (value & 0xff00) >> 8

    @property
    def val(self):
        return self.uint16
    
    def as_tuple(self):
        return (self._ho_byte, self._lo_byte)
