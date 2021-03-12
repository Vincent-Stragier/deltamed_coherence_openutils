"""The aim of this script is to automatically build a 'predataset'.

First, the script will list all the files available in the datasources.
Second, the list will be filtered and only the .eeg files will be kept.
Third, an excel (.xlsx) file will be used to select the file to scrap
in order to build the dataset.
Fourth, each patient will be researched in the list of files.
Fith, each required file will be anonymise by default
and transfered to a destination path.
"""
import json
import multiprocessing as mp
import os
import shutil
import sys

import pandas as pd
import win32api


def exe_path():
    """ Return the path of the executable or of the script. """
    if hasattr(sys, 'frozen'):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


SCRIPT_PATH = exe_path()
CONFIG_FILE = 'dataset_maker.config'
CONFIG_FILE = os.path.join(SCRIPT_PATH, CONFIG_FILE)


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
    if not os.path.isdir(path):
        os.makedirs(path)


def extract_header(filename: str):
    header = []

    with open(filename, 'rb') as f:
        for line in f:
            header.extend(line)
            if len(header) > 719:
                header = [
                    char if isinstance(char, bytes) else bytes([char])
                    for char in header
                ]

                return header


def display_fields(filename: str):
    fields = b''.join(extract_header(filename))

    print(
        'Name: "',
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
        'Date: "',
        fields[394:404].decode('ascii', errors='ignore'),
        '"',
        sep='',
    )  # 10 characters (Date)

    print(
        'Sex: "',
        fields[404:405].decode('ascii', errors='ignore'),
        '"',
        sep='',
    )  # 1 charaters (Sex)

    print(
        'Folder: "',
        fields[405:425].decode('ascii', errors='ignore'),
        '"',
        sep='',
    )  # 20 charaters (Folder)

    print(
        'Center: "',
        fields[425:464].decode('ascii', errors='ignore'),
        '"',
        sep='',
    )  # 39 charaters (Center)

    print(
        'Comment: "',
        fields[464:719].decode('ascii', errors='ignore'),
        '"',
        sep='',
    )  # 255 charaters (Comment)


def change_field(
    array, start: int, stop: int, content: list, filler: bytes = b'\x00'
):
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
    field_comment: str = '',
    verbose=False,
):
    """Anonymaze an .eeg file.

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
    # From:
    # Display current values
    if verbose:
        print('From:')
        display_fields(original_file)

    # Copy the original content
    content = extract_header(original_file)

    # Anonymise
    if verbose:
        print('To:')

    if field_name is None:
        pass
    else:
        change_field(content, 314, 364, field_name.encode('ascii'))

    if field_surname is None:
        pass
    else:
        change_field(content, 364, 394, field_surname.encode('ascii'))

    if field_birthdate is None:
        pass
    else:
        change_field(content, 394, 404, field_birthdate.encode('ascii'))

    if field_sex is None:
        pass
    else:
        change_field(content, 404, 405, field_sex.encode('ascii'))

    if field_folder is None:
        pass
    else:
        change_field(content, 405, 425, field_folder.encode('ascii'))

    if field_centre is None:
        pass
    else:
        change_field(content, 425, 464, field_centre.encode('ascii'))

    if field_comment is None:
        pass
    else:
        change_field(content, 464, 719, field_comment.encode('ascii'))

    ensure_path(path=os.path.dirname(destination_file))

    content = (
        char if isinstance(char, bytes) else bytes([char]) for char in content
    )

    if not os.path.isfile(destination_file):
        shutil.copyfile(original_file, destination_file + '.part')
        os.rename(destination_file + '.part', destination_file)

    with open(destination_file, 'rb+') as f:
        f.seek(0)

        for char in content:
            f.write(char if isinstance(char, bytes) else bytes([char]))

    if verbose:
        display_fields(destination_file)

    return True


def find_files(basename: str, sources: dict):
    """Find the path to the file if it exists.

    Args:
        basename: the basename of the recording.
        sources: the sources to use.
    Returns:
        An empty list or a list of string which contains the path to the files.
    """
    for files in sources.values():
        matching_files = [
            file_ for file_ in files
            if os.path.basename(file_).startswith(basename + '_')
        ]

        if len(matching_files):
            return matching_files

    return []


def main(
    xlsx: str,
    destination_path: str,
    anonymise: bool,
    parent_folder_as_name: str
):
    # Load config information
    try:
        configs = json.load(open(CONFIG_FILE))
    except FileNotFoundError:
        drives = win32api.GetLogicalDriveStrings()
        configs = {
            'data_sources': [
                drivestr for drivestr in drives.split('\000') if drivestr
            ],
        }
        print(
            'Generating "dataset_maker.config" file, please edit it '
            'to set the correct paths to the sources. \n'
            'You can find the configuration file here: {0}\n'.format(SCRIPT_PATH)

        )
        json.dump(configs, open(CONFIG_FILE, 'w'))
        sys.exit(1)

    # List all the files contained in the sources
    data_sources = configs['data_sources']

    print(
        '1 - Start listing files in [{0}]...'.format(', '.join(data_sources))
    )

    files_lists = []
    with mp.Pool() as pool:
        files_lists = pool.map(list_files, data_sources)

    # Only keep the .eeg files
    print('2 - Filter files (only keep .eeg files)...')
    eegs_lists = {}
    for source, files_list in zip(data_sources, files_lists):
        eegs_lists[source] = [
            file_ for file_ in files_list if file_.lower().endswith('.eeg')
        ]
    del files_lists

    print(
        'Found {0} file(s)'.format(
            sum([len(files_list) for files_list in eegs_lists.values()]),
        ),
    )

    # List the files to find and extract
    print('3 - Open the excel file containing the list of files to export...')
    xls = pd.ExcelFile(xlsx)
    df = pd.read_excel(xls, 'to_export')
    cols = list(df.columns)
    n_patients = df.shape[0]
    files_indexes = cols.index('Files')
    paths_indexes = cols.index('Paths')

    patient_dict = {}
    for patient_index in range(n_patients):
        patient_dict[patient_index] = {
            'destination_paths': [
                df[cols[index]][patient_index]
                for index in range(paths_indexes, files_indexes)
            ],
            'files': [
                df[cols[index]][patient_index]
                for index in range(files_indexes, len(cols))
            ],
        }

    # Research each file to extract
    print('4 - Find the emplacement of each original file...')
    original_destination = []
    for patient_index, patient_info in patient_dict.items():
        for file_index, file_ in enumerate(patient_info['files']):
            # If a file is specified, try to find it in the sources.
            # The first source specified in the config file is used firt, etc.
            if isinstance(file_, str):
                file_cluster = find_files(file_, eegs_lists)
                unique_names = {
                    os.path.basename(file_) for file_ in file_cluster
                }
                path_fragment = 'L{0}/EEG2'.format(file_[:4])

                if len(unique_names):
                    print(
                        (
                            'The recording "{0}" is '
                            'fragmented in {1} part(s).'
                        ).format(
                            file_,
                            len(unique_names),
                        ),
                    )

                else:
                    print('The recording "{0}" is missing.'.format(
                            file_,
                        ),
                    )

                for record_part in unique_names:
                    best_path = ''

                    for record_name in file_cluster:
                        if os.path.basename(record_name) == record_part:
                            if path_fragment in record_name.replace('\\', '/'):
                                best_path = record_name
                                break

                    if best_path == '':
                        for record_name in file_cluster:
                            if os.path.basename(record_name) == record_part:
                                best_path = record_name
                                break

                    destination = patient_info['destination_paths'][file_index]
                    if not isinstance(destination, str):
                        try:
                            destination = [
                                dest for dest
                                in patient_info['destination_paths']
                                if isinstance(
                                    patient_info['destination_paths']
                                )
                            ][-1]
                        except IndexError:
                            print('No destination path provided.')
                            destination = ''

                    if destination != '':
                        original_destination.append(
                            (
                                best_path,
                                os.path.join(
                                    destination_path,
                                    destination,
                                    record_part,
                                ),
                            ),
                        )
                    else:
                        original_destination.append(
                            (
                                best_path,
                                os.path.join(destination_path, record_part),
                            ),
                        )

    # Anonymise if required and transfert the file to the dataset path
    print('5 - Anonymise and export files to the dataset path...')

    def folder_name(path):
        return os.path.basename(os.path.dirname(path))

    number_of_files = len(original_destination)

    for file_index, recording_file in enumerate(original_destination, start=1):
        if parent_folder_as_name:
            field_name = folder_name(recording_file[1])
        else:
            field_name = ''

        print(
            'Current file ({0}/{1}):'.format(file_index, number_of_files),
            recording_file[0],
            '-->',
            recording_file[1],
        )

        anonymise_eeg(
            recording_file[0], recording_file[1], field_name=field_name,
        )


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(allow_abbrev=True)

    parser.add_argument(
        'xlsx',
        type=str,
        help='list of recordings to import',
    )

    parser.add_argument(
        'destination_path',
        type=str,
        help=(
            'destination of the dataset'
        ),
        default=None,
    )

    parser.add_argument(
        '-fn',
        '--parent_folder_as_name_field',
        action='store_true',
        help=(
            'if set, fill the name field with the name of the file\'s parent.'
            'folder.'
        ),
        default=False,
    )

    parser.add_argument(
        '-na',
        '--non_anonymised',
        action='store_true',
        help=(
            'if set, the dataset will not be anonymised.'
        ),
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

    print('The following arguments have been parsed:')
    for k, v in vars(args).items():
        print('{0}: {1}'.format(k, v))

    if not args.no:
        print()
        if not args.yes:
            try:
                while True:
                    conti = input('Do you want to run the program (yes/no)? ')
                    if conti.lower() in ('y', 'yes'):
                        break

                    elif conti.lower() in ('n', 'no'):
                        sys.exit()

            except KeyboardInterrupt:
                print(
                    '\nThe user requested the end of the program'
                    ' (KeyboardInterrupt).',
                )

                sys.exit()
    else:
        sys.exit()

    main(
        xlsx=args.xlsx,
        destination_path=args.destination_path,
        anonymise=(not args.non_anonymised),
        parent_folder_as_name=args.parent_folder_as_name_field,
    )
