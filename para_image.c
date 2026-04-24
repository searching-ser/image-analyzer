#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>
#include "selec_proc.h"

int main()
{
    int threads_list[3] = {6, 12, 18};
    int i;
    FILE *fptr;
    FILE *reporte;
    char data[80] = "arcl.txt";


    reporte = fopen("resultados_rendimiento.csv", "w");
    if (reporte == NULL) {
        printf("Error\n");
        exit(1);
    }
    fprintf(reporte, "threads,tiempo_segundos\n");

    for (i = 0; i < 3; i++) {
        int num_threads = threads_list[i];
        double t_start;
        double t_end;

        char img1_inv_ver[80];
        char img1_col_ver[80];
        char img1_inv_hor[80];
        char img1_col_hor[80];
        char img1_desenf_col[80];
        char img1_desenf_gry[80];

        char img2_inv_ver[80];
        char img2_col_ver[80];
        char img2_inv_hor[80];
        char img2_col_hor[80];
        char img2_desenf_col[80];
        char img2_desenf_gry[80];

        char img3_inv_ver[80];
        char img3_col_ver[80];
        char img3_inv_hor[80];
        char img3_col_hor[80];
        char img3_desenf_col[80];
        char img3_desenf_gry[80];

        sprintf(img1_inv_ver, "1_t%d_inv_ver", num_threads);
        sprintf(img1_col_ver, "1_t%d_col_ver", num_threads);
        sprintf(img1_inv_hor, "1_t%d_inv_hor", num_threads);
        sprintf(img1_col_hor, "1_t%d_col_hor", num_threads);
        sprintf(img1_desenf_col, "1_t%d_desenf_col", num_threads);
        sprintf(img1_desenf_gry, "1_t%d_desenf_gry", num_threads);

        sprintf(img2_inv_ver, "2_t%d_inv_ver", num_threads);
        sprintf(img2_col_ver, "2_t%d_col_ver", num_threads);
        sprintf(img2_inv_hor, "2_t%d_inv_hor", num_threads);
        sprintf(img2_col_hor, "2_t%d_col_hor", num_threads);
        sprintf(img2_desenf_col, "2_t%d_desenf_col", num_threads);
        sprintf(img2_desenf_gry, "2_t%d_desenf_gry", num_threads);

        sprintf(img3_inv_ver, "3_t%d_inv_ver", num_threads);
        sprintf(img3_col_ver, "3_t%d_col_ver", num_threads);
        sprintf(img3_inv_hor, "3_t%d_inv_hor", num_threads);
        sprintf(img3_col_hor, "3_t%d_col_hor", num_threads);
        sprintf(img3_desenf_col, "3_t%d_desenf_col", num_threads);
        sprintf(img3_desenf_gry, "3_t%d_desenf_gry", num_threads);

        omp_set_num_threads(num_threads);

        /* Medir tiempo */
        t_start = omp_get_wtime();

        /*
         * Las tres imagenes grandes ("img1.bmp", "img2.bmp", "img3.bmp")
         * deben estar dentro de "./img/". Se asume que existen.
         */

        #pragma omp parallel
        {
            #pragma omp sections
            {
                /* ================== IMAGEN 1 ================== */
                #pragma omp section
                inv_img(img1_inv_ver, "./img/img1.bmp");

                #pragma omp section
                inv_img_color(img1_col_ver, "./img/img1.bmp");

                #pragma omp section
                inv_img_grey_horizontal(img1_inv_hor, "./img/img1.bmp");

                #pragma omp section
                inv_img_color_horizontal(img1_col_hor, "./img/img1.bmp");

                #pragma omp section
                desenfoque("./img/img1.bmp", img1_desenf_col, 27);

                #pragma omp section
                desenfoque_grey("./img/img1.bmp", img1_desenf_gry, 27);


                /* ================== IMAGEN 2 ================== */
                #pragma omp section
                inv_img(img2_inv_ver, "./img/img2.bmp");

                #pragma omp section
                inv_img_color(img2_col_ver, "./img/img2.bmp");

                #pragma omp section
                inv_img_grey_horizontal(img2_inv_hor, "./img/img2.bmp");

                #pragma omp section
                inv_img_color_horizontal(img2_col_hor, "./img/img2.bmp");

                #pragma omp section
                desenfoque("./img/img2.bmp", img2_desenf_col, 27);

                #pragma omp section
                desenfoque_grey("./img/img2.bmp", img2_desenf_gry, 27);


                /* ================== IMAGEN 3 ================== */
                #pragma omp section
                inv_img(img3_inv_ver, "./img/img3.bmp");

                #pragma omp section
                inv_img_color(img3_col_ver, "./img/img3.bmp");

                #pragma omp section
                inv_img_grey_horizontal(img3_inv_hor, "./img/img3.bmp");

                #pragma omp section
                inv_img_color_horizontal(img3_col_hor, "./img/img3.bmp");

                #pragma omp section
                desenfoque("./img/img3.bmp", img3_desenf_col, 27);

                #pragma omp section
                desenfoque_grey("./img/img3.bmp", img3_desenf_gry, 27);
            }
        }

        t_end = omp_get_wtime();
        printf("Procesamiento terminado con %d threads.\n", num_threads);
        printf("Tiempo total de ejecucion: %f segundos\n", t_end - t_start);
        fprintf(reporte, "%d,%f\n", num_threads, t_end - t_start);
    }

    fclose(reporte);
    return 0;
}
