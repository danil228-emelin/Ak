import sys

import Opcode
import Opcode as Op
from enum import Enum
import argparse
import os
import re
import ALU


class Signals(str, Enum):
    INC = "inc"
    DEC = "dec"
    INPUT = "input"
    write_data_to_mem_from_command = "write_data_to_mem_from_command"
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
        assert len(code_data) <= memory_size / 2, "Commands  size must be less or equal memory_size"

        self.memory_size = memory_size

        self.io_port_write = 1

        self.command_register = 2

        self._memory_delimiter = memory_size / 2

        self.data_register: int = memory_size - 1

        self.memory = [""] * memory_size

        self._counter = 0

        self.data_counter = 0

        self.stack_top_register = -1

        self.stack: list = []
        self.input_buffer = []
        for i in range(len(input_buffer)):
            if input_buffer[i].isdigit():
                self.memory[self.data_register] = input_buffer[i]
                self.data_register -= 1
            else:
                self.input_buffer.append(input_buffer[i])

        self.data_register = memory_size - 1

        self.output_buffer = []

        self.stack_size = stack_size

        for el in code_data:
            self.memory[self.command_register + self._counter] = el
            self._counter += 1

    def restore_memory_register(self):
        self.data_register = self.memory_size - 1

    def __str__(self):
        return f"Memory size:{self.memory_size}\nIo_port_read:{self.io_port_write}\nIo port write:{self.io_port_write}\nData register:{self.data_register}\nMemory:{[el for el in self.memory if el != '']}\nCommand register:{self.command_register}\nStack size:{self.stack_size}\nInput buffer:{self.input_buffer}\nOutput buffer:{self.output_buffer}"

    def signal_latch_data_register(self, sel):
        assert sel in {Signals.INC.value, Signals.DEC.value}, "internal error, incorrect selector: {}".format(sel)
        self.data_register = self.data_register - 1 if sel == Signals.DEC else self.data_register + 1

        assert self._memory_delimiter <= self.data_register < self.memory_size, f"out of memory: \nMemory  size:{self.memory_size}\nMemory delimeter:{self._memory_delimiter}\nData register:{self.data_register}"

    def signal_latch_command_register(self, sel):
        assert sel in {Signals.INC.value, Signals.DEC.value}, "internal error, incorrect selector: {}".format(sel)

        self.command_register = self.command_register - 1 if sel == Op.Opcode.DEC.value else self.command_register + 1

        assert 2 <= self.command_register < self._memory_delimiter, "out of memory: {}".format(
            self.command_register)

    # read_data
    def signal_latch_push_data(self, sel):
        self.stack_top_register += 1
        assert 0 <= self.stack_top_register < self.stack_size, "out of memory: {}".format(
            self.stack_top_register)

        assert sel in {Signals.read_data_from_IO_port_to_stack.value,
                       Signals.read_data_from_mem_to_stack.value}, "internal error, incorrect selector: {}".format(
            sel)

        if sel == Signals.read_data_from_mem_to_stack:
            self.stack.append(self.memory[self.data_register])

        if sel == Signals.read_data_from_IO_port_to_stack:
            self.stack.append(self.memory[self.io_port_write])

        self.stack_top_register = len(self.stack) - 1

    def signal_latch_pop(self) -> int:
        assert 0 <= self.stack_top_register < self.stack_size, "out of memory: {}".format(
            self.stack_top_register)
        element = self.stack.pop(self.stack_top_register)
        self.stack_top_register -= 1
        return element

    def signal_write(self, sel, data=""):
        assert 0 <= self.data_register < self.memory_size, "out of memory: {}".format(
            self.data_register)

        assert sel in {Signals.write_data_to_mem_from_stack.value,
                       Signals.write_data_to_IO_port_from_buffer.value,
                       Signals.write_data_to_mem_from_command}, "internal error, incorrect selector: {}".format(
            sel)
        if sel == Signals.write_data_to_mem_from_command:
            self.memory[self.data_register] = data
        if sel == Signals.write_data_to_mem_from_stack:
            self.memory.append(self.signal_latch_pop)

        if sel == Signals.write_data_to_IO_port_from_buffer:
            if len(self.input_buffer) <= 0:
                print(f"\nInput buffer is empty.\nOutput:{self.output_buffer}\n{self.stack}")
                sys.exit(0)
            symbol = self.input_buffer.pop(0)
            if symbol=="0":
                print("END OF LINE DETECTED.")
                return
            self.memory[self.io_port_write] = symbol


class ControlUnit:

    def __init__(self, data_path):
        self.data_path = data_path
        self.tick = 0
        self.basic_operations_handlers = {
            "write_mem_from_IO": lambda: self.data_path.signal_write(Signals.write_data_to_IO_port_from_buffer),
            "read_io_to_stack": lambda: self.data_path.signal_latch_push_data(Signals.read_data_from_IO_port_to_stack),
            "print":self.print_handler,
            "halt": self.stop,
            "write_string_into_memory": self.write_string_into_memory_handler,
            "read_mem_to_stack": self.read_mem_to_stack_handler,
            "sum": self.sum_handler,
            "restore": self.data_path.restore_memory_register,
            "dec": self.dec_handler,
            "sum_all": self.sum_all_handler,
            "inc": self.inc_handler
        }
        self.stop_machine = False
        self.current_command = ""

    def print_handler(self):
        res = self.data_path.signal_latch_pop()
        self.data_path.output_buffer.append(res)

    def inc_handler(self):
        self.data_path.signal_latch_data_register(Signals.INC)

    def sum_all_handler(self):
        counter = 0
        while len(self.data_path.stack) > 0:
            first_value: int = int(self.data_path.stack.pop())
            counter = ALU.ALU.sum(counter, first_value)
        self.data_path.stack_top_register = len(self.data_path.stack)
        self.data_path.stack.append(counter)

    def dec_handler(self):
        self.data_path.signal_latch_data_register(Signals.DEC)

    def sum_handler(self):

        self.data_path.signal_latch_push_data(Signals.read_data_from_mem_to_stack)
        self.data_path.signal_latch_data_register(Signals.DEC)
        self.data_path.signal_latch_push_data(Signals.read_data_from_mem_to_stack)
        self.data_path.signal_latch_data_register(Signals.DEC)

        first_arg: int = self.data_path.signal_latch_pop()
        second_arg: int = self.data_path.signal_latch_pop()

        first_arg = int(first_arg)
        second_arg = int(second_arg)

        result = ALU.ALU.sum(first_arg, second_arg)

        self.data_path.signal_write(Signals.write_data_to_mem_from_command, data=result)
        self.data_path.signal_latch_data_register(Signals.INC)

    def read_mem_to_stack_handler(self):
        self.data_path.signal_latch_push_data(Signals.read_data_from_mem_to_stack)
        self.data_path.signal_latch_data_register(Signals.INC)

    def write_string_into_memory_handler(self):
        instr = self.data_path.memory[self.data_path.command_register]
        symbol_code = instr["argument"]

        self.data_path.signal_write(Signals.write_data_to_mem_from_command, data=symbol_code)
        self.data_path.signal_latch_data_register(Signals.DEC)

    def stop(self):
        self.stop_machine = True

    def inc_tick(self):
        self.tick += 1

    def get_tick(self):
        return self.tick

    def signal_latch_program_counter(self, sel_next):

        if sel_next:
            self.data_path.command_register += 1
        else:
            instr = self.data_path.memory[self.data_path.command_register]

            self.program_counter = instr["arg"]

    # Счет тактов
    def decode_and_execute_instruction(self):

        instr = self.data_path.memory[self.data_path.command_register]

        print(f"Current procedure : {instr['procedure_name']}")

        print(f"Operations :    {instr['basic_operations']}")

        print(f"Line in code :  {instr['line_in_dereference_code']}")

        if instr['procedure_name'] == "LOOP":
            print(f"iterations:{instr['iterations']}")
            [[self.basic_operations_handlers[basic_operation]() for basic_operation in instr["basic_operations"]]
             for p in [i for i in range(int(instr['iterations']))]]
        elif instr['procedure_name'] == "WHILE":
            condition = instr['condition']
            if "$data_register" in condition:
                condition = condition.replace("$data_register", f"{self.data_path.data_register}")
            if "$*data_register" in condition:
                condition = condition.replace("$*data_register",
                                              f"{self.data_path.memory[self.data_path.data_register]}")

            while eval(condition):
                if isinstance(instr["basic_operations"], dict):
                    if_condition = instr["basic_operations"]["CONDITION"]
                    if_body = instr["basic_operations"]["IF_BODY"]
                    else_body = instr["basic_operations"]["ELSE_BODY"]
                    if "$data_register" in if_condition:
                        if_condition = if_condition.replace("$data_register", f"{self.data_path.data_register}")
                    if "$*data_register" in if_condition:
                        if_condition = if_condition.replace("$*data_register",
                                                            f"{self.data_path.memory[self.data_path.data_register]}")

                    if eval(if_condition):
                        self.basic_operations_handlers[if_body]()
                    else:
                        self.basic_operations_handlers[else_body]()
                else:
                    for basic_operation in instr["basic_operations"]:
                        print(f"Invoke {basic_operation}")
                        self.basic_operations_handlers[basic_operation]()
                if "$data_register" in instr['condition']:
                    condition = instr['condition']
                    condition = condition.replace("$data_register", f"{self.data_path.data_register}")
                if "$*data_register" in instr['condition']:
                    condition = instr['condition']
                    condition = condition.replace("$*data_register",
                                                  f"{self.data_path.memory[self.data_path.data_register]}")
        else:
            for basic_operation in instr["basic_operations"]:
                print(f"Invoke {basic_operation}")
                self.basic_operations_handlers[basic_operation]()

        self.data_path.signal_latch_command_register(Signals.INC)


def simulation(data, input_buffer, memory_size, stack_size, limit):
    data_path = DataPath(data, memory_size, input_buffer, stack_size)
    control_unit = ControlUnit(data_path)
    instr_counter = 0
    while instr_counter < limit and data_path.memory[
        data_path.command_register] != "" and not control_unit.stop_machine:
        control_unit.decode_and_execute_instruction()
        instr_counter += 1
    if instr_counter > limit:
        print("LIMIT is reached")
    elif data_path.memory[data_path.command_register] == "":
        print("DATA IN MEMORY_COMMAND IS NULL")
    else:
        print("HALT invoked")
    return control_unit.data_path.output_buffer, instr_counter, control_unit.get_tick(), control_unit


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
    output, instr_counter, ticks, control_un = simulation(
        data=code,
        input_buffer=input_buffer,
        memory_size=512,
        stack_size=64,
        limit=128, )

    print(f"output:{output}")

    print(f"Instructions:{instr_counter}")
    print(f"ticks:{ticks}")


if __name__ == "__main__":
    main()
