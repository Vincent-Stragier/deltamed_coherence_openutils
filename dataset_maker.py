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
import sys

import pandas as pd
import win32api
from utils import (
    anonymise_eeg,
    display_arguments,
    find_files,
    handle_yes_no,
    list_files,
)


def exe_path():
    """ Return the path of the executable or of the script. """
    if hasattr(sys, 'frozen'):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


SCRIPT_PATH = exe_path()
CONFIG_FILE = 'dataset_maker.config'
CONFIG_FILE = os.path.join(SCRIPT_PATH, CONFIG_FILE)


def main(
    xlsx: str,
    destination_path: str,
    anonymise: bool,
    parent_folder_as_name: str
):
    """ Run the main tasks. """
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
            'You can find the configuration file here: {0}\n'.format(
                SCRIPT_PATH
            ),
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
    sheet = pd.read_excel(pd.ExcelFile(xlsx), 'to_export')
    cols = list(sheet.columns)
    files_indexes = cols.index('Files')

    patient_dict = {}
    # Go through the number of patient
    for patient_index in range(sheet.shape[0]):
        patient_dict[patient_index] = {
            'destination_paths': [
                sheet[cols[index]][patient_index]
                for index in range(cols.index('Paths'), files_indexes)
            ],
            'files': [
                sheet[cols[index]][patient_index]
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

                if unique_names:
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

        if anonymise:
            anonymise_eeg(
                recording_file[0], recording_file[1], field_name=field_name,
            )
        else:  # Do not anonymise
            anonymise_eeg(
                recording_file[0],
                recording_file[1],
                field_name=None,
                field_surname=None,
                field_birthdate=None,
                field_sex=None,
                field_folder=None,
                field_centre=None,
                field_comment=None,
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
    display_arguments(args)
    handle_yes_no(args)

    main(
        xlsx=args.xlsx,
        destination_path=args.destination_path,
        anonymise=(not args.non_anonymised),
        parent_folder_as_name=args.parent_folder_as_name_field,
    )
