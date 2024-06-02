import sys
import Opcode as Op
from enum import Enum
import argparse
import os
import ALU
import logging

root = logging.getLogger(__name__)
root.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter(' %(levelname)s:%(name)s:%(asctime)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)


class Signals(str, Enum):
    INC = "inc"
    DEC = "dec"
    INPUT = "input"
    write_data_to_mem_from_argument = "write_data_to_mem_from_argument"
    write_data_to_mem_from_stack = "write_data_to_mem_from_stack"
    write_data_to_IO_port_from_buffer = "write_data_to_IO_port_from_buffer"
    read_data_from_mem_to_stack = "read_data_from_mem_to_stack"
    read_data_from_IO_port_to_stack = "read_data_from_IO_port_to_stack"
    read_data_to_io = "read_data_to_io"
    read_stack = "read_stack"


class DataPath:
    def __init__(self, code_data, memory_size, input_buffer, stack_size):
        root.info("Start initializing DataPath object.")
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
        root.info("Process input buffer.")

        for i in range(len(input_buffer)):
            if input_buffer[i].isdigit():
                root.info(f"{input_buffer[i]} is digit.It goes to memory.")
                self.memory[self.data_register] = input_buffer[i]
                self.data_register -= 1
            else:
                root.info(f"{input_buffer[i]} is not a digit.It goes to input_buffer.")
                self.input_buffer.append(input_buffer[i])

        self.data_register = memory_size - 1

        self.output_buffer = []

        self.stack_size = stack_size

        for el in code_data:
            root.info(f"{el} command goes to memory.")
            self.memory[self.command_register + self._counter] = el
            self._counter += 1

    def restore_memory_register(self):
        root.info(f"Restore memory register to {self.memory_size - 1}")
        self.data_register = self.memory_size - 1

    def __str__(self):
        return f"Memory size:{self.memory_size}\nIo_port_read:{self.io_port_write}\nIo port write:{self.io_port_write}\nData register:{self.data_register}\nMemory:{[el for el in self.memory if el != '']}\nCommand register:{self.command_register}\nStack size:{self.stack_size}\nInput buffer:{self.input_buffer}\nOutput buffer:{self.output_buffer}"

    def signal_latch_data_register(self, sel):
        root.info("signal_latch_data_register")
        root.info(f"Value of data_register {self.data_register}")

        assert sel in {Signals.INC.value, Signals.DEC.value}, "internal error, incorrect selector: {}".format(sel)
        self.data_register = self.data_register - 1 if sel == Signals.DEC else self.data_register + 1
        root.info(f"Value of data_register {self.data_register}")

        assert self._memory_delimiter <= self.data_register < self.memory_size, f"out of memory: \nMemory  size:{self.memory_size}\nMemory delimeter:{self._memory_delimiter}\nData register:{self.data_register}"

    def signal_latch_command_register(self, sel):
        assert sel in {Signals.INC.value, Signals.DEC.value}, "internal error, incorrect selector: {}".format(sel)

        self.command_register = self.command_register - 1 if sel == Op.Opcode.DEC.value else self.command_register + 1

        assert 2 <= self.command_register < self._memory_delimiter, "out of memory: {}".format(
            self.command_register)

    # read_data
    def signal_latch_push_data(self, sel):
        root.info(f"signal_latch_push_data started with selector {sel}")
        self.stack_top_register += 1
        root.info(f"Value of stack_top_register {self.stack_top_register}")
        assert 0 <= self.stack_top_register < self.stack_size, "out of memory: {}".format(
            self.stack_top_register)

        assert sel in {Signals.read_data_from_IO_port_to_stack.value,
                       Signals.read_data_from_mem_to_stack.value}, "internal error, incorrect selector: {}".format(
            sel)

        if sel == Signals.read_data_from_mem_to_stack:
            root.info(f"Read data from memory to stack.")
            result = self.memory[self.data_register]
            root.info(f"Value {result} from memory. Address {self.data_register}.")
            self.stack.append(result)

        if sel == Signals.read_data_from_IO_port_to_stack:
            root.info(f"Read data from IO port to stack.")
            result = self.memory[self.io_port_write]
            root.info(f"Data from port {result}.")
            self.stack.append(result)

        self.stack_top_register = len(self.stack) - 1

    def signal_latch_pop(self) -> int:
        root.info("signal_latch_pop started")
        root.info(f"Value of stack_top_register {self.stack_top_register}")
        assert 0 <= self.stack_top_register < self.stack_size, "out of memory: {}".format(
            self.stack_top_register)
        element = self.stack.pop(self.stack_top_register)
        root.info(f"Element from stack {element}.")
        self.stack_top_register -= 1
        return element

    def signal_write(self, sel, data=""):
        root.info(f"signal_write operation started.With selector {sel}.With data {data}")
        assert 0 <= self.data_register < self.memory_size, "out of memory: {}".format(
            self.data_register)

        assert sel in {Signals.write_data_to_mem_from_stack.value,
                       Signals.write_data_to_IO_port_from_buffer.value,
                       Signals.write_data_to_mem_from_argument}, "internal error, incorrect selector: {}".format(
            sel)
        if sel == Signals.write_data_to_mem_from_argument:
            root.info(f"Write {data} to address {self.data_register}.")
            self.memory[self.data_register] = data
        if sel == Signals.write_data_to_mem_from_stack:
            result = self.signal_latch_pop
            root.info(f"Write {result} from stack to memory.")
            self.memory.append(result)

        if sel == Signals.write_data_to_IO_port_from_buffer:
            root.info("Try write data from inner buffer to IO port.")
            if len(self.input_buffer) <= 0:
                root.info("Input buffer is empty")
                root.info(f"output:{self.output_buffer}")
                sys.exit(0)
            symbol = self.input_buffer.pop(0)
            if symbol == "0":
                root.info("END OF LINE DETECTED.")
                return
            root.info(f"COPY {symbol} in port")
            self.memory[self.io_port_write] = symbol


class ControlUnit:

    def __init__(self, data_path):
        root.info("Initialize ControlUnit class.")
        self.data_path = data_path
        self.tick = 0
        self.basic_operations_handlers = {
            "write_mem_from_IO": self.write_mem_from_IO_handler,
            "read_io_to_stack": self.read_io_to_stack_handler,
            "print": self.print_handler,
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
    def read_io_to_stack_handler(self):
        root.info("read_io_to_stack_handler Started.")
        self.data_path.signal_latch_push_data(Signals.read_data_from_IO_port_to_stack)
    def write_mem_from_IO_handler(self):
        root.info("write_mem_from_IO_handler Started.")
        self.data_path.signal_write(Signals.write_data_to_IO_port_from_buffer)

    def print_handler(self):
        root.info("print_handler started.")
        res = self.data_path.signal_latch_pop()
        self.data_path.output_buffer.append(res)

    def inc_handler(self):
        root.info("inc_handler started.")
        self.data_path.signal_latch_data_register(Signals.INC)

    def sum_all_handler(self):
        root.info("sum_all_handler started.")
        counter = 0
        while len(self.data_path.stack) > 0:
            first_value: int = int(self.data_path.stack.pop())
            counter = ALU.ALU.sum(counter, first_value)
        self.data_path.stack_top_register = len(self.data_path.stack)
        self.data_path.stack.append(counter)

    def dec_handler(self):
        root.info("dec_handler started.")
        self.data_path.signal_latch_data_register(Signals.DEC)

    def sum_handler(self):
        root.info("sum_handler Started.")
        self.data_path.signal_latch_push_data(Signals.read_data_from_mem_to_stack)
        self.data_path.signal_latch_data_register(Signals.DEC)
        self.data_path.signal_latch_push_data(Signals.read_data_from_mem_to_stack)
        self.data_path.signal_latch_data_register(Signals.DEC)

        first_arg: int = self.data_path.signal_latch_pop()
        second_arg: int = self.data_path.signal_latch_pop()

        first_arg = int(first_arg)
        second_arg = int(second_arg)

        result = ALU.ALU.sum(first_arg, second_arg)

        self.data_path.signal_write(Signals.write_data_to_mem_from_argument, data=result)
        self.data_path.signal_latch_data_register(Signals.INC)

    def read_mem_to_stack_handler(self):
        root.info("read_mem_to_stack_handler started.")
        self.data_path.signal_latch_push_data(Signals.read_data_from_mem_to_stack)
        self.data_path.signal_latch_data_register(Signals.INC)

    def write_string_into_memory_handler(self):
        root.info("write_string_into_memory_handler started")
        instr = self.data_path.memory[self.data_path.command_register]
        symbol_code = instr["argument"]
        self.data_path.signal_write(Signals.write_data_to_mem_from_argument, data=symbol_code)
        self.data_path.signal_latch_data_register(Signals.DEC)

    def stop(self):
        root.info("Halt operation started.")
        self.stop_machine = True

    def inc_tick(self):
        root.info("Inc tick")
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

        root.info(f"Current Procedure : {instr['procedure_name']}")

        root.info(f"Operations :    {instr['basic_operations']}")

        root.info(f"Line in code :  {instr['line_in_dereference_code']}")

        if instr['procedure_name'] == "LOOP":
            root.info(f"iterations: {instr['iterations']}")
            [[self.basic_operations_handlers[basic_operation]() for basic_operation in instr["basic_operations"]]
             for p in [i for i in range(int(instr['iterations']))]]
        elif instr['procedure_name'] == "WHILE":
            condition = instr['condition']
            root.info(f"Condition for WHILE {condition}")

            if "$data_register" in condition:
                root.info(f"Detected $data_register in condition.Replace with data_register value.")
                condition = condition.replace("$data_register", f"{self.data_path.data_register}")
            if "$*data_register" in condition:
                root.info(
                    f"Detected $*data_register in condition.Replace with value from memory addressed via data_register")

                condition = condition.replace("$*data_register",
                                              f"{self.data_path.memory[self.data_path.data_register]}")

            while eval(condition):
                if isinstance(instr["basic_operations"], dict):
                    root.info("FOUND IF ELSE OPERATIONS.")
                    if_condition = instr["basic_operations"]["CONDITION"]
                    if_body = instr["basic_operations"]["IF_BODY"]
                    else_body = instr["basic_operations"]["ELSE_BODY"]
                    root.info(f"if_condition:{if_condition}")
                    root.info(f"if_body:{if_body}")
                    root.info(f"else_body:{else_body}")
                    if "$data_register" in if_condition:
                        root.info(f"Detected $data_register in if_condition.Replace with data_register value.")

                        if_condition = if_condition.replace("$data_register", f"{self.data_path.data_register}")
                    if "$*data_register" in if_condition:
                        root.info(f"Detected $data_register in if_condition.Replace with value from memory addressed via data_register.")

                        if_condition = if_condition.replace("$*data_register",
                                                            f"{self.data_path.memory[self.data_path.data_register]}")

                    if eval(if_condition):
                        root.info(f"{if_condition} is TRUE.Invoke {if_body}")
                        self.basic_operations_handlers[if_body]()
                    else:
                        root.info(f"{if_condition} is False.Invoke {else_body}")
                        self.basic_operations_handlers[else_body]()
                else:
                    root.info("IF ELSE NOT FOUND.")
                    for basic_operation in instr["basic_operations"]:
                        root.info(f"Invoke {basic_operation}")
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
                root.info(f"Invoke {basic_operation}")
                self.basic_operations_handlers[basic_operation]()

        self.data_path.signal_latch_command_register(Signals.INC)


def simulation(data, input_buffer, memory_size, stack_size, limit):
    root.info(f"Memory size - {memory_size}.")
    root.info(f"Stack size - {stack_size}.")
    root.info(f"limit for commands - {memory_size}.")
    data_path = DataPath(data, memory_size, input_buffer, stack_size)

    control_unit = ControlUnit(data_path)
    instr_counter = 0
    root.info("Start processing commands.")
    while instr_counter < limit and data_path.memory[
        data_path.command_register] != "" and not control_unit.stop_machine:
        control_unit.decode_and_execute_instruction()
        instr_counter += 1
    if instr_counter > limit:
        root.info("Limit of commands  is reached.Exit")
    elif data_path.memory[data_path.command_register] == "":
        root.info("Nothing to do.Current command is null.Exit.")
    else:
        root.info("HALT invoked.Exit")
    return control_unit.data_path.output_buffer, instr_counter, control_unit.get_tick(), control_unit


def file_checker(path):
    if not os.path.isfile(path) or not os.access(path, os.R_OK):
        raise argparse.ArgumentError(f"{path} isn't valid file")
    return path


class Parser:
    def __init__(self):
        root.info("Initialize Parser object.Invoke module with -h key for more information.")
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
    root.info("Parse command line arguments.")
    root.info(f"Input machine code in File - {command_line_arguments.input_code}")
    root.info(f"Input data in File - {command_line_arguments.input_data}")

    code = Op.read_code(command_line_arguments.input_code)
    input_buffer = []
    with open(command_line_arguments.input_data, encoding="utf-8") as file:
        input_text = file.read()
        for char in input_text:
            input_buffer.append(char)
    root.info(f"Parse input data into list of chars.{input_buffer}")
    root.info(f"Start simulation.")
    output, instr_counter, ticks, control_un = simulation(
        data=code,
        input_buffer=input_buffer,
        memory_size=512,
        stack_size=64,
        limit=128, )

    root.info(f"output:{output}")
    root.info(f"Instructions:{instr_counter}")
    root.info(f"ticks:{ticks}")


if __name__ == "__main__":
    main()
