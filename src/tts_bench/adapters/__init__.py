from ..core.registry import register

register("fake", "tts_bench.adapters.fake:FakeAdapter")
register("phonon", "tts_bench.adapters.phonon:PhononAdapter")
register("pocket_tts", "tts_bench.adapters.pocket_tts:PocketTTSAdapter")
register("piper", "tts_bench.adapters.piper:PiperAdapter")
