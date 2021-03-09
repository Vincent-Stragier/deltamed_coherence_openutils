# comtypes==1.1.7 pywinauto pywin32==224
import json
import os
import time

import pywinauto
from pywinauto.application import Application


CONFIG_FILE = 'coh3toEDF.config'
EXECUTABLE_PATH = json.load(open(CONFIG_FILE))['path_to_executable']


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


def convert_coh3_to_EDF(
    eeg_path:str,
    edf_path:str = None,
    executable_path:str = EXECUTABLE_PATH,
):
    """ Convert Coherence 3 (.eeg) to EDF file format.

    Args:
        eeg_path: path to the eeg file to convert.
        edf_path: 
        executable_path: 
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
        import traceback
        traceback.print_exc()
        
        # Only use one instance at a time
        os.system(
            "taskkill /f /im {0}".format(
                os.path.basename(executable_path),
            ),
        )

        convert_coh3_to_EDF(eeg_path, edf_path, executable_path)

    # If the windows if not found, relaunch the program
    except pywinauto.findwindows.ElementNotFoundError:
        import traceback
        traceback.print_exc()

        convert_coh3_to_EDF(eeg_path, edf_path, executable_path)


def main(
    path_to_executable:str,
    original_path:str,
    destination_path:str = None,
    overwrite: bool = False,
):
    """ Run batch conversion process.

    Args:
        path_to_executable: path to the converter executable.
        original_path: path to the dataset to convert.
        destination_path: destination path.
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
        print(
            '({0}/{1}) Convert "{2}" to "{3}.EDF"'.format(
                index,
                n_files,
                file_,
                file_[:-4],
            ),
        )

        if os.path.isfile(file_[:-4] + ".EDF") and not overwrite:
            print('File has already been converted.')
        else:
            if os.path.isfile(file_[:-4] + ".EDF"):
                print('File has already been converted (will be overwrited).')
            convert_coh3_to_EDF(
                eeg_path=file_,
                edf_path=None,
                executable_path=EXECUTABLE_PATH,
            )


if __name__ == '__main__':
    # Load config information
    configs = json.load(open(CONFIG_FILE))

    # List all the files contained in the sources
    path_to_executable = configs['path_to_executable']

    original_path = 'F:/dataset/'
    destination_path = 'F:/dataset/'
    main(path_to_executable, original_path, destination_path, overwrite=False)
