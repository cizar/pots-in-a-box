/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
#include "dtmf.h"

int8_t dtmf_code_to_digit(uint8_t q) {
    if (q >= 1 && q <= 9) return (int8_t)q;
    switch (q) {
    case 10: return 0;
    case 11: return DTMF_STAR;
    case 12: return DTMF_HASH;
    default: return -1; /* 0 = D, 13-15 = A-C, >15 invalid */
    }
}
