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

El script tampoco toca `pots-in-a-box.kicad_pro` si ya existe, porque ahí están las clases de
red y las reglas de DRC.

Al final, el script también genera la **lista de materiales** con `hardware/tools/gen_bom.py`.
Ese script se puede correr solo y necesita `kicad-cli` y Google Chrome. Escribe dos archivos:

- `hardware/bom.csv`, con los datos del esquemático;
- `hardware/bom.pdf`, para imprimir: A4, agrupado por tipo, con casillas para tildar y lo que no
  está en el esquemático (zócalos, módulo elevador, fuente, gabinete).

Las descripciones de encapsulado, las notas y los extras están en tablas al principio de
`gen_bom.py`. Si aparece una huella nueva sin descripción, el PDF muestra el nombre crudo de la
huella.

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

## PCB preliminar (para elegir el gabinete)

`hardware/kicad/pots-in-a-box.kicad_pcb` es una **ubicación inicial, sin rutear**, generada
desde el esquemático:

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/tools/gen_pcb.py
```

Sirve para definir el tamaño de la placa, dónde van los conectores y qué altura tienen los
componentes, para elegir o diseñar el gabinete. No sirve para fabricar.

- **Diseño en mil** (milésimas de pulgada, la grilla de los DIP). Cada pieza se ubica por su
  origen (la pata 1), así que DIP y resistencias quedan con todas las patas sobre la grilla de
  100 mil. Las filas de piezas iguales van cada 200 mil. Las piezas de paso métrico (cerámicos
  de 5 mm, el capacitor de 15 mm, cristales, fusibles) tienen la pata 1 en la grilla y la otra
  donde cae. Las piezas ubicadas automáticamente van a una grilla de 50 mil.
- Placa de 5500 × 3850 mil (139,70 × 97,79 mm), 2 capas, 4 agujeros M3 a 150 mil de cada borde.
  Gabinete previsto: ABS de 150 × 120 × 40 mm, admite hasta 5500 × 3850 mil. La placa ya tiene
  ese tamaño; faltan las muescas de los tubos de cierre y los agujeros sobre los soportes,
  cuando estén las medidas. Mientras se acomoda a mano, el script genera la placa igual aunque
  haya piezas fuera del borde o superpuestas, y las lista para corregirlas en KiCad.
- **Organización modular.** Mirando el panel trasero desde atrás, de izquierda a derecha:
  jack de 12 V y bloques compartidos, línea L1, línea L2. Cada línea es una columna de 1400 mil (35,56 mm)
  que va de atrás hacia adelante, con las mismas piezas en el mismo lugar (los RJ11 quedan
  separados 1400 mil). Para agregar una línea se suma una columna en ese extremo (`LINES`,
  `LINE_W` en el script).
- **Panel trasero** (coordenadas vistas desde arriba, x = 0 en el extremo de L2): RJ11 L2
  (x = 600 mil), RJ11 L1 (x = 2000 mil), jack de 12 V (x = 5000 mil).
- **Panel frontal:** LED PWR y LED CALL (posiciones provisorias, se están acomodando a
  mano). El conector de la llave AR/US (SW1) va adentro de la placa, con cable al panel.
- **Columna de línea** (ubicada a mano en `LINE_LAYOUT`, de atrás hacia adelante siguiendo la
  señal): RJ11 con el TVS pegado a sus patas y el relé de ring al lado; alimentación del lazo
  (F, Q101/Q102 junto a R101/R102); capacitor de acople; optoacoplador con su diodo; red de
  audio y filtro de tono; MT8870 acostado con su cristal en OSC y su desacople en VDD; abajo
  de Q1–Q4, las resistencias serie paradas.
- **Bus DTMF:** las salidas Q1–Q4 de todos los MT8870 van, cada una por su resistencia de
  1 k, a un bus común (`DTMF_Q1..Q4`) que entra al ATmega por PC2–PC5. Se deja libre una
  franja de 300 mil a lo largo del frente de las columnas para ese bus y para las señales propias
  de cada línea (TONE, StD, OFFHOOK, relé). El ATmega está girado para que PC2–PC5 queden
  sobre esa franja.
- Bloques compartidos: puente H (ring) atrás, junto a L1; alimentación atrás, en el extremo;
  MCU adelante junto a L1 (con su cristal en XTAL1/2, `SHARED_LAYOUT`); relé de unión y
  ULN2003A adelante, en el extremo.
- No hay espacio reservado para el elevador propio: por ahora queda como módulo externo en `J2`,
  que el script ubica donde haya lugar en la zona compartida.
- La biblioteca de KiCad no tiene modelo 3D del RJ12: `hardware/kicad/3d/rj12_body.wrl` es una
  caja de las medidas del conector, solo para el render.
- Ver en 3D: abrir el PCB en KiCad y usar Ver → Visor 3D (Alt+3).

**Mover piezas a mano y pasarlas al script.** Se puede ajustar la ubicación en KiCad
(mover, rotar) y después copiarla al script, para no perderla al regenerar:

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/tools/pull_layout.py
```

Compara el PCB guardado con uno recién generado y escribe en `gen_pcb.py` cada pieza que se
movió: las de línea (de L1 o de L2) en `LINE_LAYOUT`, que vale para todas las líneas;
las compartidas en `SHARED_LAYOUT`. Si se acomodó una sola línea, `--line L2` (o `L1`) toma
las posiciones solo de esa y las copia a las demás; `--dry-run` muestra los cambios sin escribir.
Las posiciones se miden desde el borde de la placa, así que no importa si KiCad la movió en la hoja.
Conviene mover las piezas con la grilla de KiCad en 25 o 50 mil (el script deja la placa dentro del marco
de la hoja, con la esquina en 1000,1000 mil, y pone ahí el origen de la grilla); si alguna queda fuera, el script lo avisa. Los conectores del panel y los agujeros solo los informa
(van en `EDGE_PARTS`). Las pistas se ignoran. Hay que correrlo sobre un PCB generado por la
versión actual del script.

**Clases de red** (en `kicad/pots-in-a-box.kicad_pro`, no en el PCB; `gen_pcb.py` conserva ese archivo al
regenerar, porque guardar el PCB desde Python lo reescribiría con valores por defecto):

| Clase | Redes | Pista | Separación |
|---|---|---|---|
| `HV` | V_LINE, RING_A/B, riel del puente (`Net-(Q3-D)`), lado alto de los IR2104 (VB, HO, gate alta), TIP/RING de cada jack, alimentación del lazo (Q1x1), TIP_FEED, RING_RET | 0,5 mm | 0,6 mm |
| `Power` | +12V, +5V, GND | 0,6 mm | 0,2 mm |
| `Default` | el resto | 0,25 mm | 0,2 mm |

La separación de `HV` sale de IPC-2221 para capa externa sin recubrir hasta 150 V (V_LINE de
24–48 V para la línea, hasta ~90 V para el ring). Varias redes `HV` no tienen nombre en el
esquemático y se asignan por patrón (`Net-(D?02-A?)`, `Net-(Q?01-?)`, …): si cambian las
referencias, hay que revisar los patrones. `kicad/pots-in-a-box.kicad_dru` deja las patas de un
mismo transistor de la alimentación del lazo (TO-126 / TO-92) con la separación normal, porque el
encapsulado las tiene más juntas que 0,6 mm.
Q1x2 (BC546) usa el TO-92 de patas separadas (`TO-92_Inline_Wide`, 2,54 mm): con el TO-92
común no entra una pista `HV` entre sus patas. El script deja además una franja de 1 mm
(`EDGE_KEEPOUT`) sin pistas ni vías a lo largo del borde, porque Freerouting no respeta la
distancia al borde. El ancho mínimo de pista de la placa es 0,15 mm: Freerouting angosta las
pistas al 75 % al entrar a las patas.

**Ruteo de prueba:** Tools → External Plugins → Freerouting (plugin instalado desde el
Plugin and Content Manager). Sirve para ver si la ubicación se puede rutear; el ruteo se pierde
al regenerar.

Cuando se congele el esquemático, el PCB también pasa a editarse en KiCad: la ubicación final y
el ruteo se hacen a mano y este script queda como histórico.

## Pendiente

- [ ] Valores finales de `V_LINE`, R_SENSE, acople y nivel de tono (salen de la prueba de banco).
- [ ] Huella alternativa del transformador 600:600 en paralelo con el capacitor de acople (spec §7.4).
- [ ] Elevador propio en la placa, en lugar del módulo.
- [x] Dibujo con cables en todas las hojas.
- [x] PCB preliminar sin rutear, para el gabinete.
- [ ] PCB: separar la zona de alta tensión (`V_LINE`, puente, relés, RJ11) de la lógica.
