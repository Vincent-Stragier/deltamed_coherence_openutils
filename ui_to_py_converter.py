# −∗− coding: utf−8 −∗−
"""PyQt6 uic module convert ui file (XML code) into py file (Python code)"""
from PyQt6 import uic

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(allow_abbrev=True)

    parser.add_argument(
        'input_file', type=str,
        help='path to the .ui file to convert to a .py file')

    parser.add_argument(
        'output_file', type=str,
        help='path to the converted .py file')

    args = parser.parse_args()

    with open(args.input_file, 'r') as file_in:
        with open(args.output_file, 'w') as file_out:
            uic.compileUi(file_in, file_out, execute=True)
