import pytest

import cors_vm.virtual_machine as cvm

from cors_vm.base_types import uint16_t, uint8_t

@pytest.fixture
def default_program():
    return b'\x08\x00\x41\x03\x00'

@pytest.fixture
def call_program():
    # Call function at address placed in Reg01
    return b'\x08\x37\x37\x03\x09\x03\x08\x00\x41\x03\x00'

@pytest.fixture
def subroutine():

    return b'\x03\x13\x37\x0A'

def test_cpu_halt_instruction_halts_program():

    vm = cvm.VirtualMachineV2()

    vm.halt()

    assert vm._should_halt == True

def test_virtual_machine_can_start_without_program():

    vm = cvm.VirtualMachineV2()

    assert vm.ram.read_byte(uint16_t(0x0000)).uint8 == 0

def test_virtual_machine_can_load_program_at_0x0000(default_program):

    vm = cvm.VirtualMachineV2()

    # Load program at 0x0000
    # Push 'A' to Reg01
    # Halt

    program = (uint16_t(0x0000), default_program)
    vm.load_program(program)

    vm.run_program()

    assert vm.cpu.reg01.uint16 == 65

def test_virtual_machine_provides_code_segment_length_value(default_program):

    vm = cvm.VirtualMachineV2()

    program = (uint16_t(0x0000), default_program)

    vm.load_program(program)

    assert vm.code_segments[0].length == 5

def test_virtual_machine_can_load_program_at_0x1000(default_program):

    vm = cvm.VirtualMachineV2()

    # Load program at 0x0000
    # Push 'A' to Reg01
    # Halt

    program = (uint16_t(0x1000), default_program)
    vm.load_program(program)

    vm.run_program()

    assert vm.cpu.reg01.uint16 == 65

def test_virtual_machine_can_load_data_at_boot():

    vm = cvm.VirtualMachineV2()

    STATIC_STRING = b"This is a static string."
    vm.load_data((uint16_t(0x0000), STATIC_STRING, "static_string"))

    length = 0
    for segment in vm.code_segments:
        length += segment.length

    assert STATIC_STRING in vm.ram.memory[length:length+len(STATIC_STRING)]

    data_strings = [segment.name for segment in vm.data_segments]

    assert "static_string" in data_strings

def test_virtual_machine_can_load_multiple_data_sets_into_memory():

    vm = cvm.VirtualMachineV2()

    STATIC_STRING = b"This is a static string.\x00"
    SECOND_STRING = b"Second string this is second static sbbbb.\x00"
    vm.load_data((uint16_t(0x0000), STATIC_STRING, "static_string"))
    vm.load_data((uint16_t(0x0000), SECOND_STRING, "second_string"))

    for segment in vm.data_segments:
        if segment.name == "second_string":
            addr = segment.start_addr
    
    assert SECOND_STRING in vm.ram.memory[addr.uint16:addr.uint16+len(SECOND_STRING)]

    data_strings = [segment.name for segment in vm.data_segments]

    assert "second_string" in data_strings


def test_virtual_machine_can_run_subroutine_from_main_program(call_program, subroutine):

    vm = cvm.VirtualMachineV2()

    CORS_FLAG = b"CORS_CTF{03783743}\x00"
    vm.load_data((uint16_t(0x1337), CORS_FLAG, "cors_flag"))
    vm.load_program((uint16_t(0x3737), subroutine), "secret_func")

    program = (uint16_t(0x0000), call_program)
    vm.load_program(program)
    
    vm.run_program()
        
    assert "CORS_CTF" in vm.output
    print(vm.cpu.ip)
    print(vm.ram.read_byte(vm.cpu.ip - 2))
    assert 0x41 == vm.cpu.reg01.uint16