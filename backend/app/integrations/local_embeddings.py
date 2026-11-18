import threading

from filelock import FileLock
from app.core.native_paths import native_directory


MODEL = "all-MiniLM-L6-v2"
SCHEMA = "minilm-220tokens-overlap24-v2"


class LocalEmbeddings:
    def __init__(self, runtime):
        self.runtime = native_directory(runtime)
        self.lock = threading.RLock()
        self.encoder = None
        self.tokenizer = None

    def prepare(self):
        with self.lock:
            if self.encoder is not None:
                return
            from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2
            from tokenizers import Tokenizer
            encoder = ONNXMiniLM_L6_V2(preferred_providers=["CPUExecutionProvider"])
            encoder.DOWNLOAD_PATH = self.runtime / "models" / MODEL
            self.runtime.mkdir(parents=True, exist_ok=True)
            with FileLock(str(self.runtime / "model.lock"), timeout=180):
                encoder(["Prepare local document search."])
            tokenizer = Tokenizer.from_str(encoder.tokenizer.to_str())
            tokenizer.no_truncation()
            tokenizer.no_padding()
            self.encoder, self.tokenizer = encoder, tokenizer

    def split(self, text):
        self.prepare()
        offsets = [(a, b) for a, b in self.tokenizer.encode(text).offsets if b > a]
        if not offsets:
            return []
        return [text[offsets[start][0]:offsets[min(start + 220, len(offsets)) - 1][1]] for start in range(0, len(offsets), 196)]

    def embed(self, texts):
        self.prepare()
        with self.lock:
            return [vector.tolist() for vector in self.encoder(texts)]
