#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <sys/stat.h>
#include <omp.h>
#include <mpi.h>
#include "selec_proc.h"

#define MAX_IMAGES 1000
#define MAX_PATH_LEN 260
#define MAX_MASK_LEN 160
#define MPI_TAG_WORK 100
#define MPI_TAG_DONE 101
#define MPI_NO_MORE_WORK -1

typedef struct {
    int do_gray;
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
    strncpy(output, input, size - 1);
    output[size - 1] = '\0';
}

static int has_bmp_extension(const char *path)
{
    const char *dot = strrchr(path, '.');

    if (dot == NULL) {
        return 0;
    }

    return strcmp(dot, ".bmp") == 0 || strcmp(dot, ".BMP") == 0 ||
           strcmp(dot, ".Bmp") == 0 || strcmp(dot, ".bMp") == 0 ||
           strcmp(dot, ".bmP") == 0 || strcmp(dot, ".BMp") == 0 ||
           strcmp(dot, ".bMP") == 0 || strcmp(dot, ".BmP") == 0;
}

static int compare_paths(const void *left, const void *right)
{
    const char *a = (const char *)left;
    const char *b = (const char *)right;

    return strcmp(a, b);
}

static void add_image_path(char images[][MAX_PATH_LEN], int *image_count, const char *path)
{
    if (*image_count >= MAX_IMAGES) {
        printf("Aviso: se alcanzo el limite de %d imagenes. Se ignorara %s\n", MAX_IMAGES, path);
        return;
    }

    strncpy(images[*image_count], path, MAX_PATH_LEN - 1);
    images[*image_count][MAX_PATH_LEN - 1] = '\0';
    (*image_count)++;
}

static void add_images_from_directory(char images[][MAX_PATH_LEN], int *image_count, const char *dir_path)
{
    DIR *dir;
    struct dirent *entry;
    char full_path[MAX_PATH_LEN];

    dir = opendir(dir_path);
    if (dir == NULL) {
        printf("Error: No se pudo abrir carpeta %s\n", dir_path);
        return;
    }

    while ((entry = readdir(dir)) != NULL) {
        if (entry->d_name[0] == '.') {
            continue;
        }
        if (!has_bmp_extension(entry->d_name)) {
            continue;
        }

        snprintf(full_path, sizeof(full_path), "%s/%s", dir_path, entry->d_name);
        add_image_path(images, image_count, full_path);
    }

    closedir(dir);
}

static void collect_image_paths(int argc, char *argv[], char images[][MAX_PATH_LEN], int *image_count)
{
    int i;

    *image_count = 0;

    for (i = 3; i < argc; i++) {
        struct stat path_stat;

        if (strcmp(argv[i], "--kernel") == 0) {
            i++;
            continue;
        }

        if (argv[i][0] == '-') {
            continue;
        }

        if (stat(argv[i], &path_stat) != 0) {
            printf("Aviso: no se encontro %s\n", argv[i]);
            continue;
        }

        if (S_ISDIR(path_stat.st_mode)) {
            add_images_from_directory(images, image_count, argv[i]);
        } else if (S_ISREG(path_stat.st_mode)) {
            add_image_path(images, image_count, argv[i]);
        }
    }

    qsort(images, (size_t)(*image_count), MAX_PATH_LEN, compare_paths);
}

static void parse_flags(int argc, char *argv[], ProcessFlags *flags)
{
    int i;

    flags->do_gray = 0;
    flags->do_vg = 0;
    flags->do_vc = 0;
    flags->do_hg = 0;
    flags->do_hc = 0;
    flags->do_bg = 0;
    flags->do_bc = 0;

    for (i = 3; i < argc; i++) {
        if (strcmp(argv[i], "--kernel") == 0) {
            i++;
            continue;
        }
        if (strcmp(argv[i], "--gray") == 0) flags->do_gray = 1;
        if (strcmp(argv[i], "--vg") == 0) flags->do_vg = 1;
        if (strcmp(argv[i], "--vc") == 0) flags->do_vc = 1;
        if (strcmp(argv[i], "--hg") == 0) flags->do_hg = 1;
        if (strcmp(argv[i], "--hc") == 0) flags->do_hc = 1;
        if (strcmp(argv[i], "--bg") == 0) flags->do_bg = 1;
        if (strcmp(argv[i], "--bc") == 0) flags->do_bc = 1;
    }

    if (!flags->do_gray && !flags->do_vg && !flags->do_vc && !flags->do_hg &&
        !flags->do_hc && !flags->do_bg && !flags->do_bc) {
        flags->do_gray = 1;
        flags->do_vg = 1;
        flags->do_vc = 1;
        flags->do_hg = 1;
        flags->do_hc = 1;
        flags->do_bg = 1;
        flags->do_bc = 1;
    }
}

static int parse_kernel(int argc, char *argv[])
{
    int i;

    for (i = 3; i < argc - 1; i++) {
        if (strcmp(argv[i], "--kernel") == 0) {
            int kernel = atoi(argv[i + 1]);
            if (kernel > 0) {
                return kernel;
            }
            printf("Aviso: kernel invalido '%s'. Se usara 27.\n", argv[i + 1]);
            return 27;
        }
    }

    return 27;
}

static void process_image(const char *path, const ProcessFlags *flags, int kernel)
{
    char base[120];

    get_base_name(path, base, sizeof(base));

    #pragma omp parallel sections
    {
        #pragma omp section
        {
            if (flags->do_gray) {
                char mask[MAX_MASK_LEN];
                snprintf(mask, sizeof(mask), "%s_gray", base);
                inv_img_grey(mask, (char *)path);
            }
        }

        #pragma omp section
        {
            if (flags->do_vg) {
                char mask[MAX_MASK_LEN];
                snprintf(mask, sizeof(mask), "%s_vg", base);
                inv_img(mask, (char *)path);
            }
        }

        #pragma omp section
        {
            if (flags->do_vc) {
                char mask[MAX_MASK_LEN];
                snprintf(mask, sizeof(mask), "%s_vc", base);
                inv_img_color(mask, (char *)path);
            }
        }

        #pragma omp section
        {
            if (flags->do_hg) {
                char mask[MAX_MASK_LEN];
                snprintf(mask, sizeof(mask), "%s_hg", base);
                inv_img_grey_horizontal(mask, (char *)path);
            }
        }

        #pragma omp section
        {
            if (flags->do_hc) {
                char mask[MAX_MASK_LEN];
                snprintf(mask, sizeof(mask), "%s_hc", base);
                inv_img_color_horizontal(mask, (char *)path);
            }
        }

        #pragma omp section
        {
            if (flags->do_bg) {
                char mask[MAX_MASK_LEN];
                snprintf(mask, sizeof(mask), "%s_bg", base);
                desenfoque_grey((char *)path, mask, kernel);
            }
        }

        #pragma omp section
        {
            if (flags->do_bc) {
                char mask[MAX_MASK_LEN];
                snprintf(mask, sizeof(mask), "%s_bc", base);
                desenfoque((char *)path, mask, kernel);
            }
        }
    }
}

static void process_image_index(int rank, int image_index, char image_paths[][MAX_PATH_LEN],
                                const ProcessFlags *flags, int kernel)
{
    char local_image[MAX_PATH_LEN];

    normalize_shared_path(image_paths[image_index], local_image, sizeof(local_image));
    printf("[rank %d] procesando %s\n", rank, local_image);
    process_image(local_image, flags, kernel);
    printf("[rank %d] termino %s\n", rank, local_image);
}

int main(int argc, char *argv[])
{
    int rank;
    int world_size;
    int num_threads = 0;
    int kernel = 27;
    char output_dir[MAX_PATH_LEN] = {0};
    char image_paths[MAX_IMAGES][MAX_PATH_LEN];
    int image_count = 0;
    ProcessFlags flags;
    int flags_array[7];
    double t_start;
    double t_end;

    setvbuf(stderr, NULL, _IONBF, 0);
    fprintf(stderr, "[pre-mpi] proceso iniciado argc=%d\n", argc);

    MPI_Init(&argc, &argv);
    fprintf(stderr, "[post-mpi] MPI_Init terminado\n");

    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    fprintf(stderr, "[post-mpi] MPI_Comm_rank terminado\n");
    MPI_Comm_size(MPI_COMM_WORLD, &world_size);
    fprintf(stderr, "[post-mpi] MPI_Comm_size terminado\n");
    setvbuf(stdout, NULL, _IONBF, 0);
    fprintf(stderr, "[rank %d/%d] MPI_Init terminado argc=%d\n", rank, world_size, argc);

    if (rank == 0) {
        if (argc < 4) {
            printf("Uso: mpirun -n <procesos> para_image_mpi <threads_locales> <output_dir> <img_o_carpeta1> [img_o_carpeta2 ...] [--kernel N] [--gray --vg --vc --hg --hc --bg --bc]\n");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }

        num_threads = atoi(argv[1]);
        kernel = parse_kernel(argc, argv);
        strncpy(output_dir, argv[2], MAX_PATH_LEN - 1);
        output_dir[MAX_PATH_LEN - 1] = '\0';
        parse_flags(argc, argv, &flags);
        printf("[rank 0] threads=%d kernel=%d output=%s\n", num_threads, kernel, output_dir);

        collect_image_paths(argc, argv, image_paths, &image_count);

        if (image_count == 0) {
            printf("No se recibieron imagenes para procesar.\n");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
        printf("[rank 0] imagenes recibidas=%d\n", image_count);

        flags_array[0] = flags.do_gray;
        flags_array[1] = flags.do_vg;
        flags_array[2] = flags.do_vc;
        flags_array[3] = flags.do_hg;
        flags_array[4] = flags.do_hc;
        flags_array[5] = flags.do_bg;
        flags_array[6] = flags.do_bc;
    } else {
        memset(&flags, 0, sizeof(flags));
    }

    MPI_Bcast(&num_threads, 1, MPI_INT, 0, MPI_COMM_WORLD);
    MPI_Bcast(&kernel, 1, MPI_INT, 0, MPI_COMM_WORLD);
    MPI_Bcast(output_dir, MAX_PATH_LEN, MPI_CHAR, 0, MPI_COMM_WORLD);
    MPI_Bcast(&image_count, 1, MPI_INT, 0, MPI_COMM_WORLD);
    MPI_Bcast(image_paths, MAX_IMAGES * MAX_PATH_LEN, MPI_CHAR, 0, MPI_COMM_WORLD);

    if (rank == 0) {
        flags_array[0] = flags.do_gray;
        flags_array[1] = flags.do_vg;
        flags_array[2] = flags.do_vc;
        flags_array[3] = flags.do_hg;
        flags_array[4] = flags.do_hc;
        flags_array[5] = flags.do_bg;
        flags_array[6] = flags.do_bc;
    }
    MPI_Bcast(flags_array, 7, MPI_INT, 0, MPI_COMM_WORLD);
    if (rank != 0) {
        flags.do_gray = flags_array[0];
        flags.do_vg = flags_array[1];
        flags.do_vc = flags_array[2];
        flags.do_hg = flags_array[3];
        flags.do_hc = flags_array[4];
        flags.do_bg = flags_array[5];
        flags.do_bc = flags_array[6];
    }

    t_start = MPI_Wtime();

    {
        char local_output_dir[MAX_PATH_LEN];

        omp_set_num_threads(num_threads);
        normalize_shared_path(output_dir, local_output_dir, sizeof(local_output_dir));
        set_output_directory(local_output_dir);
    }

    if (rank == 0) {
        int next_index = 0;
        int completed = 0;
        int active_workers = 0;
        int worker_rank;

        printf("[rank 0/%d] cola dinamica iniciada con %d imagen(es)\n", world_size, image_count);

        for (worker_rank = 1; worker_rank < world_size; worker_rank++) {
            int work_index;

            if (next_index < image_count) {
                work_index = next_index++;
                MPI_Send(&work_index, 1, MPI_INT, worker_rank, MPI_TAG_WORK, MPI_COMM_WORLD);
                active_workers++;
                printf("[rank 0] asigno indice %d a rank %d\n", work_index, worker_rank);
            } else {
                work_index = MPI_NO_MORE_WORK;
                MPI_Send(&work_index, 1, MPI_INT, worker_rank, MPI_TAG_WORK, MPI_COMM_WORLD);
            }
        }

        while (completed < image_count) {
            int has_done = 0;
            MPI_Status status;

            do {
                MPI_Iprobe(MPI_ANY_SOURCE, MPI_TAG_DONE, MPI_COMM_WORLD, &has_done, &status);
                if (has_done) {
                    int done_index;
                    int work_index;

                    MPI_Recv(&done_index, 1, MPI_INT, status.MPI_SOURCE, MPI_TAG_DONE, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
                    completed++;
                    printf("[rank 0] recibio fin de indice %d desde rank %d (%d/%d)\n",
                           done_index, status.MPI_SOURCE, completed, image_count);

                    if (next_index < image_count) {
                        work_index = next_index++;
                        MPI_Send(&work_index, 1, MPI_INT, status.MPI_SOURCE, MPI_TAG_WORK, MPI_COMM_WORLD);
                        printf("[rank 0] asigno indice %d a rank %d\n", work_index, status.MPI_SOURCE);
                    } else {
                        work_index = MPI_NO_MORE_WORK;
                        MPI_Send(&work_index, 1, MPI_INT, status.MPI_SOURCE, MPI_TAG_WORK, MPI_COMM_WORLD);
                        active_workers--;
                    }
                }
            } while (has_done);

            if (next_index < image_count) {
                int local_index = next_index++;

                printf("[rank 0] tomo indice %d de la cola local\n", local_index);
                process_image_index(rank, local_index, image_paths, &flags, kernel);
                completed++;
                printf("[rank 0] termino indice %d localmente (%d/%d)\n",
                       local_index, completed, image_count);
            } else if (active_workers > 0) {
                int done_index;
                int work_index = MPI_NO_MORE_WORK;
                MPI_Status status;

                MPI_Recv(&done_index, 1, MPI_INT, MPI_ANY_SOURCE, MPI_TAG_DONE, MPI_COMM_WORLD, &status);
                completed++;
                printf("[rank 0] recibio fin de indice %d desde rank %d (%d/%d)\n",
                       done_index, status.MPI_SOURCE, completed, image_count);
                MPI_Send(&work_index, 1, MPI_INT, status.MPI_SOURCE, MPI_TAG_WORK, MPI_COMM_WORLD);
                active_workers--;
            }
        }
    } else {
        while (1) {
            int work_index;

            MPI_Recv(&work_index, 1, MPI_INT, 0, MPI_TAG_WORK, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            if (work_index == MPI_NO_MORE_WORK) {
                printf("[rank %d] cola terminada\n", rank);
                break;
            }

            printf("[rank %d/%d] procesara 1 imagen(es): indice %d\n", rank, world_size, work_index);
            process_image_index(rank, work_index, image_paths, &flags, kernel);
            MPI_Send(&work_index, 1, MPI_INT, 0, MPI_TAG_DONE, MPI_COMM_WORLD);
        }
    }

    MPI_Barrier(MPI_COMM_WORLD);
    t_end = MPI_Wtime();

    if (rank == 0) {
        printf("Procesamiento distribuido terminado.\n");
        printf("Threads locales por proceso: %d\n", num_threads);
        printf("Tiempo total MPI: %.6f segundos\n", t_end - t_start);
        printf("Procesos MPI utilizados: %d\n", world_size);
    }

    MPI_Finalize();
    return 0;
}
