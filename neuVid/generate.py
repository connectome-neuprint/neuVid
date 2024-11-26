from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from PySide6.QtWidgets import QFileDialog, QInputDialog, QLabel, QMenuBar, QMenu, QMessageBox, QPushButton, QTextEdit, QSplitter
from PySide6.QtGui import QAction
from PySide6.QtCore import QObject, QRunnable, QSettings, Qt, QThreadPool, QTimer, Signal, Slot

import datetime
import os
import platform
import sys
import tempfile
import textwrap

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from gen import generate, generate_single_step, get_raw_training_doc
from utilsGeneral import report_version

class Worker(QRunnable):
    # Only a subclass of QObject can have signals.  QRunnable is not such a subclass,
    # so it uses an instance of this class to send its signal.
    class Signaler(QObject):
        finished = Signal(dict)
                      
    def __init__(self, raw_doc, previous_result, user_request, api_key, models, temperature, step_count):
        super().__init__()
        self.raw_doc = raw_doc
        self.previous_result = previous_result
        self.user_request = user_request
        self.api_key = api_key
        self.models = models
        self.temperature = temperature
        self.step_count = step_count
        self.signaler = Worker.Signaler()

    def run(self):
        if self.step_count == 1:
            result = generate_single_step(self.raw_doc, self.previous_result, self.user_request, 
                                          self.api_key, self.models, self.temperature)
        else:
            result = generate(self.raw_doc, self.previous_result, self.user_request, 
                              self.api_key, self.models, self.temperature)

        self.signaler.finished.emit(result)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.version = report_version()
        self.setWindowTitle(self.tr("neuVid Generate"))

        if platform.system() == "Darwin":
            # For macOS, to make settings be stored in /Users/<user>/Library/Preferences/org.janelia.neuVid.plist
            self.settings = QSettings(QSettings.UserScope, "janelia.org", "neuVid")
        else:
            self.settings = QSettings(QSettings.UserScope, "Janelia", "neuVid")

        '''
        # For debugging, to force empty settings:
        self.settings.clear()
        self.settings.sync()
        '''

        model = self.get_model_setting()
        self.models = [model, model, model]
        self.temperature = 0

        self.setup_window()
        self.setup_menus()
        self.setup_results()
        self.setup_status()
        self.setup_input()
        self.set_model()
        self.set_api_key()
        self.set_step_count()

        raw_doc_data = get_raw_training_doc()
        if not raw_doc_data["ok"]:
            QMessageBox.critical(self, self.tr("Error"), raw_doc_data["error"])
            sys.exit()

        self.raw_doc = raw_doc_data["text"]
        self.raw_doc_version = raw_doc_data["version"]
        self.raw_doc_source = raw_doc_data["source"]

        self.cumulative_cost = 0

        self.setup_logging()
        self.setup_undo_redo()

    def setup_window(self):
        main = QSplitter(self)
        main.setOrientation(Qt.Vertical)
        main.setChildrenCollapsible(False)
        self.setCentralWidget(main)

        top = QWidget(main)
        self.top = QVBoxLayout()
        top.setLayout(self.top)
        main.addWidget(top)

        bottom = QWidget(main)
        self.bottom = QVBoxLayout()
        bottom.setLayout(self.bottom)
        main.addWidget(bottom)

        h = 500
        w = 1.618 * h
        self.resize(w, h)
        main.setSizes([round(2/3 * h), round(1/3 * h)])

    def setup_results(self):
        self.result_textedit = QTextEdit()
        self.result_textedit.setAcceptRichText(False)
        self.result_textedit.textChanged.connect(self.result_text_changed)
        self.top.addWidget(self.result_textedit)

        h = QHBoxLayout()

        self.open_button = QPushButton(self.tr("Open..."))
        self.open_button.clicked.connect(self.open_button_clicked)
        h.addWidget(self.open_button)

        self.save_button = QPushButton(self.tr("Save..."))
        self.save_button.clicked.connect(self.save_button_clicked)
        self.save_button.setEnabled(False)
        h.addWidget(self.save_button)

        self.undo_button = QPushButton(self.tr("Undo"))
        self.undo_button.clicked.connect(self.undo_button_clicked)
        h.addWidget(self.undo_button)

        self.redo_button = QPushButton(self.tr("Redo"))
        self.redo_button.clicked.connect(self.redo_button_clicked)
        h.addWidget(self.redo_button)

        self.top.addLayout(h)

    def setup_status(self):
        h = QHBoxLayout()

        self.status_label = QLabel()
        self.status_label.setText(self.tr("Ready"))
        h.addWidget(self.status_label)

        self.stats_label = QLabel()
        self.stats_label.setAlignment(Qt.AlignRight)
        h.addWidget(self.stats_label)

        self.top.addLayout(h)

    def setup_input(self):
        self.input_textedit = QTextEdit()
        self.input_textedit.setAcceptRichText(False)
        self.input_textedit.textChanged.connect(self.input_text_changed)
        self.input_textedit.setPlaceholderText(self.tr("Describe your video."))
        self.bottom.addWidget(self.input_textedit)

        h = QHBoxLayout()

        self.generate_button = QPushButton(self.tr("Generate"))
        self.generate_button.clicked.connect(self.generate_button_clicked)
        self.generate_button.setEnabled(False)
        h.addWidget(self.generate_button)

        self.clear_input_button = QPushButton(self.tr("Clear"))
        self.clear_input_button.clicked.connect(self.clear_input_button_clicked)
        self.clear_input_button.setEnabled(False)
        h.addWidget(self.clear_input_button)

        h.setStretch(0, 3)
        h.setStretch(1, 1)

        self.bottom.addLayout(h)

        self.input_textedit.setFocus()

    def setup_menus(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        file_menu = QMenu(self.tr("&File"), self)
        menu_bar.addMenu(file_menu)

        if platform.system() != "Darwin":
            self.quit_action = QAction(self.tr("&Quit"), self)
            self.quit_action.triggered.connect(self.close)
            file_menu.addAction(self.quit_action)

        settings_menu = QMenu(self.tr("&Settings"), self)
        menu_bar.addMenu(settings_menu)

        self.set_model_action = QAction(self.tr("Model..."), self)
        self.set_model_action.triggered.connect(self.force_model)
        settings_menu.addAction(self.set_model_action)

        self.set_api_key_action = QAction(self.tr("API key..."), self)
        self.set_api_key_action.triggered.connect(self.force_api_key)
        settings_menu.addAction(self.set_api_key_action)

        self.show_log_file_action = QAction(self.tr("Log file..."), self)
        self.show_log_file_action.triggered.connect(self.show_log_file)
        settings_menu.addAction(self.show_log_file_action)

        self.step_count_action = QAction(self.tr("Single vs. multiple steps..."), self)
        self.step_count_action.triggered.connect(self.force_step_count)
        settings_menu.addAction(self.step_count_action)

        if platform.system() == "Darwin":
            # This unusual pattern, with empty strings for names and the QAction.AboutRole,
            # is necessary for putting the "About" item in the application menu
            app_menu = QMenu("")
            menu_bar.addMenu(app_menu)
            self.about_action = QAction("")
            self.about_action.setMenuRole(QAction.AboutRole)
            self.about_action.triggered.connect(self.about)
            app_menu.addAction(self.about_action)
        else:
            # On Linux VS Code, there is a "Help" menu with and "About" item, so follow that pattern.
            help_menu = QMenu("Help")
            menu_bar.addMenu(help_menu)
            self.about_action = QAction("About")
            self.about_action.triggered.connect(self.about)
            help_menu.addAction(self.about_action)

    def setup_logging(self):
        self.log_file = ""
        try:
            log_dir = os.getenv("NEUVID_GENERATE_LOG_DIR") or ""
            if not log_dir:
                log_base = self.temp_dir()
                if os.path.exists(log_base) and os.path.isdir(log_base):
                    log_dir = os.path.join(log_base, "neuVid-generate")
                    if not os.path.exists(log_dir):
                        os.mkdir(log_dir)
            if os.access(log_dir, os.W_OK):
                timestamp = str(self.now()).replace(":", "-").replace(" ", "_")
                name = f"neuVid-generate-log-{timestamp}.txt"
                self.log_file = os.path.join(log_dir, name)

                header = f"neuVid version: {self.version}\n"
                header += f"Training source: {self.raw_doc_source}\n"
                header += f"Training version: {self.raw_doc_version}\n"
                header += f"Step 1 model (initial): {self.models[0]}\n"
                header += f"Step 2 model (initial): {self.models[1]}\n"
                header += f"Step 3 model (initial): {self.models[2]}\n"
                header += f"Temperature: {self.temperature}\n"
                header += "\n"

                print(f"Log file: {self.log_file}")
                with open(self.log_file, "w") as f:
                    f.write(header)
            else:
                raise Exception(f"Cannot access log directory {log_dir}")
        except Exception as e:
            msg = f"Logging disabled due to error: {str(e)}"
            QMessageBox.critical(self, self.tr("Error"), self.tr(msg))
            self.log_file = ""

    def setup_undo_redo(self):
        self.results = [""]
        self.current_result = 0
        self.set_undo_redo_enabled()

    def set_undo_redo_enabled(self):
        self.undo_button.setEnabled(len(self.results) > 1 and self.current_result > 0)
        self.redo_button.setEnabled(len(self.results) > 1 and self.current_result < len(self.results) - 1)

    @Slot()
    def about(self):
        text = f"neuVid version: {self.version}\n"
        if self.raw_doc_version:
            text += f"Training documentation version: {self.raw_doc_version}"
        QMessageBox.about(self, "About neuVid Generate", text)   

    def get_vendor(self):
        model = self.models[0]
        if model.startswith("gpt"):
            return "OpenAI"
        elif model.startswith("claude"):
            return "Anthropic"
        else:
            return None
        
    def get_vendor_token_keys(self):
        vendor = self.get_vendor()
        if vendor == "OpenAI":
            input_tokens_key = "prompt_tokens"
            output_tokens_key = "completion_tokens"
        elif vendor == "Anthropic":
            input_tokens_key = "input_tokens"
            output_tokens_key = "output_tokens"
        else:
            input_tokens_key = None
            output_tokens_key = None
        return (input_tokens_key, output_tokens_key)
        
    def get_model_setting(self):
        KEY = "MODEL"
        result = "claude-3-opus-20240229"
        if self.settings.contains(KEY):
            result = self.settings.value(KEY)
        return result

    @Slot()
    def force_model(self):
        self.set_model(force=True)

    def set_model(self, force=False):
        KEY = "MODEL"
        model = self.settings.value(KEY)

        if model and not force:
            self.models = [model, model, model]
        else:
            if not model:
                model = "claude-3-opus-20240229"
            text, ok = QInputDialog.getText(self, "Model", "Name of model to use for neuVid Generate", text=model)
            if ok and text:
                model = text
                self.models = [model, model, model]
                self.settings.setValue(KEY, model)
                path = self.settings.fileName()
                QMessageBox.information(self, "Model", f"The model name is stored in {path}")

    @Slot()
    def force_api_key(self):
        self.set_api_key(force=True)

    def set_api_key(self, force=False):
        vendor = self.get_vendor()
        KEY = "OPENAI_API_KEY" if vendor == "OpenAI" else "ANTHROPIC_API_KEY"
        self.api_key = self.settings.value(KEY).strip()
        if not self.api_key or force:
            self.api_key = os.getenv(KEY)
            if not self.api_key or force:
                text, ok = QInputDialog.getText(self, f"{vendor} API Key", f"{vendor} API key for neuVid Generate")
                if ok and text:
                    self.api_key = text
                    self.settings.setValue(KEY, self.api_key)
                    path = self.settings.fileName()
                    QMessageBox.information(self, f"{vendor} API Key", f"The {vendor} API key is stored in {path}")

    @Slot()
    def show_log_file(self):
        if self.log_file:
            msg = f"Log file: {self.log_file}"
        else:
            msg = "Logging is disabled"
        QMessageBox.information(self, self.tr("Log file"), self.tr(msg))

    @Slot()
    def force_step_count(self):
        self.set_step_count(force=True)

    def set_step_count(self, force=False):
        KEY = "STEP_COUNT"
        self.step_count = self.settings.value(KEY)
        if not self.step_count:
            self.step_count = 3
            self.settings.setValue(KEY, self.step_count)
        elif force:
            items = ["One step (experimental)", "Three steps"]
            current = 0 if self.step_count == 1 else 1
            choice, ok = QInputDialog.getItem(self, f"Step Count", "Translation step count", items, current)
            if ok and choice:
                self.step_count = 1 if choice.startswith("One") else 3
                self.settings.setValue(KEY, self.step_count)
                path = self.settings.fileName()
                QMessageBox.information(self, f"Step Count", f"The step count is stored in {path}")

    @Slot()
    def result_text_changed(self):
        text = self.result_textedit.toPlainText()
        empty = len(text) == 0 or text.isspace()
        self.save_button.setEnabled(not empty)
        if empty:
            self.input_textedit.setPlaceholderText(self.tr("Describe your video."))
        else:
            self.input_textedit.setPlaceholderText(self.tr("Describe the changes and additions to your video."))

    @Slot(bool)
    def open_button_clicked(self, checked):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Open a JSON file for context"), ".", "JSON files (*.json)")
        if path:
            with open(path, "r") as f:
                s = f.read()
                self.result_textedit.setPlainText(s)
                self.scroll_to_end()
                self.results = [s]
                self.current_result = 0
                self.set_undo_redo_enabled()

    @Slot(bool)
    def save_button_clicked(self, checked):
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Save JSON results"), ".", "JSON files (*.json)")
        if path:
            with open(path, "w") as f:
                f.write(self.result_textedit.toPlainText())
    
    @Slot(bool)
    def undo_button_clicked(self, checked):
        if self.current_result > 0:
            self.current_result -= 1
            self.result_textedit.setPlainText(self.results[self.current_result])
            self.scroll_to_end()
            self.set_generate_enabled(True)
        self.set_undo_redo_enabled()

    @Slot(bool)
    def redo_button_clicked(self, checked):
        if self.current_result < len(self.results) - 1:
            self.current_result += 1
            self.result_textedit.setPlainText(self.results[self.current_result])
            self.scroll_to_end()
        self.set_undo_redo_enabled()

    def set_generate_enabled(self, enabled):
        if enabled:
            text = self.input_textedit.toPlainText()
            empty = len(text) == 0 or text.isspace()
            self.generate_button.setEnabled(not empty)
            return not empty
        else:
            self.generate_button.setEnabled(False)
            return False

    @Slot()
    def input_text_changed(self):
        enabled = self.set_generate_enabled(True)
        self.clear_input_button.setEnabled(enabled)

    @Slot(bool)
    def clear_input_button_clicked(self, checked):
        self.input_textedit.clear()

    @Slot(bool)
    def generate_button_clicked(self, checked):
        self.status_label.setText(self.tr("Working..."))
        self.set_all_enabled(False)

        self.submission_time = self.now()
        self.start_generate_worker()

    def start_generate_worker(self):
        # To keep the main UI thread fully responsive, do the work on another thread.
        pool = QThreadPool.globalInstance()

        self.user_request = self.input_textedit.toPlainText()
        # May have been edited manually by the user.
        self.previous_result = self.result_textedit.toPlainText()
        worker = Worker(self.raw_doc, self.previous_result, self.user_request,
                        self.api_key, self.models, self.temperature, self.step_count)

        # This signal will trigger this slot back on the main UI thread when the work is done.
        worker.signaler.finished.connect(self.worker_finished)
        pool.start(worker)

    def set_all_enabled(self, enabled):
        if not enabled:
            self.result_textedit.setReadOnly(True)
            self.open_button.setEnabled(False)
            self.save_button.setEnabled(False)
            self.undo_button.setEnabled(False)
            self.redo_button.setEnabled(False)
            self.input_textedit.setReadOnly(True)
            self.generate_button.setEnabled(False)
            self.clear_input_button.setEnabled(False)
        else:
            self.result_textedit.setReadOnly(False)
            self.open_button.setEnabled(True)

            text = self.result_textedit.toPlainText()
            empty = len(text) == 0 or text.isspace()
            self.save_button.setEnabled(not empty)

            self.set_undo_redo_enabled()
            self.input_textedit.setReadOnly(False)

            text = self.input_textedit.toPlainText()
            empty = len(text) == 0 or text.isspace()
            self.clear_input_button.setEnabled(not empty)

    @Slot(dict)
    def worker_finished(self, result):
        if result["ok"]:
            generated_json = result["generated_json"]
            elapsed = result["elapsed_sec"]
            cost = result["cost_USD"]

            self.result_textedit.setPlainText(generated_json)
            self.scroll_to_end()
            
            self.current_result += 1
            self.results = self.results[:self.current_result]
            self.results.append(generated_json)

            self.cumulative_cost += cost
            self.stats_label.setText(f"{elapsed} sec, ${cost:.2f}, cumulative ${self.cumulative_cost:.2f}")

            self.add_to_log(result)
            self.status_label.setText(self.tr("Ready"))

        else:
            '''
            if "code" in result and result["code"] == "context_length_exceeded":
                self.backoff()
            else:
                QMessageBox.critical(self, self.tr("Error"), result["error"])
                self.status_label.setText(self.tr("Ready"))
                self.generate_button.setEnabled(True)
            '''
            QMessageBox.critical(self, self.tr("Error"), result["error"])
            self.status_label.setText(self.tr("Ready"))

        self.set_all_enabled(True)

    '''
    def backoff(self, count=60):
        if count > 0:
            self.status_label.setText(self.tr(f"Too many tokens, retrying with fewer after {count} sec..."))
            QTimer.singleShot(1000, lambda: self.backoff(count - 1))
        else:
            self.start_generate_worker()
    '''

    def scroll_to_end(self):
        max = self.result_textedit.verticalScrollBar().maximum()
        self.result_textedit.verticalScrollBar().setValue(max)
    
    def add_to_log(self, result):
        if not self.log_file:
            return

        if len(self.previous_result) == 0 or self.previous_result.isspace():
            context = "<empty>"
        elif self.previous_result == self.results[self.current_result - 1] and self.current_result > 1:
            context = "<previous generated>"
        else:
            context = self.previous_result
        user_request = "\n".join(textwrap.wrap(self.user_request, 100))

        log = f"{str(self.submission_time)} ----------\n"
        log += f"Context:\n{context}\n"
        log += f"Request:\n{user_request}\n"

        input_tokens_key, output_tokens_key = self.get_vendor_token_keys()

        if self.step_count > 1:
            elapsed1 = result["elapsed_sec1"]
            cost1 = result["cost_USD1"]
            usage1 = result["usage1"]
            input_tokens1 = usage1[input_tokens_key]
            output_tokens1 = usage1[output_tokens_key]
            total_tokens1 = usage1["total_tokens"] if "total_tokens" in usage1 else input_tokens1 + output_tokens1
            generated_json1 = result["generated_json1"]

            log += f"Step 1 model {self.models[0]}\n"
            log += f"Step 1 generation time {elapsed1} sec, cost ${cost1:.2f}\n"
            log += f"Step 1 generation tokens: input {input_tokens1}, output {output_tokens1}, total {total_tokens1}\n"
            log += f"Step 1 generated JSON:\n{generated_json1}"

            elapsed2 = result["elapsed_sec2"]
            cost2 = result["cost_USD2"]
            usage2 = result["usage2"]
            input_tokens2 = usage2[input_tokens_key]
            output_tokens2 = usage2[output_tokens_key]
            total_tokens2 = usage2["total_tokens"] if "total_tokens" in usage2 else input_tokens2 + output_tokens2
            generated_json2 = result["generated_json2"]

            log += f"Step 2 model {self.models[1]}\n"
            log += f"Step 2 generation time {elapsed2} sec, cost ${cost2:.2f}\n"
            log += f"Step 2 generation tokens: input {input_tokens2}, output {output_tokens2}, total {total_tokens2}\n"
            log += f"Step 2 generated JSON:\n{generated_json2}"

            elapsed3 = result["elapsed_sec3"]
            cost3 = result["cost_USD3"]
            usage3 = result["usage3"]
            input_tokens3 = usage3[input_tokens_key]
            output_tokens3 = usage3[output_tokens_key]
            total_tokens3 = usage3["total_tokens"] if "total_tokens" in usage3 else input_tokens3 + output_tokens3

            log += f"Step 3 model {self.models[2]}\n"
            log += f"Step 3 generation time {elapsed3} sec, cost ${cost3:.2f}\n"
            log += f"Step 3 generation tokens: input {input_tokens3}, output {output_tokens3}, total {total_tokens3}\n"
        else:
            usage = result["usage"]
            input_tokens = usage[input_tokens_key]
            output_tokens = usage[output_tokens_key]
            total_tokens = usage["total_tokens"] if "total_tokens" in usage else input_tokens + output_tokens

            log += f"Model {self.models[0]}\n"
            log += f"Generation tokens: input {input_tokens}, output {output_tokens}, total {total_tokens}\n"

        generated_json = result["generated_json"]
        elapsed = result["elapsed_sec"]
        cost = result["cost_USD"]

        log += f"Final generation time {elapsed} sec\n"
        log += f"Final cost ${cost:.2f}, cumulative cost ${self.cumulative_cost:.2f}\n"
        log += f"Final generated JSON:\n{generated_json}\n"

        with open(self.log_file, "a") as f:
            f.write(log)
        
    def now(self):
        t = datetime.datetime.now()
        return t.replace(microsecond=0)

    def temp_dir(self):
        if platform.system() == "Darwin":
            return "/tmp"
        else:
            return tempfile.gettempdir()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
