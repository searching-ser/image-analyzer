#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>
#include <mpi.h>
#include "selec_proc.h"

#define MAX_IMAGES 10
#define MAX_PATH_LEN 260
#define MAX_MASK_LEN 160
#define WINDOWS_SHARED_ROOT "\\\\emisan-pc\\ImagAnShared"
#define MAC_SHARED_ROOT "/Users/ser/Universidad/ImagAnShared"

typedef struct {
    int do_vg;
    int do_vc;
    int do_hg;
    int do_hc;
    int do_bg;
    int do_bc;
} ProcessFlags;

static void get_base_name(const char *path, char *output, size_t size)
{
    const char *start = strrchr(path, '/');
    const char *back = strrchr(path, '\\');
    const char *dot;
    size_t len;

    if (back != NULL && (start == NULL || back > start)) {
        start = back;
    }
    start = start ? start + 1 : path;

    dot = strrchr(start, '.');
    len = dot ? (size_t)(dot - start) : strlen(start);
    if (len >= size) {
        len = size - 1;
    }

    memcpy(output, start, len);
    output[len] = '\0';
}

static void normalize_shared_path(const char *input, char *output, size_t size)
{
#ifdef _WIN32
    strncpy(output, input, size - 1);
    output[size - 1] = '\0';
#else
    size_t windows_len = strlen(WINDOWS_SHARED_ROOT);
    size_t mac_len = strlen(MAC_SHARED_ROOT);
    size_t i;
    size_t j;

    if (strncmp(input, WINDOWS_SHARED_ROOT, windows_len) != 0) {
        strncpy(output, input, size - 1);
        output[size - 1] = '\0';
        return;
    }

    if (mac_len >= size) {
        output[0] = '\0';
        return;
    }

    strcpy(output, MAC_SHARED_ROOT);
    j = mac_len;

    for (i = windows_len; input[i] != '\0' && j < size - 1; i++) {
        output[j++] = (input[i] == '\\') ? '/' : input[i];
    }
    output[j] = '\0';
#endif
}

static void parse_flags(int argc, char *argv[], ProcessFlags *flags)
{
    int i;

    flags->do_vg = 0;
    flags->do_vc = 0;
    flags->do_hg = 0;
    flags->do_hc = 0;
    flags->do_bg = 0;
    flags->do_bc = 0;

    for (i = 3; i < argc; i++) {
        if (strcmp(argv[i], "--vg") == 0) flags->do_vg = 1;
        if (strcmp(argv[i], "--vc") == 0) flags->do_vc = 1;
        if (strcmp(argv[i], "--hg") == 0) flags->do_hg = 1;
        if (strcmp(argv[i], "--hc") == 0) flags->do_hc = 1;
        if (strcmp(argv[i], "--bg") == 0) flags->do_bg = 1;
        if (strcmp(argv[i], "--bc") == 0) flags->do_bc = 1;
    }

    if (!flags->do_vg && !flags->do_vc && !flags->do_hg &&
        !flags->do_hc && !flags->do_bg && !flags->do_bc) {
        flags->do_vg = 1;
        flags->do_vc = 1;
        flags->do_hg = 1;
        flags->do_hc = 1;
        flags->do_bg = 1;
        flags->do_bc = 1;
    }
}

static void process_image(const char *path, const ProcessFlags *flags, int kernel)
{
    char base[120];
    char mask[MAX_MASK_LEN];

    get_base_name(path, base, sizeof(base));

    if (flags->do_vg) {
        snprintf(mask, sizeof(mask), "%s_vg", base);
        inv_img(mask, (char *)path);
    }
    if (flags->do_vc) {
        snprintf(mask, sizeof(mask), "%s_vc", base);
        inv_img_color(mask, (char *)path);
    }
    if (flags->do_hg) {
        snprintf(mask, sizeof(mask), "%s_hg", base);
        inv_img_grey_horizontal(mask, (char *)path);
    }
    if (flags->do_hc) {
        snprintf(mask, sizeof(mask), "%s_hc", base);
        inv_img_color_horizontal(mask, (char *)path);
    }
    if (flags->do_bg) {
        snprintf(mask, sizeof(mask), "%s_bg", base);
        desenfoque_grey((char *)path, mask, kernel);
    }
    if (flags->do_bc) {
        snprintf(mask, sizeof(mask), "%s_bc", base);
        desenfoque((char *)path, mask, kernel);
    }
}

static void send_images_to_worker(int worker_rank, char images[][MAX_PATH_LEN], int count)
{
    MPI_Send(&count, 1, MPI_INT, worker_rank, 100, MPI_COMM_WORLD);
    if (count > 0) {
        MPI_Send(images, count * MAX_PATH_LEN, MPI_CHAR, worker_rank, 101, MPI_COMM_WORLD);
    }
}

int main(int argc, char *argv[])
{
    int rank;
    int world_size;
    int num_threads = 0;
    int kernel = 27;
    char output_dir[MAX_PATH_LEN] = {0};
    ProcessFlags flags;
    int flags_array[6];
    double t_start;
    double t_end;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &world_size);

    if (world_size < 2) {
        if (rank == 0) {
            printf("Uso: mpiexec -n 2 para_image_mpi.exe <threads_locales> <output_dir> <img1> [img2 ... img10] [--vg --vc --hg --hc --bg --bc]\n");
            printf("Se requieren al menos 2 procesos MPI: 1 maestra y 1 o mas esclavas.\n");
        }
        MPI_Finalize();
        return 1;
    }

    if (rank == 0) {
        int image_count = 0;
        int i;

        if (argc < 4) {
            printf("Uso: mpiexec -n 2 para_image_mpi.exe <threads_locales> <output_dir> <img1> [img2 ... img10] [--vg --vc --hg --hc --bg --bc]\n");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }

        num_threads = atoi(argv[1]);
        strncpy(output_dir, argv[2], MAX_PATH_LEN - 1);
        output_dir[MAX_PATH_LEN - 1] = '\0';
        parse_flags(argc, argv, &flags);

        for (i = 3; i < argc; i++) {
            if (argv[i][0] == '-') {
                continue;
            }
            if (image_count >= MAX_IMAGES) {
                break;
            }
            image_count++;
        }

        if (image_count == 0) {
            printf("No se recibieron imagenes para procesar.\n");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }

        flags_array[0] = flags.do_vg;
        flags_array[1] = flags.do_vc;
        flags_array[2] = flags.do_hg;
        flags_array[3] = flags.do_hc;
        flags_array[4] = flags.do_bg;
        flags_array[5] = flags.do_bc;
    } else {
        memset(&flags, 0, sizeof(flags));
    }

    MPI_Bcast(&num_threads, 1, MPI_INT, 0, MPI_COMM_WORLD);
    MPI_Bcast(&kernel, 1, MPI_INT, 0, MPI_COMM_WORLD);
    MPI_Bcast(output_dir, MAX_PATH_LEN, MPI_CHAR, 0, MPI_COMM_WORLD);

    if (rank == 0) {
        flags_array[0] = flags.do_vg;
        flags_array[1] = flags.do_vc;
        flags_array[2] = flags.do_hg;
        flags_array[3] = flags.do_hc;
        flags_array[4] = flags.do_bg;
        flags_array[5] = flags.do_bc;
    }
    MPI_Bcast(flags_array, 6, MPI_INT, 0, MPI_COMM_WORLD);
    if (rank != 0) {
        flags.do_vg = flags_array[0];
        flags.do_vc = flags_array[1];
        flags.do_hg = flags_array[2];
        flags.do_hc = flags_array[3];
        flags.do_bg = flags_array[4];
        flags.do_bc = flags_array[5];
    }

    t_start = MPI_Wtime();

    if (rank == 0) {
        int image_count = 0;
        int i;
        char image_paths[MAX_IMAGES][MAX_PATH_LEN];
        int done_rank;
        int worker_count = world_size - 1;
        int worker_rank;
        int start;
        int end;
        int count;

        for (i = 3; i < argc; i++) {
            if (argv[i][0] == '-') {
                continue;
            }
            if (image_count >= MAX_IMAGES) {
                break;
            }
            strncpy(image_paths[image_count], argv[i], MAX_PATH_LEN - 1);
            image_paths[image_count][MAX_PATH_LEN - 1] = '\0';
            image_count++;
        }

        for (worker_rank = 1; worker_rank < world_size; worker_rank++) {
            char worker_images[MAX_IMAGES][MAX_PATH_LEN];

            start = ((worker_rank - 1) * image_count) / worker_count;
            end = (worker_rank * image_count) / worker_count;
            count = end - start;

            for (i = 0; i < count; i++) {
                strcpy(worker_images[i], image_paths[start + i]);
            }

            send_images_to_worker(worker_rank, worker_images, count);
        }

        for (worker_rank = 1; worker_rank < world_size; worker_rank++) {
            MPI_Recv(&done_rank, 1, MPI_INT, worker_rank, 200, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        }
    } else {
        int my_count = 0;
        char my_images[MAX_IMAGES][MAX_PATH_LEN];
        char local_output_dir[MAX_PATH_LEN];
        int done_rank;
        int i;

        MPI_Recv(&my_count, 1, MPI_INT, 0, 100, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        if (my_count > 0) {
            MPI_Recv(my_images, my_count * MAX_PATH_LEN, MPI_CHAR, 0, 101, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        }

        omp_set_num_threads(num_threads);
        normalize_shared_path(output_dir, local_output_dir, sizeof(local_output_dir));
        set_output_directory(local_output_dir);

        #pragma omp parallel for schedule(dynamic)
        for (i = 0; i < my_count; i++) {
            char local_image[MAX_PATH_LEN];
            normalize_shared_path(my_images[i], local_image, sizeof(local_image));
            process_image(local_image, &flags, kernel);
        }

        done_rank = rank;
        MPI_Send(&done_rank, 1, MPI_INT, 0, 200, MPI_COMM_WORLD);
    }

    t_end = MPI_Wtime();

    if (rank == 0) {
        printf("Procesamiento distribuido terminado.\n");
        printf("Threads locales por esclava: %d\n", num_threads);
        printf("Tiempo total MPI: %.6f segundos\n", t_end - t_start);
        printf("Esclavas utilizadas: %d\n", world_size - 1);
    }

    MPI_Finalize();
    return 0;
}
