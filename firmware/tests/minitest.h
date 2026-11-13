/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
/* minitest.h — minimal test framework for running on the host. */
#ifndef MINITEST_H
#define MINITEST_H

#include <stdio.h>

static int mt_tests = 0;
static int mt_failures = 0;
static int mt_current_failed = 0;

#define TEST(name) static void name(void)

#define CHECK(cond)                                                        \
    do {                                                                   \
        if (!(cond)) {                                                     \
            printf("  FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);      \
            mt_current_failed = 1;                                         \
        }                                                                  \
    } while (0)

#define CHECK_EQ(a, b)                                                     \
    do {                                                                   \
        long mt_a = (long)(a), mt_b = (long)(b);                           \
        if (mt_a != mt_b) {                                                \
            printf("  FAIL %s:%d: %s == %s (%ld != %ld)\n", __FILE__,     \
                   __LINE__, #a, #b, mt_a, mt_b);                          \
            mt_current_failed = 1;                                         \
        }                                                                  \
    } while (0)

#define RUN(name)                                                          \
    do {                                                                   \
        mt_current_failed = 0;                                             \
        name();                                                            \
        mt_tests++;                                                        \
        if (mt_current_failed) {                                           \
            mt_failures++;                                                 \
            printf("FAIL: %s\n", #name);                                  \
        }                                                                  \
    } while (0)

#define MINITEST_MAIN_END(suite)                                           \
    do {                                                                   \
        printf("%s: %d tests, %d failures\n", suite, mt_tests,             \
               mt_failures);                                               \
        return mt_failures ? 1 : 0;                                        \
    } while (0)

#endif
