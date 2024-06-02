import argparse
import os
import sys
from typing import List
import Opcode
import re
import json
import logging

root = logging.getLogger(__name__)
root.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter(' %(levelname)s:%(name)s:%(asctime)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)


def file_checker(path):
    if not os.path.isfile(path) or not os.access(path, os.R_OK):
        raise argparse.ArgumentError(f"{path} isn't valid file")
    return path


class Parser:
    def __init__(self):
        root.info("initialized Parser object")
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
    literal: str = ""

    @classmethod
    def get_element(cls, key):
        return cls.dictionary_definition_procedures[key].split(" ")

    def __init__(self):
        self.basic_operation: str = ""
        self.procedure: str = ""

    def __str__(self):
        return f"literal:{self.literal}\nbasic_operation:{self.basic_operation}\nprocedure:{self.procedure}"


def dereference_procedure_name(code: List[str], input_file_name):
    root.info("Start dereference_procedure_name.")

    line_number = 0
    dereference_code = []
    for line in code:
        root.info(f"Work with {line}")
        dereference_line_procedure = ""

        is_contain_procedure = False
        line_number += 1
        splitted_line = line.strip().split(" ")
        assert splitted_line[-1] == ';', \
            f"\nERROR:ends with '{splitted_line[-1]}'.\nProcedure definition must end with ';'.\nLine {line_number} in file {input_file_name}\n{line}"

        if splitted_line[0] == ":":

            assert re.match(r"[A-Z]+[0-9]*", splitted_line[1]) is not None, \
                f"\nERROR:wrong procedure Name '{splitted_line[1]}'.\nProcedure name must match pattern [A-Z]+[0-9]*.\nLine {line_number} in file {input_file_name}\n{line}"
            if splitted_line[1] == "SUM":
                root.info("Line contain SUM special word.")

                TranslatorHelper.dictionary_definition_procedures["SUM"] = "sum"
                root.info("Add in dictionary_definition_procedures sum definition")
                continue
            if splitted_line[1] == "WRITE":
                root.info("Line contain WRITE special word.")
                literal = splitted_line[2]
                assert re.match(r"\".+\"",
                                literal
                                ) is not None, f"WRITE must have string literal in \"\" \nLine {line_number} in file {input_file_name}\n{line}\n{splitted_line[ind + 2 + 1]}"

                chars = list(literal)[1:-1]
                chars.reverse()
                chars.insert(0, "0")
                for index, char in enumerate(chars):
                    if char == "\"" or char == "_":
                        continue
                    new_procedure_name = "WRITE_{0}".format(index)
                    root.info(f"Create new Write method {new_procedure_name} with literal {char}.")
                    dereference_code.append(new_procedure_name)
                    TranslatorHelper.dictionary_definition_procedures[
                        new_procedure_name] = "write_string_into_memory {0}".format(char)
                continue
            procedure_body = splitted_line[2:]
            root.info("Start parsing splitted_line[2:]")
            for ind, term in enumerate(procedure_body):
                if re.match("\\d", term):
                    continue

                if re.match(r"[A-Z]+[0-9]*", term) is not None:
                    assert term in TranslatorHelper.dictionary_definition_procedures, \
                        f"In procedure definition only previously defined procedures сan be referenced.\nLine {line_number} in file {input_file_name}\nWhole Line:{line}\nProcedure name:{term}."
                    is_contain_procedure = True
                    root.info(f"{term} was found in dictionary definition.")
                    dereference_line_procedure = (
                            ' '.join(splitted_line[:2]) + ' ' + ' '.join(
                        procedure_body[:ind]) + ' ' + TranslatorHelper.dictionary_definition_procedures.get(
                        term) + ' ' + ' '.join(procedure_body[ind + 1:]))

                if re.match(r"[a-z]+", term) is not None:
                    assert Opcode.Opcode.is_value_in_Opcode(term), \
                        f"Procedure definition can contain only basic operation from Opcode class.\nLine {line_number} in file {input_file_name}\n{line}\n'{term}'"

            if is_contain_procedure:
                TranslatorHelper.dictionary_definition_procedures[
                    splitted_line[1]] = ' '.join(dereference_line_procedure.strip().split(" ")[2:-1]).strip()

            else:
                root.info(f"{splitted_line[1]} add definition in dictionary.")
                TranslatorHelper.dictionary_definition_procedures[splitted_line[1]] = ' '.join(splitted_line[2:-1])

        else:

            if splitted_line[0] != "LOOP" and splitted_line[0] != "WHILE" and splitted_line[0] != "IF":
                assert splitted_line[0] in TranslatorHelper.dictionary_definition_procedures, \
                    f"Only previously defined procedure can be invoked.\nLine {line_number} in file {input_file_name}\n{line}\n{line.strip()}"
                root.info(f"Invoked {line} found in dict.Add in dereference_code.")
                dereference_code.append(line)
            elif splitted_line[0] == "LOOP":
                assert splitted_line[2].isdigit(), \
                    f"In LOOP body iterations must be positive digit.\nLine {line_number} in file {input_file_name}\n{line}\n{line.strip()}"
                dereference_code.append(
                    "LOOP " + TranslatorHelper.dictionary_definition_procedures[splitted_line[1]] + " " + splitted_line[
                        2] + " ;")
                root.info(f"Invoked LOOP Operation.Add  in dereference_code")

            elif splitted_line[0] == "WHILE":
                assert splitted_line[2] in TranslatorHelper.dictionary_definition_procedures, \
                    f"Error in WHILE body:WRONG KEY IN TranslatorHelper.dictionary_definition_procedures.\nWrong key:\"{splitted_line}\"\nLine:{line_number}\nFile:{input_file_name}\n{line}"
                dereference_code.append(
                    "WHILE " + splitted_line[1] + " " + TranslatorHelper.dictionary_definition_procedures[
                        splitted_line[2]] + " ;")
                root.info(f"Invoked WHILE Operation.Add in dereference_code")

            elif splitted_line[0] == "IF":
                root.info(f"Invoked IF Operation.Add in dereference_code")

                assert splitted_line[2] in TranslatorHelper.dictionary_definition_procedures, \
                    f"Error in IF body:Only previously defined procedure can be used un true_body.\nWrong key:\"{splitted_line[2]}\"\nLine:{line_number}\nFile:{input_file_name}\n{line}"

                assert splitted_line[4] in TranslatorHelper.dictionary_definition_procedures, \
                    f"Error in IF body:Only previously defined procedure can be used un true_body.\nWrong key:\"{splitted_line[4]}\"\nLine:{line_number}\nFile:{input_file_name}\n{line}"

                TranslatorHelper.dictionary_definition_procedures[
                    "IF"] = f"CONDITION:{splitted_line[1]},IF_BODY:{TranslatorHelper.dictionary_definition_procedures[splitted_line[2]]},ELSE_BODY:{TranslatorHelper.dictionary_definition_procedures[splitted_line[4]]}"


            else:
                assert False, f"Wrong syntax line\nLine {line_number} in file {input_file_name}\n{line}"
    return dereference_code


def translate_and_write(dereference_code: List[str], output_file_name: str, input_file_name: str):
    line_number = 0
    json_list = []
    root.info(f"Start translate code in json format")

    for line in dereference_code:
        json_object = {}
        arguments = []
        line_number += 1
        root.info(f"Parsing line - {line}")

        splitted_line = line.strip().split(" ")
        procedure_name = splitted_line[0]

        if re.match("WRITE_\d+", procedure_name) is not None:
            root.info(f"Handle WRITE operation.")

            procedure_body = TranslatorHelper.get_element(procedure_name)
            literal = procedure_body[1]
            procedure_body.pop(1)
            json_object = {"procedure_name": procedure_name,
                           "basic_operations": list(procedure_body),
                           "argument": literal,
                           "line_in_dereference_code": line_number}


        elif procedure_name == "LOOP":
            root.info(f"Handle LOOP operation.")

            loop_body = splitted_line[1:-2]
            json_object = {"procedure_name": "LOOP", "basic_operations": loop_body, "iterations": splitted_line[-2],
                           "line_in_dereference_code": line_number}
        elif procedure_name == "WHILE":
            root.info(f"Handle WHILE operation.")

            while_body = splitted_line[2:-1]
            json_object = {"procedure_name": "WHILE", "basic_operations": while_body, "condition": splitted_line[1],
                           "line_in_dereference_code": line_number}
        elif "IF" in procedure_name:
            root.info(f"Handle IF operation.")
            if_body = splitted_line[2:-1]
            json_object = {"procedure_name": "IF", "basic_operations": if_body, "condition": splitted_line[1],
                           "line_in_dereference_code": line_number}
        elif procedure_name == "SUM":
            root.info(f"Handle SUM operation.")
            procedure_body = TranslatorHelper.get_element(procedure_name)
            json_object = {"procedure_name": procedure_name,
                           "basic_operations": [procedure_body[0]],
                           "line_in_dereference_code": line_number}
        else:
            json_object = {"procedure_name": procedure_name,
                           "basic_operations": TranslatorHelper.get_element(procedure_name),
                           "line_in_dereference_code": line_number}

        if "CONDITION" in line:
            root.info("FOUND CONDITION IN LINE")
            if_condition = next(x for x in splitted_line if x.startswith("CONDITION"))
            pattern = re.compile(r'([\w]+):([^,]+)')
            converted_dict = dict(pattern.findall(if_condition))
            json_object["basic_operations"] = converted_dict
        json_list.append(json_object)

    with open(output_file_name, "w") as outfile:
        json.dump(json_list, outfile, indent=4)


def main():
    obj = Parser()
    command_line_arguments = obj.parser.parse_args()
    root.info("Parse line arguments.")
    with open(command_line_arguments.input, encoding="utf-8") as f:
        source = f.read()
    root.info(f"File with source code-{command_line_arguments.input}.")

    code = dereference_procedure_name(source.split("\n"), command_line_arguments.input)

    translate_and_write(code, command_line_arguments.output, command_line_arguments.input)


main() if __name__ == "__main__" else ''
