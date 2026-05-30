#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stddef.h>

/* auto-generated new.c from spec.json */

int main(int argc, char **argv) {
    if (argc != 12) {
        fprintf(stderr, "Usage: %s p1Null p2Null isValidp1 isValidp2 isStringp1 isStringp2 isDisjointp1p2 sizeof1 sizeof2 strlen1 strlen2\n", argv[0]);
        return 2;
    }

    int p1Null = atoi(argv[1]);
    int p2Null = atoi(argv[2]);
    int isValidp1 = atoi(argv[3]);
    int isValidp2 = atoi(argv[4]);
    int isStringp1 = atoi(argv[5]);
    int isStringp2 = atoi(argv[6]);
    int isDisjointp1p2 = atoi(argv[7]);
    int sizeof1 = atoi(argv[8]);
    int sizeof2 = atoi(argv[9]);
    int strlen1 = atoi(argv[10]);
    int strlen2 = atoi(argv[11]);

    char *p1 = NULL;
    char *p2 = NULL;

    if (p1Null) p1 = NULL;
    else if (isValidp1) {
        p1 = (char*)malloc(sizeof1);
        memset(p1, 'A', sizeof1);
        if (isStringp1) p1[strlen1] = '\0';
    }

    if (p2Null) p2 = NULL;
    else if (isValidp2 && isDisjointp1p2) {
        p2 = (char*)malloc(sizeof2);
        memset(p2, 'A', sizeof2);
        if (isStringp2) p2[strlen2] = '\0';
    }

    if (!isDisjointp1p2 && !p1Null && !p2Null) {
        p2 = p1 + 2;
    }

    /* call target function returning char* */
    char *res = strcat(p1, p2);
    (void)res;

    if (!p1Null && isValidp1) free(p1);
    if (!p2Null && isDisjointp1p2 && isValidp2) free(p2);

    return 0;
}