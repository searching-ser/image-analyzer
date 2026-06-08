import sys
import os
import subprocess
import shutil
import shlex
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
MPI_LAUNCHER = "/opt/mpich-4.2.0/bin/mpiexec"
MPI_EXECUTABLE_NAME = "para_image_mpi"
MPI_MASTER_HOST = "ubuntu-master"
MPI_MACHINEFILE = str(Path(__file__).resolve().parent / "machinefile")
MPI_HOSTS = ["ubuntu-master", "searching_ser@searchingser", "diego@diegovm"]
MPI_HOST_EXECUTABLES = {
    "ubuntu-master": "/home/vboxuser/image-analyzer/para_image_mpi",
    "searching_ser@searchingser": "/home/searching_ser/image-analyzer/para_image_mpi",
    "diego@diegovm": "/home/diego/image-analyzer/para_image_mpi",
}
MPI_EXTRA_ARGS = [
    "-launcher", "ssh",
    "-disable-x",
    "-genv", "DISPLAY", "",
    "-genv", "XAUTHORITY", "",
    "-genv", "PATH", "/opt/mpich-4.2.0/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "-genv", "LD_LIBRARY_PATH", "/opt/mpich-4.2.0/lib",
    "-genv", "FI_PROVIDER", "tcp",
    "-genv", "FI_TCP_IFACE", "tailscale0",
    "-localhost", MPI_MASTER_HOST,
    "-f", MPI_MACHINEFILE,
    "-prepend-rank",
]
MPI_ENV = {
    "FI_PROVIDER": "tcp",
    "FI_TCP_IFACE": "tailscale0",
    "LD_LIBRARY_PATH": "/opt/mpich-4.2.0/lib",
}


def parse_machinefile_hosts(machinefile_path):
    hosts = []

    try:
        with open(machinefile_path, "r", encoding="utf-8") as machinefile:
            for line in machinefile:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                host = line.split()[0]
                if ":" in host:
                    name, slots = host.rsplit(":", 1)
                    if slots.isdigit():
                        host = name

                hosts.append(host)
    except OSError:
        return list(MPI_HOSTS)

    return hosts if hosts else list(MPI_HOSTS)


def executable_for_host(host, local_executable):
    if host in MPI_HOST_EXECUTABLES:
        return MPI_HOST_EXECUTABLES[host]

    if "@" in host:
        user = host.split("@", 1)[0]
        return f"/home/{user}/image-analyzer/{MPI_EXECUTABLE_NAME}"

    return str(local_executable)


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

            if not file_path.lower().endswith(".bmp") and not Path(file_path).is_dir():
                continue

            if file_path in existing:
                continue

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

        btn_add_folder = QPushButton("Agregar carpeta")
        btn_add_folder.clicked.connect(self.select_folder)

        btn_clear = QPushButton("Limpiar")
        btn_clear.clicked.connect(self.clear_list)

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_add_folder)
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

            self.list_widget.addItem(f)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta con imagenes")

        if not folder:
            return

        existing = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        if folder not in existing:
            self.list_widget.addItem(folder)

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

                if source.is_dir():
                    for bmp_file in sorted(source.iterdir()):
                        if not bmp_file.is_file() or bmp_file.suffix.lower() != ".bmp":
                            continue

                        destination = SHARED_INPUT_DIR / bmp_file.name
                        if destination.exists() and bmp_file.resolve() != destination.resolve():
                            destination = SHARED_INPUT_DIR / f"{len(image_paths) + 1:03d}_{bmp_file.name}"

                        if bmp_file.resolve() != destination.resolve():
                            shutil.copy2(bmp_file, destination)

                        image_paths.append(str(destination))
                    continue

                if source.suffix.lower() != ".bmp":
                    continue

                destination = SHARED_INPUT_DIR / source.name

                if destination.exists() and source.resolve() != destination.resolve():
                    destination = SHARED_INPUT_DIR / f"{len(image_paths) + 1:03d}_{source.name}"

                if source.resolve() != destination.resolve():
                    shutil.copy2(source, destination)

                image_paths.append(str(destination))
        except OSError as exc:
            self.output_box.setText(
                f"No se pudieron copiar las imagenes a la carpeta compartida.\n{exc}"
            )
            return

        if not image_paths:
            self.output_box.setText("No se encontraron imagenes BMP para procesar.")
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

        mpi_hosts = parse_machinefile_hosts(MPI_MACHINEFILE)

        if not mpi_hosts:
            self.output_box.setText("Configura el machinefile con la maestra y las esclavas Ubuntu.")
            return

        cmd = [
            MPI_LAUNCHER,
            *MPI_EXTRA_ARGS,
        ]
        for index, host in enumerate(mpi_hosts):
            executable = executable_for_host(host, local_executable)
            if index > 0:
                cmd.append(":")
            cmd.extend([
                "-wdir",
                str(SHARED_ROOT),
                "-n",
                "1",
                executable,
            ])
            cmd.extend(common_args)

        printable_cmd = " ".join(shlex.quote(part) for part in cmd)
        self.output_box.setText(f"Procesando...\n\nComando MPI:\n{printable_cmd}\n")

        env = os.environ.copy()
        env.update(MPI_ENV)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(SHARED_ROOT),
                env=env,
            )
        except FileNotFoundError:
            self.output_box.setText(
                "No se encontró mpiexec.\n"
                "Instala MPICH 4.2.0 o revisa la ruta de MPI_LAUNCHER."
            )
            return

        output = f"Comando MPI:\n{printable_cmd}\n\n"
        output += result.stdout

        if result.stderr:
            output += "\n" + result.stderr

        if result.returncode != 0:
            output += f"\nEl proceso terminó con código {result.returncode}."

        self.output_box.setText(output)


app = QApplication(sys.argv)
window = App()
window.show()
sys.exit(app.exec())
