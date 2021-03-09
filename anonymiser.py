r""" The aim of this script is to anonymise every .eeg in a tree of folders.

Usage:
    .\python-3.8.8-embed-win32\python.exe .\anonymiser.py .\dataset -dp .\dataset_anonym -y
"""
import os
import shutil
import sys
import traceback


def list_files(path:str):
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


def extract_header(filename:str):
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


def display_fields(filename:str):
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
    array, start:int, stop:int, content:list, filler:bytes=b'\x00'
):
    for index in range(start, stop):
        if index - start < len(content):
            array[index] = content[index - start]
        else:
            array[index] = filler
    
    return stop - start >= len(content)


def anonymise_eeg(
    original_file:str,
    destination_file:str,
    field_name:str='',
    field_surname:str='',
    field_birthdate:str='',
    field_sex:str='',
    field_folder:str='',
    field_centre:str='',
    field_comment:str='',
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

    content = (char if isinstance(char, bytes) else bytes([char]) for char in content)
    
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


def main(path:str, destination_path:str, use_folder_as_name:bool=True):
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
    folder_name = lambda path : os.path.basename(os.path.dirname(path))
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
            anonymise_eeg(file_, file_path, field_name=field_name, verbose=True)
        except MemoryError:
            print('MemoryError: retry...')
            try:
                anonymise_eeg(file_, file_path, field_name=field_name, verbose=True)
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
        path=args.path,
        use_folder_as_name=args.parent_folder_as_name_field,
        destination_path=args.destination_path,
    )
