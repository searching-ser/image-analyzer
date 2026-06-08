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
from PySide6.QtGui import QPainter, QPen, QTextCursor
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
    "-localhost", MPI_MASTER_HOST,
    "-f", MPI_MACHINEFILE,
    "-prepend-rank",
]
MPI_ENV = {} if LOCAL_ONLY_TESTING else {
    "FI_PROVIDER": "tcp",
    "FI_TCP_IFACE": "tailscale0",
    "LD_LIBRARY_PATH": "/opt/mpich-4.2.0/lib",
}

MAX_UI_IMAGES = 600
MAX_BACKEND_IMAGES = 10 if LOCAL_ONLY_TESTING else MAX_UI_IMAGES
PROCESS_OPTIONS = [
    ("Escala de grises", (), "placeholder"),
    ("Espejo horizontal color", ("--hc",), "functional"),
    ("Espejo vertical color", ("--vc",), "functional"),
    ("Espejo horizontal gris", ("--hg",), "functional"),
    ("Espejo vertical gris", ("--vg",), "functional"),
    ("Blur kernel 55-155", ("--bg", "--bc"), "functional"),
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


class TrendChart(QFrame):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(220)
        self.setObjectName("card")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(24, 58, -24, -44)

        painter.setPen(QPen(Qt.GlobalColor.lightGray, 1))
        for index in range(5):
            y = rect.top() + index * rect.height() / 4
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))

        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawText(18, 26, "Rendimiento en el tiempo")

        painter.setPen(QPen(Qt.GlobalColor.darkCyan, 2, Qt.DashLine))
        y_mid = rect.center().y()
        painter.drawLine(rect.left(), y_mid, rect.right(), y_mid)

        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawText(rect.left(), rect.bottom() + 22, "00:00")
        painter.drawText(rect.center().x() - 24, rect.bottom() + 22, "01:00")
        painter.drawText(rect.right() - 44, rect.bottom() + 22, "02:00")

        painter.setPen(QPen(Qt.GlobalColor.darkCyan, 1))
        painter.drawText(rect.left(), 48, "Placeholder - pendiente de métricas en vivo")


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


@dataclass
class RunRequest:
    image_paths: list
    selected_flags: list
    thread_count: str


class ProcessingWorker(QThread):
    finished = Signal(str, int, float)
    failed = Signal(str)
    log_received = Signal(str)

    def __init__(self, request):
        super().__init__()
        self.request = request

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
                existing_bmp.unlink()

            for index, source_text in enumerate(self.request.image_paths[:MAX_BACKEND_IMAGES]):
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

        common_args = [self.request.thread_count, str(SHARED_OUTPUT_DIR), str(SHARED_INPUT_DIR), *self.request.selected_flags]
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
            process = subprocess.Popen(
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

        if process.stdout is not None:
            for line in process.stdout:
                output_parts.append(line)
                self.log_received.emit(line)

        returncode = process.wait()
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
        self.costs_page = self.build_costs_page()
        self.stack.addWidget(self.metrics_page)
        self.stack.addWidget(self.costs_page)

        self.apply_styles()
        self.refresh_metrics()

    def build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(286)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 26, 20, 20)
        layout.setSpacing(12)

        members_title = QLabel("Integrantes")
        members_title.setObjectName("sideTitle")
        layout.addWidget(members_title)
        for member in TEAM_MEMBERS:
            layout.addWidget(QLabel(member))

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        layout.addWidget(divider)

        views = QLabel("Vistas")
        views.setObjectName("sideTitle")
        layout.addWidget(views)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_metrics = QPushButton("Métricas")
        self.nav_metrics.setObjectName("navButton")
        self.nav_metrics.setCheckable(True)
        self.nav_metrics.setChecked(True)
        self.nav_costs = QPushButton("Costos")
        self.nav_costs.setObjectName("navButton")
        self.nav_costs.setCheckable(True)
        self.nav_group.addButton(self.nav_metrics, 0)
        self.nav_group.addButton(self.nav_costs, 1)
        self.nav_group.idClicked.connect(self.show_view)
        layout.addWidget(self.nav_metrics)
        layout.addWidget(self.nav_costs)
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
        for item in [self.system_state, self.system_user, self.system_version, self.system_date]:
            system_layout.addWidget(item)
        layout.addWidget(system)
        return sidebar

    def show_view(self, index):
        self.stack.setCurrentIndex(index)

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

        split = QHBoxLayout()
        split.setSpacing(16)
        split.addWidget(self.info_card("Secciones funcionales", "Selección de carpeta BMP, detección de hasta 600 archivos, cálculo de píxeles, selección de opciones conectadas al backend, threads OpenMP y ejecución MPI en segundo plano.", "Conectado"))
        split.addWidget(self.placeholder_card("Secciones placeholder", "Escala de grises independiente, ETA real por lote completo de 600 imágenes, métricas por nodo en vivo, comparativa AWS y enlaces de reporte/presentación."))
        layout.addLayout(split)

        self.selection_note = QLabel()
        self.selection_note.setObjectName("statusNote")
        self.selection_note.setWordWrap(True)
        self.selection_note.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout.addWidget(self.selection_note)

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
        self.progress_count = QLabel("0 / 0 imágenes conectadas al backend actual")
        self.progress_eta = QLabel("Tiempo estimado restante: pendiente")
        self.progress_count.setWordWrap(True)
        self.progress_eta.setWordWrap(True)
        self.progress_count.setMinimumWidth(0)
        self.progress_eta.setMinimumWidth(0)
        self.progress_count.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.progress_eta.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        progress_meta.addWidget(self.progress_count, 1)
        progress_meta.addWidget(self.progress_eta, 1)
        progress_layout.addLayout(progress_meta)
        layout.addWidget(self.progress_group)

        cards = QHBoxLayout()
        cards.setSpacing(16)
        self.pixel_card = self.metric_card("Píxeles procesables", "0 px")
        self.batch_card = self.metric_card("Imágenes seleccionadas", "0")
        self.rate_card = self.metric_card("Rendimiento", "Pendiente")
        self.time_card = self.metric_card("Tiempo total", "Pendiente")
        cards.addWidget(self.pixel_card)
        cards.addWidget(self.batch_card)
        cards.addWidget(self.rate_card)
        cards.addWidget(self.time_card)
        layout.addLayout(cards)

        lower = QHBoxLayout()
        lower.setSpacing(16)
        lower.addWidget(TrendChart(), 1)
        lower.addWidget(NodeTable(), 1)
        layout.addLayout(lower)

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
        action_layout.addStretch()
        self.run_button = QPushButton("Procesar carga distribuida")
        self.run_button.setObjectName("primaryButton")
        self.run_button.clicked.connect(self.run_program)
        action_layout.addWidget(self.run_button)
        layout.addLayout(action_layout)
        outer_layout.addLayout(layout)
        return panel

    def build_costs_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Costos")
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addWidget(self.placeholder_card("Comparativa anual AWS", "Reservado para integrar la estimación de operación 8 horas diarias de lunes a viernes contra un servicio AWS equivalente."))
        layout.addWidget(self.placeholder_card("Reporte y presentación", "Reservado para enlazar el reporte de GitHub y la presentación final solicitada en el reto."))
        layout.addStretch()
        return page

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
        self.input_path_label.setText(str(folder_path))
        self.refresh_metrics()

    def selected_thread_count(self):
        button = self.thread_group.checkedButton()
        return button.text() if button else "12"

    def selected_flags(self):
        flags = []
        for checkbox in self.option_checks:
            if not checkbox.isChecked():
                continue
            for flag in checkbox.flags:
                if flag not in flags:
                    flags.append(flag)
        return flags

    def refresh_metrics(self):
        image_count = len(self.image_paths)
        pixels = sum(read_bmp_pixels(path) for path in self.image_paths)
        runnable = min(image_count, MAX_BACKEND_IMAGES)

        self.progress_bar.setValue(100 if self.last_elapsed and runnable else 0)
        self.progress_count.setText(f"0 / {runnable} imágenes conectadas al backend actual")
        self.progress_eta.setText("Tiempo estimado restante: placeholder hasta ejecución asíncrona por lote completo")
        self.pixel_card.value_label.setText(format_scientific(pixels, "px"))
        if image_count > MAX_BACKEND_IMAGES:
            self.batch_card.value_label.setText(f"{runnable} de {image_count}")
        else:
            self.batch_card.value_label.setText(str(image_count))
        self.selection_note.setText(
            f"Funcional: selección de carpeta BMP, opciones, threads y ejecución MPI para {MAX_BACKEND_IMAGES} imágenes. "
            f"Placeholder: orquestación completa de hasta {MAX_UI_IMAGES} imágenes, ETA en vivo, costos AWS y reporte."
        )
        self.updated_at.setText("Datos actualizados: " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    def run_program(self):
        if not self.image_paths:
            self.log_box.setText("No hay carpeta con imágenes BMP seleccionada.")
            return
        self.run_button.setEnabled(False)
        self.system_state.setText("Estado: Ejecución")
        self.progress_bar.setRange(0, 0)
        self.log_box.setText("Procesando carga distribuida...\n")
        request = RunRequest(self.image_paths, self.selected_flags(), self.selected_thread_count())
        self.worker = ProcessingWorker(request)
        self.worker.log_received.connect(self.handle_log_received)
        self.worker.finished.connect(self.handle_finished)
        self.worker.failed.connect(self.handle_failed)
        self.worker.start()

    def handle_log_received(self, text):
        self.log_box.moveCursor(QTextCursor.MoveOperation.End)
        self.log_box.insertPlainText(text)
        self.log_box.moveCursor(QTextCursor.MoveOperation.End)

    def handle_finished(self, output, returncode, elapsed):
        self.last_elapsed = elapsed
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100 if returncode == 0 else 0)
        runnable = min(len(self.image_paths), MAX_BACKEND_IMAGES)
        if returncode == 0:
            self.progress_count.setText(f"{runnable} / {runnable} imágenes conectadas al backend actual")
        self.progress_eta.setText("Tiempo estimado restante: 00:00:00")
        self.time_card.value_label.setText(f"{elapsed:.1f} s")
        pixels = sum(read_bmp_pixels(path) for path in self.image_paths[:MAX_BACKEND_IMAGES])
        if elapsed > 0:
            self.rate_card.value_label.setText(format_scientific(pixels / elapsed, "px/s"))
        match = re.search(r"Tiempo total MPI:\s*([0-9.]+)", output)
        if match:
            self.time_card.value_label.setText(f"{float(match.group(1)):.1f} s")
        self.log_box.setText(output)
        self.run_button.setEnabled(True)
        self.system_state.setText("Estado: Listo")
        self.updated_at.setText("Datos actualizados: " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    def handle_failed(self, message):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.log_box.setText(message)
        self.run_button.setEnabled(True)
        self.system_state.setText("Estado: Requiere configuración")

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
