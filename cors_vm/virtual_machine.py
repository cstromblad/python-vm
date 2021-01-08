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

    def __len__(self):
        return len(self._memory)

    def reset(self):
        self._memory = bytearray(self._memory_size)

    @property
    def memory(self):
        return self._memory

    def read_byte(self, addr: uint16_t):

        val = self.memory[addr.uint16]

        return uint8_t(val) 

    def read_word(self, addr: uint16_t):

        src_addr = addr.uint16 & self._memory_size  # Truncate to max_memory

        if src_addr + 1 > self._memory_size:
            raise ValueError('Segmentation fault, reading outside MAX memory_size.')

        val = ((self.memory[src_addr]) << 8) + (self.memory[src_addr + 1])

        return uint16_t(val)

    def write_word(self, args):
        (value, addr) = args

        self.memory[addr.uint16 % self._memory_size] = value.ho_byte
        self.memory[(addr.uint16 + 1) % self._memory_size] = value.lo_byte

    def write_byte(self, args):

        (value, addr) = args

        self.memory[addr.uint16 % self._memory_size] = value.uint8 

class CentralProcessingUnit:

    def __init__(self, ram):
        
        self.ram = ram

        self._reg01 = uint16_t(0)
        self._reg02 = 0
        self._reg03 = 0
        self._reg04 = 0

        self._ip = uint16_t(0x0000)
        self._sp = uint16_t(0x7fff)
        self._bp = uint16_t(0x7fff)

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

        # Write it to the stack
        self.ram.write_word((uint16_t(value), self.sp - 2))

        # Decrement stackpointer to accomodate the new 

        self.sp.uint16 -= 2

    def pop_reg(self, args):

        (reg) = args

        word = self.ram.read_word(self.sp)

        self.registers[reg.uint8]['value'].uint16 = word.uint16

        self.sp.uint16 += 2
        
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
        self.stdout = ""

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
            4: {"name": "m_word",
                "func": self.ram.write_word,
                "size": 4},
            5: {"name": "m_byte",
                "func": self.ram.write_byte,
                "size": 3,
                "reversed": False},
            6: {"name": "push",
                "func": self.cpu.push_reg,
                "size": 1},
            7: {"name": "pop",
                "func": self.cpu.pop_reg,
                "size": 1},
            8: {"name": "mov",
                "func": self.cpu.move_to_reg,
                "size": 3,
                "reversed": True},
            9: {"name": "call",
                "func": self.call_func,
                "size": 1,
                "reversed": False},
            0xa:    {"name": "ret",
                     "func": self.return_func,
                     "size": 0,
                     "reversed": False},

            # input (addr)
            #
            # Reads input 
            # Input function, kind of fake right now, but will copy from a buffer
            # to a location relative the stack pointer.
            # Using this to simulate vulnerable function and buffer overflow
            0xb: {"name": "input",
                  "func": self.fake_input,
                  "size": 1,
                  "reversed": False},
            0x90: {"name": "noop",
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
        
        try:
            opcode = self.ram.read_byte(self.cpu.ip).uint8
            self.opcodes[opcode]
        except KeyError:
            self.stdout += f"Ogiltig instruktion ({hex(opcode)}), avslutar körning.\n"
            self._should_halt = True

        return opcode

    def decode_instruction(self, opcode):

        instruction_pointer = self.cpu.ip + 1

        try:
            isize = self.opcodes[opcode]['size']
        except KeyError:
            self.stdout += "Segmentation fault (core dumped)\n"
            self._should_halt = True
            
            return ()

        if isize == 0:
            # Zero arguments

            return ()

        elif isize == 1:

            byte = self.ram.read_byte(instruction_pointer)

            return tuple([byte])
        
        elif isize == 2:
            # One argument (1 word)

            word = self.ram.read_word(instruction_pointer)

            return tuple([word])

        elif isize == 3:
            # Two arguments (1 byte and 1 word)
            if self.opcodes[opcode]['reversed']:

                word = self.ram.read_word(instruction_pointer)
                byte = self.ram.read_byte(instruction_pointer + 2)

            else:

                byte = self.ram.read_byte(instruction_pointer)
                word = self.ram.read_word(instruction_pointer + 1)

            return (word, byte)

        elif isize == 4:
            # Two arguments (2 words)

            word_1 = self.ram.read_word(instruction_pointer)
            word_2 = self.ram.read_word(instruction_pointer + 2)

            return (word_1, word_2)

    def run_program(self):

        # IP | Instruction | Arguments
        # ----------------------------
        
        self.output += f"{'IP' : <8}|{' Instruction' : <15} | {'Arguments' : >15}\n"
        self.output += f"-------------------------------------------------\n"

        self.started_at = time.time()
        while not self.should_halt():

            opcode = self.fetch_instruction()

            if self.should_halt():
                break

            args = self.decode_instruction(opcode)

            if self.opcodes[opcode]['size'] == 0:
                ip_print = f"{hex(self.cpu.ip.uint16) : <10}"
                op_name = self.opcodes[opcode]['name']

                self.output += f"{ip_print : <8} {op_name : <15}\n"

                self.cpu.ip.uint16 += self.opcodes[opcode]['size'] + 1
                self.opcodes[opcode]['func']()

            else:
                op_size = self.opcodes[opcode]['size']

                ip_print = f"{hex(self.cpu.ip.uint16) : <10}"
                op_name = self.opcodes[opcode]['name']
                args_print = ""
                for arg in args:
                    args_print += f"{arg} "

                self.output += f"{ip_print : <8} {op_name : <15}{args_print : <15}\n"
                self.cpu.ip.uint16 += self.opcodes[opcode]['size'] + 1
                self.opcodes[opcode]['func'](args)

            if self.started_at + MAX_RUN_TIME < time.time():

                self._should_halt = True

            # Increment IP (+1 for instruction opcode, before decode)


    def should_halt(self):

        return self._should_halt
    
    # Instructions

    def halt(self):
        self._should_halt = True

    def out(self, args):
        (addr, ) = args

        i = 0
        while True:

            byte = self.ram.read_byte(addr + i).uint8

            if byte == 0:
                break

            self.stdout += chr(byte)

            i += 1

    def call_func(self, args):

        (call_reg) = args

        call_reg = call_reg[0]
        # First push current IP so that when function returns it knows to where
        reg = (uint8_t(0x0))
        self.cpu.push_reg(reg)

        # Setup new stack frame
        # Push current BP
        reg = (uint8_t(0x2))
        self.cpu.push_reg(reg)

        # Set BP to SP
        self.cpu.bp.uint16 = self.cpu.sp.uint16

        # Finally we set IP to the addr of the function to be called

        self.cpu.ip.uint16 = self.cpu.registers[call_reg.val]['value'].uint16
        
    def return_func(self):

        self.cpu.pop_reg((uint8_t(0x2)))
        self.cpu.pop_reg((uint8_t(0x0)))

        self.cpu.sp.uint16 = self.cpu.bp.uint16
        
    def fake_input(self, args):
        # Used for exploitation_02
        # Data loaded at 0x2000, read from there.
        # And we write to the "stack" at 0x7fff, but we pretend that
        # first the ret value and bp have been pushed and then an allocation of
        # 256 bytes. So final address to start writing from is 0x7efe
        try:
            i = 0
            while True:
                byte = self.ram.read_byte(uint16_t(0x2000 + i)).uint8
                self.ram.write_byte((uint8_t(byte), uint16_t(self.cpu.sp.uint16 - 256 + i)))
                i += 1

                if i == 260:  # Buffer is 256, BP + IP 4, hence 260
                    break

        except Exception as err:
            print(err)

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
