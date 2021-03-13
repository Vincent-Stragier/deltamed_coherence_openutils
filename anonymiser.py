r""" The aim of this script is to anonymise every .eeg in a tree of folders.

Usage:
    .\python-3.8.8-embed-win32\python.exe .\anonymiser.py \
    .\dataset -dp .\dataset_anonym -y
"""
import os
import traceback

from utils import (
    anonymise_eeg_verbose,
    display_arguments,
    handle_yes_no,
    list_files,
)


def main(path: str, destination_path: str, use_folder_as_name: bool = True):
    """Main process.

    Args:
        path: path to the dataset.
        destination_path: destination path to the anonymised dataset.
        If not set, the files will be overwritten.
        use_folder_as_name: fill the name field with the name of the parent
        folder.
    """
    files_in_dataset = [
        eeg for eeg in list_files(path) if eeg.lower().endswith('.eeg')
    ]

    def folder_name(path):
        return os.path.basename(os.path.dirname(path))

    number_of_files = len(files_in_dataset)

    for file_index, file_ in enumerate(sorted(files_in_dataset), start=1):
        # Set name as the parent folder's name or as an empty field
        if use_folder_as_name:
            field_name = folder_name(file_)
        else:
            field_name = ''

        # Destination file path
        if destination_path is None:
            file_path = file_
        else:
            file_path = os.path.join(
                destination_path,
                os.path.relpath(file_, path)
            )

        print(
            '\nCurrent file ({0}/{1}):'.format(file_index, number_of_files),
            file_,
            '-->',
            file_path,
        )

        try:
            anonymise_eeg_verbose(
                file_, file_path, field_name=field_name, verbose=True
            )
        except MemoryError:
            print('MemoryError: retry...')
            try:
                anonymise_eeg_verbose(
                    file_, file_path, field_name=field_name, verbose=True
                )
            except MemoryError:
                print('MemoryError: not able to process the file')
                traceback.print_exc()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(allow_abbrev=True)

    parser.add_argument(
        'path',
        type=str,
        help='path to the dataset to anonymise',
    )

    parser.add_argument(
        '-dp',
        '--destination_path',
        type=str,
        help=(
            'destination of the anonymised dataset (if not set, the dataset '
            'will be overwritten)'
        ),
        default=None,
    )

    parser.add_argument(
        '-fn',
        '--parent_folder_as_name_field',
        action='store_true',
        help=(
            'if set, fill the name field with the name of the file\'s parent '
            'folder.'
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
        path=args.path,
        use_folder_as_name=args.parent_folder_as_name_field,
        destination_path=args.destination_path,
    )
