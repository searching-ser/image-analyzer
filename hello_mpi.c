#include <stdio.h>
#include <mpi.h>

int main(int argc, char **argv) {
    int rank, size;
    fprintf(stderr, "before init\n");
    MPI_Init(&argc, &argv);
    fprintf(stderr, "after init\n");
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    printf("hello rank %d/%d\n", rank, size);
    MPI_Finalize();
    return 0;
}
