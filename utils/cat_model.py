"""utils/cat_model.py — loads domesticated-LLM and generates cat messages"""
import torch
import os
from functools import lru_cache

MODEL_PATH = os.getenv("CAT_MODEL_PATH", "./domesticated-LLM")

# ── Lazy load — only instantiates on first call ───────────────────────────────
_model     = None
_tokenizer = None

def _load():
    global _model, _tokenizer
    if _model is not None:
        return
    from transformers import AutoTokenizer, AutoModelForCausalLM
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    _model     = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        dtype=torch.float32,
        device_map="auto",
    )
    _model.eval()

# ── Style → instruction mapping ───────────────────────────────────────────────
STYLE_INSTRUCTIONS = {
    "food":      "Ask for food",
    "play":      "Ask to play",
    "sleep":     "Tell the owner you are sleepy",
    "affection": "Ask to be petted",
    "grooming":  "Tell the owner you are grooming yourself",
    "alarm":     "Warn the owner about something outside",
    "boredom":   "Tell the owner you are bored",
    "comfort":   "Tell the owner you are scared",
    # toy-driven styles
    "zoomies":   "Ask to play",
    "hunt":      "Warn the owner about a bird you spotted",
    "happy":     "Tell the owner you love them",
}

def generate_cat_message(
    instruction: str,
    context: str,
    temperature: float = 0.85,
    max_new_tokens: int = 40,
) -> str:
    _load()
    prompt = f"### Instruction: {instruction}\n### Context: {context}\n### Response:"
    inputs = _tokenizer(prompt, return_tensors="pt").to(_model.device)

    with torch.no_grad():
        output = _model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=0.9,
            repetition_penalty=1.2,
            pad_token_id=_tokenizer.eos_token_id,
        )

    decoded  = _tokenizer.decode(output[0], skip_special_tokens=True)
    response = decoded.split("### Response:")[-1].strip()
    # Cap to first line in case model rambles
    return response.split("\n")[0].strip()


def pick_style(happiness: int, hunger: int, toy_style: str) -> str:
    """Choose what the cat talks about based on its current state."""
    if hunger < 20:
        return "food"
    if happiness < 30:
        return "comfort"
    if toy_style == "zoomies":
        return "zoomies"
    if toy_style == "hunt":
        return "hunt"
    if happiness > 80 and toy_style == "happy":
        return "happy"
    if happiness < 50:
        return "boredom"
    import random
    return random.choice(["affection", "play", "boredom", "food", "sleep"])


def build_check_in_message(
    pet_name: str,
    happiness: int,
    hunger: int,
    toy_style: str,
    owner_context: str = "I haven't heard from you in a while",
) -> str:
    style       = pick_style(happiness, hunger, toy_style)
    instruction = STYLE_INSTRUCTIONS[style]
    message     = generate_cat_message(instruction, owner_context)
    return f"**{pet_name}:** {message}"
