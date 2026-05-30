#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stddef.h>

/* auto-generated new.c from spec.json */

int main(int argc, char **argv) {
    if (argc != 6) {
        fprintf(stderr, "Usage: %s p1Null isValidp1 isStringp1 sizeof1 strlen1\n", argv[0]);
        return 2;
    }

    int p1Null = atoi(argv[1]);
    int isValidp1 = atoi(argv[2]);
    int isStringp1 = atoi(argv[3]);
    int sizeof1 = atoi(argv[4]);
    int strlen1 = atoi(argv[5]);

    char *p1 = NULL;

    if (p1Null) p1 = NULL;
    else if (isValidp1) {
        p1 = (char*)malloc(sizeof1);
        memset(p1, 'A', sizeof1);
        if (isStringp1) p1[strlen1] = '\0';
    }


    /* call target function returning long int */
    long int r = atol(p1);
    (void)r;

    if (!p1Null && isValidp1) free(p1);

    return 0;
}