import sys

import Opcode as Op
from enum import Enum
import argparse
import os


class Signals(str, Enum):
    INC = "increment"
    DEC = "decrement"
    INPUT = "input"
    write_data_to_mem_from_stack = "write_data_to_mem_from_stack"
    write_data_to_IO_port_from_buffer = "write_data_to_IO_port_from_buffer"
    read_data_from_mem_to_stack = "read_data_from_mem_to_stack"
    read_data_from_IO_port_to_stack = "read_data_from_IO_port_to_stack"
    read_data_to_io = "read_data_to_io"
    read_stack = "read_stack"


class DataPath:

    def __init__(self, code_data, memory_size, input_buffer, stack_size):
        assert memory_size > 100 and memory_size % 2 == 0, "Memory size should be non-zero and even"
        assert stack_size > 0 and stack_size % 2 == 0, "Stack size should be non-zero and even"
        assert len(code_data) <= memory_size / 2, "Data size must be less or equal memory_size"

        self.memory_size = memory_size

        self.io_port_read = 0

        self.io_port_write = 1

        self.command_register = 2

        self._memory_delimiter = memory_size / 2

        self.data_register = memory_size - 1

        self.memory = [""] * memory_size

        self._counter = 0

        self.stack_top_register = -1

        self.stack: list = []

        self.input_buffer = input_buffer.copy()

        self.output_buffer = []

        self.stack_size = stack_size

        for el in code_data:
            if el["procedure_name"] == "LOOP":
                for _ in range(int(el["iterations"])):
                    for basic_operation in el["basic_operations"]:
                        self.memory[self.command_register + self._counter] = basic_operation
                        self._counter += 1
            else:
                for basic_operation in el["basic_operations"]:
                    self.memory[self.command_register + self._counter] = basic_operation
                    self._counter += 1

    def __str__(self):
        return f"Memory size:{self.memory_size}\nIo_port_read:{self.io_port_read}\nIo port write:{self.io_port_write}\nData register:{self.data_register}\nMemory:{self.memory}\nCommand register:{self.command_register}\nStack size:{self.stack_size}\nInput buffer:{self.input_buffer}"

    def signal_latch_data_register(self, sel):
        assert sel in {Signals.INC.value, Signals.DEC.value}, "internal error, incorrect selector: {}".format(sel)

        self.data_register = self.data_register - 1 if sel == Op.Opcode.DEC.value else self.data_register + 1

        assert self._memory_delimiter <= self.data_register < self.memory_size, "out of memory: {}".format(
            self.data_register)

    def signal_latch_command_register(self, sel):
        assert sel in {Signals.INC.value, Signals.DEC.value}, "internal error, incorrect selector: {}".format(sel)

        self.command_register = self.command_register - 1 if sel == Op.Opcode.DEC.value else self.command_register + 1

        assert 2 <= self.command_register < self._memory_delimiter, "out of memory: {}".format(
            self.command_register)

    # read_data
    def signal_latch_push_data(self, sel):
        self.stack_top_register += 1
        assert 0 <= self.stack_top_register < self.stack_size, "out of memory: {}".format(
            self.data_register)

        assert sel in {Signals.read_data_from_IO_port_to_stack.value,
                       Signals.read_data_from_mem_to_stack.value}, "internal error, incorrect selector: {}".format(
            sel)

        if sel == Signals.read_data_from_mem_to_stack:
            self.stack.append(self.memory[self.data_register])

        if sel == Signals.read_data_from_IO_port_to_stack:
            self.stack.append(self.memory[self.io_port_read])

        self.stack_top_register = len(self.stack) - 1

    def signal_latch_pop(self):
        assert 0 <= self.stack_top_register < self.stack_size, "out of memory: {}".format(
            self.stack_top_register)
        element = self.stack.pop(self.stack_top_register)
        self.stack_top_register -= 1
        return element

    def signal_write(self, sel):
        assert 0 <= self.data_register < self.memory_size, "out of memory: {}".format(
            self.data_register)

        assert sel in {Signals.write_data_to_mem_from_stack.value,
                       Signals.write_data_to_IO_port_from_buffer.value}, "internal error, incorrect selector: {}".format(
            sel)

        if sel == Signals.write_data_to_mem_from_stack:
            self.memory.append(self.signal_latch_pop)

        if sel == Signals.write_data_to_IO_port_from_buffer:
            assert len(self.input_buffer) > 0, f"Input buffer is empty.\nSize:{self}"
            symbol = self.input_buffer.pop(0)
            symbol_code = ord(symbol)
            assert -128 <= symbol_code <= 127, "input symbol_code is out of bound: {}".format(symbol_code)
            self.memory[self.io_port_write] = self.memory[self.io_port_read] = symbol_code


class ControlUnit:
    def __init__(self, data_path):
        self.data_path = data_path
        self.tick = 0

    def inc_tick(self):
        self.tick += 1

    def get_tick(self):
        return self.tick

    def signal_latch_program_counter(self, sel_next):

        if sel_next:
            self.program_counter += 1
        else:
            instr = self.data_path.memory[self.program_counter]

            self.program_counter = instr["arg"]

    def decode_and_execute_control_flow_instruction(self, opcode):
        if opcode is Op.Opcode.HALT.value:
            raise StopIteration()

    # Счет тактов
    def decode_and_execute_instruction(self):

        instr = self.data_path.memory[self.data_path.command_register]

        print(f"CURRENT INSTRICTION:{instr}")

        self.data_path.signal_latch_command_register(Signals.INC)

        if self.decode_and_execute_control_flow_instruction(instr):
            return

        if instr == "write_mem_from_IO":
            self.data_path.signal_write(Signals.write_data_to_IO_port_from_buffer)

        elif instr == "read_io_to_stack":
            self.data_path.signal_latch_push_data(Signals.read_data_from_IO_port_to_stack)
        elif instr == "print":
            symbol = self.data_path.signal_latch_pop()
            self.data_path.output_buffer.append(chr(symbol))


def simulation(data, input_buffer, memory_size, stack_size, limit):
    data_path = DataPath(data, memory_size, input_buffer, stack_size)
    control_unit = ControlUnit(data_path)
    instr_counter = 0
    while instr_counter < limit and data_path.memory[data_path.command_register] != "":
        control_unit.decode_and_execute_instruction()
        instr_counter += 1

    return control_unit.data_path.output_buffer, instr_counter, control_unit.get_tick()


def file_checker(path):
    if not os.path.isfile(path) or not os.access(path, os.R_OK):
        raise argparse.ArgumentError(f"{path} isn't valid file")
    return path


class Parser:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Virtual machine simulation")
        self.parser.add_argument("-input_code",
                                 dest="input_code",
                                 help="Example: -input './output_machine_code'-this file is consisted of machine code,generated by translator",
                                 type=file_checker,
                                 required=True)
        self.parser.add_argument("-input_data",
                                 dest="input_data",
                                 required=True,
                                 help="Example: -input_data './input'-this file is consisted of input for virtual_machine.",
                                 )


def main():
    obj = Parser()
    command_line_arguments = obj.parser.parse_args()
    code = Op.read_code(command_line_arguments.input_code)
    input_buffer = []
    with open(command_line_arguments.input_data, encoding="utf-8") as file:
        input_text = file.read()
        for char in input_text:
            input_buffer.append(char)

    output, instr_counter, ticks = simulation(
        data=code,
        input_buffer=input_buffer,
        memory_size=256,
        stack_size=64,
        limit=128, )

    print(f"output:{output}")
    print(f"Instructions:{instr_counter}")
    print(f"ticks:{ticks}")


if __name__ == "__main__":
    main()
