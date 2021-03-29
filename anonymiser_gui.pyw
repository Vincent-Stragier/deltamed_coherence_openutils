r"""GUI allowing to anonymise .eeg files from Deltamed (coh3).

Compile the GUI:

pyinstaller.exe -F --clean  --add-data './data/;data'
-n "name" --windowed
--icon=ico/logo.ico .\gui_main.pyw
"""
import ctypes
import json
import multiprocessing as mp
import os
import sys
import traceback
import warnings

# pylint: disable=E0611
from PyQt5.QtCore import (
    pyqtSlot,
    Qt,
    QUrl,
    pyqtSignal,
    QThreadPool,
    QRunnable,
)
from PyQt5.QtGui import (
    QDesktopServices,
    QStandardItemModel,
    QIcon,
    QStandardItem,
)
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QMainWindow,
    QMessageBox,
    QFileDialog,
)

warnings.simplefilter("ignore", UserWarning)
sys.coinit_flags = 2

# Import Ui_MainWindow class from UiMainApp.py generated by uic module
from gui_anonymiser_main import Ui_MainWindow  # noqa: E402
from gui_anonymiser_settings import Ui_Settings_dialog  # noqa: E402
from utils import (  # noqa E402
    anonymise_eeg,
    convert_coh3_to_edf,
    ensure_path,
    list_files,
    resource_path,
)


def exe_path():
    """ Return the path of the executable or of the script. """
    if hasattr(sys, 'frozen'):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


SCRIPT_PATH = exe_path()
PREFERENCES_PATH = 'preferences.config'
PREFERENCES_PATH = os.path.join(SCRIPT_PATH, 'data', PREFERENCES_PATH)


# Worker class for the QThread handler
# https://stackoverflow.com/questions/50855210/how-to-pass-parameters-into-qrunnable-for-pyqt5
class Worker(QRunnable):  # pylint: disable=too-few-public-methods
    """Worker class to run a function in a QThread."""

    def __init__(self, function, *args, **kwargs):
        super().__init__()
        # Store constructor arguments (re-used for processing)
        self.function = function
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        """Run the function in the worker."""
        self.function(*self.args, **self.kwargs)


class MainApp(QMainWindow, Ui_MainWindow):
    """
    MainApp class inherit from QMainWindow and from
    Ui_MainWindow class in UiMainApp module.
    """
    progress_changed = pyqtSignal(int)
    progress_text_changed = pyqtSignal(str)
    progress_style_changed = pyqtSignal(str)
    state_changed = pyqtSignal(bool)
    ok_changed = pyqtSignal(bool)
    show_qmessagebox_exception = pyqtSignal(dict)

    def __init__(self):
        """Constructor or the initialiser."""
        QMainWindow.__init__(self)
        # It is imperative to call self.setupUi (self) to initialise the GUI
        # This is defined in gui_autogenerated_template.py file automatically
        self.setupUi(self)
        self.base_title = 'EEG (coh3) anonymiser and EDF converter'
        self.setWindowTitle(self.base_title)
        # Maximize the window
        # self.showMaximized()

        # Desactivate the buttons
        self.OK.setEnabled(False)
        self.Cancel.setEnabled(False)
        self.state_changed.connect(self.set_application_busy)
        self.cancel_process = mp.Queue(1)
        self.ok_changed.connect(self.OK.setEnabled)

        # Set editable line to read only.
        self.destination.setReadOnly(True)

        # Set progress bar and slots
        self.progress_bar.setValue(0)
        self.progress_changed.connect(self.progress_bar.setValue)
        self.progress_bar.setFormat('IDLE')
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_text_changed.connect(self.progress_bar.setFormat)
        self.progress_style_changed.connect(self.progress_bar.setStyleSheet)

        # Configure qmessagebox for exception via signals
        self.show_qmessagebox_exception.connect(self.show_critical_exception)

        # Set the slots
        self.path = ''
        self.executable_path = ''
        self.conversion_origin_path = ''
        self.load_preferences()
        if not os.path.isdir(self.path):
            self.path = ''
        if not os.path.isfile(self.executable_path):
            self.executable_path = ''
        self.save_preferences(
            path=self.path,
            executable_path=self.executable_path,
        )

        self.OK.clicked.connect(self.main_process)
        self.Cancel.clicked.connect(self.cancel)
        self.actionAbout.triggered.connect(self.show_about)
        self.actionOnline_documentation.triggered.connect(
            self.open_documentation
        )
        self.actionSelect_file_s.triggered.connect(self.select_files_browser)
        self.actionSelect_folder.triggered.connect(self.select_folder_browser)
        self.actionSettings.triggered.connect(
            self.show_settings,
        )
        self.tool_source.clicked.connect(self.select_files_browser)
        self.tool_destination.clicked.connect(
            self.select_destination_folder_browser,
        )
        self.name_check.stateChanged.connect(self.save_preferences)
        self.surname_check.stateChanged.connect(self.save_preferences)
        self.birthdate_check.stateChanged.connect(self.save_preferences)
        self.sex_check.stateChanged.connect(self.save_preferences)
        self.folder_check.stateChanged.connect(self.save_preferences)
        self.centre_check.stateChanged.connect(self.save_preferences)
        self.comment_check.stateChanged.connect(self.save_preferences)
        self.folder_as_name_check.stateChanged.connect(self.save_preferences)
        self.anonymise_check.stateChanged.connect(self.save_preferences)
        self.convert_check.stateChanged.connect(self.save_preferences)

        # List View
        self.source_list_model = QStandardItemModel()
        self.source.setModel(self.source_list_model)
        self.source.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Create a QThread to avoid to hang the main process
        self.threadpool = QThreadPool()
        self.files = []

    def keyPressEvent(self, event):  # pylint: disable=C0103
        """Intercept the key events.

        Args:
            self: self.
            event: the intercepted event.
        """
        # Close the program
        if event.key() == Qt.Key_Escape:
            self.close()

        # Maximize the window
        if event.key() == Qt.Key_F11:
            if self.isMaximized():
                self.showNormal()
            else:
                self.showMaximized()

    def set_application_busy(self, state=False):
        """ Enable and disable elements. """
        self.Cancel.setEnabled(state)
        self.OK.setEnabled(not state)
        self.fields.setEnabled(not state)
        self.Source_box.setEnabled(not state)
        self.Destination_box.setEnabled(not state)

    def main_process(self):
        """ Start a job to run the main process. """
        if self.destination.text() == self.path:
            result = self.show_overwrite_warning()
            if result != QMessageBox.Yes:
                return

        worker = Worker(self._main_process)
        self.threadpool.start(worker)

    def _main_process(self):
        # Enable Cancel and disable the interfaces.
        self.state_changed.emit(True)
        self.progress_bar.setStyleSheet('')  # Reset stylesheet to default

        if self.anonymise_check.checkState():
            # Only anonymise if all is anonymise
            # or the some fields are selected.
            self.anonymise()
            self.conversion_origin_path = self.destination.text()

        else:
            self.conversion_origin_path = self.path

        if self.convert_check.checkState():
            self.convert()

        # Disable Cancel and enable the interfaces.
        self.state_changed.emit(False)

    def anonymise(self):
        # if self.
        name_check = self.name_check.isChecked()
        folder_as_name_check = self.folder_as_name_check.isChecked()

        anonymise_ = self.anonymise_check.checkState() == 2
        name = '' if name_check or anonymise_ else None
        surname = '' if self.surname_check.isChecked() or anonymise_ else None
        birthdate = (
            '' if self.birthdate_check.isChecked() or anonymise_ else None
        )
        sex = '' if self.sex_check.isChecked() or anonymise_ else None
        folder = '' if self.folder_check.isChecked() or anonymise_ else None
        centre = '' if self.centre_check.isChecked() or anonymise_ else None
        comment = '' if self.comment_check.isChecked() or anonymise_ else None

        destination_path = self.destination.text()

        n_files = len(self.files)
        destination_files = []

        # Process the files
        for file_index, file_ in enumerate(self.files, start=1):

            # Stop the operation if the cancel flag is set.
            if not self.cancel_process.empty():
                if self.cancel_process.get():
                    self.progress_changed.emit(0)
                    break

            file_destination = os.path.realpath(
                os.path.join(
                    destination_path,
                    os.path.relpath(
                        file_,
                        self.path,
                    ),
                ),
            )
            destination_files.append(file_destination)

            if (
                (folder_as_name_check and name_check)
                or (folder_as_name_check and anonymise_)
            ):
                name = os.path.basename(os.path.dirname(file_destination))

            self.progress_text_changed.emit(
                'Anonymise: {0} ({1}/{2})'.format(file_, file_index, n_files)
            )

            try:
                anonymise_eeg(
                    file_,
                    file_destination,
                    field_name=name,
                    field_surname=surname,
                    field_birthdate=birthdate,
                    field_sex=sex,
                    field_folder=folder,
                    field_centre=centre,
                    field_comment=comment,
                )
            except OSError as exception_message:
                self.progress_style_changed.emit(
                    'QProgressBar::chunk {background-color: red;}'
                )

                self.show_qmessagebox_exception.emit(
                    {
                        'title': (
                            'An OSError occured during '
                            'the anonymisation process'
                        ),
                        'text': 'OSError: {0}'.format(exception_message),
                        'detailed_text': traceback.format_exc(),
                    }
                )
                break

            self.progress_changed.emit(int(file_index * 100 / n_files))
        self.files = destination_files
        self.progress_text_changed.emit(
            '{0} ({1}/{2})'.format('IDLE', file_index, n_files)
        )

    def convert(self):
        """ Convert .eeg to .EDF files. """
        destination_path = self.destination.text()
        n_files = len(self.files)

        # Process the files
        for file_index, file_ in enumerate(self.files, start=1):

            # Stop the operation if the cancel flag is set.
            if not self.cancel_process.empty():
                if self.cancel_process.get():
                    self.progress_changed.emit(0)
                    break

            file_destination = os.path.realpath(
                os.path.join(
                    destination_path,
                    os.path.relpath(
                        '{0}.edf'.format(file_[:-4]),
                        self.conversion_origin_path,
                    ),
                ),
            )

            self.progress_text_changed.emit(
                'Convert: {0} ({1}/{2})'.format(file_, file_index, n_files)
            )

            try:
                convert_coh3_to_edf(
                    self.executable_path,
                    file_,
                    file_destination,
                )
            except OSError as exception_message:
                self.progress_style_changed.emit(
                    'QProgressBar::chunk {background-color: red;}'
                )

                self.show_qmessagebox_exception.emit(
                    {
                        'title': (
                            'An OSError occured during '
                            'the conversion process'
                        ),
                        'text': 'OSError: {0}'.format(exception_message),
                        'detailed_text': traceback.format_exc(),
                    }
                )
                break

            self.progress_changed.emit(int(file_index * 100 / n_files))
        self.progress_text_changed.emit(
            '{0} ({1}/{2})'.format('IDLE', file_index, n_files)
        )

    def cancel(self):
        """ Send a signal to the anonymisation process to stop it. """
        # Set cancel flag
        if self.cancel_process.empty():
            self.cancel_process.put(True)

    def open_documentation(self):
        """Open program documentation."""
        url = QUrl(
            'https://github.com/2010019970909/'
            'deltamed_coherence_openutils/wiki/Anonymiser-GUI'
        )
        QDesktopServices.openUrl(url)

    def show_about(self):
        """Show the about me."""
        msg = QMessageBox()
        msg.setWindowTitle('About')
        msg.setText(
            'This program has been programmed by Vincent Stragier.\n\n'
            'It has been created to anonymise .eeg (coh3) '
            'files from Deltamed (a Natus company).\n\n'
            'The program (PyQt5 GUI) is under a GNU GPL and its '
            'source code is in part under a '
            'Creative Commons licence.'
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def show_overwrite_warning(self):
        """Show the overwrite warning."""
        msg = QMessageBox()
        msg.setWindowTitle('Overwriting Warning')
        msg.setIcon(QMessageBox.Warning)
        msg.setText(
            'The source path and the destination path are the same. '
            'You are going to overwrite the file(s).\n\n'
            'Do you want to continue and process the file(s) inplace?'
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        return msg.exec_()

    def show_critical_exception(self, parameters):
        """Show generic error."""
        msg = QMessageBox()
        msg.setWindowTitle(parameters.get('title', 'Unexpected error'))
        msg.setIcon(QMessageBox.Critical)

        text = parameters.get('text', None)
        detailed_text = parameters.get('detailed_text', None)
        if text is not None:
            msg.setText(text)
        if detailed_text is not None:
            msg.setDetailedText(detailed_text)
        msg.setStandardButtons(QMessageBox.Ok)
        return msg.exec_()

    def select_files_browser(self):
        """Show the files browser."""
        dialog = QFileDialog(self)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setDirectory(self.path)
        dialog.setFileMode(QFileDialog.ExistingFiles)
        # Filetype:
        # http://justsolve.archiveteam.org/wiki/NII
        # https://stackoverflow.com/a/27994762
        filters = ["Deltamed EEG files (*.eeg)", "All Files (*)"]
        dialog.setNameFilters(filters)
        dialog.selectNameFilter(filters[0])
        dialog.setOption(QFileDialog.ShowDirsOnly, False)
        dialog.setViewMode(QFileDialog.Detail)

        if dialog.exec_() == QFileDialog.Accepted:
            self.files = [
                os.path.realpath(file_) for file_ in dialog.selectedFiles()
            ]
            filenames = sorted([
                '{0}'.format(os.path.basename(file_)) for file_ in self.files
            ])

            self.source_list_model.clear()
            for filename in filenames:
                item = QStandardItem()
                item.setText(filename)
                item.setIcon(QIcon(resource_path('ico/file.svg')))
                self.source_list_model.appendRow(item)

            self.OK.setEnabled(True)
            self.path = os.path.dirname(self.files[0])
            self.save_preferences(self.path)
            self.progress_bar.setValue(0)
            if self.destination.text() == '':
                self.destination.setText(self.path)

    def select_folder_browser(self):
        """Show the files browser."""
        dialog = QFileDialog(self)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setDirectory(self.path)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setViewMode(QFileDialog.Detail)

        if dialog.exec_() == QFileDialog.Accepted:
            folder = dialog.selectedFiles()[0]

            self.files = sorted(
                [
                    os.path.realpath(eeg) for eeg in list_files(folder)
                    if eeg.lower().endswith('.eeg')
                ],
                key=os.path.basename,
            )

            if self.files:
                self.source_list_model.clear()
                item = QStandardItem()
                item.setText(folder)
                item.setIcon(QIcon(resource_path('ico/folder.svg')))
                self.source_list_model.appendRow(item)

                self.path = folder
                self.save_preferences(self.path)
                self.progress_bar.setValue(0)
                if self.destination.text() == '':
                    self.destination.setText(self.path)

                self.OK.setEnabled(True)
            else:
                self.show_qmessagebox_exception.emit(
                    {
                        'title': (
                            'No .eeg files detected in the selected folder.'
                        ),
                        'text': (
                            'No .eeg files have been detected in the selected'
                            ' folder. Please select another folder.'
                        ),
                    }
                )

    def show_settings(self):
        dialog = SettingsWindow(self, self.executable_path)
        if dialog.exec_() == dialog.Accepted:
            self.save_preferences(
                path=self.path, executable_path=dialog.path_to_executable,
            )

    def select_destination_folder_browser(self):
        """Show the files browser to select the destination."""
        dialog = QFileDialog(self)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setDirectory(self.path)
        dialog.setFileMode(QFileDialog.Directory)

        if dialog.exec_() == QFileDialog.Accepted:
            folder = dialog.selectedFiles()[0]
            self.destination.setText(folder)

    def load_preferences(self):
        """ Load the saved preferences from file. """
        try:
            preferences = json.load(open(resource_path(PREFERENCES_PATH)))

            self.name_check.setChecked(preferences.get('name_check', True))
            self.surname_check.setChecked(
                preferences.get('surname_check', True),
            )
            self.birthdate_check.setChecked(
                preferences.get('birthdate_check', True),
            )
            self.sex_check.setChecked(preferences.get('sex_check', True))
            self.folder_check.setChecked(preferences.get('folder_check', True))
            self.centre_check.setChecked(preferences.get('centre_check', True))
            self.comment_check.setChecked(
                preferences.get('comment_check', True),
            )
            self.anonymise_check.setCheckState(
                preferences.get('anonymise_check', True),
            )

            self.convert_check.setChecked(
                preferences.get('convert_check', True),
            )
            self.folder_as_name_check.setChecked(
                preferences.get('folder_as_name_check', False)
            )
            self.path = preferences.get('path', '')
            self.executable_path = preferences.get(
                'executable_path', 'coh3toEDF.exe',
            )

        except (
            FileNotFoundError,
            json.decoder.JSONDecodeError,
        ):
            self.save_preferences(
                path=exe_path(),
                executable_path=os.path.join(exe_path(), 'coh3toEDF.exe'),
            )

    def save_preferences(self, path: str = None, executable_path: str = None):
        """ Save the application current states. """
        preferences = {
            'name_check': self.name_check.isChecked(),
            'surname_check': self.surname_check.isChecked(),
            'birthdate_check': self.birthdate_check.isChecked(),
            'sex_check': self.sex_check.isChecked(),
            'folder_check': self.folder_check.isChecked(),
            'centre_check': self.centre_check.isChecked(),
            'comment_check': self.comment_check.isChecked(),
            'folder_as_name_check': self.folder_as_name_check.isChecked(),
            'anonymise_check': self.anonymise_check.checkState(),
            'convert_check': self.convert_check.isChecked(),
        }

        if isinstance(path, str) and os.path.isdir(path):
            preferences['path'] = path
        else:
            preferences['path'] = self.path

        if (
            isinstance(executable_path, str)
            and os.path.isfile(executable_path)
        ):
            preferences['executable_path'] = executable_path
            self.executable_path = executable_path
        else:
            preferences['executable_path'] = self.executable_path

        # Disable the fields when nothing or all is anonymised
        for checkbox in (
            self.name_check,
            self.surname_check,
            self.birthdate_check,
            self.sex_check,
            self.centre_check,
            self.folder_check,
            self.comment_check,
        ):
            checkbox.setEnabled(
                not self.anonymise_check.checkState() in (0, 2),
            )

        if self.anonymise_check.checkState() == 2:
            self.folder_as_name_check.setEnabled(True)
        elif self.anonymise_check.checkState() == 0:
            self.folder_as_name_check.setEnabled(False)
        else:
            self.folder_as_name_check.setEnabled(self.name_check.isChecked())

        ensure_path(os.path.dirname(PREFERENCES_PATH))
        json.dump(preferences, open(PREFERENCES_PATH, 'w'))


class SettingsWindow(QDialog):
    """Settings dialog."""
    def __init__(self, parent=None, path_to_executable=''):
        super().__init__(parent)
        # Create an instance of the GUI
        self.ui = Ui_Settings_dialog()
        # Run the .setupUi() method to show the GUI
        self.ui.setupUi(self)
        self.setWindowTitle('Settings')

        # Connect signals
        self.ui.toolButton.clicked.connect(self.select_coh3toedf_path)
        self.ui.lineEdit.textEdited.connect(self.save_change)
        # self.ui.accept.clicked.connect(self.check)

        # Initialise the GUI text
        self.path_to_executable = path_to_executable
        self.ui.lineEdit.setText(self.path_to_executable)

    def accept(self):
        """Overwrite the accept() method, to validate the settings changes."""
        if (
            os.path.exists(self.path_to_executable)
            and self.path_to_executable.lower().endswith('.exe')
        ):
            super().accept()
        else:
            self.show_error_message()

    def select_coh3toedf_path(self):
        """Show the the file browser to select the path to coh3toEDF.exe"""
        dialog = QFileDialog(self)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)

        if os.path.isfile(self.path_to_executable):
            dialog.setDirectory(os.path.dirname(self.path_to_executable))
        elif os.path.isdir(self.path_to_executable):
            dialog.setDirectory(self.path_to_executable)

        dialog.setFileMode(QFileDialog.ExistingFile)
        filters = ["Executable (*.exe)", "All Files (*)"]
        dialog.setNameFilters(filters)
        dialog.selectNameFilter(filters[0])
        dialog.setOption(QFileDialog.ShowDirsOnly, False)
        dialog.setViewMode(QFileDialog.Detail)

        if dialog.exec_() == QFileDialog.Accepted:
            self.path_to_executable = dialog.selectedFiles()[0]
            self.ui.lineEdit.setText(self.path_to_executable)

    def save_change(self):
        """ Update the edited text. """
        self.path_to_executable = self.ui.lineEdit.text()

    def show_error_message(self):
        """ Show a warning about the range of the parameter. """
        msg = QMessageBox()
        msg.setWindowTitle('Unvalid file path')
        msg.setIcon(QMessageBox.Warning)
        msg.setText(
            'Please select an existing .exe file.'
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()


if __name__ == '__main__':
    # For Windows set AppID to add an Icon in the taskbar
    # https://stackoverflow.com/questions/1551605/how-to-set-applications-taskbar-icon-in-windows-7
    if sys.platform == 'win32':
        from ctypes import wintypes

        APPID = u'vincent_stragier.cetic.v1.0.0'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APPID)

        lp_buffer = wintypes.LPWSTR()
        ctypes.windll.shell32.GetCurrentProcessExplicitAppUserModelID(
            ctypes.cast(ctypes.byref(lp_buffer), wintypes.LPWSTR))
        # appid = lp_buffer.value
        ctypes.windll.kernel32.LocalFree(lp_buffer)

    app = QApplication(sys.argv)
    # Launch the main app.
    MyApplication = MainApp()
    MyApplication.show()  # Show the form
    # os.path.join(os.path.dirname(sys.argv[0]),'..', 'ico', 'fpms.svg')
    icon_path = resource_path('ico/fpms_anonymous.ico')
    app.setWindowIcon(QIcon(icon_path))
    MyApplication.setWindowIcon(QIcon(icon_path))
    sys.exit(app.exec_())  # Execute the app
