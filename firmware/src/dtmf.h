/* dtmf.h — traduce el código de 4 bits del MT8870 a un dígito. */
#ifndef DTMF_H
#define DTMF_H

#include <stdint.h>

#define DTMF_STAR 10
#define DTMF_HASH 11

/* q: bits Q4..Q1 del MT8870. Devuelve 0-9, DTMF_STAR, DTMF_HASH,
 * o -1 para A/B/C/D o un código inválido. */
int8_t dtmf_code_to_digit(uint8_t q);

#endif
