import sys
import subprocess
import shutil
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QListWidget, QLabel, QCheckBox,
    QHBoxLayout, QFileDialog, QComboBox, QTextEdit, QDialog
)
from PySide6.QtCore import Qt


SHARED_ROOT = Path("/mnt/mirror")
SHARED_INPUT_DIR = SHARED_ROOT / "input"
SHARED_OUTPUT_DIR = SHARED_ROOT / "output"
MPI_LAUNCHER = "mpiexec.mpich"
MPI_EXECUTABLE_NAME = "para_image_mpi"
MPI_HOSTS = ["localhost", "searching_ser@searchingser"]
MPI_HOST_EXECUTABLES = {
    "localhost": "/home/vboxuser/image-analyzer/para_image_mpi",
    "searching_ser@searchingser": "/home/searching_ser/image-analyzer/para_image_mpi",
}
MPI_PROCESS_COUNT = len(MPI_HOSTS)
MPI_EXTRA_ARGS = [
    "-launcher", "ssh",
]


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

        project_dir = Path(__file__).resolve().parent
        local_executable = project_dir / MPI_EXECUTABLE_NAME

        if not SHARED_ROOT.exists():
            self.output_box.setText(
                f"No se encontro la carpeta compartida:\n{SHARED_ROOT}\n\n"
                "Verifica que el recurso compartido de emisan-pc este disponible por Tailscale."
            )
            return

        if not local_executable.exists():
            self.output_box.setText(
                f"No se encontro {MPI_EXECUTABLE_NAME} en:\n{local_executable}\n\n"
                "Compila el procesador MPI en el repo de la maestra."
            )
            return

        try:
            SHARED_INPUT_DIR.mkdir(exist_ok=True)
            SHARED_OUTPUT_DIR.mkdir(exist_ok=True)
        except OSError as exc:
            self.output_box.setText(
                f"No se pudieron preparar las carpetas compartidas input/output.\n{exc}"
            )
            return

        image_paths = []
        try:
            for i in range(self.list_widget.count()):
                source = Path(self.list_widget.item(i).text())
                destination = SHARED_INPUT_DIR / source.name

                if destination.exists() and source.resolve() != destination.resolve():
                    destination = SHARED_INPUT_DIR / f"{i + 1:02d}_{source.name}"

                if source.resolve() != destination.resolve():
                    shutil.copy2(source, destination)

                image_paths.append(str(destination))
        except OSError as exc:
            self.output_box.setText(
                f"No se pudieron copiar las imagenes a la carpeta compartida.\n{exc}"
            )
            return

        selected_flags = []
        if self.cb_vg.isChecked(): selected_flags.append("--vg")
        if self.cb_vc.isChecked(): selected_flags.append("--vc")
        if self.cb_hg.isChecked(): selected_flags.append("--hg")
        if self.cb_hc.isChecked(): selected_flags.append("--hc")
        if self.cb_bg.isChecked(): selected_flags.append("--bg")
        if self.cb_bc.isChecked(): selected_flags.append("--bc")

        common_args = [
            self.thread_selector.currentText(),
            str(SHARED_OUTPUT_DIR),
        ]
        common_args.extend(image_paths)
        common_args.extend(selected_flags)

        if not MPI_HOSTS:
            self.output_box.setText("Configura MPI_HOSTS con la maestra y las esclavas Ubuntu.")
            return

        cmd = [MPI_LAUNCHER, *MPI_EXTRA_ARGS]
        for index, host in enumerate(MPI_HOSTS):
            executable = MPI_HOST_EXECUTABLES.get(host, str(local_executable))
            if index > 0:
                cmd.append(":")
            cmd.extend([
                "-host",
                host,
                "-n",
                "1",
                executable,
            ])
            cmd.extend(common_args)

        self.output_box.setText("Procesando...\n")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(SHARED_ROOT),
            )
        except FileNotFoundError:
            self.output_box.setText(
                "No se encontró mpiexec.\n"
                "Instala OpenMPI o agrega mpirun al PATH para ejecutar para_image_mpi."
            )
            return

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
