# Image Analyzer

Image Analyzer is a small desktop GUI for processing BMP images with a C/OpenMP backend. The Python app in `main.py` lets you select or drag up to 10 `.bmp` files, choose which transformations to apply, select the thread count, and run the compiled `para_image` program.

## Requirements

- Python 3.9 or newer
- A C compiler with OpenMP support
- Python dependencies from `requirements.txt`

On Windows, MinGW-w64 with OpenMP support is a good option. On macOS, the default Apple Clang usually does not include OpenMP, so install GCC with Homebrew:

```bash
brew install gcc
```

## Set Up Python

Create and activate a virtual environment:

```bash
python3 -m venv .venv
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the GUI dependency:

```bash
pip install -r requirements.txt
```

## Compile the Image Processor

`main.py` expects the executable to be named `para_image.exe`.

On Windows with GCC:

```powershell
gcc -Wall -Wextra -std=c11 -fopenmp para_image.c selec_proc.c -o para_image.exe
```

On macOS with Homebrew GCC, use the installed GCC version. For example:

```bash
gcc-15 -Wall -Wextra -std=c11 -fopenmp para_image.c selec_proc.c -o para_image.exe
```

If your installed version is different, check it with:

```bash
ls /opt/homebrew/bin/gcc-*
```

On Linux:

```bash
gcc -Wall -Wextra -std=c11 -fopenmp para_image.c selec_proc.c -o para_image.exe
```

## Run the GUI

From the project folder, run:

```bash
python main.py
```

## Use the App

1. Add `.bmp` files with the file picker or drag them into the list.
2. Select one or more processing options:
   - Vertical Gris (`--vg`)
   - Vertical Color (`--vc`)
   - Horizontal Gris (`--hg`)
   - Horizontal Color (`--hc`)
   - Blur Gris (`--bg`)
   - Blur Color (`--bc`)
3. Choose the number of threads: `6`, `12`, or `18`.
4. Click **Procesar**.

If no processing option is selected, the C program applies all transformations.

## Output

Generated BMP files are saved in the `img` folder. Output names use the source image name plus the selected transformation suffix.

Examples:

```text
img/prueba1_vg.bmp
img/prueba1_vc.bmp
img/prueba1_hg.bmp
img/prueba1_hc.bmp
img/prueba1_bg.bmp
img/prueba1_bc.bmp
```

The app displays the processor output and total execution time in the results box.
