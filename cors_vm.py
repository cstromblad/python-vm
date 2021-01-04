import random
import time

from collections import namedtuple
from typing import List

DataByte = namedtuple('DataByte', ['addr','data'])


"""
    Flaggan finns på minnesadress 0x3300 - 0x332b. För att skriva ut den pushar
    vi första adressen till stacken och anropar därefter print-funktionen.
    
    jmp 0x1000
    push 0x3300
    call 3 (print)

    print hämtar alltid sitt första argument från stacken.

"""

# Memory alignment == 2

SECRET_FLAG = b"CORS_CTF{9fa19b901162d238941a36e2a1a322e6}\x00"

MAX_RUN_TIME = 2.0  # Two seconds

class uint8_t:

    def __init__(self, value):
        self._uint8 = value & 0xff

    def __repr__(self):

        return f"uint8_t({hex(self.uint8)})"

    @property
    def uint8(self):
        return self._uint8 

class uint16_t:

    def __init__(self, value):
        self._lo_byte = (value & 0xff)
        self._ho_byte = (value & 0xff00) >> 8

    def __repr__(self):

        return f"uint16_t({hex(self.uint16)})"

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

    def as_tuple(self):
        return (self._ho_byte, self._lo_byte)

class RandomAccessMemory:

    def __init__(self, size: int = 32768):

        self._memory: bytearray = bytearray(size)

    @property
    def memory(self):
        return self._memory

    def read_byte(self, addr: uint16_t):

        val = self.memory[addr.uint16]

        return uint8_t(val)

    def read_word(self, addr: uint16_t):

        val = ((self.memory[addr.uint16]) << 8) + (self.memory[addr.uint16 + 1])
        return uint16_t(val)

    def write_word(self, args):
        (value, addr) = args

        self.memory[addr.uint16] = value.ho_byte
        self.memory[addr.uint16 + 1] = value.lo_byte

    def write_byte(self, args):

        (value, addr) = args

        self.memory[addr.uint16] = value.uint8

class CentralProcessingUnit:

    def __init__(self, ram):
        
        self.ram = ram

        self._reg01 = uint16_t(0)
        self._reg02 = 0
        self._reg03 = 0
        self._reg04 = 0

        self._ip = 0
        self._sp = uint16_t(0x8000)
        self._bp = uint16_t(0x8000)

        self.registers = {
            0: {"name": "Instruction Pointer",
                "value": self.ip},
            1: {"name": "Stack Pointer",
                "value": self.sp},
            2: {"name": "Base Pointer",
                "value": self.bp},
            3: {"name": "Register 01",
                "value": self.reg01}
            }

    @property
    def ip(self):
        return self._ip

    @ip.setter
    def ip(self, addr: uint16_t):
        self._ip = addr

    @property
    def sp(self):
        return self._sp
    
    @sp.setter
    def sp(self, addr: uint16_t):
        self._sp = addr

    @property
    def bp(self):
        return self._bp
    
    @property
    def reg01(self):
        return self._reg01

    @reg01.setter
    def reg01(self, value: uint16_t):
        self._reg01 = value

    # Instructions

    def move_to_reg(self, args):

        (reg, value) = args
        
        self.registers[reg.uint8]['value'].uint16 = value.uint16

    def push_reg(self, args):

        (reg) = args
        
        # Stack grows downards, reduce by two bytes and then write value to 
        # the address pointed to by cpu.sp
             
        value = self.registers[reg.uint8]['value']
        
        # Write it to the stack
        self.ram.write_word((value, self.sp - 2))

        # Decrement stackpointer to accomodate the new 

        self.sp.uint16 -= 2

    def pop_reg(self, args):
        pass

    def no_operation(self):
        return
    
class VirtualMachineV2:

    def __init__(self, 
                 program: bytes, 
                 data: List[tuple] = [], 
                 memory_size: int = 32768, 
                 num_cpus: int = 1):

        self.ram = RandomAccessMemory(memory_size)
        self.cpu = CentralProcessingUnit(self.ram)

        self.output = ""

        self._should_halt = False

        self.opcodes = {
            0: {"name": "halt",
                "func": self.halt,
                "size": 0},
            3: {"name": "out",
                "func": self.out,
                "size": 2},
            4: {"name": "write_word",
                "func": self.ram.write_word,
                "size": 4},
            5: {"name": "write_byte",
                "func": self.ram.write_byte,
                "size": 3,
                "reversed": False},
            6: {"name": "push_from_reg",
                "func": self.cpu.push_reg,
                "size": 1},
            7: {"name": "pop_to_reg",
                "func": self.cpu.pop_reg,
                "size": 1},
            8: {"name": "move to register",
                "func": self.cpu.move_to_reg,
                "size": 3,
                "reversed": True},
            9: {"name": "call",
                "func": self.call_func,
                "size": 1,
                "reversed": False},
            90: {"name": "no operation",
                "func": self.cpu.no_operation,
                "size": 0},
            }

        # Write program to memory at location 0x0000
        for index, byte in enumerate(program):

            args = (uint8_t(byte), uint16_t(0x0000 + index))

            self.ram.write_byte(args)

        self.cpu.ip = uint16_t(0x0000)
        
    def fetch_instruction(self):
        
        return self.ram.read_byte(self.cpu.ip)

    def decode_instruction(self, opcode):
        
        isize = self.opcodes[opcode]['size']
        if isize == 0:
            # Zero arguments

            return ()
        elif isize == 1:

            byte = self.ram.read_byte(self.cpu.ip)

            return (byte)
        
        elif isize == 2:
            # One argument (1 word)

            word = self.ram.read_word(self.cpu.ip)

            return (word)

        elif isize == 3:
            # Two arguments (1 byte and 1 word)
            if self.opcodes[opcode]['reversed']:

                word = self.ram.read_word(self.cpu.ip)
                byte = self.ram.read_byte(self.cpu.ip + 2)

            else:

                byte = self.ram.read_byte(self.cpu.ip)
                word = self.ram.read_word(self.cpu.ip + 1)


            return (byte, word)

        elif isize == 4:
            # Two arguments (2 words)

            word_1 = self.ram.read_word(self.cpu.ip)
            word_2 = self.ram.read_word(self.cpu.ip + 2)

            return (word_1, word_2)

    def run_program(self):

        while not self.should_halt():

            opcode = self.fetch_instruction().uint8
            self.cpu.ip += 1

            args = self.decode_instruction(opcode)
            self.cpu.ip += self.opcodes[opcode]['size']

            self.opcodes[opcode]['func'](args)

    def should_halt(self):

        return self._should_halt
    
    # Instructions

    def halt(self, _ ):
        self._should_halt = True

    def out(self, args):
        (addr) = args

        i = 0
        while True:
            byte = self.ram.read_byte(addr + i).uint8
            if byte == 0:
                break

            self.output += chr(byte)

            i += 1

    def call_func(self, args):

        """ Set IP to value from Reg01 and push next instruction to SP """

        (addr) = args

        # Push current SP 
        self.cpu.push_reg(self.cpu.bp.uint16)

        # Set BP to SP
        self.cpu.bp.uint16 = self.cpu.sp.uint16

        # Finally we set IP to the addr of the function to be called
        self.cpu.ip.uint16 = addr.uint16
        

    # Debug and helpers methods

    def stack_info(self):
        print(f"--- Stack frame--- ")

        if (self.cpu.bp - self.cpu.sp).uint16 == 0:
            print("Här var det tomt.")
        else:

            for i in range(0, (self.cpu.bp - self.cpu.sp).uint16):
                
                addr = format((self.cpu.bp - 1 - i).uint16, 'x')
                data = format(self.ram.read_byte(self.cpu.bp - 1 - i ).uint8, 'x')

                if not (i % 4):
                    print(f"\n{addr}: {data}", end='')
                else:
                    print(f" {data}", end='')

        print('\n')



# vm  = VirtualMachine(b'\x01\x00\x41\x01\x00\x41\x02\x02\x00\x03')
# vm = VirtualMachine(b'\x04\x00\x43\x20\x00\x04\x00\x4f\x20\x02\x04\x00\x52\x20\x04\x04\x00\x53\x20\x06\x04\x00\x00\x20\x08\x03\x20\x00\x00', data=[b"CORS_CTF{9fa19b901162d238941a36e2a1a322e6}\x00"])
"""

push 'H'
push 'A'
pop &(0x200) // 512

"""


"""
mov 'C', R01
push R01
mov 'O', R01
push

0x03 

0x7fff EBP / ESP
 ...
0x0021 Empty
0x0020 Data End 

0x0005 Data start
0x0004 Program end
0x0001 Program start
...

...

Uppgiften är att skriva CORS\x00 till minnesadressen 0x2000 .. 0x2008 och sedan
anropa funktionen OUT 0x2000 vilket då skriver ut CORS och om rätt text kommer
till output så skickas även flaggan.

\x04\x00\x43\x20\x00\x04\x00\x4f\x20\x02\x04\x00\x52\x20\x04\x04\x00\x53\x20\x06\x04\x00\x00\x20\x08\x03\x20\x00\x00

write 'C', 0x2000
write 'O', 0x2002
write 'R', 0x2004
write 'S', 0x2006
write \x00, 0x2008
out 0x2000
halt

"""