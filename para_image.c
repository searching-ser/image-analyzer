#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>
#include "selec_proc.h"

int main()
{
    int num_threads = 18;
    double t_start;
    double t_end;

    omp_set_num_threads(num_threads);

    t_start = omp_get_wtime();

    #pragma omp parallel
    {
        #pragma omp sections
        {
            /* ================== IMAGEN 1 ================== */
            #pragma omp section
            inv_img("1_inv_ver", "./input/prueba1.bmp");

            #pragma omp section
            inv_img_color("1_col_ver", "./input/prueba1.bmp");

            #pragma omp section
            inv_img_grey_horizontal("1_inv_hor", "./input/prueba1.bmp");

            #pragma omp section
            inv_img_color_horizontal("1_col_hor", "./input/prueba1.bmp");

            #pragma omp section
            desenfoque("./input/prueba1.bmp", "1_desenf_col", 27);

            #pragma omp section
            desenfoque_grey("./input/prueba1.bmp", "1_desenf_gry", 27);

            /* ================== IMAGEN 2 ================== */
            #pragma omp section
            inv_img("2_inv_ver", "./input/prueba2.bmp");

            #pragma omp section
            inv_img_color("2_col_ver", "./input/prueba2.bmp");

            #pragma omp section
            inv_img_grey_horizontal("2_inv_hor", "./input/prueba2.bmp");

            #pragma omp section
            inv_img_color_horizontal("2_col_hor", "./input/prueba2.bmp");

            #pragma omp section
            desenfoque("./input/prueba2.bmp", "2_desenf_col", 27);

            #pragma omp section
            desenfoque_grey("./input/prueba2.bmp", "2_desenf_gry", 27);

            /* ================== IMAGEN 3 ================== */
            #pragma omp section
            inv_img("3_inv_ver", "./input/prueba3.bmp");

            #pragma omp section
            inv_img_color("3_col_ver", "./input/prueba3.bmp");

            #pragma omp section
            inv_img_grey_horizontal("3_inv_hor", "./input/prueba3.bmp");

            #pragma omp section
            inv_img_color_horizontal("3_col_hor", "./input/prueba3.bmp");

            #pragma omp section
            desenfoque("./input/prueba3.bmp", "3_desenf_col", 27);

            #pragma omp section
            desenfoque_grey("./input/prueba3.bmp", "3_desenf_gry", 27);
        }
    }

    t_end = omp_get_wtime();
    printf("Procesamiento terminado con %d threads.\n", num_threads);
    printf("Tiempo total de ejecucion: %f segundos\n", t_end - t_start);

    return 0;
}
