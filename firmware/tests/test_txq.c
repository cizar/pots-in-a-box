/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
#include "minitest.h"
#include "../src/txq.h"

TEST(fifo_order) {
    txq_t q; txq_init(&q); uint8_t b;
    CHECK(!txq_pop(&q, &b));
    txq_push(&q, (const uint8_t *)"ab", 2);
    CHECK(txq_pop(&q, &b)); CHECK_EQ(b, 'a');
    CHECK(txq_pop(&q, &b)); CHECK_EQ(b, 'b');
    CHECK(!txq_pop(&q, &b));
}
TEST(drops_whole_message_when_full) {
    txq_t q; txq_init(&q); uint8_t b; uint8_t fill[TXQ_SIZE - 1];
    for (unsigned i = 0; i < sizeof fill; i++) fill[i] = 'x';
    CHECK(txq_push(&q, fill, sizeof fill));    /* exactly full */
    CHECK(!txq_push(&q, (const uint8_t *)"y", 1));
    int n = 0; while (txq_pop(&q, &b)) { CHECK_EQ(b, 'x'); n++; }
    CHECK_EQ(n, TXQ_SIZE - 1);
}
TEST(wraps_around) {
    txq_t q; txq_init(&q); uint8_t b;
    for (unsigned r = 0; r < 3 * TXQ_SIZE; r++) {
        CHECK(txq_push(&q, (const uint8_t *)"z", 1));
        CHECK(txq_pop(&q, &b)); CHECK_EQ(b, 'z');
    }
}

int main(void) {
    RUN(fifo_order); RUN(drops_whole_message_when_full); RUN(wraps_around);
    MINITEST_MAIN_END("test_txq");
}
