# Hardware de POTS in a box

Proyecto KiCad 10 en `hardware/kicad/`. Se abre con `pots-in-a-box.kicad_pro`.

## Cómo está armado

El esquemático **se genera con un script**, no se dibuja a mano:

```sh
python3 hardware/tools/gen_schematic.py
```

El script (`hardware/tools/gen_schematic.py`) tiene la lista de componentes y la red de cada
pata, bloque por bloque, y una función de dibujo por hoja que ubica los componentes y une las
patas con cables, puntos de unión y rieles de alimentación, como un esquemático hecho a mano.
Se usan etiquetas solo donde un cable tendría que cruzar otros (las E/S del ATmega, los
contactos del relé de ring, las salidas del MT8870) o para ir a otra hoja.

Al terminar, el script exporta la netlist con `kicad-cli` y la **compara con la lista de
redes del script**: si un cable quedó mal dibujado (un componente girado al revés, una unión
de más o de menos), lo informa como problema. Tiene que decir `netlist check: OK`. **Si se
edita el `.kicad_sch` a mano y después se vuelve a correr el script, los cambios se pierden**:
los cambios de circuito van en el script.

**Hasta cuándo:** el script es la fuente hasta tener los resultados de la prueba de banco.
Antes de diseñar el PCB se congela: desde ese momento los `.kicad_sch` pasan a ser la fuente,
se editan solo en KiCad y el script queda como histórico.

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
  La pata ~SD de cada IR2104 va directo a +12 V (la entrada admite hasta VCC), sin
  resistencia de pull-up: los drivers quedan siempre habilitados.
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
- [x] Dibujo con cables en todas las hojas.
- [ ] PCB: separar la zona de alta tensión (`V_LINE`, puente, relés, RJ11) de la lógica.
