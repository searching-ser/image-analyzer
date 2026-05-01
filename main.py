import sys
import subprocess
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QListWidget, QLabel, QCheckBox,
    QHBoxLayout, QFileDialog, QComboBox, QTextEdit, QDialog
)
from PySide6.QtCore import Qt


class DropListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)
        self.setStyleSheet(self.default_style())

    def default_style(self):
        return """
            QListWidget {
                border: 2px dashed #555;
                border-radius: 10px;
                padding: 10px;
                background-color: #1e1e1e;
                color: white;
            }
        """

    def highlight_style(self):
        return """
            QListWidget {
                border: 2px dashed #00aaff;
                border-radius: 10px;
                padding: 10px;
                background-color: #2a2a2a;
                color: white;
            }
        """

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self.highlight_style())
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.default_style())

    def dropEvent(self, event):
        if not event.mimeData().hasUrls():
            event.ignore()
            return

        self.setStyleSheet(self.default_style())

        existing = [self.item(i).text() for i in range(self.count())]

        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue

            file_path = url.toLocalFile()

            if not file_path.lower().endswith(".bmp"):
                continue

            if file_path in existing:
                continue

            if self.count() >= 10:
                break

            self.addItem(file_path)

        event.acceptProposedAction()


class AboutDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Sobre Nosotros")
        self.resize(300, 200)

        layout = QVBoxLayout()

        label = QLabel("Integrantes del equipo:\n\n- Diego López Romero\n- Emiliano Sánchez Domínguez \n- Sergio David Pimentel Pérez")
        label.setAlignment(Qt.AlignTop)

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.close)

        layout.addWidget(label)
        layout.addWidget(btn_close)

        self.setLayout(layout)


class App(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Image Analyzer")
        self.resize(500, 700)

        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: white;
                font-size: 14px;
            }
            QPushButton {
                background-color: #00aaff;
                border: none;
                padding: 8px;
                border-radius: 8px;
                color: white;
            }
            QPushButton:hover {
                background-color: #0088cc;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border-radius: 8px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout()

      
        btn_about = QPushButton("Sobre Nosotros")
        btn_about.clicked.connect(self.show_about)
        layout.addWidget(btn_about)

        title = QLabel("Image Analyzer")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

   
        layout.addWidget(QLabel("Arrastra imágenes (.bmp) aquí (máx 10):"))
        self.list_widget = DropListWidget()
        layout.addWidget(self.list_widget)

        
        btn_layout = QHBoxLayout()

        btn_add = QPushButton("Agregar imágenes")
        btn_add.clicked.connect(self.select_images)

        btn_clear = QPushButton("Limpiar")
        btn_clear.clicked.connect(self.clear_list)

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_clear)

        layout.addLayout(btn_layout)

       
        layout.addWidget(QLabel("Procesamientos:"))

        self.cb_vg = QCheckBox("Vertical Gris")
        self.cb_vc = QCheckBox("Vertical Color")
        self.cb_hg = QCheckBox("Horizontal Gris")
        self.cb_hc = QCheckBox("Horizontal Color")
        self.cb_bg = QCheckBox("Blur Gris")
        self.cb_bc = QCheckBox("Blur Color")

        layout.addWidget(self.cb_vg)
        layout.addWidget(self.cb_vc)
        layout.addWidget(self.cb_hg)
        layout.addWidget(self.cb_hc)
        layout.addWidget(self.cb_bg)
        layout.addWidget(self.cb_bc)

        
        btn_select_all = QPushButton("Seleccionar / Deseleccionar todo")
        btn_select_all.clicked.connect(self.toggle_all)
        layout.addWidget(btn_select_all)

        
        layout.addWidget(QLabel("Threads:"))
        self.thread_selector = QComboBox()
        self.thread_selector.addItems(["6", "12", "18"])
        self.thread_selector.setCurrentText("12")
        layout.addWidget(self.thread_selector)

       
        btn_run = QPushButton("Procesar")
        btn_run.clicked.connect(self.run_program)
        layout.addWidget(btn_run)

       
        layout.addWidget(QLabel("Resultados:"))
        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        layout.addWidget(self.output_box)

        self.setLayout(layout)

    def show_about(self):
        dialog = AboutDialog()
        dialog.exec()

    def toggle_all(self):
        checkboxes = [self.cb_vg, self.cb_vc, self.cb_hg, self.cb_hc, self.cb_bg, self.cb_bc]
        all_checked = all(cb.isChecked() for cb in checkboxes)

        for cb in checkboxes:
            cb.setChecked(not all_checked)

    def select_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Seleccionar imágenes", "", "Images (*.bmp)")

        existing = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]

        for f in files:
            if f in existing:
                continue

            if self.list_widget.count() >= 10:
                break

            self.list_widget.addItem(f)

    def clear_list(self):
        self.list_widget.clear()

    def run_program(self):
        if self.list_widget.count() == 0:
            self.output_box.setText("No hay imágenes seleccionadas")
            return

        executable = Path(__file__).resolve().parent / "para_image.exe"
        if not executable.exists():
            self.output_box.setText(
                "No se encontró para_image.exe.\n"
                "Compila el procesador de imágenes antes de ejecutar."
            )
            return

        cmd = [str(executable), self.thread_selector.currentText()]

        for i in range(self.list_widget.count()):
            cmd.append(self.list_widget.item(i).text())

        if self.cb_vg.isChecked(): cmd.append("--vg")
        if self.cb_vc.isChecked(): cmd.append("--vc")
        if self.cb_hg.isChecked(): cmd.append("--hg")
        if self.cb_hc.isChecked(): cmd.append("--hc")
        if self.cb_bg.isChecked(): cmd.append("--bg")
        if self.cb_bc.isChecked(): cmd.append("--bc")

        self.output_box.setText("Procesando...\n")

        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout

        if result.stderr:
            output += "\n" + result.stderr

        if result.returncode != 0:
            output += f"\nEl proceso terminó con código {result.returncode}."

        self.output_box.setText(output)


app = QApplication(sys.argv)
window = App()
window.show()
sys.exit(app.exec())