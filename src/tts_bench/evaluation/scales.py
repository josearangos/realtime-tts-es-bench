"""Frozen Spanish scales and anchors (contracts/labeling-interfaces.md). Changing any text changes scale_hash()."""

from __future__ import annotations

import hashlib
import json

MOS_CRITERIA = {
    "naturalidad": {
        "question": "¿Qué tan natural suena la voz?",
        "anchors": {
            5: "Excelente, completamente natural",
            4: "Buena, casi natural",
            3: "Aceptable, claramente sintética pero cómoda",
            2: "Pobre, artificial y molesta",
            1: "Muy mala, no natural",
        },
    },
    "pronunciacion": {
        "question": "¿Las palabras, cifras y nombres se pronuncian correctamente?",
        "anchors": {
            5: "Todo correcto",
            4: "Un error leve",
            3: "Algunos errores sin afectar el sentido",
            2: "Errores que dificultan entender",
            1: "Incomprensible",
        },
    },
    "prosodia": {
        "question": "¿El ritmo, la entonación y las pausas son adecuados para una llamada?",
        "anchors": {
            5: "Muy natural",
            4: "Adecuada",
            3: "Algo monótona o irregular",
            2: "Poco natural",
            1: "Robótica o confusa",
        },
    },
}

CMOS = {
    "question": "Considerando la naturalidad general, ¿cómo es B comparado con A?",
    "choices": {
        -3: "B es mucho peor que A",
        -2: "B es peor que A",
        -1: "B es ligeramente peor que A",
        0: "Iguales",
        1: "B es ligeramente mejor que A",
        2: "B es mejor que A",
        3: "B es mucho mejor que A",
    },
}

SIM = {
    "question": "¿Qué tan parecida es la voz del audio a la de la referencia?",
    "note": "Juzgue la identidad de la voz, no la calidad de la grabación.",
    "anchors": {
        5: "Misma persona, sin duda",
        4: "Probablemente la misma",
        3: "No estoy seguro",
        2: "Probablemente distinta",
        1: "Claramente distinta",
    },
}

INSTRUCTIONS = (
    "Escuche cada audio con audífonos, al menos una vez completa. "
    "Ignore el contenido de la frase y juzgue solo la voz. "
    "Esta evaluación es para hablantes nativos de español."
)


def definitions() -> dict:
    return {"mos": MOS_CRITERIA, "cmos": CMOS, "sim": SIM, "instructions": INSTRUCTIONS}


def scale_hash() -> str:
    blob = json.dumps(definitions(), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
