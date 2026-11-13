/* dtmf.h — maps the MT8870 4-bit code to a digit. */
#ifndef DTMF_H
#define DTMF_H

#include <stdint.h>

#define DTMF_STAR 10
#define DTMF_HASH 11

/* q: MT8870 bits Q4..Q1. Returns 0-9, DTMF_STAR, DTMF_HASH,
 * or -1 for A/B/C/D or an invalid code. */
int8_t dtmf_code_to_digit(uint8_t q);

#endif
