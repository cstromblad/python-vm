import pytest

import cors_vm.virtual_machine as cvm

from cors_vm.base_types import uint16_t, uint8_t

@pytest.fixture
def default_program():
    return b'\x08\x00\x41\x03\x00'

def test_mov_value_to_register():

    vm = cvm.VirtualMachineV2()

    # Move 'A' to Register 01
    args = (uint16_t(0x0041), uint8_t(0x3))
    vm.cpu.move_to_reg(args)

    assert vm.cpu.reg01.uint16 == 65

def test_push_register_to_stack():
    """ Assumes stack is located at 0x7fff """
    vm = cvm.VirtualMachineV2()

    args = (uint16_t(0x41), uint8_t(0x3))
    vm.cpu.move_to_reg(args)

    register = (uint8_t(0x3))
    vm.cpu.push_reg(register)

    assert vm.cpu.sp.uint16 == 0x7ffd

    assert 0x41 == vm.ram.read_word(vm.cpu.sp).uint16

def test_push_and_pop_to_stack():

    vm = cvm.VirtualMachineV2()

    args = (uint16_t(0x41), uint8_t(0x3))
    vm.cpu.move_to_reg(args)

    register = (uint8_t(0x3))
    vm.cpu.push_reg(register)
    
    register = (uint8_t(0x2))
    vm.cpu.pop_reg(register)

    assert 0x41 == vm.cpu.bp.uint16

def test_multiple_push_and_pops_to_stack():

    vm = cvm.VirtualMachineV2()

    args = (uint16_t(0x41), uint8_t(0x3))
    vm.cpu.move_to_reg(args)

    register = (uint8_t(0x3))
    vm.cpu.push_reg(register)

    args = (uint16_t(0x42), uint8_t(0x3))
    vm.cpu.move_to_reg(args)
    
    register = (uint8_t(0x3))
    vm.cpu.push_reg(register)
    
    register = (uint8_t(0x2))
    vm.cpu.pop_reg(register)
    
    register = (uint8_t(0x0))
    vm.cpu.pop_reg(register)

    assert 0x41 == vm.cpu.ip.uint16
    assert 0x42 == vm.cpu.bp.uint16
    