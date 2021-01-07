import virtual_machine as cvm
from base_types import uint16_t, uint8_t

# Anropa metod på minnesadress 0x3737
main_program = b'\x08\x37\x37\x03\x09\x03\x00'

# Skriv ut meddelande och återvänd
print_close = b'\x0B\xFF\x03\x72\x37\x0A'

# Denna funktion ska anropas
secret_func = b'\x03\x73\x37\x0A'

CORS_FLAG = b"CORS_CTF{9fa19b901162d238941a36e2a1a322e6}\x00"
CLSCON_MSG = b"Anslutningen avslutas, ogiltigt certifikat.\x00"

vm = cvm.VirtualMachineV2()

# Software
vm.load_program((uint16_t(0x3737), print_close))
vm.load_program((uint16_t(0x1337), secret_func), "secret_func")
vm.load_program((uint16_t(0x1000), main_program))

# Data 
vm.load_data((uint16_t(0x7337), CORS_FLAG, "cors_flag"))
vm.load_data((uint16_t(0x7237), CLSCON_MSG, "con_close"))

code = b"\x08\x13\x37\x03\x09\x03\x00"

buf = b'\x90' * (256 - len(code))

buf += code + b'\x7f\x00\x7f\x00'

vm.load_data((uint16_t(0x2000), buf, "user_func"))

vm.run_program()


print(vm.stdout)