#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "selec_proc.h"

#define BMP_HEADER_SIZE 54

typedef struct {
    unsigned char header[BMP_HEADER_SIZE];
    int width;
    int height;
    int row_padded;
    unsigned char *data;
} BmpImage;

static int read_le_int(const unsigned char *bytes)
{
    return bytes[0] | (bytes[1] << 8) | (bytes[2] << 16) | (bytes[3] << 24);
}

static int load_bmp(const char *path, BmpImage *bmp)
{
    FILE *image;
    int data_size;

    image = fopen(path, "rb");
    if (image == NULL) {
        printf("Error: No se pudo abrir %s\n", path);
        return 0;
    }

    if (fread(bmp->header, 1, BMP_HEADER_SIZE, image) != BMP_HEADER_SIZE) {
        fclose(image);
        printf("Error: No se pudo leer la cabecera BMP\n");
        return 0;
    }

    bmp->width = read_le_int(&bmp->header[18]);
    bmp->height = read_le_int(&bmp->header[22]);
    if (bmp->height < 0) {
        bmp->height = -bmp->height;
    }

    bmp->row_padded = (bmp->width * 3 + 3) & (~3);
    data_size = bmp->row_padded * bmp->height;
    bmp->data = (unsigned char *)malloc((size_t)data_size);
    if (bmp->data == NULL) {
        fclose(image);
        printf("Memory not allocated.\n");
        return 0;
    }

    if (fread(bmp->data, 1, (size_t)data_size, image) != (size_t)data_size) {
        free(bmp->data);
        bmp->data = NULL;
        fclose(image);
        printf("Error: No se pudieron leer los datos BMP\n");
        return 0;
    }

    fclose(image);
    return 1;
}

static int save_bmp(const char *mask, const BmpImage *bmp)
{
    FILE *outputImage;
    char add_char[80] = "./img/";
    int data_size = bmp->row_padded * bmp->height;

    strcat(add_char, mask);
    strcat(add_char, ".bmp");

    outputImage = fopen(add_char, "wb");
    if (outputImage == NULL) {
        printf("Error: No se pudo crear %s\n", add_char);
        return 0;
    }

    fwrite(bmp->header, 1, BMP_HEADER_SIZE, outputImage);
    fwrite(bmp->data, 1, (size_t)data_size, outputImage);
    fclose(outputImage);

    printf("%s\n", add_char);
    return 1;
}

static void free_bmp(BmpImage *bmp)
{
    free(bmp->data);
    bmp->data = NULL;
}

static unsigned char to_gray(unsigned char b, unsigned char g, unsigned char r)
{
    return (unsigned char)(0.21 * r + 0.72 * g + 0.07 * b);
}

extern void inv_img(char mask[], char path[])
{
    BmpImage bmp;
    int y;
    int x;

    if (!load_bmp(path, &bmp)) {
        return;
    }

    for (y = 0; y < bmp.height; y++) {
        unsigned char *row = bmp.data + y * bmp.row_padded;
        for (x = 0; x < bmp.width; x++) {
            int idx = x * 3;
            unsigned char b = row[idx];
            unsigned char g = row[idx + 1];
            unsigned char r = row[idx + 2];
            unsigned char pixel = to_gray(b, g, r);

            row[idx] = pixel;
            row[idx + 1] = pixel;
            row[idx + 2] = pixel;
        }
    }

    {
        unsigned char *temp = (unsigned char *)malloc((size_t)(bmp.row_padded * bmp.height));
        if (temp == NULL) {
            printf("Memory not allocated.\n");
            free_bmp(&bmp);
            return;
        }

        for (y = 0; y < bmp.height; y++) {
            memcpy(
                temp + y * bmp.row_padded,
                bmp.data + (bmp.height - 1 - y) * bmp.row_padded,
                (size_t)bmp.row_padded
            );
        }

        memcpy(bmp.data, temp, (size_t)(bmp.row_padded * bmp.height));
        free(temp);
    }

    save_bmp(mask, &bmp);
    free_bmp(&bmp);
}

extern void inv_img_grey(char mask[], char path[])
{
    BmpImage bmp;
    int y;
    int x;

    if (!load_bmp(path, &bmp)) {
        return;
    }

    for (y = 0; y < bmp.height; y++) {
        unsigned char *row = bmp.data + y * bmp.row_padded;
        for (x = 0; x < bmp.width; x++) {
            int idx = x * 3;
            unsigned char pixel = to_gray(row[idx], row[idx + 1], row[idx + 2]);

            row[idx] = pixel;
            row[idx + 1] = pixel;
            row[idx + 2] = pixel;
        }
    }

    save_bmp(mask, &bmp);
    free_bmp(&bmp);
}

extern void inv_img_color(char mask[], char path[])
{
    BmpImage bmp;
    unsigned char *temp;
    int y;

    if (!load_bmp(path, &bmp)) {
        return;
    }

    temp = (unsigned char *)malloc((size_t)(bmp.row_padded * bmp.height));
    if (temp == NULL) {
        printf("Memory not allocated.\n");
        free_bmp(&bmp);
        return;
    }

    for (y = 0; y < bmp.height; y++) {
        memcpy(
            temp + y * bmp.row_padded,
            bmp.data + (bmp.height - 1 - y) * bmp.row_padded,
            (size_t)bmp.row_padded
        );
    }

    memcpy(bmp.data, temp, (size_t)(bmp.row_padded * bmp.height));
    free(temp);

    save_bmp(mask, &bmp);
    free_bmp(&bmp);
}

extern void inv_img_grey_horizontal(char mask[], char path[])
{
    BmpImage bmp;
    int y;
    int x;

    if (!load_bmp(path, &bmp)) {
        return;
    }

    for (y = 0; y < bmp.height; y++) {
        unsigned char *row = bmp.data + y * bmp.row_padded;
        unsigned char *out_row = (unsigned char *)malloc((size_t)bmp.row_padded);

        if (out_row == NULL) {
            printf("Memory not allocated.\n");
            free_bmp(&bmp);
            return;
        }

        memcpy(out_row, row, (size_t)bmp.row_padded);
        for (x = 0; x < bmp.width; x++) {
            int orig_idx = x * 3;
            int new_idx = (bmp.width - 1 - x) * 3;
            unsigned char pixel = to_gray(row[orig_idx], row[orig_idx + 1], row[orig_idx + 2]);

            out_row[new_idx] = pixel;
            out_row[new_idx + 1] = pixel;
            out_row[new_idx + 2] = pixel;
        }

        memcpy(row, out_row, (size_t)bmp.row_padded);
        free(out_row);
    }

    save_bmp(mask, &bmp);
    free_bmp(&bmp);
}

extern void inv_img_color_horizontal(char mask[], char path[])
{
    BmpImage bmp;
    int y;
    int x;

    if (!load_bmp(path, &bmp)) {
        return;
    }

    for (y = 0; y < bmp.height; y++) {
        unsigned char *row = bmp.data + y * bmp.row_padded;
        unsigned char *out_row = (unsigned char *)malloc((size_t)bmp.row_padded);

        if (out_row == NULL) {
            printf("Memory not allocated.\n");
            free_bmp(&bmp);
            return;
        }

        memcpy(out_row, row, (size_t)bmp.row_padded);
        for (x = 0; x < bmp.width; x++) {
            int orig_idx = x * 3;
            int new_idx = (bmp.width - 1 - x) * 3;

            out_row[new_idx] = row[orig_idx];
            out_row[new_idx + 1] = row[orig_idx + 1];
            out_row[new_idx + 2] = row[orig_idx + 2];
        }

        memcpy(row, out_row, (size_t)bmp.row_padded);
        free(out_row);
    }

    save_bmp(mask, &bmp);
    free_bmp(&bmp);
}

extern void inv_img_grey_vertical(char mask[], char path[])
{
    inv_img(mask, path);
}

extern void inv_img_color_vertical(char mask[], char path[])
{
    inv_img_color(mask, path);
}

extern void desenfoque_grey(char path[], char mask[], int kernel)
{
    BmpImage bmp;
    unsigned char *gray_in;
    unsigned char *gray_tmp;
    unsigned char *gray_out;
    int y;
    int x;
    int k;

    if (!load_bmp(path, &bmp)) {
        return;
    }

    gray_in = (unsigned char *)malloc((size_t)(bmp.width * bmp.height));
    gray_tmp = (unsigned char *)malloc((size_t)(bmp.width * bmp.height));
    gray_out = (unsigned char *)malloc((size_t)(bmp.width * bmp.height));
    if (gray_in == NULL || gray_tmp == NULL || gray_out == NULL) {
        printf("Memory not allocated.\n");
        free(gray_in);
        free(gray_tmp);
        free(gray_out);
        free_bmp(&bmp);
        return;
    }

    for (y = 0; y < bmp.height; y++) {
        unsigned char *row = bmp.data + y * bmp.row_padded;
        for (x = 0; x < bmp.width; x++) {
            int idx = x * 3;
            gray_in[y * bmp.width + x] = to_gray(row[idx], row[idx + 1], row[idx + 2]);
        }
    }

    k = kernel / 2;

    for (y = 0; y < bmp.height; y++) {
        int sum = 0;

        for (x = 0; x < bmp.width; x++) {
            int left = x - k;
            int right = x + k;

            if (x == 0) {
                int dx;
                sum = 0;
                for (dx = -k; dx <= k; dx++) {
                    int nx = x + dx;
                    if (nx >= 0 && nx < bmp.width) {
                        sum += gray_in[y * bmp.width + nx];
                    }
                }
            } else {
                if (left - 1 >= 0) {
                    sum -= gray_in[y * bmp.width + (left - 1)];
                }
                if (right < bmp.width) {
                    sum += gray_in[y * bmp.width + right];
                }
            }

            {
                int valid_left = left < 0 ? 0 : left;
                int valid_right = right >= bmp.width ? bmp.width - 1 : right;
                int count = valid_right - valid_left + 1;
                gray_tmp[y * bmp.width + x] = (unsigned char)(sum / count);
            }
        }
    }

    for (x = 0; x < bmp.width; x++) {
        int sum = 0;

        for (y = 0; y < bmp.height; y++) {
            int top = y - k;
            int bottom = y + k;

            if (y == 0) {
                int dy;
                sum = 0;
                for (dy = -k; dy <= k; dy++) {
                    int ny = y + dy;
                    if (ny >= 0 && ny < bmp.height) {
                        sum += gray_tmp[ny * bmp.width + x];
                    }
                }
            } else {
                if (top - 1 >= 0) {
                    sum -= gray_tmp[(top - 1) * bmp.width + x];
                }
                if (bottom < bmp.height) {
                    sum += gray_tmp[bottom * bmp.width + x];
                }
            }

            {
                int valid_top = top < 0 ? 0 : top;
                int valid_bottom = bottom >= bmp.height ? bmp.height - 1 : bottom;
                int count = valid_bottom - valid_top + 1;
                gray_out[y * bmp.width + x] = (unsigned char)(sum / count);
            }
        }
    }

    for (y = 0; y < bmp.height; y++) {
        unsigned char *row = bmp.data + y * bmp.row_padded;
        for (x = 0; x < bmp.width; x++) {
            int idx = x * 3;
            unsigned char pixel = gray_out[y * bmp.width + x];

            row[idx] = pixel;
            row[idx + 1] = pixel;
            row[idx + 2] = pixel;
        }
    }

    free(gray_in);
    free(gray_tmp);
    free(gray_out);
    save_bmp(mask, &bmp);
    free_bmp(&bmp);
}

extern void desenfoque_color(char path[], char mask[], int kernel)
{
    BmpImage bmp;
    unsigned char *temp;
    int y;
    int x;
    int k;

    if (!load_bmp(path, &bmp)) {
        return;
    }

    temp = (unsigned char *)malloc((size_t)(bmp.row_padded * bmp.height));
    if (temp == NULL) {
        printf("Memory not allocated.\n");
        free_bmp(&bmp);
        return;
    }

    k = kernel / 2;

    for (y = 0; y < bmp.height; y++) {
        unsigned char *src_row = bmp.data + y * bmp.row_padded;
        unsigned char *tmp_row = temp + y * bmp.row_padded;
        int sum_b = 0;
        int sum_g = 0;
        int sum_r = 0;

        memcpy(tmp_row, src_row, (size_t)bmp.row_padded);

        for (x = 0; x < bmp.width; x++) {
            int left = x - k;
            int right = x + k;
            int idx = x * 3;

            if (x == 0) {
                int dx;
                sum_b = 0;
                sum_g = 0;
                sum_r = 0;
                for (dx = -k; dx <= k; dx++) {
                    int nx = x + dx;
                    if (nx >= 0 && nx < bmp.width) {
                        int nidx = nx * 3;
                        sum_b += src_row[nidx];
                        sum_g += src_row[nidx + 1];
                        sum_r += src_row[nidx + 2];
                    }
                }
            } else {
                if (left - 1 >= 0) {
                    int lidx = (left - 1) * 3;
                    sum_b -= src_row[lidx];
                    sum_g -= src_row[lidx + 1];
                    sum_r -= src_row[lidx + 2];
                }
                if (right < bmp.width) {
                    int ridx = right * 3;
                    sum_b += src_row[ridx];
                    sum_g += src_row[ridx + 1];
                    sum_r += src_row[ridx + 2];
                }
            }

            {
                int valid_left = left < 0 ? 0 : left;
                int valid_right = right >= bmp.width ? bmp.width - 1 : right;
                int count = valid_right - valid_left + 1;
                tmp_row[idx] = (unsigned char)(sum_b / count);
                tmp_row[idx + 1] = (unsigned char)(sum_g / count);
                tmp_row[idx + 2] = (unsigned char)(sum_r / count);
            }
        }
    }

    for (x = 0; x < bmp.width; x++) {
        int sum_b = 0;
        int sum_g = 0;
        int sum_r = 0;

        for (y = 0; y < bmp.height; y++) {
            int top = y - k;
            int bottom = y + k;
            unsigned char *out_row = bmp.data + y * bmp.row_padded;
            int idx = x * 3;

            if (y == 0) {
                int dy;
                sum_b = 0;
                sum_g = 0;
                sum_r = 0;
                for (dy = -k; dy <= k; dy++) {
                    int ny = y + dy;
                    if (ny >= 0 && ny < bmp.height) {
                        unsigned char *tmp_row = temp + ny * bmp.row_padded;
                        int tidx = x * 3;
                        sum_b += tmp_row[tidx];
                        sum_g += tmp_row[tidx + 1];
                        sum_r += tmp_row[tidx + 2];
                    }
                }
            } else {
                if (top - 1 >= 0) {
                    unsigned char *top_row = temp + (top - 1) * bmp.row_padded;
                    int tidx = x * 3;
                    sum_b -= top_row[tidx];
                    sum_g -= top_row[tidx + 1];
                    sum_r -= top_row[tidx + 2];
                }
                if (bottom < bmp.height) {
                    unsigned char *bottom_row = temp + bottom * bmp.row_padded;
                    int tidx = x * 3;
                    sum_b += bottom_row[tidx];
                    sum_g += bottom_row[tidx + 1];
                    sum_r += bottom_row[tidx + 2];
                }
            }

            {
                int valid_top = top < 0 ? 0 : top;
                int valid_bottom = bottom >= bmp.height ? bmp.height - 1 : bottom;
                int count = valid_bottom - valid_top + 1;
                out_row[idx] = (unsigned char)(sum_b / count);
                out_row[idx + 1] = (unsigned char)(sum_g / count);
                out_row[idx + 2] = (unsigned char)(sum_r / count);
            }
        }
    }

    free(temp);
    save_bmp(mask, &bmp);
    free_bmp(&bmp);
}

extern void desenfoque(char path[], char mask[], int kernel)
{
    desenfoque_color(path, mask, kernel);
}
