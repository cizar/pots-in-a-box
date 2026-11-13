/* dds.h — síntesis digital de 1 o 2 senos para PWM de 8 bits. */
#ifndef DDS_H
#define DDS_H

#include <stdint.h>

/* Timer0 PWM rápido 8 bits a 62500 Hz; la muestra cambia cada 2 desbordes. */
#define DDS_SAMPLE_RATE_HZ 31250u

typedef struct {
    uint16_t phase1, phase2, inc1, inc2;
} dds_t;

/* Incremento de fase para f_hz (división de 32 bits: llamar fuera de cli). */
uint16_t dds_increment(uint16_t f_hz);
/* Solo guarda los incrementos (barato, apto para una sección crítica). */
void dds_set_increments(dds_t *d, uint16_t inc1, uint16_t inc2);
/* f1 = f2 = 0: silencio. f2 = 0: un solo tono. No resetea la fase. */
void dds_set(dds_t *d, uint16_t f1_hz, uint16_t f2_hz);
/* Muestra 0-255 centrada en 128; avanza las fases. */
uint8_t dds_next(dds_t *d);

#endif
