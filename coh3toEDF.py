""" This script is intended to batch convert Deltamed .eeg files to .edf files.
"""
# comtypes==1.1.7 pywinauto pywin32==228 and Python 3.8
import json
import os
import sys
import traceback

import pywinauto
from pywinauto.application import Application
from utils import display_arguments, ensure_path, handle_yes_no, list_files


def exe_path():
    """ Return the path of the executable or of the script. """
    if hasattr(sys, 'frozen'):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


SCRIPT_PATH = exe_path()
CONFIG_FILE = 'coh3toEDF.config'
CONFIG_FILE = os.path.join(SCRIPT_PATH, CONFIG_FILE)

try:
    EXECUTABLE_PATH = json.load(open(CONFIG_FILE))['path_to_executable']
except FileNotFoundError:
    EXECUTABLE_PATH = os.path.join(SCRIPT_PATH, 'coh3toEDF.exe')
    print(
        'Generating "coh3toEDF.config" file, please edit it '
        'to set the correct path to the executable "coh3toEDF.exe".\n'
        'You can find "coh3toEDF.config" here: {0}'.format(SCRIPT_PATH)
    )
    config = {'path_to_executable': EXECUTABLE_PATH}
    json.dump(config, open(CONFIG_FILE, 'w'))


def convert_coh3_to_edf(
    eeg_path: str,
    edf_path: str = None,
    executable_path: str = EXECUTABLE_PATH,
):
    """ Convert Coherence 3 (.eeg) to EDF file format.

    Args:
        eeg_path: path to the eeg file to convert.
        edf_path: path to the converted EDF file.
        executable_path: path to the converter executable.
    """
    if edf_path is None:
        edf_path = eeg_path[:-4] + '.EDF'

    overwrite_edf = os.path.isfile(edf_path)

    # Open the executable
    try:
        app = Application(backend='uia').start(executable_path)
        app = Application().connect(title='Source (C:\\EEG2)')

        # Select file in folder
        app.Dialog.child_window(class_name='ComboBoxEx32').child_window(
            class_name="Edit",
        ).set_text(eeg_path)
        app.Dialog.Ouvrir.click()

        # Start conversion
        app.TEDFForm.OK.click()

        # Saving path
        app.Destination.wait('exists ready')
        app.Destination['ComboBox2'].child_window(
            class_name='Edit',
        ).set_text(edf_path)

        # Indicate where to save the file
        app.Destination.Button1.click()

        # If the file already exist overwrite it.
        if overwrite_edf:
            app['Confirmer l’enregistrement'].wait('exists')

            if app['Dialog0'].texts() == ['Confirmer l’enregistrement']:
                app['Dialog0'].Oui.click()

        # Wait for the process to complete
        app.wait_for_process_exit(timeout=60)

    # If multiple instances are runing, kill them all
    except (
        pywinauto.findwindows.ElementAmbiguousError,
        pywinauto.findbestmatch.MatchError,
    ):
        traceback.print_exc()

        # Only use one instance at a time
        os.system(
            'taskkill /f /im {0}'.format(
                os.path.basename(executable_path),
            ),
        )
        convert_coh3_to_edf(eeg_path, edf_path, executable_path)

    # If the windows if not found, relaunch the program
    except pywinauto.findwindows.ElementNotFoundError:
        traceback.print_exc()
        convert_coh3_to_edf(eeg_path, edf_path, executable_path)


def main(
    original_path: str,
    executable_path: str = EXECUTABLE_PATH,
    destination_path: str = None,
    overwrite: bool = False,
):
    """ Run batch conversion process.

    Args:
        original_path: path to the dataset to convert.
        executable_path: path to the converter executable.
        destination_path: destination path.
        overwrite: if True, any previous .edf
        with the same name will be overwrited.
    """
    print('1 - List the files to convert...')
    files = [
        os.path.abspath(file_) for file_ in list_files(original_path)
        if os.path.basename(file_).lower().endswith('.eeg')
    ]

    n_files = len(files)
    print('{0} file(s) will be converted.'.format(n_files))

    print('2 - Convert files')
    for index, file_ in enumerate(sorted(files), start=1):
        # Destination file path
        if destination_path is None:
            file_destination_path = file_[:-4] + '.EDF'
        else:
            file_destination_path = os.path.join(
                destination_path,
                os.path.relpath(file_, original_path)
            )

        print(
            '({0}/{1}) Convert "{2}" to "{3}"'.format(
                index,
                n_files,
                file_,
                file_destination_path,
            ),
        )

        ensure_path(path=os.path.dirname(file_destination_path))

        if os.path.isfile(file_destination_path) and not overwrite:
            print('File has already been converted.')
        else:
            if os.path.isfile(file_destination_path):
                print('File has already been converted (will be overwrited).')
            convert_coh3_to_edf(
                eeg_path=file_,
                edf_path=file_destination_path,
                executable_path=executable_path,
            )

    if n_files:
        print('3 - Kill the converter process(es).')
        os.system(
            'taskkill /f /im {0}'.format(
                os.path.basename(executable_path),
            ),
        )


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(allow_abbrev=True)

    parser.add_argument(
        'path',
        type=str,
        help='path to the dataset to convert from coh3 (.eeg) to EDF',
    )

    parser.add_argument(
        '-dp',
        '--destination_path',
        type=str,
        help=(
            'destination of the converted (.edf) files'
        ),
        default=None,
    )

    parser.add_argument(
        '-ep',
        '--executable_path',
        type=str,
        help=(
            'path to the converter executable'
        ),
        default=None,
    )

    parser.add_argument(
        '-o',
        '--overwrite',
        help='if set, the program will overwrite the existing .edf files',
        action='store_true',
        default=False,
    )

    # By default ask to the user if a want to proceed.
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

    args = parser.parse_args()
    display_arguments(args)
    handle_yes_no(args)

    if args.executable_path is None:
        # Load config information
        configs = json.load(open(CONFIG_FILE))
        path_to_executable = configs['path_to_executable']

        if not os.path.isfile(path_to_executable):
            print(
                '"{0}" does not exist. '
                'The path to the executable "coh3toEDF.exe" is not valid. '
                'Please check that the path provided in the "coh3toEDG.config"'
                ' file is correct.'.format(path_to_executable)
            )
            sys.exit(1)

    else:
        path_to_executable = args.executable_path
        if not os.path.isfile(path_to_executable):
            print(
                '"{0}" does not exist. '
                'The path to the executable "coh3toEDF.exe" is not valid. '
                'Please check that the path provided as argument.'.format(
                    path_to_executable,
                )
            )
            sys.exit(1)

    main(
        original_path=args.path,
        executable_path=path_to_executable,
        destination_path=args.destination_path,
        overwrite=args.overwrite,
    )
