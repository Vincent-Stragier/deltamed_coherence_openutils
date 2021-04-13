""" This module contains all the useful functions of this project. """
import os
import re
import shutil
import sys
import traceback
from functools import reduce

import pywinauto
from pywinauto.application import Application


# Files and directories related functions
def list_files(path: str):
    """List all the files in a folder and subfolders.

    Args:
        path: the path to use as parent directory.
    Returns:
        A list of files.
    """
    files_list = set()

    for folder, _, files in os.walk(path):
        for file_ in files:
            files_list.add(os.path.join(folder, file_))

    return list(files_list)


def ensure_path(path: str):
    """ Ensure the existence of a specified path.

    Args:
        path: path to create if non existing.
    """
    if not os.path.isdir(path):
        os.makedirs(path)


def find_files(basename_prefix: str, sources: dict):
    """Find the path to the file if it exists.

    Args:
        basename_prefix: the basename prefix of the recording.
        sources: the sources to use.
    Returns:
        An empty list or a list of string which contains the path to the files.
    """
    for files in sources.values():
        matching_files = [
            file_ for file_ in files
            if os.path.basename(file_).startswith(basename_prefix + '_')
        ]

        if matching_files:
            return matching_files
    return []


# Args parsing related functions
def display_arguments(args, message: str = ''):
    """ Display the parsed arguments. """
    if message is not None and message == '':
        print('The following arguments have been parsed:')
    elif message is not None and message != '':
        print(message)

    for key, value in vars(args).items():
        print('{0}: {1}'.format(key, value))


def handle_yes_no(args):
    """ Handle the arguments 'yes' and 'no'. """
    if not args.no:
        print()
        if not args.yes:
            try:
                while True:
                    conti = input('Do you want to run the program (yes/no)? ')
                    if conti.lower() in ('n', 'no'):
                        sys.exit()

                    elif conti.lower() in ('y', 'yes'):
                        break

            except KeyboardInterrupt:
                print(
                    '\nThe user requested the end of the program'
                    ' (KeyboardInterrupt).',
                )

                sys.exit()
    else:
        sys.exit()


# String processing related function
def split_keep_sep(string, separator):
    """Split a string according to a separator.

    Args:
        string: the string to split.
        separator: the separator to use and to keep.

    Returns:
        A list with the splited elements.
    """
    return reduce(
        lambda acc, elem: acc[:-1] + [acc[-1] + elem] if elem == separator
        else acc + [elem], re.split('(%s)' % re.escape(separator), string), [],
    )


# PyInstaller related function
def resource_path(relative_path: str):
    """Get absolute path to resource, works for dev and for PyInstaller.

    Args:
        relative_path: the path to resolve.

    Returns:
        The absolute path to the ressource.
    """
    base_path = getattr(
        sys,
        '_MEIPASS',
        os.path.dirname(os.path.abspath(__file__)),
    )

    return os.path.join(base_path, relative_path)


# Deltamed anonymisation related functions
def extract_header(filename: str):
    """ Extract the header of a Deltamed .eeg file.

    Args:
        filename: path to the .eeg file.
    Returns:
        A list of bytes
    """
    header = []

    with open(filename, 'rb') as file_:
        header = [
            char if isinstance(char, bytes) else bytes([char])
            for char in file_.read(720)
        ]
    return header


def change_field(
    array, start: int, stop: int, content: list, filler: bytes = b'\x00',
):
    """ Change the content of a .eeg file field in memory.

    Args:
        array: is the header of the .eeg file.
        start: is the starting index of where to change the field.
        stop: is the stoping index of where to change the field.
        content: is the content to write in the field.
        filler: is the filling character used in the field.
    """
    for index in range(start, stop):
        if index - start < len(content):
            array[index] = content[index - start]
        else:
            array[index] = filler

    return stop - start >= len(content)


def anonymise_eeg(
    original_file: str,
    destination_file: str,
    field_name: str = '',
    field_surname: str = '',
    field_birthdate: str = '',
    field_sex: str = '',
    field_folder: str = '',
    field_centre: str = '',
    field_comment: str = ''
):
    """Anonymise an .eeg file.

    Args:
        orginale_file: path to the original file.
        destination_file: path to affect the anonymisation.
        field_name: patient name.
        field_surname: patient surname.
        field_birthdate: birthdate.
        field_sex: sex.
        field_folder: folder name.
        field_centre: centre name.
        field_comment: comment.
    """
    # Copy the original content
    content = extract_header(original_file)

    # Anonymise
    if field_name is not None:
        change_field(content, 314, 364, field_name.encode('ascii'))

    if field_surname is not None:
        change_field(content, 364, 394, field_surname.encode('ascii'))

    if field_birthdate is not None:
        change_field(content, 394, 404, field_birthdate.encode('ascii'))

    if field_sex is not None:
        change_field(content, 404, 405, field_sex.encode('ascii'))

    if field_folder is not None:
        change_field(content, 405, 425, field_folder.encode('ascii'))

    if field_centre is not None:
        change_field(content, 425, 464, field_centre.encode('ascii'))

    if field_comment is not None:
        change_field(content, 464, 720, field_comment.encode('ascii'))

    ensure_path(path=os.path.dirname(destination_file))

    content = (
        char if isinstance(char, bytes) else bytes([char]) for char in content
    )

    if not os.path.isfile(destination_file):
        shutil.copyfile(original_file, destination_file + '.part')
        os.rename(destination_file + '.part', destination_file)

    with open(destination_file, 'rb+') as file_:
        file_.seek(0)

        for char in content:
            file_.write(char if isinstance(char, bytes) else bytes([char]))

    return True


def display_fields(filename: str):
    """ Display the fields of a .eeg file.

    Args:
        filename: path to the .eeg file.
    """
    fields = b''.join(extract_header(filename))

    print(
        'Name:    "',
        fields[314:364].decode('ascii', errors='ignore'),
        '"',
        sep='',
    )  # 50 characters (Name)

    print(
        'Surname: "',
        fields[364:394].decode('ascii', errors='ignore'),
        '"',
        sep='',
    )  # 30 characters (Surname)

    print(
        'Date:    "',
        fields[394:404].decode('ascii', errors='ignore'),
        '"',
        sep='',
    )  # 10 characters (Date)

    print(
        'Sex:     "',
        fields[404:405].decode('ascii', errors='ignore'),
        '"',
        sep='',
    )  # 1 charaters (Sex)

    print(
        'Folder:  "',
        fields[405:425].decode('ascii', errors='ignore'),
        '"',
        sep='',
    )  # 20 charaters (Folder)

    print(
        'Centre:  "',
        fields[425:464].decode('ascii', errors='ignore'),
        '"',
        sep='',
    )  # 39 charaters (Center)

    print(
        'Comment: "',
        fields[464:720].decode('ascii', errors='ignore'),
        '"',
        sep='',
    )  # 256 charaters (Comment)


def anonymise_eeg_verbose(
    original_file: str,
    destination_file: str,
    field_name: str = '',
    field_surname: str = '',
    field_birthdate: str = '',
    field_sex: str = '',
    field_folder: str = '',
    field_centre: str = '',
    field_comment: str = '',
    verbose=False,
):
    """Anonymise an .eeg file.

    Args:
        orginale_file: path to the original file.
        destination_file: path to affect the anonymisation.
        field_name: patient name.
        field_surname: patient surname.
        field_birthdate: birthdate.
        field_sex: sex.
        field_folder: folder name.
        field_centre: centre name.
        field_comment: comment.
        verbose: display or not the content of the fields before and after.
    """
    # From:
    # Display current values
    if verbose:
        print('From:')
        display_fields(original_file)

    # To:
    anonymise_eeg(
        original_file=original_file,
        destination_file=destination_file,
        field_name=field_name,
        field_surname=field_surname,
        field_birthdate=field_birthdate,
        field_sex=field_sex,
        field_folder=field_folder,
        field_centre=field_centre,
        field_comment=field_comment,
    )

    if verbose:
        print('To:')
        display_fields(destination_file)

    return True


# EEG (Deltamed) to EDF related functions
def convert_coh3_to_edf(
    executable_path: str,
    eeg_path: str,
    edf_path: str = None,
    depth: int = 3,
):
    """ Convert Coherence 3 (.eeg) to EDF file format.

    Args:
        executable_path: path to the converter executable.
        eeg_path: path to the eeg file to convert.
        edf_path: path to the converted EDF file.
    """
    if edf_path is None:
        edf_path = eeg_path[:-4] + '.EDF'

    overwrite_edf = os.path.isfile(edf_path)

    char_at_424 = b''
    with open(eeg_path, 'rb') as file_:
        file_.seek(424)
        char_at_424 = file_.read(1)

    # Open the executable
    path = ''
    try:
        app = Application(backend='uia').start(executable_path)
        app = Application().connect(title='Source (C:\\EEG2)')

        # Select file in folder
        if char_at_424 != b'\x00':
            if hasattr(sys, 'frozen'):
                tmpdir = os.path.dirname(os.path.abspath(sys.executable))
            else:
                tmpdir = os.path.dirname(os.path.abspath(__file__))

            path = os.path.realpath(
                os.path.join(tmpdir, 'temp', os.path.basename(eeg_path)),
            )
            ensure_path(os.path.dirname(path))
            src = r'\\?\{0}'.format(eeg_path)
            dst = r'\\?\{0}'.format(path)
            try:
                shutil.copyfile(src, dst)
            except OSError:
                shutil.copyfile(eeg_path, path)

            eeg_path = path
            with open(eeg_path, 'rb+') as file_:
                file_.seek(424)
                file_.write(b'\x00')

        app.Dialog.child_window(class_name='ComboBoxEx32').child_window(
            class_name="Edit",
        ).set_text(eeg_path)
        app.Dialog.Ouvrir.click()

        # Start conversion
        app.TEDFForm.child_window(
            title="UTF-8", class_name="TGroupButton",
        ).click()
        app.TEDFForm.child_window(
            title="EDF+", class_name="TGroupButton",
        ).click()
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
        if depth:
            convert_coh3_to_edf(
                executable_path, eeg_path, edf_path, depth-1,
            )

    # If the windows if not found, relaunch the program
    except pywinauto.findwindows.ElementNotFoundError:
        traceback.print_exc()
        if depth:
            convert_coh3_to_edf(
                executable_path, eeg_path, edf_path, depth-1,
            )

    finally:
        # Remove temp file and dir if it exits
        if os.path.dirname(path) != '':
            if os.path.exists(os.path.dirname(path)):
                shutil.rmtree(os.path.dirname(path))


if __name__ == '__main__':
    print('utils.py is a module, not a script')
