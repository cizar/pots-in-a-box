# POTS in a box

Una central telefónica analógica de 2 líneas para que computadoras retro con módem se
llamen entre sí, sin una línea telefónica real. La red analógica (POTS, *Plain Old
Telephone Service*) ya no existe: esta caja la simula entera.

```
 [Commodore 64 + Modem 1200] ──RJ11── ┌──────────────┐ ──RJ11── [PC con BBS + módem]
                                      │ POTS in a box │
                                      └──────┬───────┘
                                          12 V
```

- Alimentación de línea, tono de invitación a marcar, ring, tono de llamada y de ocupado.
- Marcado por tonos (DTMF) y por pulsos. Cualquier número marcado hace sonar la otra línea.
- Tonos de Argentina (ITU-T E.180) o de EE.UU., con una llave física.
- Se alimenta con una fuente externa de 12 V: no hay 220 V dentro de la caja.
- ATmega328P, MT8870 y ULN2003A. Todos los componentes son pasantes.

## Estado

- **Firmware:** completo y probado en la PC (`make -C firmware test`). Todavía no se probó en
  hardware.
- **Hardware:** en prueba de banco ([docs/prueba-banco.md](docs/prueba-banco.md)). El
  esquemático y el PCB en KiCad vienen después.

## Documentación

- [Diseño](docs/superpowers/specs/2026-11-13-pots-2-lineas-design.md)
- [Firmware: cómo compilar y grabar, mapa de pines](firmware/README.md)
- [Prueba de banco](docs/prueba-banco.md)

## Seguridad

Las líneas llevan hasta 48 V de continua y la ring, con corriente limitada. Leé la sección
de seguridad de la prueba de banco antes de armar nada.

## Licencia

Firmware bajo GPL-3.0-or-later; hardware y documentación bajo CERN-OHL-S-2.0. Ver
[LICENSE.md](LICENSE.md).
