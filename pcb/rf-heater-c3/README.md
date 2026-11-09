# rf-heater-c3

Placa de connexió de 2 capes (FR4 1.6 mm, 43.7 × 30 mm) per a un ESP32-C3 Super Mini amb un mòdul CC1101 868 MHz (format M115, pads castellats). Tota la placa es genera des de `generate.py`.

## Fitxers

- `generate.py`: genera `rf-heater-c3.kicad_pcb` i `.kicad_pro`, rutat amb Freerouting, zones GND, DRC, Gerbers i renders.
- `fab/rf-heater-c3-gerbers.zip`: Gerbers (Cu, Mask, Silk, Paste, Edge.Cuts) i Excellon.
- `render-top.png`, `render-bottom.png`.

## Mapatge de pins

| ESP32-C3 (U1) | GPIO | Net | CC1101 (U2) |
|---|---|---|---|
| 3V3 | - | 3V3 | 1 VCC |
| G | - | GND | 2, 9, 11 GND |
| 4 | GPIO4 | SCK | 4 SCLK |
| 5 | GPIO5 | MISO | 5 SO |
| 6 | GPIO6 | MOSI | 3 SI |
| 7 | GPIO7 | CSN | 8 CSN |
| 10 | GPIO10 | GDO0 | 7 GDO0 |

U2.6 (GDO2) no es connecta. U2.10 (ANT) no té net: és el pad on es solda l'antena de molla.

## Regenerar

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 -I generate.py
```

Cal Freerouting a `~/.local/share/freerouting/freerouting-2.5.0.jar` i Java (per defecte `brew --prefix openjdk`; es pot fixar amb `JAVA_BIN`). El script sobreescriu els fitxers de sortida.

## BOM

| Ref | Component | Qtat | Notes |
|---|---|---|---|
| U1 | ESP32-C3 Super Mini | 1 | 2 files de 8 forats de 2.54 mm, separades 15.24 mm |
| U2 | Mòdul CC1101 868 MHz (M115) | 1 | 8 pads a la vora de capçalera, 3 a la vora d'antena |
| ANT | Antena de molla 868 MHz | 1 | Soldada al pad 10 |
| C1 | Electrolític 10 µF, radial 5 mm, P 2.00 mm | 1 | Polaritat: el `+` és el pad 1 (3V3) |
| C2 | Ceràmic 100 nF, disc D3 mm, P 2.50 mm | 1 | |
| H1, H2 | Forat M3 (3.2 mm, sense pad) | 2 | Per a cargols M3 |
| - | Pins 2×8 de 2.54 mm | 2 | Opcional, per soldar o endollar el C3 |

## Muntatge

- Soldar primer C2 i C1, després U1 i finalment U2.
- U2: el punt de pin 1 és a la part inferior de la vora de capçalera. Els pads són SMD de 2 × 1 mm que sobresurten de la vora del mòdul: soldar-los amb ferro i una mica de flux.
- Pad 10 (ANT) sense net: només serveix de punt de soldadura per a l'antena. Al voltant hi ha una zona prohibida de 3 mm (sense pistes, vies ni farcit de GND), amb dos corredors per als pads 9 i 11.
- Les posicions dels pads d'antena (`ANT_PAD_OFFSETS`, mesurades des de la cantonada del pin 1) són les del mòdul real que s'ha mesurat. Les mides del mòdul (`MOD_H = 17.4`) i els pads 9 i 11 (1.2 mm) també venen d'aquesta mesura.
- **El `.kicad_pcb` té edicions manuals** (serigrafia, p. ex. el text «elboletaire» i la data, i algunes posicions). Regenerar amb `generate.py` les sobreescriuria: aleshores cal tornar-les a aplicar a mà.

## Notes

- La vora dreta de la placa és a x = 43.7, no a 42.4: així els pads d'antena (que sobresurten 1 mm del mòdul) queden dins la placa amb 0.3 mm de marge.
- El GND no es rutat: el connecten el farcit de les dues capes, tres petites pistes de 0.5 mm (pads 9 i 11 i pad 2 del mòdul cap al farcit), una pista de 0.6 mm des del GND del C3 (U1.2) per la vora superior, i 3 vies d'unió entre capes.
- DRC: 0 errors, 0 unconnected. Avisos: 2 de biblioteca de footprint `rf-heater-c3` (custom, no és a la taula de biblioteques de l'usuari) i 3 de serigrafia tocant la vora (el contorn del C3 és a y = 0).
- Freerouting ha estrenyit alguns segments: 3V3 a 0.375 mm (a prop del C3, a la vora superior), MOSI i SCK a 0.225 mm (prop dels pads). Compleixen el mínim de 0.2 mm, però no els objectius de 0.5 mm (3V3) i 0.3 mm (senyals).
