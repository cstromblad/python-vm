import random
import time

import collections
from typing import List

from cors_vm.base_types import uint16_t, uint8_t

Segment = collections.namedtuple('Segment', ['name', 'start_addr', 'length'])

MAX_RUN_TIME = 2.0  # Two seconds

class RandomAccessMemory:

    def __init__(self, size: int = 32768):

        self._memory_size = size
        self._memory: bytearray = bytearray(size)

    def __repr__(self):
        return f"RAM({self._memory_size})"
    def reset(self):
        self._memory = bytearray(self._memory_size)

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

        self._ip = uint16_t(0x0000)
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
                "value": self.reg01},
            4: {"name": "Instruction Pointer",
                "value": self.ip}
            }

    def __repr__(self):
        return f"CPU({self.ram})"

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
    
    @bp.setter
    def bp(self, addr: uint16_t):
        self._bp = addr

    @property
    def reg01(self):
        return self._reg01

    @reg01.setter
    def reg01(self, value: uint16_t):
        self._reg01 = value

    # Instructions

    def move_to_reg(self, args):

        (value, reg) = args
        
        self.registers[reg.uint8]['value'].uint16 = value.uint16

    def push_reg(self, args):

        (reg) = args
        
        # Stack grows downards, reduce by two bytes and then write value to 
        # the address pointed to by cpu.sp
             
        value = self.registers[reg.uint8]['value'].uint16
        print(f"push_reg: {reg} {value}")

        # Write it to the stack
        self.ram.write_word((uint16_t(value), self.sp - 2))

        # Decrement stackpointer to accomodate the new 

        self.sp -= 2

    def pop_reg(self, args):

        (reg) = args

        print(self.sp)
        word = self.ram.read_word(self.sp)
        print(word)
        self.registers[reg.uint8]['value'].uint16 = word.uint16

        self.sp += 2
        
    def no_operation(self):
        return
    
class VirtualMachineV2:

    def __init__(self, 
                 program: bytes = b'', 
                 data: List[tuple] = [], 
                 memory_size: int = 32768, 
                 num_cpus: int = 1):

        self.ram = RandomAccessMemory(memory_size)
        self.cpu = CentralProcessingUnit(self.ram)

        # Start of code_segment and length
        self.output = ""

        self._code_segments: List = list()
        self._data_segments: List = list()

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
            0xa:    {"name": "return",
                     "func": self.return_func,
                     "size": 0,
                     "reversed": False}, 
            90: {"name": "no operation",
                "func": self.cpu.no_operation,
                "size": 0},
            }

        # Write program to memory at location 0x0000

        if len(program):
            for index, byte in enumerate(program):

                args = (uint8_t(byte), uint16_t(0x0000 + index))

                self.ram.write_byte(args)

            self._code_segments.append(Segment('main_program', uint16_t(0x0000), len(program)))

            self.cpu.ip = uint16_t(0x0000)
    
    @property
    def code_segments(self):
        return self._code_segments
    
    @property
    def data_segments(self):
        return self._data_segments
    

    def load_program(self, program: tuple, name: str = "main_func()"):

        (start_addr, data) = program
        for index, byte in enumerate(data):

            args = (uint8_t(byte), start_addr + index)

            self.ram.write_byte(args)

        self._code_segments.append(Segment(name, start_addr, len(data)))

        self.cpu.ip.uint16 = start_addr.uint16

    def load_data(self, args):

        (start_addr, data, name) = args

        if start_addr.uint16 == 0:
            # User has opted to allow VM to choose memory position.
            # Defaults to immediatley after all code_segments and other data
            length = 0

            for segment in self.code_segments:
                length += segment.length

            for segment in self.data_segments:
                length += segment.length

            start_addr = start_addr + length

            for index, byte in enumerate(data):

                args = (uint8_t(byte), start_addr + index)

                self.ram.write_byte(args)

            self._data_segments.append(Segment(name, start_addr, len(data)))

        else:
            # User wants to place data at a given location, let him.

            for index, byte in enumerate(data):

                args = (uint8_t(byte), start_addr + index)

                self.ram.write_byte(args)

            self._data_segments.append(Segment(name, start_addr, len(data)))


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


            return (word, byte)

        elif isize == 4:
            # Two arguments (2 words)

            word_1 = self.ram.read_word(self.cpu.ip)
            word_2 = self.ram.read_word(self.cpu.ip + 2)

            return (word_1, word_2)

    def run_program(self):

        while not self.should_halt():

            opcode = self.fetch_instruction().uint8
            self.cpu.ip.uint16 += 1

            args = self.decode_instruction(opcode)

            if self.opcodes[opcode]['size'] == 0:

                self.opcodes[opcode]['func']()
                print(f"ip:{hex(self.cpu.ip.uint16)} {self.opcodes[opcode]['name']}()")

            else:
                self.cpu.ip.uint16 += self.opcodes[opcode]['size']
                print(f"ip:{hex(self.cpu.ip.uint16)} {self.opcodes[opcode]['name']}({args})")
                self.opcodes[opcode]['func'](args)

    def should_halt(self):

        return self._should_halt
    
    # Instructions

    def halt(self):
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

        (call_reg) = args

        # First push current IP so that when function returns it knows to where
        reg = (uint8_t(0x0))
        self.cpu.push_reg(reg)

        # Setup new stack frame
        # Push current BP
        reg = (uint8_t(0x2))
        self.cpu.push_reg(reg)

        # Set BP to SP
        self.cpu.bp = self.cpu.sp

        # Finally we set IP to the addr of the function to be called

        self.cpu.ip.uint16 = self.cpu.registers[call_reg.uint8]['value'].uint16
        
    def return_func(self):

        print(f"return_func (IP): {self.cpu.ip}")
        
        self.cpu.pop_reg((uint8_t(0x2)))
        self.cpu.pop_reg((uint8_t(0x0)))
        self.cpu.sp = self.cpu.bp

        print(f"return_func (IP): {self.cpu.registers[0]['value']}")

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
