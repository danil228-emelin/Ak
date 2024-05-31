from enum import Enum
import json


class Opcode(str, Enum):
    READ_MEM_TO_STACK = "read_mem_to_stack"
    READ_IO_TO_STACK = "read_io_to_stack"
    PRINT = "print"
    HALT = "halt"
    WRITE_MEM_FROM_STACK = "write_mem_from_stack"
    WRITE_MEM_FROM_IO = "write_mem_from_IO"
    INC = "increment"
    DEC = "decrement"
    INPUT = "input"
    WRITE_STRING_INTO_MEMORY = "write_string_into_memory"
    SUM = "sum"

    @classmethod
    def is_value_in_Opcode(cls, value):
        try:
            cls(value)
            return True
        except ValueError:
            return False

    def __str__(self):
        return str(self.value)


def read_code(filename):
    with open(filename, encoding="utf-8") as file:
        code = json.loads(file.read())

    return code
