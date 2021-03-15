""" Test the functions of utils.py """
import argparse
import io
import filecmp
import hashlib
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

# Add the path of the script to the module
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils import (
    anonymise_eeg,
    change_field,
    display_arguments,
    ensure_path,
    extract_header,
    find_files,
    handle_yes_no,
    list_files,
    resource_path,
    split_keep_sep,
)


def exe_path():
    """ Return the path of the executable or of the script. """
    if hasattr(sys, 'frozen'):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def create_parser():
    """ Minimal test parser. """
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-y',
        '--yes',
        help='if set, the program will start directly',
        action='store_true',
        default=False,
    )

    group.add_argument(
        '-n',
        '--no',
        help='if set, the program will exit directly',
        action='store_true',
        default=False,
    )

    return parser


class TestUtils(unittest.TestCase):

    def test_list_files(self):
        """ Test the function list_files. """
        files = (
            os.path.join('folder_0', 'subfolder_0', 'file_0'),
            os.path.join('folder_0', 'subfolder_0', 'file_1'),
            os.path.join('folder_0', 'subfolder_1', 'file_0'),
            os.path.join('folder_0', 'subfolder_1', 'file_1'),
            os.path.join('folder_1', 'subfolder_0', 'file_0'),
            os.path.join('folder_1', 'subfolder_0', 'file_1'),
            os.path.join('folder_1', 'subfolder_1', 'file_0'),
            os.path.join('folder_1', 'subfolder_1', 'file_1'),
        )

        with tempfile.TemporaryDirectory() as tmpdirname:
            for file_ in files:
                path = os.path.join(tmpdirname, os.path.dirname(file_))

                try:
                    os.makedirs(path)
                except FileExistsError:
                    pass

                with open(os.path.join(tmpdirname, file_), 'w') as _:
                    pass
            
            files = [os.path.join(tmpdirname, file_) for file_ in files]
            listed_files = list_files(tmpdirname)
            self.assertEqual(sorted(listed_files), sorted(files))
    
    def test_ensure_path(self):
        """ Test the function ensure_path. """
        with tempfile.TemporaryDirectory() as tmpdirname:
            subfolder_path = os.path.join(tmpdirname, 'folder', 'subfolder')
            folder_path = os.path.join(tmpdirname, 'folder')

            # No folder and subfolder should exist
            self.assertEqual(os.path.exists(subfolder_path), False)
            self.assertEqual(os.path.exists(folder_path), False)

            # Create folder and subfolder
            ensure_path(subfolder_path)

            # Folder and subfolder should exist
            self.assertEqual(os.path.exists(subfolder_path), True)
            self.assertEqual(os.path.exists(folder_path), True)

            # Should not change anything
            ensure_path(folder_path)

            # Folder and subfolder should exist
            self.assertEqual(os.path.exists(subfolder_path), True)
            self.assertEqual(os.path.exists(folder_path), True)
    
    def test_find_files(self):
        """ Test the function find_files. """
        files = [
            os.path.join('folder_0', 'subfolder_0', 'file_0'),
            os.path.join('folder_0', 'subfolder_0', 'file_1'),
            os.path.join('folder_0', 'subfolder_1', 'file_0'),
            os.path.join('folder_0', 'subfolder_1', 'file_1'),
            os.path.join('folder_1', 'subfolder_0', 'file_0'),
            os.path.join('folder_1', 'subfolder_0', 'file_1'),
            os.path.join('folder_1', 'subfolder_1', 'file_0'),
            os.path.join('folder_1', 'subfolder_1', 'file_1'),
        ]

        sources_0 = {'folder_0' : files[:4], 'folder_1' : files[4:],}

        sources_1 = {
            'folder_0' : ['1', '2', '3', '4'], 'folder_1' : files[4:],
        }

        sources_2 = {
            'folder_1' : ['1', '2', '3', '4'], 'folder_0' : files[:4],
        }

        sources_3 = {
            'folder_1' : ['1', '2', '3', '4'],
            'folder_0' : ['1', '2', '3', '4'],
        }

        self.assertEqual(find_files(basename_prefix='file', sources=sources_0), files[:4])
        self.assertEqual(find_files(basename_prefix='file', sources=sources_1), files[4:])
        self.assertEqual(find_files(basename_prefix='file', sources=sources_2), files[:4])
        self.assertEqual(find_files(basename_prefix='file', sources=sources_3), [])

    def test_display_arguments(self):
        """ Test the function display_arguments. """
        # Build a dummy arg paser
        parser = create_parser()
        args_0 = parser.parse_args(['--yes'])
        args_1 = parser.parse_args(['--no'])

        # Capture sys.stdout, etc.
        with patch('sys.stdout', new=io.StringIO()) as captured_output:
            display_arguments(args=args_0, message='')
            self.assertEqual(
                captured_output.getvalue(),
                (
                    'The following arguments have been parsed:'
                    '\nyes: True\nno: False\n'
                ),
            )

        with patch('sys.stdout', new=io.StringIO()) as captured_output:
            display_arguments(args=args_1, message='')
            self.assertEqual(
                captured_output.getvalue(),
                (
                    'The following arguments have been parsed:'
                    '\nyes: False\nno: True\n'
                ),
            )

        with patch('sys.stdout', new=io.StringIO()) as captured_output:
            display_arguments(args=args_0, message=None)
            self.assertEqual(
                captured_output.getvalue(), 'yes: True\nno: False\n',
            )

        with patch('sys.stdout', new=io.StringIO()) as captured_output:
            display_arguments(args=args_1, message=None)
            self.assertEqual(
                captured_output.getvalue(), 'yes: False\nno: True\n',
            )

        with patch('sys.stdout', new=io.StringIO()) as captured_output:
            display_arguments(args=args_0, message='Parsed')
            self.assertEqual(
                captured_output.getvalue(),
                'Parsed\nyes: True\nno: False\n',
            )

        with patch('sys.stdout', new=io.StringIO()) as captured_output:
            display_arguments(args=args_1, message='Parsed')
            self.assertEqual(
                captured_output.getvalue(),
                'Parsed\nyes: False\nno: True\n',
            )

    def test_handle_yes_no(self):
        """ Test the function handle_yes_no. """
        # Build a dummy arg paser
        parser = create_parser()
        args_0 = parser.parse_args(['--yes'])
        args_1 = parser.parse_args(['--no'])
        args_2 = parser.parse_args(['-y'])
        args_3 = parser.parse_args(['-n'])
        args_4 = parser.parse_args([])

        # Capture sys.stdout, etc.
        with patch('sys.stdout', new=io.StringIO()) as captured_output:
            handle_yes_no(args=args_0)  # --yes
            self.assertEqual(captured_output.getvalue(), '\n')

        with patch('sys.stdout', new=io.StringIO()) as captured_output:
            with self.assertRaises(SystemExit) as cm:
                handle_yes_no(args=args_1)  # --no
            self.assertEqual(cm.exception.code, None)
            self.assertEqual(captured_output.getvalue(), '')

        with patch('sys.stdout', new=io.StringIO()) as captured_output:
            handle_yes_no(args=args_2)  # -y
            self.assertEqual(captured_output.getvalue(), '\n')

        with patch('sys.stdout', new=io.StringIO()) as captured_output:
            with self.assertRaises(SystemExit) as cm:
                handle_yes_no(args=args_3)  # -n
            self.assertEqual(cm.exception.code, None)
            self.assertEqual(captured_output.getvalue(), '')

        test_no = ('n', 'N', 'no', 'No', 'NO', 'nO')
        for no in test_no:
            with patch('sys.stdout', new=io.StringIO()) as captured_output:
                with patch('builtins.input', return_value=no):
                    with self.assertRaises(SystemExit) as cm:
                        handle_yes_no(args=args_4)
                    self.assertEqual(cm.exception.code, None)
                self.assertEqual(captured_output.getvalue(), '\n')

        test_yes = (
            'y', 'Y', 'yes', 'Yes', 'YEs', 'yEs', 'yES', 'yeS', 'YeS', 'YES',
        )
        for yes in test_yes:
            with patch('sys.stdout', new=io.StringIO()) as captured_output:
                with patch('builtins.input', return_value=yes):
                    handle_yes_no(args=args_4)
                self.assertEqual(captured_output.getvalue(), '\n')

        # User input and 'yes'
        with patch('sys.stdout', new=io.StringIO()) as captured_output:
            with patch('builtins.input', side_effect=['Sì', 'sì', '', 'yes']):
                handle_yes_no(args=args_4)
            self.assertEqual(captured_output.getvalue(), '\n')

        # User input and 'no'
        with patch('sys.stdout', new=io.StringIO()) as captured_output:
            with patch('builtins.input', side_effect=['Sì', 'sì', '', 'no']):
                with self.assertRaises(SystemExit) as cm:
                    handle_yes_no(args=args_4)
                    self.assertEqual(cm.exception.code, None)
            self.assertEqual(captured_output.getvalue(), '\n')
        
        # Send KeyboardInterrupt
        with patch('sys.stdout', new=io.StringIO()) as captured_output:
            with patch('builtins.input', side_effect=KeyboardInterrupt()):
                with self.assertRaises(SystemExit) as cm:
                    handle_yes_no(args=args_4)
                    self.assertEqual(cm.exception.code, None)
            self.assertEqual(
                captured_output.getvalue(),
                '\n\nThe user requested the end of the program '
                '(KeyboardInterrupt).\n',
            )

    def test_split_keep_sep(self):
        """ Test the function split_keep_sep. """
        test_string = 'this\nis\na\ntest\nstring\n'
        expected_split = ['this\n', 'is\n', 'a\n', 'test\n', 'string\n', '']
        separator = '\n'
        splitted_string = split_keep_sep(test_string, separator)

        self.assertEqual(splitted_string, expected_split)

    def test_resource_path(self):
        """ Test the function resource_path. """
        # Will return the absolute path to utils.py folder
        path = resource_path('') 

        if hasattr(sys, 'frozen'):  # Probably never during the test.
            check_path = sys._MEIPASS
        else:
            check_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                '',
            )

        self.assertEqual(path, check_path)
    
    def test_extract_header(self):
        """ Test the function extract_header. """
        path_eeg_r = os.path.join(exe_path(), 'test_data', 'EEG_R.eeg')
        header_eeg_r = extract_header(path_eeg_r)
        hashed_expected_header_eeg_r = (
            '2ed65bfe84f0db86fe36df25d9cf05287986fa8d8146f381a718f3b149213dae'
        )
        hashed_header_eeg_r = hashlib.sha256(
            b''.join(header_eeg_r)
        ).hexdigest()
        self.assertEqual(hashed_header_eeg_r, hashed_expected_header_eeg_r)

        path_eeg_r_anonymised = os.path.join(
            exe_path(), 'test_data', 'EEG_R_anonymised.eeg',
        )
        header_eeg_r_anonymised = extract_header(path_eeg_r_anonymised)
        hashed_expected_header_eeg_r_anonymised = (
            'fde46c624b9401a540ebdd528cbeb524a64286f30ea1720552d1a14e37598e9c'
        )
        hashed_header_eeg_r_anonymised = hashlib.sha256(
            b''.join(header_eeg_r_anonymised)
        ).hexdigest()
        self.assertEqual(
            hashed_header_eeg_r_anonymised,
            hashed_expected_header_eeg_r_anonymised,
        )

    def test_change_field(self):
        """ Test the function change_field. """
        path_eeg_r = os.path.join(exe_path(), 'test_data', 'EEG_R.eeg')
        header_eeg_r = extract_header(path_eeg_r)
        hashed_expected_header_eeg_r = (
            '2ed65bfe84f0db86fe36df25d9cf05287986fa8d8146f381a718f3b149213dae'
        )
        hashed_header_eeg_r = hashlib.sha256(
            b''.join(header_eeg_r)
        ).hexdigest()
        self.assertEqual(hashed_header_eeg_r, hashed_expected_header_eeg_r)

        # Just empty all the fields
        change_field(header_eeg_r, 314, 720, [])

        path_eeg_r_anonymised = os.path.join(
            exe_path(), 'test_data', 'EEG_R_anonymised.eeg',
        )
        header_eeg_r_anonymised = extract_header(path_eeg_r_anonymised)
        hashed_expected_header_eeg_r_anonymised = (
            'fde46c624b9401a540ebdd528cbeb524a64286f30ea1720552d1a14e37598e9c'
        )
        hashed_header_eeg_r_anonymised = hashlib.sha256(
            b''.join(header_eeg_r_anonymised)
        ).hexdigest()
        self.assertEqual(
            hashed_header_eeg_r_anonymised,
            hashed_expected_header_eeg_r_anonymised,
        )
        self.assertEqual(
            b''.join(header_eeg_r),
            b''.join(header_eeg_r_anonymised),
        )

    def test_anonymise_eeg(self):
        """ Test the function anonymise_eeg. """
        path_eeg_r = os.path.join(exe_path(), 'test_data', 'EEG_R.eeg')
        path_eeg_r_anonymised_with_deltamed = os.path.join(
            exe_path(), 'test_data', 'EEG_R_anonymised.eeg',
        )

        with tempfile.TemporaryDirectory() as tmpdirname:
            path_eeg_r_anonymised = os.path.join(
                tmpdirname, 'EEG_R_anonymised.eeg',
            )
            anonymise_eeg(
                path_eeg_r,
                path_eeg_r_anonymised,
            )
            compare_against_old = filecmp.cmp(
                path_eeg_r,
                path_eeg_r_anonymised,
                shallow=False,
            )
            # Anonymised file should be different from source
            self.assertEqual(compare_against_old, False)
            compare_against_anonymised_with_deltamed = filecmp.cmp(
                path_eeg_r_anonymised_with_deltamed,
                path_eeg_r_anonymised,
                shallow=False,
            )
            # Anonymised file should be the same as the file anonymised
            # with Deltamed's tool.
            self.assertEqual(compare_against_anonymised_with_deltamed, True)


if __name__ == '__main__':
    unittest.main()
