"""Explicit one-time download; all later model inference is local."""
from huggingface_hub import snapshot_download

from src.ocr_pipeline.multilingual import ENCODER_ID, ENCODER_PATH, ENCODER_REVISION, ROOT


if __name__ == "__main__":
    print(snapshot_download(
        ENCODER_ID,
        revision=ENCODER_REVISION,
        local_dir=str(ROOT / ENCODER_PATH),
        allow_patterns=["config.json", "modules.json", "sentence_bert_config.json",
                        "model.safetensors", "tokenizer.json", "tokenizer_config.json",
                        "special_tokens_map.json", "sentencepiece.bpe.model", "1_Pooling/config.json"],
    ))
