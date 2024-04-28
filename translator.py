import argparse
import os
import sys
from typing import List
import Opcode
import re
import json


def file_checker(path):
    if not os.path.isfile(path) or not os.access(path, os.R_OK):
        raise argparse.ArgumentError(f"{path} isn't valid file")
    return path


class Parser:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Forth translator")
        self.parser.add_argument("-input",
                                 dest="input",
                                 help="Example: -input './Forth_file'-this file is consisted of Forth code",
                                 type=file_checker,
                                 required=True)
        self.parser.add_argument("-output",
                                 dest="output",
                                 help="Example: -output './machine_code'-this file is consisted of machine code after translation.",
                                 default='output_machine_code'
                                 )


class TranslatorHelper:
    dictionary_definition_procedures = {}

    def __init__(self):
        self.literal: str = ""
        self.basic_operation: str = ""
        self.procedure: str = ""

    def __str__(self):
        return f"literal:{self.literal}\nbasic_operation:{self.basic_operation}\nprocedure:{self.procedure}"


def dereference_procedure_name(code: List[str]):
    line_number = 0
    dereference_code = []
    for line in code:
        dereference_line_procedure = ""

        is_contain_procedure = False
        line_number += 1
        splitted_line = line.strip().split(" ")
        if splitted_line[0] == ":":
            assert splitted_line[-1] == ';', \
                f"\nERROR:ends with '{splitted_line[-1]}'.\nProcedure definition must end with ';'.\nLine {line_number} in file {input}\n{line}"

            assert re.match(r"[A-Z]+[0-9]*", splitted_line[1]) is not None, \
                f"\nERROR:wrong procedure Name '{splitted_line[1]}'.\nProcedure name must match pattern [A-Z]+[0-9]*.\nLine {line_number} in file {input}\n{line}"

            for index_splitted_line, el in enumerate(splitted_line[2:]):

                if re.match(r"[A-Z]+[0-9]*", el) is not None:
                    assert el in TranslatorHelper.dictionary_definition_procedures, \
                        f"In procedure definition only previously defined procedures сan be referenced.\nLine {line_number} in file {input}\n{line}\n{el}."
                    is_contain_procedure = True
                    dereference_line_procedure = (
                            ' '.join(splitted_line[:2]) + ' ' + ' '.join(splitted_line[2:][
                                                                         :index_splitted_line]) + ' ' + TranslatorHelper.dictionary_definition_procedures.get(
                        el) + ' ' + ' '.join(splitted_line[2:][index_splitted_line + 1:]))

                if re.match(r"[a-z]+", el) is not None:
                    assert Opcode.Opcode.is_value_in_Opcode(el), \
                        f"in Procedure definition can contain only basic operation from Opcode class.\nLine {line_number} in file {input}\n{line}\n'{el}'"

            if is_contain_procedure:
                TranslatorHelper.dictionary_definition_procedures[
                    splitted_line[1]] = ' '.join(dereference_line_procedure.strip().split(" ")[2:-1]).strip()

            else:
                TranslatorHelper.dictionary_definition_procedures[splitted_line[1]] = ' '.join(splitted_line[2:-1])

        else:
            assert line.strip() in TranslatorHelper.dictionary_definition_procedures, \
                f"In procedure definition only previously defined procedures сan be invoked.\nLine {line_number} in file {input}\n{line}\n{line.strip()}."
            assert re.match(r"[A-Z]+[0-9]*", line.strip()) is not None, \
                f"\nERROR:wrong procedure Name '{line.strip()}'.\nProcedure name must match pattern [A-Z]+[0-9]*.\nLine {line_number} in file {input}\n{line.strip()}"
            dereference_code.append(line)

    return dereference_code


def translate_and_write(dereference_code: List[str], output_file_name: str, input_file_name: str):
    line_number = 0
    json_list = []
    for line in dereference_code:
        line_number += 1
        assert line.strip() in TranslatorHelper.dictionary_definition_procedures, \
            f"In procedure definition only previously defined procedures сan be invoked.\nLine {line_number} in file {input_file_name}\n{line}\n{line.strip()}."
        assert re.match(r"[A-Z]+[0-9]*", line.strip()) is not None, \
            f"\nERROR:wrong procedure Name '{line.strip()}'.\nProcedure name must match pattern [A-Z]+[0-9]*.\nLine {line_number} in file {input_file_name}\n{line.strip()}"

        json_object = {"procedure_name": line.strip(),
                       "basic_operations": TranslatorHelper.dictionary_definition_procedures[line.strip()].split(" "),
                       "line_in_dereference_code": line_number}
        json_list.append(json_object)

    with open(output_file_name, "w") as outfile:
        json.dump(json_list, outfile, indent=4)


def main():
    obj = Parser()
    command_line_arguments = obj.parser.parse_args()

    with open(command_line_arguments.input, encoding="utf-8") as f:
        source = f.read()

    code = dereference_procedure_name(source.split("\n"))

    translate_and_write(code, command_line_arguments.output, command_line_arguments.input)


main() if __name__ == "__main__" else ''