import logging
import sys
root = logging.getLogger(__name__)
root.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter(' %(levelname)s:%(name)s:%(asctime)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)
class ALU:
    @staticmethod
    def sum(el1: int, el2: int) -> int:
        root.info("ALU SUM OPERATION started.")
        return el1 + el2
