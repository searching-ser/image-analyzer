#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>
#include "selec_proc.h"


void get_base_name(const char *path, char *output) {
    const char *start = strrchr(path, '/');
    if (!start) start = strrchr(path, '\\');
    start = start ? start + 1 : path;

    strcpy(output, start);

    char *dot = strrchr(output, '.');
    if (dot) *dot = '\0';
}

int main(int argc, char *argv[])
{
    if (argc < 3) {
        printf("Uso: para_image.exe <threads> img1.bmp ... [--vg --vc --hg --hc --bg --bc]\n");
        return 1;
    }

    int num_threads = atoi(argv[1]);


    int do_vg = 0; //vertical gris
    int do_vc = 0; //vertical color
    int do_hg = 0; //horizontal gris
    int do_hc = 0; //horizontal color
    int do_bg = 0; //blur gris
    int do_bc = 0; //blur color


    for (int i = 2; i < argc; i++) {
        if (strcmp(argv[i], "--vg") == 0) do_vg = 1;
        if (strcmp(argv[i], "--vc") == 0) do_vc = 1;
        if (strcmp(argv[i], "--hg") == 0) do_hg = 1;
        if (strcmp(argv[i], "--hc") == 0) do_hc = 1;
        if (strcmp(argv[i], "--bg") == 0) do_bg = 1;
        if (strcmp(argv[i], "--bc") == 0) do_bc = 1;
    }

    if (!do_vg && !do_vc && !do_hg && !do_hc && !do_bg && !do_bc) {
        do_vg = do_vc = do_hg = do_hc = do_bg = do_bc = 1;
    }

    omp_set_num_threads(num_threads);

    double t_start = omp_get_wtime();

    #pragma omp parallel for
    for (int i = 2; i < argc; i++) {

   
        if (argv[i][0] == '-') continue;

        char *path = argv[i];

        char base[100];
        get_base_name(path, base);

        char mask[120];

        if (do_vg) {
            sprintf(mask, "%s_vg", base);
            inv_img(mask, path);
        }

        if (do_vc) {
            sprintf(mask, "%s_vc", base);
            inv_img_color(mask, path);
        }

        if (do_hg) {
            sprintf(mask, "%s_hg", base);
            inv_img_grey_horizontal(mask, path);
        }

        if (do_hc) {
            sprintf(mask, "%s_hc", base);
            inv_img_color_horizontal(mask, path);
        }

        if (do_bg) {
            sprintf(mask, "%s_bg", base);
            desenfoque_grey(path, mask, 27);
        }

        if (do_bc) {
            sprintf(mask, "%s_bc", base);
            desenfoque(path, mask, 27);
        }
    }

    double t_end = omp_get_wtime();

    printf("Procesamiento terminado con %d threads.\n", num_threads);
    printf("Tiempo total de ejecucion: %f segundos\n", t_end - t_start);

    return 0;
}