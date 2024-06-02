import contextlib
import io
import os
import tempfile

import pytest
import translator
import machine
import logging
@pytest.mark.golden_test("golden/*.yml")
def test_translator(golden,caplog):
    caplog.set_level(logging.INFO)
    with tempfile.TemporaryDirectory() as tmpdirname:
        source = os.path.join(tmpdirname, "source")
        input_stream = os.path.join(tmpdirname, "input")
        target_code = os.path.join(tmpdirname, "target_code.o")

        with open(source, "w", encoding="utf-8") as file:
            file.write(golden["in_source"])
        with open(input_stream, "w", encoding="utf-8") as file:
            file.write(golden["in_stdin"])

        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            translator.main(source, target_code)
            print("============================================================")
            machine.main(target_code,input_stream)

        with open(target_code, mode="rb") as file:
            code = file.read()


        assert caplog.text == golden.out["out_log"]
        assert code == golden.out["out_code"]
        assert stdout.getvalue() == golden.out["out_stdout"]
