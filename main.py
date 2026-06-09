import os
import re
import shlex
import shutil
import struct
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


PROJECT_DIR = Path(__file__).resolve().parent


def env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "local"}


LOCAL_ONLY_TESTING = env_flag("IMAGE_ANALYZER_LOCAL_ONLY", False)
LOCAL_MPIEXEC = os.environ.get("IMAGE_ANALYZER_MPIEXEC", "mpiexec")

SHARED_ROOT = PROJECT_DIR / "local_mirror" if LOCAL_ONLY_TESTING else Path("/mnt/mirror")
SHARED_INPUT_DIR = SHARED_ROOT / "input"
SHARED_OUTPUT_DIR = SHARED_ROOT / "output"
MPI_LAUNCHER = LOCAL_MPIEXEC if LOCAL_ONLY_TESTING else "/opt/mpich-4.2.0/bin/mpiexec"
MPI_EXECUTABLE_NAME = "para_image_mpi"
MPI_MASTER_HOST = "ubuntu-master"
MPI_MACHINEFILE = str(PROJECT_DIR / "machinefile")
MPI_HOSTS = ["localhost"] if LOCAL_ONLY_TESTING else ["ubuntu-master", "searching_ser@searchingser", "diego@diegovm"]
MPI_HOST_EXECUTABLES = {
    "ubuntu-master": "/home/vboxuser/image-analyzer/para_image_mpi",
    "searching_ser@searchingser": "/home/searching_ser/image-analyzer/para_image_mpi",
    "diego@diegovm": "/home/diego/image-analyzer/para_image_mpi",
}
MPI_EXTRA_ARGS = [] if LOCAL_ONLY_TESTING else [
    "-launcher", "ssh",
    "-disable-x",
    "-genv", "DISPLAY", "",
    "-genv", "XAUTHORITY", "",
    "-genv", "PATH", "/opt/mpich-4.2.0/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "-genv", "LD_LIBRARY_PATH", "/opt/mpich-4.2.0/lib",
    "-genv", "FI_PROVIDER", "tcp",
    "-genv", "FI_TCP_IFACE", "tailscale0",
    "-genv", "IMAGE_ANALYZER_TMPDIR", "/var/tmp",
    "-localhost", MPI_MASTER_HOST,
    "-f", MPI_MACHINEFILE,
    "-prepend-rank",
]
MPI_ENV = {} if LOCAL_ONLY_TESTING else {
    "FI_PROVIDER": "tcp",
    "FI_TCP_IFACE": "tailscale0",
    "LD_LIBRARY_PATH": "/opt/mpich-4.2.0/lib",
    "IMAGE_ANALYZER_TMPDIR": "/var/tmp",
}

MAX_UI_IMAGES = 600
MAX_BACKEND_IMAGES = 10 if LOCAL_ONLY_TESTING else MAX_UI_IMAGES
PROCESS_OPTIONS = [
    ("Escala de grises", ("--gray",), "functional"),
    ("Espejo horizontal color", ("--hc",), "functional"),
    ("Espejo vertical color", ("--vc",), "functional"),
    ("Espejo horizontal gris", ("--hg",), "functional"),
    ("Espejo vertical gris", ("--vg",), "functional"),
    ("Blur gris", ("--bg",), "functional"),
    ("Blur color", ("--bc",), "functional"),
]
TEAM_MEMBERS = [
    "Diego López Romero",
    "Emiliano Sánchez Domínguez",
    "Sergio David Pimentel Pérez",
]


def format_scientific(value, unit=""):
    if value <= 0:
        return f"0 {unit}".strip()
    exponent_text = f"{value:.2e}".replace("e+", " x 10^").replace("e", " x 10^")
    return f"{exponent_text} {unit}".strip()


def read_bmp_pixels(path):
    try:
        with open(path, "rb") as handle:
            header = handle.read(26)
        if len(header) < 26 or header[:2] != b"BM":
            return 0
        width = struct.unpack_from("<i", header, 18)[0]
        height = abs(struct.unpack_from("<i", header, 22)[0])
        return max(width, 0) * max(height, 0)
    except OSError:
        return 0


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Integrantes")
        self.resize(360, 220)

        layout = QVBoxLayout(self)
        title = QLabel("Integrantes del equipo")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        for member in TEAM_MEMBERS:
            layout.addWidget(QLabel(member))

        close_button = QPushButton("Cerrar")
        close_button.clicked.connect(self.close)
        layout.addStretch()
        layout.addWidget(close_button)


def parse_machinefile_hosts(machinefile_path):
    if LOCAL_ONLY_TESTING:
        return ["localhost"]

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


class FolderDropZone(QFrame):
    folderSelected = Signal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropZone")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        self.icon = QLabel("□")
        self.icon.setAlignment(Qt.AlignCenter)
        self.icon.setObjectName("dropIcon")
        title = QLabel("Seleccionar carpeta con hasta 600 imágenes BMP")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("dropTitle")
        detail = QLabel("Arrastra y suelta una carpeta aquí\n(Solo imágenes BMP)")
        detail.setAlignment(Qt.AlignCenter)
        detail.setObjectName("muted")
        layout.addWidget(self.icon)
        layout.addWidget(title)
        layout.addWidget(detail)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("active", True)
            self.style().unpolish(self)
            self.style().polish(self)
            return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("active", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event):
        self.setProperty("active", False)
        self.style().unpolish(self)
        self.style().polish(self)
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            candidate = Path(url.toLocalFile())
            if candidate.is_dir():
                self.folderSelected.emit(str(candidate))
                event.acceptProposedAction()
                return
        event.ignore()


class NodeTable(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("nodeCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(14, 14, 14, 14)
        outer_layout.setSpacing(12)

        title = QLabel("Resumen por nodo")
        title.setObjectName("fieldLabel")
        badge = QLabel("Placeholder - pendiente de métricas por nodo")
        badge.setObjectName("badge")
        outer_layout.addWidget(title)
        outer_layout.addWidget(badge)

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(12)
        headers = ["Nodo", "Estado", "Progreso", "Imágenes", "Rendimiento"]
        for col, text in enumerate(headers):
            label = QLabel(text)
            label.setObjectName("tableHeader")
            label.setMinimumWidth(0)
            label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            layout.addWidget(label, 0, col)
            layout.setColumnStretch(col, 1)

        nodes = [
            ("Lenovo", "Pendiente", "-", "-", "-"),
            ("Lanix", "Pendiente", "-", "-", "-"),
            ("Gamer", "Pendiente", "-", "-", "-"),
            ("Total", "-", "-", "-", "-"),
        ]
        for row, node in enumerate(nodes, start=1):
            for col, text in enumerate(node):
                label = QLabel(text)
                label.setMinimumWidth(0)
                label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
                if row == 4:
                    label.setObjectName("tableTotal")
                layout.addWidget(label, row, col)
        outer_layout.addLayout(layout)


class NodeStatusTable(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("nodeCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.rows = {}
        self.completed_counts = {}

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(14, 14, 14, 14)
        outer_layout.setSpacing(12)

        title = QLabel("Resumen por nodo")
        title.setObjectName("fieldLabel")
        self.badge = QLabel("Esperando ejecucion")
        self.badge.setObjectName("badge")
        outer_layout.addWidget(title)
        outer_layout.addWidget(self.badge)

        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(12)
        headers = ["Rank/Nodo", "Estado", "Imagen actual", "Terminadas", "Rendimiento"]
        for col, text in enumerate(headers):
            label = QLabel(text)
            label.setObjectName("tableHeader")
            label.setMinimumWidth(0)
            label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            self.grid.addWidget(label, 0, col)
            self.grid.setColumnStretch(col, 1)

        outer_layout.addLayout(self.grid)
        self.set_nodes([])

    def clear_rows(self):
        for labels in self.rows.values():
            for label in labels:
                self.grid.removeWidget(label)
                label.deleteLater()
        self.rows.clear()
        self.completed_counts.clear()

    def set_nodes(self, hosts):
        self.clear_rows()
        if not hosts:
            hosts = ["Sin nodos configurados"]

        for rank, host in enumerate(hosts):
            row = rank + 1
            values = [f"{rank} / {host}", "Pendiente", "-", "0", "-"]
            labels = []
            for col, value in enumerate(values):
                label = QLabel(value)
                label.setWordWrap(True)
                label.setMinimumWidth(0)
                label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
                self.grid.addWidget(label, row, col)
                labels.append(label)
            self.rows[rank] = labels
            self.completed_counts[rank] = 0

        self.badge.setText("Nodos listos")

    def mark_assigned(self, rank, count):
        if rank not in self.rows:
            return
        labels = self.rows[rank]
        labels[1].setText("Sin imagenes" if count == 0 else "Asignado")
        labels[2].setText("-")

    def mark_processing(self, rank, image_path):
        if rank not in self.rows:
            return
        labels = self.rows[rank]
        labels[1].setText("Procesando")
        labels[2].setText(Path(image_path).name)

    def mark_finished_image(self, rank, image_path):
        if rank not in self.rows:
            return
        self.completed_counts[rank] = self.completed_counts.get(rank, 0) + 1
        labels = self.rows[rank]
        labels[1].setText("Activo")
        labels[2].setText(Path(image_path).name)
        labels[3].setText(str(self.completed_counts[rank]))

    def mark_complete(self):
        for labels in self.rows.values():
            labels[1].setText("Terminado")
            labels[2].setText("-")
        total = sum(self.completed_counts.values())
        self.badge.setText(f"Total terminado: {total} imagenes")

    def set_rate_for_all(self, rate_text):
        for labels in self.rows.values():
            labels[4].setText(rate_text)


@dataclass
class RunRequest:
    image_paths: list
    selected_flags: list
    thread_count: str
    kernel_size: str


class ProcessingWorker(QThread):
    finished = Signal(str, int, float)
    failed = Signal(str)
    log_received = Signal(str)
    aborted = Signal(str)

    def __init__(self, request):
        super().__init__()
        self.request = request
        self.process = None
        self.abort_requested = False

    def abort(self):
        self.abort_requested = True
        process = self.process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass

    def cleanup_cluster_processes(self, hosts):
        kill_command = (
            "pkill -TERM -f para_image_mpi 2>/dev/null; "
            "pkill -TERM -f hydra_pmi_proxy 2>/dev/null; "
            "sleep 1; "
            "pkill -KILL -f para_image_mpi 2>/dev/null; "
            "pkill -KILL -f hydra_pmi_proxy 2>/dev/null"
        )

        for host in hosts:
            if host in {"localhost", MPI_MASTER_HOST}:
                command = ["bash", "-lc", kill_command]
            else:
                command = ["ssh", "-x", host, kill_command]

            try:
                subprocess.run(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=8,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue

    def run(self):
        started = datetime.now()
        local_executable = PROJECT_DIR / MPI_EXECUTABLE_NAME

        if LOCAL_ONLY_TESTING:
            try:
                SHARED_ROOT.mkdir(exist_ok=True)
            except OSError as exc:
                self.failed.emit(f"No se pudo crear la carpeta local de prueba:\n{SHARED_ROOT}\n\n{exc}")
                return
        elif not SHARED_ROOT.exists():
            self.failed.emit(
                f"No se encontró la carpeta compartida:\n{SHARED_ROOT}\n\n"
                "Verifica que el recurso compartido esté disponible por Tailscale."
            )
            return

        if not local_executable.exists():
            self.failed.emit(
                f"No se encontró {MPI_EXECUTABLE_NAME} en:\n{local_executable}\n\n"
                "Compila el procesador MPI antes de ejecutar la carga."
            )
            return

        try:
            SHARED_INPUT_DIR.mkdir(exist_ok=True)
            SHARED_OUTPUT_DIR.mkdir(exist_ok=True)
        except OSError as exc:
            self.failed.emit(f"No se pudieron preparar las carpetas compartidas input/output.\n{exc}")
            return

        image_paths = []
        try:
            for existing_bmp in SHARED_INPUT_DIR.glob("*.bmp"):
                if self.abort_requested:
                    self.aborted.emit("Ejecucion abortada antes de preparar la carpeta compartida.")
                    return
                existing_bmp.unlink()

            for index, source_text in enumerate(self.request.image_paths[:MAX_BACKEND_IMAGES]):
                if self.abort_requested:
                    self.aborted.emit("Ejecucion abortada durante la copia de imagenes a /mnt/mirror/input.")
                    return
                source = Path(source_text)
                destination = SHARED_INPUT_DIR / source.name
                if destination.exists() and source.resolve() != destination.resolve():
                    destination = SHARED_INPUT_DIR / f"{index + 1:02d}_{source.name}"
                if source.resolve() != destination.resolve():
                    shutil.copy2(source, destination)
                image_paths.append(str(destination))
        except OSError as exc:
            self.failed.emit(f"No se pudieron copiar las imágenes a la carpeta compartida.\n{exc}")
            return

        if not image_paths:
            self.failed.emit("No se encontraron imagenes BMP para procesar.")
            return

        if self.abort_requested:
            self.aborted.emit("Ejecucion abortada antes de lanzar MPI.")
            return

        common_args = [
            self.request.thread_count,
            str(SHARED_OUTPUT_DIR),
            str(SHARED_INPUT_DIR),
            "--kernel",
            self.request.kernel_size,
            *self.request.selected_flags,
        ]
        mpi_hosts = parse_machinefile_hosts(MPI_MACHINEFILE)

        if not mpi_hosts:
            self.failed.emit("Configura al menos un host MPI para ejecutar la carga.")
            return

        cmd = [MPI_LAUNCHER, *MPI_EXTRA_ARGS]
        for index, host in enumerate(mpi_hosts):
            executable = executable_for_host(host, local_executable)
            if index > 0:
                cmd.append(":")
            cmd.extend(["-wdir", str(SHARED_ROOT), "-n", "1", executable, *common_args])

        printable_cmd = " ".join(shlex.quote(part) for part in cmd)
        env = os.environ.copy()
        env.update(MPI_ENV)
        output_parts = [f"Comando MPI:\n{printable_cmd}\n\n"]
        self.log_received.emit(output_parts[0])

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(SHARED_ROOT),
                env=env,
                bufsize=1,
            )
        except FileNotFoundError:
            self.failed.emit("No se encontró mpiexec.\nInstala MPICH 4.2.0 o revisa la ruta de MPI_LAUNCHER.")
            return

        process = self.process
        if process.stdout is not None:
            for line in process.stdout:
                output_parts.append(line)
                self.log_received.emit(line)
                if self.abort_requested:
                    break

        if self.abort_requested and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            except OSError:
                pass

        returncode = process.wait()
        if self.abort_requested:
            self.log_received.emit("\nAbortando procesos MPI en master y esclavas...\n")
            self.cleanup_cluster_processes(mpi_hosts)
            message = "".join(output_parts)
            message += "\n\nEjecucion abortada por el usuario. Procesos MPI detenidos en master/esclavas."
            self.aborted.emit(message)
            return

        if returncode != 0:
            error_line = f"\nEl proceso termino con codigo {returncode}."
            output_parts.append(error_line)
            self.log_received.emit(error_line)

        elapsed = (datetime.now() - started).total_seconds()
        self.finished.emit("".join(output_parts), returncode, elapsed)


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Analyzer")
        self.resize(1420, 860)
        self.image_paths = []
        self.worker = None
        self.last_elapsed = 0.0
        self.processed_image_count = 0
        self.finished_image_paths = set()

        root = QWidget()
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.sidebar = self.build_sidebar()
        shell.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        shell.addWidget(self.stack, 1)
        self.metrics_page = self.build_metrics_page()
        self.stack.addWidget(self.metrics_page)

        self.apply_styles()
        self.refresh_metrics()

    def build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(286)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 26, 20, 20)
        layout.setSpacing(12)

        logo = QLabel()
        logo.setObjectName("sidebarLogo")
        logo.setAlignment(Qt.AlignCenter)
        logo_pixmap = QPixmap(str(PROJECT_DIR / "img" / "tecnologico_monterrey.png"))
        if not logo_pixmap.isNull():
            logo.setPixmap(logo_pixmap.scaledToWidth(176, Qt.SmoothTransformation))
        layout.addWidget(logo)

        course = QLabel("Implementación de redes de área amplia y servicios distribuidos (Gpo 502)")
        course.setObjectName("courseInfo")
        course.setWordWrap(True)
        course.setAlignment(Qt.AlignCenter)
        layout.addWidget(course)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        layout.addWidget(divider)

        members_title = QLabel("Integrantes")
        members_title.setObjectName("sideTitle")
        layout.addWidget(members_title)
        for member in TEAM_MEMBERS:
            layout.addWidget(QLabel(member))

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        layout.addWidget(divider)

        layout.addStretch()

        system = QFrame()
        system.setObjectName("systemBox")
        system_layout = QVBoxLayout(system)
        system_layout.addWidget(QLabel("Información del sistema"))
        self.system_state = QLabel("Estado: Listo")
        mode = "Local" if LOCAL_ONLY_TESTING else "Distribuido"
        self.system_user = QLabel(f"Modo: {mode}")
        self.system_version = QLabel("Versión: 1.0.0")
        self.system_date = QLabel("Fecha: " + datetime.now().strftime("%d/%m/%Y %H:%M"))
        self.system_wiki = QLabel('<a href="https://github.com/searching-ser/image-analyzer/wiki">Wiki del proyecto</a>')
        self.system_wiki.setOpenExternalLinks(True)
        self.system_wiki.setWordWrap(True)
        for item in [self.system_state, self.system_user, self.system_version, self.system_date, self.system_wiki]:
            system_layout.addWidget(item)
        layout.addWidget(system)
        return sidebar

    def build_metrics_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        page = QWidget()
        page.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        scroll.setWidget(page)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(16)

        title = QLabel("Image Analyzer")
        title.setObjectName("title")
        subtitle = QLabel("Sistema distribuido para procesamiento de imágenes BMP")
        subtitle.setObjectName("subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        heading = QLabel("Vista de métricas")
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)

        folders = QHBoxLayout()
        folders.setSpacing(16)
        folders.addLayout(self.build_path_selector("Carpeta de entrada", True))
        folders.addLayout(self.build_path_selector("Carpeta de salida", False))
        layout.addLayout(folders)

        top = QHBoxLayout()
        top.setSpacing(16)
        self.drop_zone = FolderDropZone()
        self.drop_zone.folderSelected.connect(self.set_input_folder)
        top.addWidget(self.drop_zone, 1)
        top.addWidget(self.build_options_panel(), 1)
        layout.addLayout(top)

        self.progress_group = QFrame()
        self.progress_group.setObjectName("progressCard")
        self.progress_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.progress_group.setMaximumHeight(132)
        progress_layout = QVBoxLayout(self.progress_group)
        progress_layout.setContentsMargins(14, 14, 14, 14)
        progress_layout.setSpacing(10)
        progress_title = QLabel("Progreso de procesamiento")
        progress_title.setObjectName("fieldLabel")
        progress_layout.addWidget(progress_title)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        progress_layout.addWidget(self.progress_bar)
        progress_meta = QHBoxLayout()
        self.progress_count = QLabel("   0 / 0")
        self.progress_count.setWordWrap(True)
        self.progress_count.setMinimumWidth(0)
        self.progress_count.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        progress_meta.addWidget(self.progress_count, 1)
        progress_layout.addLayout(progress_meta)
        layout.addWidget(self.progress_group)

        cards = QHBoxLayout()
        cards.setSpacing(16)
        self.pixel_card = self.metric_card("Píxeles procesados", "0 px")
        self.batch_card = self.metric_card("Imágenes seleccionadas", "0")
        self.rate_card = self.metric_card("Rendimiento", "Pendiente")
        self.time_card = self.metric_card("Tiempo total", "Pendiente")
        cards.addWidget(self.pixel_card)
        cards.addWidget(self.batch_card)
        cards.addWidget(self.rate_card)
        cards.addWidget(self.time_card)
        layout.addLayout(cards)

        self.node_table = NodeStatusTable()
        layout.addWidget(self.node_table)

        log_title = QLabel("Salida de logs")
        log_title.setObjectName("fieldLabel")
        layout.addWidget(log_title)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("La salida del proceso MPI aparecerá aquí.")
        layout.addWidget(self.log_box)

        footer = QHBoxLayout()
        footer.addWidget(QLabel("Ejecución distribuida con MPI + OpenMP"))
        footer.addStretch()
        self.updated_at = QLabel("Datos actualizados: pendiente")
        self.updated_at.setWordWrap(True)
        footer.addWidget(self.updated_at)
        layout.addLayout(footer)
        return scroll

    def build_path_selector(self, label_text, is_input):
        layout = QVBoxLayout()
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        row = QHBoxLayout()
        row.setSpacing(12)
        path_label = QLabel(str(Path("input").resolve() if is_input else SHARED_OUTPUT_DIR))
        path_label.setObjectName("pathBox")
        path_label.setWordWrap(True)
        path_label.setMinimumHeight(58)
        path_label.setMinimumWidth(80)
        path_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        button = QPushButton("Explorar")
        button.setMinimumHeight(58)
        button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        if is_input:
            self.input_path_label = path_label
            button.clicked.connect(self.choose_input_folder)
        else:
            self.output_path_label = path_label
            button.clicked.connect(self.choose_output_folder)
        row.addWidget(path_label, 1)
        row.addWidget(button)
        layout.addWidget(label)
        layout.addLayout(row)
        return layout

    def build_options_panel(self):
        panel = QFrame()
        panel.setObjectName("optionsCard")
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        outer_layout = QVBoxLayout(panel)
        outer_layout.setContentsMargins(14, 14, 14, 14)
        outer_layout.setSpacing(14)

        title = QLabel("Opciones de procesamiento")
        title.setObjectName("fieldLabel")
        outer_layout.addWidget(title)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        checks_layout = QVBoxLayout()
        checks_layout.setSpacing(10)
        self.option_checks = []
        used_flags = set()
        for label, flags, status in PROCESS_OPTIONS:
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)
            checkbox.flags = flags
            if status == "placeholder":
                checkbox.setText(f"{label} (placeholder)")
                checkbox.setToolTip("Reservado para conectar una salida de escala de grises independiente.")
            for flag in flags:
                used_flags.add(flag)
            checkbox.stateChanged.connect(lambda _state: self.refresh_metrics())
            self.option_checks.append(checkbox)
            checks_layout.addWidget(checkbox)
        layout.addLayout(checks_layout)

        action_layout = QVBoxLayout()
        action_layout.setSpacing(14)
        action_layout.addWidget(QLabel("Threads OpenMP"))
        thread_row = QHBoxLayout()
        thread_row.setSpacing(12)
        self.thread_group = QButtonGroup(self)
        self.thread_group.setExclusive(True)
        for value in ["6", "12", "18"]:
            button = QPushButton(value)
            button.setObjectName("threadButton")
            button.setCheckable(True)
            if value == "12":
                button.setChecked(True)
            self.thread_group.addButton(button)
            thread_row.addWidget(button)
        action_layout.addLayout(thread_row)

        action_layout.addWidget(QLabel("Kernel blur"))
        kernel_row = QHBoxLayout()
        kernel_row.setSpacing(8)
        self.kernel_group = QButtonGroup(self)
        self.kernel_group.setExclusive(True)
        for value in ["27", "55", "75", "95", "115", "135", "155"]:
            button = QPushButton(value)
            button.setObjectName("threadButton")
            button.setCheckable(True)
            if value == "27":
                button.setChecked(True)
            self.kernel_group.addButton(button)
            kernel_row.addWidget(button)
        action_layout.addLayout(kernel_row)

        action_layout.addStretch()
        self.run_button = QPushButton("Procesar carga distribuida")
        self.run_button.setObjectName("primaryButton")
        self.run_button.clicked.connect(self.run_program)
        action_layout.addWidget(self.run_button)
        self.abort_button = QPushButton("Abortar procesos")
        self.abort_button.setObjectName("dangerButton")
        self.abort_button.setEnabled(False)
        self.abort_button.clicked.connect(self.abort_processing)
        action_layout.addWidget(self.abort_button)
        layout.addLayout(action_layout)
        outer_layout.addLayout(layout)
        return panel

    def metric_card(self, label, value):
        card = QFrame()
        card.setObjectName("metricCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(QLabel(label))
        value_label = QLabel(value)
        value_label.setObjectName("metricValue")
        value_label.setMinimumWidth(0)
        value_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout.addWidget(value_label)
        card.value_label = value_label
        return card

    def placeholder_card(self, title, body):
        return self.info_card(title, body, "Placeholder - pendiente de conexión")

    def info_card(self, title, body, badge_text):
        card = QFrame()
        card.setObjectName("placeholderCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        title_label.setWordWrap(True)
        title_label.setMinimumWidth(0)
        title_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        body_label = QLabel(body)
        body_label.setWordWrap(True)
        body_label.setMinimumWidth(0)
        body_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        badge = QLabel(badge_text)
        badge.setObjectName("badge")
        badge.setWordWrap(True)
        badge.setMinimumWidth(0)
        badge.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout.addWidget(title_label)
        layout.addWidget(body_label)
        layout.addWidget(badge)
        return card

    def choose_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de entrada")
        if folder:
            self.set_input_folder(folder)

    def choose_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de salida", str(SHARED_OUTPUT_DIR))
        if folder:
            self.output_path_label.setText(folder)

    def set_input_folder(self, folder):
        folder_path = Path(folder)
        images = sorted(str(path) for path in folder_path.iterdir() if path.is_file() and path.suffix.lower() == ".bmp")
        self.image_paths = images[:MAX_UI_IMAGES]
        self.processed_image_count = 0
        self.finished_image_paths.clear()
        self.input_path_label.setText(str(folder_path))
        self.refresh_metrics()

    def selected_thread_count(self):
        button = self.thread_group.checkedButton()
        return button.text() if button else "12"

    def selected_kernel_size(self):
        button = self.kernel_group.checkedButton()
        return button.text() if button else "27"

    def selected_flags(self):
        flags = []
        for checkbox in self.option_checks:
            if not checkbox.isChecked():
                continue
            for flag in checkbox.flags:
                if flag not in flags:
                    flags.append(flag)
        return flags

    def selected_operation_count(self):
        selected = self.selected_flags()
        if selected:
            return len(selected)
        return sum(len(flags) for _label, flags, status in PROCESS_OPTIONS if status == "functional")

    def processed_pixel_count(self, paths):
        input_pixels = sum(read_bmp_pixels(path) for path in paths)
        return input_pixels * self.selected_operation_count()

    def runnable_image_count(self):
        return min(len(self.image_paths), MAX_BACKEND_IMAGES)

    def update_processed_progress(self, processed=None):
        total = self.runnable_image_count()
        if processed is not None:
            self.processed_image_count = max(0, min(processed, total))

        self.progress_count.setText(f"Imagenes Procesadas: {self.processed_image_count} / {total}")
        if total == 0:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            return

        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(max(0, min(self.processed_image_count, total)))

    def refresh_metrics(self):
        image_count = len(self.image_paths)
        processed_pixels = self.processed_pixel_count(self.image_paths[:MAX_BACKEND_IMAGES])

        self.update_processed_progress()
        self.pixel_card.value_label.setText(format_scientific(processed_pixels, "px"))
        if image_count > MAX_BACKEND_IMAGES:
            self.batch_card.value_label.setText(f"{self.runnable_image_count()} de {image_count}")
        else:
            self.batch_card.value_label.setText(str(image_count))
        self.updated_at.setText("Datos actualizados: " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    def run_program(self):
        if not self.image_paths:
            self.log_box.setText("No hay carpeta con imágenes BMP seleccionada.")
            return
        self.run_button.setEnabled(False)
        self.abort_button.setEnabled(True)
        self.system_state.setText("Estado: Ejecución")
        self.finished_image_paths.clear()
        self.update_processed_progress(0)
        self.log_box.setText("Procesando carga distribuida...\n")
        self.node_table.set_nodes(parse_machinefile_hosts(MPI_MACHINEFILE))
        request = RunRequest(
            self.image_paths,
            self.selected_flags(),
            self.selected_thread_count(),
            self.selected_kernel_size(),
        )
        self.worker = ProcessingWorker(request)
        self.worker.log_received.connect(self.handle_log_received)
        self.worker.finished.connect(self.handle_finished)
        self.worker.failed.connect(self.handle_failed)
        self.worker.aborted.connect(self.handle_aborted)
        self.worker.start()

    def abort_processing(self):
        if self.worker is None or not self.worker.isRunning():
            return

        self.abort_button.setEnabled(False)
        self.system_state.setText("Estado: Abortando")
        self.handle_log_received("\nSolicitud de aborto recibida. Deteniendo procesos MPI...\n")
        self.worker.abort()

    def handle_log_received(self, text):
        self.log_box.moveCursor(QTextCursor.MoveOperation.End)
        self.log_box.insertPlainText(text)
        self.log_box.moveCursor(QTextCursor.MoveOperation.End)
        self.update_node_table_from_log(text)

    def update_node_table_from_log(self, text):
        for line in text.splitlines():
            assigned = re.search(r"\[rank\s+(\d+)(?:/\d+)?\]\s+procesara\s+(\d+)\s+imagen", line)
            if assigned:
                self.node_table.mark_assigned(int(assigned.group(1)), int(assigned.group(2)))
                continue

            processing = re.search(r"\[rank\s+(\d+)\]\s+procesando\s+(.+)$", line)
            if processing:
                self.node_table.mark_processing(int(processing.group(1)), processing.group(2).strip())
                continue

            finished = re.search(r"\[rank\s+(\d+)\]\s+termino\s+(.+)$", line)
            if finished:
                image_path = finished.group(2).strip()
                self.node_table.mark_finished_image(int(finished.group(1)), image_path)
                if image_path not in self.finished_image_paths:
                    self.finished_image_paths.add(image_path)
                    self.update_processed_progress(len(self.finished_image_paths))

    def handle_finished(self, output, returncode, elapsed):
        self.last_elapsed = elapsed
        runnable = self.runnable_image_count()
        if returncode == 0:
            self.update_processed_progress(runnable)
        else:
            self.update_processed_progress()
        self.time_card.value_label.setText(f"{elapsed:.1f} s")
        processed_pixels = self.processed_pixel_count(self.image_paths[:MAX_BACKEND_IMAGES])
        metric_elapsed = elapsed
        match = re.search(r"Tiempo total MPI:\s*([0-9.]+)", output)
        if match:
            metric_elapsed = float(match.group(1))
            self.time_card.value_label.setText(f"{metric_elapsed:.1f} s")
        rate_text = "Pendiente"
        if metric_elapsed > 0:
            rate_text = format_scientific(processed_pixels / metric_elapsed, "px/s")
            self.rate_card.value_label.setText(rate_text)
            self.node_table.set_rate_for_all(rate_text)
        self.node_table.mark_complete()
        output += (
            "\n\nMetrica de rendimiento:\n"
            f"Pixeles procesados: {format_scientific(processed_pixels, 'px')}\n"
            f"Rendimiento: {rate_text}\n"
        )
        self.log_box.setText(output)
        self.run_button.setEnabled(True)
        self.abort_button.setEnabled(False)
        self.system_state.setText("Estado: Listo")
        self.updated_at.setText("Datos actualizados: " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    def handle_failed(self, message):
        self.update_processed_progress(0)
        self.log_box.setText(message)
        self.run_button.setEnabled(True)
        self.abort_button.setEnabled(False)
        self.system_state.setText("Estado: Requiere configuración")

    def handle_aborted(self, message):
        self.update_processed_progress()
        self.log_box.setText(message)
        self.run_button.setEnabled(True)
        self.abort_button.setEnabled(False)
        self.system_state.setText("Estado: Abortado")
        self.updated_at.setText("Datos actualizados: " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    def show_about(self):
        AboutDialog(self).exec()

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background: #f7f9fc;
                color: #122033;
                font-size: 14px;
            }
            QLabel, QCheckBox {
                background: transparent;
            }
            #sidebar {
                background: #f2f5f9;
                border-right: 1px solid #d5dbe4;
            }
            #sideTitle, #fieldLabel, QGroupBox {
                font-weight: 700;
            }
            #courseInfo {
                color: #243b5a;
                font-weight: 700;
                line-height: 1.25;
            }
            #title {
                font-size: 28px;
                font-weight: 800;
            }
            #subtitle, #muted, #statusNote {
                color: #3c4b63;
            }
            #sectionTitle {
                font-size: 18px;
                font-weight: 800;
            }
            QPushButton {
                background: #ffffff;
                border: 1px solid #cfd7e3;
                border-radius: 6px;
                padding: 9px 14px;
            }
            QPushButton:hover {
                border-color: #0b6d82;
            }
            #navButton:checked, #threadButton:checked, #primaryButton {
                background: #076d82;
                color: white;
                border: 1px solid #076d82;
                font-weight: 700;
            }
            #dangerButton {
                background: #b42318;
                color: white;
                border: 1px solid #b42318;
                font-weight: 700;
            }
            #dangerButton:disabled {
                background: #e3e8ef;
                color: #697586;
                border: 1px solid #cfd7e3;
            }
            #navButton, #threadButton {
                font-weight: 700;
            }
            #systemBox, QGroupBox, #card, #metricCard, #placeholderCard, #progressCard, #optionsCard, #nodeCard {
                background: #ffffff;
                border: 1px solid #d7dee8;
                border-radius: 8px;
            }
            QGroupBox {
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                top: 0px;
                padding: 0 4px;
                background: transparent;
            }
            #dropZone {
                background: #ffffff;
                border: 2px dashed #aeb9c8;
                border-radius: 8px;
                min-height: 190px;
            }
            #dropZone[active="true"] {
                border-color: #076d82;
                background: #eef8fb;
            }
            #dropIcon {
                color: #076d82;
                font-size: 44px;
                font-weight: 700;
            }
            #dropTitle {
                font-weight: 800;
            }
            #pathBox {
                background: #ffffff;
                border: 1px solid #cfd7e3;
                border-radius: 6px;
                padding: 10px 12px;
            }
            QProgressBar {
                border: 1px solid #d7dee8;
                border-radius: 4px;
                background: #e8edf4;
                text-align: center;
                min-height: 18px;
            }
            QProgressBar::chunk {
                background: #076d82;
                border-radius: 4px;
            }
            #metricCard {
                min-width: 0px;
                min-height: 86px;
                padding: 8px;
            }
            #metricValue {
                font-size: 22px;
                font-weight: 800;
            }
            #tableHeader, #tableTotal {
                font-weight: 800;
            }
            #activeText {
                color: #22863a;
                font-weight: 700;
            }
            #badge {
                color: #076d82;
                font-weight: 800;
            }
            QTextEdit {
                background: #ffffff;
                border: 1px solid #d7dee8;
                border-radius: 8px;
                min-height: 150px;
                font-family: Menlo, Consolas, monospace;
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())
