# Hardware de POTS in a box

Proyecto KiCad 10 en `hardware/kicad/`. Se abre con `pots-in-a-box.kicad_pro`.

## Cómo está armado

El esquemático **se genera con un script**, no se dibuja a mano:

```sh
python3 hardware/tools/gen_schematic.py
```

El script (`hardware/tools/gen_schematic.py`) tiene la lista de componentes y la red de cada
pata, bloque por bloque. Cada pata lleva un tramo corto de cable con el nombre de su red
(o un símbolo de alimentación), así las conexiones son explícitas y verificables. **Si se
edita el `.kicad_sch` a mano y después se vuelve a correr el script, los cambios se pierden**:
los cambios de circuito van en el script.

Verificación eléctrica (ERC), desde la raíz del repo:

```sh
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch erc --severity-all hardware/kicad/pots-in-a-box.kicad_sch
```

## Hojas

| Hoja | Contenido |
|---|---|
| `pots-in-a-box` (raíz) | los bloques y las conexiones entre ellos |
| `power` | jack de 12 V, PTC, diodo de protección, 7805, conector del módulo elevador (`V_LINE`), resistencia de descarga, LED de encendido |
| `mcu` | ATmega328P (mapa de pines de `firmware/README.md`, compatible con Arduino Uno), cristal, ISP, conector serie estilo FTDI, llave AR/US, LED de llamada |
| `ring` | puente H compartido: 2 × IR2104 + 4 × IRF540N, R_BRIDGE, inversor BC547 |
| `link` | ULN2003A y relé de unión de audio L1–L2 |
| `line` (×2: `line_L1`, `line_L2`) | bloque de línea completo: RJ11, TVS, limitador de corriente, relé de ring DPDT, PC817, acople por capacitor, protección del audio, filtro de tono, MT8870 |

La hoja `line` es el bloque que se repite: para más líneas se agregan instancias.
Referencias: L1 usa la serie 100 (R101, U102…) y L2 la serie 200.

## Decisiones de esta versión

- **Puente H con IR2104** (driver de medio puente de 600 V con tiempo muerto interno) y 4
  MOSFET de canal N, en lugar del puente con MOSFET de canal P de la prueba de banco.
- **Elevador como módulo:** `J2` es una bornera para el módulo elevador. El elevador propio
  (por ejemplo MC34063 + MOSFET) se diseña con los resultados de la prueba de banco.
- **Un cristal por MT8870.** Compartir uno queda para cuando se confirme en la prueba.
- **Partes del panel por conector:** la llave AR/US va por un conector de 2 pines; los LEDs
  de encendido y de llamada están en la placa, a reubicar según la caja.
- **Jack de 12 V:** pata 1 = centro (+). Verificar contra el jack que se compre.

## Pendiente

- [ ] Valores finales de `V_LINE`, R_SENSE, acople y nivel de tono (salen de la prueba de banco).
- [ ] Huella alternativa del transformador 600:600 en paralelo con el capacitor de acople (spec §7.4).
- [ ] Elevador propio en la placa, en lugar del módulo.
- [ ] Ordenar el dibujo: hoy es un esquemático "de etiquetas", correcto pero poco prolijo.
- [ ] PCB: separar la zona de alta tensión (`V_LINE`, puente, relés, RJ11) de la lógica.
