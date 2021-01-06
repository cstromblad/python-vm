import virtual_machine as cvm
from base_types import uint16_t, uint8_t

call_program = b'\x08\x37\x37\x03\x09\x03\x08\x00\x41\x03\x00'
subroutine = b'\x03\x13\x37\x0A'

vm = cvm.VirtualMachineV2()

CORS_FLAG = b"CORS_CTF{03783743}\x00"
vm.load_data((uint16_t(0x1337), CORS_FLAG, "cors_flag"))
vm.load_program((uint16_t(0x3737), subroutine), "secret_func")

program = (uint16_t(0x0000), call_program)
vm.load_program(program)

vm.run_program()

print(vm.stdout)