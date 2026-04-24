#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "selec_proc.h"

extern void inv_img(char mask[], char path[])
{
    FILE *image, *outputImage, *lecturas, *fptr;
    char add_char[80] = "./img/";
    strcat(add_char, mask);
    strcat(add_char, ".bmp");
    printf("%s\n", add_char);

    image = fopen(path, "rb");              //Original Image
    outputImage = fopen(add_char, "wb");

    if (image == NULL || outputImage == NULL) {
        printf("Error opening file\n");
        return;
    }

    //Definition of variables
    int i, j;
    long ancho, tam, bpp;
    long alto;
    unsigned char r, g, b;                  //Pixel

    unsigned char xx[54];
    for (i = 0; i < 54; i++) {
        xx[i] = fgetc(image);
        fputc(xx[i], outputImage);          //Copia cabecera a nueva imagen
    }

    tam = (long)xx[4] * 65536 + (long)xx[3] * 256 + (long)xx[2];
    bpp = (long)xx[29] * 256 + (long)xx[28];
    ancho = (long)xx[20] * 65536 + (long)xx[19] * 256 + (long)xx[18];
    alto = (long)xx[24] * 65536 + (long)xx[23] * 256 + (long)xx[22];

    printf("tamano archivo %li\n", tam);
    printf("bits por pixel %li\n", bpp);
    printf("largo img %li\n", alto);
    printf("ancho img %li\n", ancho);

    unsigned char *arr_in = (unsigned char *)malloc(ancho * alto * 3 * sizeof(unsigned char));
    if (arr_in == NULL) {
        printf("Memory not allocated.\n");
        fclose(image);
        fclose(outputImage);
        return;
    }

    j = 0;
    while (!feof(image)) {
        b = fgetc(image);
        g = fgetc(image);
        r = fgetc(image);
        arr_in[j] = 255 - b;
        arr_in[j + 1] = 255 - g;
        arr_in[j + 2] = 255 - r;
        j = j + 3;
    }

    printf("lectura de datos: %d\n", j);
    for (i = 0; i < ancho * alto * 3; i++) {
        fputc(arr_in[i], outputImage);
    }

    free(arr_in);
    fclose(image);
    fclose(outputImage);
    (void)lecturas;
    (void)fptr;
}

extern void inv_img_grey(char mask[], char path[])
{
    FILE *image, *outputImage, *lecturas, *fptr;
    char add_char[80] = "./img/";
    strcat(add_char, mask);
    strcat(add_char, ".bmp");
    printf("%s\n", add_char);

    image = fopen(path, "rb");              //Original Image
    outputImage = fopen(add_char, "wb");

    if (image == NULL || outputImage == NULL) {
        printf("Error opening file\n");
        return;
    }

    //Definition of variables
    int i, j;
    long ancho, tam, bpp;
    long alto;
    unsigned char r, g, b, pixel;           //Pixel

    unsigned char xx[54];
    for (i = 0; i < 54; i++) {
        xx[i] = fgetc(image);
        fputc(xx[i], outputImage);          //Copia cabecera a nueva imagen
    }

    tam = (long)xx[4] * 65536 + (long)xx[3] * 256 + (long)xx[2];
    bpp = (long)xx[29] * 256 + (long)xx[28];
    ancho = (long)xx[20] * 65536 + (long)xx[19] * 256 + (long)xx[18];
    alto = (long)xx[24] * 65536 + (long)xx[23] * 256 + (long)xx[22];

    printf("tamano archivo %li\n", tam);
    printf("bits por pixel %li\n", bpp);
    printf("largo img %li\n", alto);
    printf("ancho img %li\n", ancho);

    unsigned char *arr_in = (unsigned char *)malloc(ancho * alto * sizeof(unsigned char));
    if (arr_in == NULL) {
        printf("Memory not allocated.\n");
        fclose(image);
        fclose(outputImage);
        return;
    }

    j = 0;
    while (!feof(image)) {
        b = fgetc(image);
        g = fgetc(image);
        r = fgetc(image);
        pixel = 0.21 * r + 0.72 * g + 0.07 * b;
        arr_in[j] = pixel;
        j++;
    }

    printf("lectura de datos: %d\n", j * 3);
    printf("elementos faltantes: %ld\n", (ancho * alto) - j);
    for (i = 0; i < ancho * alto; i++) {
        fputc(arr_in[i], outputImage);
        fputc(arr_in[i], outputImage);
        fputc(arr_in[i], outputImage);
    }

    free(arr_in);
    fclose(image);
    fclose(outputImage);
    (void)lecturas;
    (void)fptr;
}

extern void inv_img_color(char mask[], char path[])
{
    FILE *image, *outputImage, *lecturas, *fptr;
    char add_char[80] = "./img/";
    strcat(add_char, mask);
    strcat(add_char, ".bmp");
    printf("%s\n", add_char);

    image = fopen(path, "rb");              //Original Image
    outputImage = fopen(add_char, "wb");

    if (image == NULL || outputImage == NULL) {
        printf("Error opening file\n");
        return;
    }

    //Definition of variables
    int i, j;
    long ancho, tam, bpp;
    long alto;
    unsigned char r, g, b;                  //Pixel

    unsigned char xx[54];
    for (i = 0; i < 54; i++) {
        xx[i] = fgetc(image);
        fputc(xx[i], outputImage);          //Copia cabecera a nueva imagen
    }

    tam = (long)xx[4] * 65536 + (long)xx[3] * 256 + (long)xx[2];
    bpp = (long)xx[29] * 256 + (long)xx[28];
    ancho = (long)xx[20] * 65536 + (long)xx[19] * 256 + (long)xx[18];
    alto = (long)xx[24] * 65536 + (long)xx[23] * 256 + (long)xx[22];

    printf("tamano archivo %li\n", tam);
    printf("bits por pixel %li\n", bpp);
    printf("largo img %li\n", alto);
    printf("ancho img %li\n", ancho);

    unsigned char *arr_in = (unsigned char *)malloc(ancho * alto * 3 * sizeof(unsigned char));
    if (arr_in == NULL) {
        printf("Memory not allocated.\n");
        fclose(image);
        fclose(outputImage);
        return;
    }

    j = 0;
    while (!feof(image)) {
        b = fgetc(image);
        g = fgetc(image);
        r = fgetc(image);
        arr_in[j] = g;
        arr_in[j + 1] = r;
        arr_in[j + 2] = b;
        j = j + 3;
    }

    printf("lectura de datos: %d\n", j);
    for (i = 0; i < ancho * alto * 3; i++) {
        fputc(arr_in[i], outputImage);
    }

    free(arr_in);
    fclose(image);
    fclose(outputImage);
    (void)lecturas;
    (void)fptr;
}

extern void inv_img_grey_horizontal(char mask[], char path[])
{
    FILE *image, *outputImage, *lecturas, *fptr;
    char add_char[80] = "./img/";
    strcat(add_char, mask);
    strcat(add_char, ".bmp");
    printf("%s\n", add_char);

    image = fopen(path, "rb");              //Original Image
    outputImage = fopen(add_char, "wb");

    if (image == NULL || outputImage == NULL) {
        printf("Error opening file\n");
        return;
    }

    //Definition of variables
    int i, j, fila, col, pos;
    long ancho, tam, bpp;
    long alto;
    unsigned char r, g, b;                  //Pixel

    unsigned char xx[54];
    for (i = 0; i < 54; i++) {
        xx[i] = fgetc(image);
        fputc(xx[i], outputImage);          //Copia cabecera a nueva imagen
    }

    tam = (long)xx[4] * 65536 + (long)xx[3] * 256 + (long)xx[2];
    bpp = (long)xx[29] * 256 + (long)xx[28];
    ancho = (long)xx[20] * 65536 + (long)xx[19] * 256 + (long)xx[18];
    alto = (long)xx[24] * 65536 + (long)xx[23] * 256 + (long)xx[22];

    printf("tamano archivo %li\n", tam);
    printf("bits por pixel %li\n", bpp);
    printf("largo img %li\n", alto);
    printf("ancho img %li\n", ancho);

    unsigned char *arr_in = (unsigned char *)malloc(ancho * alto * 3 * sizeof(unsigned char));
    if (arr_in == NULL) {
        printf("Memory not allocated.\n");
        fclose(image);
        fclose(outputImage);
        return;
    }

    j = 0;
    for (i = 0; i < ancho * alto; i++) {
        b = fgetc(image);
        g = fgetc(image);
        r = fgetc(image);
        unsigned char pixel = 0.21 * r + 0.72 * g + 0.07 * b;
        arr_in[j] = pixel;
        arr_in[j + 1] = pixel;
        arr_in[j + 2] = pixel;
        j = j + 3;
    }

    printf("lectura de datos: %d\n", j);
    for (fila = 0; fila < alto; fila++) {
        for (col = ancho - 1; col >= 0; col--) {
            pos = (fila * ancho * 3) + (col * 3);
            fputc(arr_in[pos], outputImage);
            fputc(arr_in[pos + 1], outputImage);
            fputc(arr_in[pos + 2], outputImage);
        }
    }

    free(arr_in);
    fclose(image);
    fclose(outputImage);
    (void)lecturas;
    (void)fptr;
}

extern void inv_img_color_horizontal(char mask[], char path[])
{
    FILE *image, *outputImage, *lecturas, *fptr;
    char add_char[80] = "./img/";
    strcat(add_char, mask);
    strcat(add_char, ".bmp");
    printf("%s\n", add_char);

    image = fopen(path, "rb");              //Original Image
    outputImage = fopen(add_char, "wb");

    if (image == NULL || outputImage == NULL) {
        printf("Error opening file\n");
        return;
    }

    //Definition of variables
    int i, j, fila, col, pos;
    long ancho, tam, bpp;
    long alto;
    unsigned char r, g, b;                  //Pixel

    unsigned char xx[54];
    for (i = 0; i < 54; i++) {
        xx[i] = fgetc(image);
        fputc(xx[i], outputImage);          //Copia cabecera a nueva imagen
    }

    tam = (long)xx[4] * 65536 + (long)xx[3] * 256 + (long)xx[2];
    bpp = (long)xx[29] * 256 + (long)xx[28];
    ancho = (long)xx[20] * 65536 + (long)xx[19] * 256 + (long)xx[18];
    alto = (long)xx[24] * 65536 + (long)xx[23] * 256 + (long)xx[22];

    printf("tamano archivo %li\n", tam);
    printf("bits por pixel %li\n", bpp);
    printf("largo img %li\n", alto);
    printf("ancho img %li\n", ancho);

    unsigned char *arr_in = (unsigned char *)malloc(ancho * alto * 3 * sizeof(unsigned char));
    if (arr_in == NULL) {
        printf("Memory not allocated.\n");
        fclose(image);
        fclose(outputImage);
        return;
    }

    j = 0;
    for (i = 0; i < ancho * alto; i++) {
        b = fgetc(image);
        g = fgetc(image);
        r = fgetc(image);
        arr_in[j] = b;
        arr_in[j + 1] = g;
        arr_in[j + 2] = r;
        j = j + 3;
    }

    printf("lectura de datos: %d\n", j);
    for (fila = 0; fila < alto; fila++) {
        for (col = ancho - 1; col >= 0; col--) {
            pos = (fila * ancho * 3) + (col * 3);
            fputc(arr_in[pos], outputImage);
            fputc(arr_in[pos + 1], outputImage);
            fputc(arr_in[pos + 2], outputImage);
        }
    }

    free(arr_in);
    fclose(image);
    fclose(outputImage);
    (void)lecturas;
    (void)fptr;
}

extern void inv_img_grey_vertical(char mask[], char path[])
{
    FILE *image, *outputImage, *lecturas, *fptr;
    char add_char[80] = "./img/";
    strcat(add_char, mask);
    strcat(add_char, ".bmp");
    printf("%s\n", add_char);

    image = fopen(path, "rb");              //Original Image
    outputImage = fopen(add_char, "wb");

    if (image == NULL || outputImage == NULL) {
        printf("Error opening file\n");
        return;
    }

    //Definition of variables
    int i, j, fila, col, pos;
    long ancho, tam, bpp;
    long alto;
    unsigned char r, g, b, pixel;           //Pixel

    unsigned char xx[54];
    for (i = 0; i < 54; i++) {
        xx[i] = fgetc(image);
        fputc(xx[i], outputImage);          //Copia cabecera a nueva imagen
    }

    tam = (long)xx[4] * 65536 + (long)xx[3] * 256 + (long)xx[2];
    bpp = (long)xx[29] * 256 + (long)xx[28];
    ancho = (long)xx[20] * 65536 + (long)xx[19] * 256 + (long)xx[18];
    alto = (long)xx[24] * 65536 + (long)xx[23] * 256 + (long)xx[22];

    printf("tamano archivo %li\n", tam);
    printf("bits por pixel %li\n", bpp);
    printf("largo img %li\n", alto);
    printf("ancho img %li\n", ancho);

    unsigned char *arr_in = (unsigned char *)malloc(ancho * alto * 3 * sizeof(unsigned char));
    if (arr_in == NULL) {
        printf("Memory not allocated.\n");
        fclose(image);
        fclose(outputImage);
        return;
    }

    j = 0;
    for (i = 0; i < ancho * alto; i++) {
        b = fgetc(image);
        g = fgetc(image);
        r = fgetc(image);
        pixel = 0.21 * r + 0.72 * g + 0.07 * b;
        arr_in[j] = pixel;
        arr_in[j + 1] = pixel;
        arr_in[j + 2] = pixel;
        j = j + 3;
    }

    printf("lectura de datos: %d\n", j);
    for (fila = alto - 1; fila >= 0; fila--) {
        for (col = 0; col < ancho; col++) {
            pos = (fila * ancho * 3) + (col * 3);
            fputc(arr_in[pos], outputImage);
            fputc(arr_in[pos + 1], outputImage);
            fputc(arr_in[pos + 2], outputImage);
        }
    }

    free(arr_in);
    fclose(image);
    fclose(outputImage);
    (void)lecturas;
    (void)fptr;
}

extern void inv_img_color_vertical(char mask[], char path[])
{
    FILE *image, *outputImage, *lecturas, *fptr;
    char add_char[80] = "./img/";
    strcat(add_char, mask);
    strcat(add_char, ".bmp");
    printf("%s\n", add_char);

    image = fopen(path, "rb");              //Original Image
    outputImage = fopen(add_char, "wb");

    if (image == NULL || outputImage == NULL) {
        printf("Error opening file\n");
        return;
    }

    //Definition of variables
    int i, j, fila, col, pos;
    long ancho, tam, bpp;
    long alto;
    unsigned char r, g, b;                  //Pixel

    unsigned char xx[54];
    for (i = 0; i < 54; i++) {
        xx[i] = fgetc(image);
        fputc(xx[i], outputImage);          //Copia cabecera a nueva imagen
    }

    tam = (long)xx[4] * 65536 + (long)xx[3] * 256 + (long)xx[2];
    bpp = (long)xx[29] * 256 + (long)xx[28];
    ancho = (long)xx[20] * 65536 + (long)xx[19] * 256 + (long)xx[18];
    alto = (long)xx[24] * 65536 + (long)xx[23] * 256 + (long)xx[22];

    printf("tamano archivo %li\n", tam);
    printf("bits por pixel %li\n", bpp);
    printf("largo img %li\n", alto);
    printf("ancho img %li\n", ancho);

    unsigned char *arr_in = (unsigned char *)malloc(ancho * alto * 3 * sizeof(unsigned char));
    if (arr_in == NULL) {
        printf("Memory not allocated.\n");
        fclose(image);
        fclose(outputImage);
        return;
    }

    j = 0;
    for (i = 0; i < ancho * alto; i++) {
        b = fgetc(image);
        g = fgetc(image);
        r = fgetc(image);
        arr_in[j] = b;
        arr_in[j + 1] = g;
        arr_in[j + 2] = r;
        j = j + 3;
    }

    printf("lectura de datos: %d\n", j);
    for (fila = alto - 1; fila >= 0; fila--) {
        for (col = 0; col < ancho; col++) {
            pos = (fila * ancho * 3) + (col * 3);
            fputc(arr_in[pos], outputImage);
            fputc(arr_in[pos + 1], outputImage);
            fputc(arr_in[pos + 2], outputImage);
        }
    }

    free(arr_in);
    fclose(image);
    fclose(outputImage);
    (void)lecturas;
    (void)fptr;
}

extern void desenfoque_grey(char path[], char mask[], int kernel)
{
    FILE *image, *outputImage, *lecturas, *fptr;
    char add_char[80] = "./img/";
    strcat(add_char, mask);
    strcat(add_char, ".bmp");
    printf("%s\n", add_char);

    image = fopen(path, "rb");              //Original Image
    outputImage = fopen(add_char, "wb");

    if (image == NULL || outputImage == NULL) {
        printf("Error opening file\n");
        return;
    }

    //Definition of variables
    int i, j, fila, col, kx, ky, pos, pos2;
    int suma, contador, radio;
    long ancho, tam, bpp;
    long alto;
    unsigned char r, g, b, pixel;           //Pixel

    unsigned char xx[54];
    for (i = 0; i < 54; i++) {
        xx[i] = fgetc(image);
        fputc(xx[i], outputImage);          //Copia cabecera a nueva imagen
    }

    tam = (long)xx[4] * 65536 + (long)xx[3] * 256 + (long)xx[2];
    bpp = (long)xx[29] * 256 + (long)xx[28];
    ancho = (long)xx[20] * 65536 + (long)xx[19] * 256 + (long)xx[18];
    alto = (long)xx[24] * 65536 + (long)xx[23] * 256 + (long)xx[22];

    printf("tamano archivo %li\n", tam);
    printf("bits por pixel %li\n", bpp);
    printf("largo img %li\n", alto);
    printf("ancho img %li\n", ancho);

    unsigned char *arr_in = (unsigned char *)malloc(ancho * alto * sizeof(unsigned char));
    unsigned char *arr_out = (unsigned char *)malloc(ancho * alto * sizeof(unsigned char));
    if (arr_in == NULL || arr_out == NULL) {
        printf("Memory not allocated.\n");
        free(arr_in);
        free(arr_out);
        fclose(image);
        fclose(outputImage);
        return;
    }

    j = 0;
    for (i = 0; i < ancho * alto; i++) {
        b = fgetc(image);
        g = fgetc(image);
        r = fgetc(image);
        pixel = 0.21 * r + 0.72 * g + 0.07 * b;
        arr_in[j] = pixel;
        j++;
    }

    radio = (kernel - 1) / 2;
    for (fila = 0; fila < alto; fila++) {
        for (col = 0; col < ancho; col++) {
            suma = 0;
            contador = 0;

            for (ky = -radio; ky <= radio; ky++) {
                for (kx = -radio; kx <= radio; kx++) {
                    if (fila + ky >= 0 && fila + ky < alto && col + kx >= 0 && col + kx < ancho) {
                        pos2 = ((fila + ky) * ancho) + (col + kx);
                        suma = suma + arr_in[pos2];
                        contador++;
                    }
                }
            }

            pos = (fila * ancho) + col;
            arr_out[pos] = suma / contador;
        }
    }

    printf("lectura de datos: %d\n", j);
    for (i = 0; i < ancho * alto; i++) {
        fputc(arr_out[i], outputImage);
        fputc(arr_out[i], outputImage);
        fputc(arr_out[i], outputImage);
    }

    free(arr_in);
    free(arr_out);
    fclose(image);
    fclose(outputImage);
    (void)lecturas;
    (void)fptr;
}

extern void desenfoque_color(char path[], char mask[], int kernel)
{
    FILE *image, *outputImage, *lecturas, *fptr;
    char add_char[80] = "./img/";
    strcat(add_char, mask);
    strcat(add_char, ".bmp");
    printf("%s\n", add_char);

    image = fopen(path, "rb");              //Original Image
    outputImage = fopen(add_char, "wb");

    if (image == NULL || outputImage == NULL) {
        printf("Error opening file\n");
        return;
    }

    //Definition of variables
    int i, j, fila, col, kx, ky, pos, pos2;
    int suma_b, suma_g, suma_r, contador, radio;
    long ancho, tam, bpp;
    long alto;
    unsigned char r, g, b;                  //Pixel

    unsigned char xx[54];
    for (i = 0; i < 54; i++) {
        xx[i] = fgetc(image);
        fputc(xx[i], outputImage);          //Copia cabecera a nueva imagen
    }

    tam = (long)xx[4] * 65536 + (long)xx[3] * 256 + (long)xx[2];
    bpp = (long)xx[29] * 256 + (long)xx[28];
    ancho = (long)xx[20] * 65536 + (long)xx[19] * 256 + (long)xx[18];
    alto = (long)xx[24] * 65536 + (long)xx[23] * 256 + (long)xx[22];

    printf("tamano archivo %li\n", tam);
    printf("bits por pixel %li\n", bpp);
    printf("largo img %li\n", alto);
    printf("ancho img %li\n", ancho);

    unsigned char *arr_in = (unsigned char *)malloc(ancho * alto * 3 * sizeof(unsigned char));
    unsigned char *arr_out = (unsigned char *)malloc(ancho * alto * 3 * sizeof(unsigned char));
    if (arr_in == NULL || arr_out == NULL) {
        printf("Memory not allocated.\n");
        free(arr_in);
        free(arr_out);
        fclose(image);
        fclose(outputImage);
        return;
    }

    j = 0;
    for (i = 0; i < ancho * alto; i++) {
        b = fgetc(image);
        g = fgetc(image);
        r = fgetc(image);
        arr_in[j] = b;
        arr_in[j + 1] = g;
        arr_in[j + 2] = r;
        j = j + 3;
    }

    radio = (kernel - 1) / 2;
    for (fila = 0; fila < alto; fila++) {
        for (col = 0; col < ancho; col++) {
            suma_b = 0;
            suma_g = 0;
            suma_r = 0;
            contador = 0;

            for (ky = -radio; ky <= radio; ky++) {
                for (kx = -radio; kx <= radio; kx++) {
                    if (fila + ky >= 0 && fila + ky < alto && col + kx >= 0 && col + kx < ancho) {
                        pos2 = ((fila + ky) * ancho * 3) + ((col + kx) * 3);
                        suma_b = suma_b + arr_in[pos2];
                        suma_g = suma_g + arr_in[pos2 + 1];
                        suma_r = suma_r + arr_in[pos2 + 2];
                        contador++;
                    }
                }
            }

            pos = (fila * ancho * 3) + (col * 3);
            arr_out[pos] = suma_b / contador;
            arr_out[pos + 1] = suma_g / contador;
            arr_out[pos + 2] = suma_r / contador;
        }
    }

    printf("lectura de datos: %d\n", j);
    for (i = 0; i < ancho * alto * 3; i++) {
        fputc(arr_out[i], outputImage);
    }

    free(arr_in);
    free(arr_out);
    fclose(image);
    fclose(outputImage);
    (void)lecturas;
    (void)fptr;
}

extern void desenfoque(char path[], char mask[], int kernel)
{
    desenfoque_color(path, mask, kernel);
}
