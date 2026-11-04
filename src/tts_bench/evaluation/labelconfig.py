"""Spanish Label Studio label configs (Community Edition tags only) generated from scales.py."""

from __future__ import annotations

from xml.sax.saxutils import escape, quoteattr

from . import scales

TITLES = {
    "mos": "MOS – Evaluación de voz",
    "cmos": "CMOS – Comparación A/B",
    "sim": "SIM – Parecido de voz",
}


def _anchor_html(anchors: dict) -> str:
    return "<br/>".join(f"<b>{k}</b> – {escape(v)}" for k, v in sorted(anchors.items(), reverse=True))


def mos_config() -> str:
    parts = ['<View>', '  <Header value="Escuche el audio"/>',
             '  <Audio name="audio" value="$audio"/>',
             '  <Text name="text" value="$text"/>']
    for key, c in scales.MOS_CRITERIA.items():
        parts.append(f'  <Header value={quoteattr(c["question"])}/>')
        parts.append(f'  <Rating name={quoteattr(key)} toName="audio" maxRating="5" icon="star" size="medium"/>')
        parts.append(f'  <Text name="ayuda_{key}" value={quoteattr(_anchor_html(c["anchors"]))}/>')
    parts.append('</View>')
    return "\n".join(parts)


def cmos_config() -> str:
    return "\n".join([
        '<View>',
        '  <Header value="Audio A"/>', '  <Audio name="audio_a" value="$audio_a"/>',
        '  <Header value="Audio B"/>', '  <Audio name="audio_b" value="$audio_b"/>',
        '  <Text name="text" value="$text"/>',
        f'  <Header value={quoteattr(scales.CMOS["question"])}/>',
        '  <Choices name="cmos" toName="audio_a" choice="single-radio" showInline="false">',
        *[
            f'    <Choice value={quoteattr(label)} alias={quoteattr(str(v))}/>'
            for v, label in sorted(scales.CMOS["choices"].items())
        ],
        '  </Choices>',
        '</View>',
    ])


def sim_config() -> str:
    return "\n".join([
        '<View>',
        '  <Header value="Referencia"/>', '  <Audio name="reference" value="$reference"/>',
        '  <Header value="Audio a evaluar"/>', '  <Audio name="audio" value="$audio"/>',
        '  <Text name="text" value="$text"/>',
        f'  <Header value={quoteattr(scales.SIM["question"])}/>',
        f'  <Text name="nota" value={quoteattr(scales.SIM["note"])}/>',
        '  <Rating name="sim" toName="audio" maxRating="5" icon="star" size="medium"/>',
        f'  <Text name="ayuda_sim" value={quoteattr(_anchor_html(scales.SIM["anchors"]))}/>',
        '</View>',
    ])


CONFIGS = {"mos": mos_config, "cmos": cmos_config, "sim": sim_config}


def label_config(project: str) -> str:
    return CONFIGS[project]()


def instructions() -> str:
    return scales.INSTRUCTIONS


SAMPLING = "Uniform sampling"  # random task order (verified name, research R14)
