# Image Processing Benchmark

This project processes 3 BMP images with OpenMP using 18 sections:

- vertical inversion
- vertical color inversion
- horizontal grayscale inversion
- horizontal color inversion
- color blur
- grayscale blur

The program runs the full workload three times using:

- 6 threads
- 12 threads
- 18 threads

## Input Images

Place these three source images inside the `img` folder:

```text
img/img1.bmp
img/img2.bmp
img/img3.bmp
```

They should be large BMP files.

## Compile

From this folder, run:

```powershell
gcc -Wall -Wextra -std=c11 -fopenmp para_image.c selec_proc.c -o para_image.exe
```

## Run

Run the program with:

```powershell
.\para_image.exe
```

## Output

The generated BMP files are saved in the `img` folder.

Their names include:

- image number
- thread count
- transformation name

Example:

```text
img/1_t6_inv_ver.bmp
img/2_t12_col_hor.bmp
img/3_t18_desenf_gry.bmp
```

## Timing Results

Execution times are written to:

```text
resultados_rendimiento.csv
```

The CSV stores one row for each run:

- 6 threads
- 12 threads
- 18 threads
