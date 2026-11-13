/* dds.h — direct digital synthesis of 1 or 2 sines for 8-bit PWM. */
#ifndef DDS_H
#define DDS_H

#include <stdint.h>

/* Timer0 fast PWM, 8 bits, 62500 Hz; each channel gets a sample every 2 overflows. */
#define DDS_SAMPLE_RATE_HZ 31250u

typedef struct {
    uint16_t phase1, phase2, inc1, inc2;
} dds_t;

/* Phase increment for f_hz (32-bit division: call outside cli). */
uint16_t dds_increment(uint16_t f_hz);
/* Stores the increments only (cheap, safe inside a critical section). */
void dds_set_increments(dds_t *d, uint16_t inc1, uint16_t inc2);
/* f1 = f2 = 0: silence. f2 = 0: single tone. Does not reset the phase. */
void dds_set(dds_t *d, uint16_t f1_hz, uint16_t f2_hz);
/* Sample 0-255 centred on 128; advances the phases. */
uint8_t dds_next(dds_t *d);

#endif
