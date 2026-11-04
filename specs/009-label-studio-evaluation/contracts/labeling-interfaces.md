# Contract: Labeling Interfaces and Scales (Spanish, frozen)

Scale definitions live in `scales.py`; their hash is stored in `batch.json` and exported.

## MOS (project "MOS – Evaluación de voz")
Three `Rating`s on one audio, each 1–5:
- **Naturalidad** — ¿Qué tan natural suena la voz? 5 Excelente, completamente natural · 4 Buena, casi natural · 3 Aceptable, claramente sintética pero cómoda · 2 Pobre, artificial y molesta · 1 Muy mala, no natural.
- **Pronunciación** — ¿Las palabras, cifras y nombres se pronuncian correctamente? 5 Todo correcto · 4 Un error leve · 3 Algunos errores sin afectar el sentido · 2 Errores que dificultan entender · 1 Incomprensible.
- **Prosodia** — ¿El ritmo, la entonación y las pausas son adecuados para una llamada? 5 Muy natural · 4 Adecuada · 3 Algo monótona o irregular · 2 Poco natural · 1 Robótica o confusa.

## CMOS (project "CMOS – Comparación A/B")
One `Choices` 7-point (values −3…+3): "B es mucho peor que A" (−3) … "Iguales" (0) … "B es mucho mejor que A" (+3). Question: "Considerando la naturalidad general, ¿cómo es B comparado con A?" A/B position is randomized per task; the mapping records which condition is B.

## SIM (project "SIM – Parecido de voz")
Reference + clip, `Rating` 1–5: 5 Misma persona, sin duda · 4 Probablemente la misma · 3 No estoy seguro · 2 Probablemente distinta · 1 Claramente distinta. Question: "¿Qué tan parecida es la voz del audio a la de la referencia?" (judge voice identity, not recording quality).

## Common
Instructions page in Spanish (listen with headphones, one listen minimum, ignore content, native speakers). Random task ordering enabled. Annotators see no model, engine or voice labels.
