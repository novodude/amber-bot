"""utils/cat_model.py — cat message generation with LLM + synthesis fallback

Priority:
  1. domesticated-LLM (transformers, if model files exist and torch is available)
  2. Synthesis engine (always available, no dependencies)
"""

import os
import random
import logging

log = logging.getLogger(__name__)

MODEL_PATH = os.getenv("CAT_MODEL_PATH", "./domesticated-LLM")

# ── Lazy LLM state ────────────────────────────────────────────────────────────
_model     = None
_tokenizer = None
_llm_ok    = None   # None = untested, True = works, False = unavailable


def _try_load_llm() -> bool:
    """Attempt to load the LLM once. Returns True on success."""
    global _model, _tokenizer, _llm_ok
    if _llm_ok is not None:
        return _llm_ok

    model_dir = os.path.isdir(MODEL_PATH) and os.listdir(MODEL_PATH)
    if not model_dir:
        log.info("cat_model: no model files found at %s — using synthesis fallback", MODEL_PATH)
        _llm_ok = False
        return False

    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM

        _tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
        _model     = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            torch_dtype=torch.float32,
            device_map="auto",
        )
        _model.eval()
        _llm_ok = True
        log.info("cat_model: domesticated-LLM loaded successfully")
        return True

    except Exception as exc:
        log.warning("cat_model: LLM unavailable (%s) — using synthesis fallback", exc)
        _llm_ok = False
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  SYNTHESIS ENGINE
# ══════════════════════════════════════════════════════════════════════════════

_CAT_NOISES = [
    "mmrp", "prrm", "mrr", "mrrow", "mrrp",
    "mrrpmm", "pprrm", "mrawh", "mrahr", "prrr",
    "rraow", "chirp", "brrt", "trrll", "mew",
]
_EMOTES = [
    "uwu", ">.<", "-_-", "o-o", "0.o",
    "o.o", "ouo", ":3", ">:3", ":D",
    "^.^", "=^.^=", "OwO", "QwQ", ";3",
]
_FILLERS = ["uh", "um", "er", "hmm", "huh", "eh", "ah", "weh", "nya", "meh"]

# Style → word pool (richer pools than data_synthesis.py)
_STYLE_POOLS: dict[str, list[str]] = {
    "food":      ["nom nom?", "food?", "hungy..", "fooood", "need eat",
                  "eat now", "tummy empty", "want food", "bowl empty", "feeeed",
                  "snack pls", "kibble?", "treat treat", "more food", "hungry cry"],
    "play":      ["g-game", "toy?", "clicky", "snek!", "play now",
                  "run run", "chase!", "fun time", "feather!", "zooomies",
                  "throw it!", "bat bat", "pounce!", "catch me", "lets go!!"],
    "sleep":     ["sleepy..", "zzz", "tired", "nap now", "warm spot",
                  "cozy pls", "blanket", "snooze", "rest time", "cuddle sleep",
                  "soft bed pls", "dark room", "no wake", "quiet now", "heavy eyes"],
    "affection": ["pet me", "scritch pls", "luv u", "headbutt", "biscuit time",
                  "purr purr", "snuggle", "chin chin", "hold me", "floofy hug",
                  "ear rub", "belly... maybe", "stay close", "dont go", "warm lap"],
    "grooming":  ["lick lick", "clean now", "groom time", "fur fix", "tidy up",
                  "bath time", "paw wash", "ear clean", "brushy?", "scrub scrub",
                  "tongue work", "so clean", "pristine cat", "dust off", "polish"],
    "alarm":     ["danger!", "intruder!", "stranger!", "bird outside!", "loud noise!",
                  "scary thing", "big thing", "watch out", "protect hooman", "alert!!",
                  "something there", "i see it", "dont move", "eyes on it", "suspicious"],
    "boredom":   ["nothing do", "bored bored", "entertain me", "pay attention",
                  "no fun", "boring here", "do something", "look at me", "me me me",
                  "hello??", "notice me", "im here", "so empty", "need content", "sighs"],
    "comfort":   ["scared..", "bad noise", "hold me pls", "no like", "make stop",
                  "too loud", "hiding now", "not safe", "need hooman", "protect me",
                  "under bed", "dont leave", "safe pls", "no more scary", "shaking"],
    # toy-specific styles
    "zoomies":   ["ZOOOOM", "fast cat", "run run RUN", "cant stop", "legs go brrr",
                  "speed mode", "activate!!", "wall run", "nowhere safe", "chaos time"],
    "hunt":      ["bird spotted", "prey detected", "stalking...", "gotcha!", "hunter mode",
                  "very sneaky", "camouflage", "pounce ready", "target locked", "shh shh"],
    "happy":     ["luv u lots", "best hooman", "so happy", "content purr", "life good",
                  "warm fuzzy", "grateful cat", "heart eyes", "wholesome", "no complaints"],
}

# Fallback pool for any unknown style
_DEFAULT_POOL = _STYLE_POOLS["affection"]


def _synthesize(style: str) -> str:
    """Build a cat message from vocabulary pools. No ML required."""
    pool = _STYLE_POOLS.get(style, _DEFAULT_POOL)
    parts: list[str] = []

    # 1–2 meaning words
    parts.append(random.choice(pool))
    if random.random() < 0.45:
        parts.append(random.choice(pool))

    # 1–2 cat noises
    parts += random.choices(_CAT_NOISES, k=random.randint(1, 2))

    # occasional filler
    if random.random() < 0.60:
        parts.append(random.choice(_FILLERS))

    # occasional emote
    if random.random() < 0.75:
        parts.append(random.choice(_EMOTES))

    random.shuffle(parts)
    msg = " ".join(parts)

    # small stylistic quirks
    if random.random() < 0.25:
        msg += " " + random.choice(_CAT_NOISES)
    if random.random() < 0.15:
        # repeat a word for emphasis
        words = msg.split()
        msg += " " + random.choice(words)

    return msg.strip()


# ══════════════════════════════════════════════════════════════════════════════
#  LLM GENERATION (used only when model is available)
# ══════════════════════════════════════════════════════════════════════════════

# Style → instruction sentence for the LLM prompt
_STYLE_INSTRUCTIONS: dict[str, str] = {
    "food":      "Ask for food",
    "play":      "Ask to play",
    "sleep":     "Tell the owner you are sleepy",
    "affection": "Ask to be petted",
    "grooming":  "Tell the owner you are grooming yourself",
    "alarm":     "Warn the owner about something outside",
    "boredom":   "Tell the owner you are bored",
    "comfort":   "Tell the owner you are scared",
    "zoomies":   "Ask to play",
    "hunt":      "Warn the owner about a bird you spotted",
    "happy":     "Tell the owner you love them",
}


def _generate_llm(instruction: str, context: str) -> str:
    import torch
    prompt = f"### Instruction: {instruction}\n### Context: {context}\n### Response:"
    inputs = _tokenizer(prompt, return_tensors="pt").to(_model.device)  # type: ignore[union-attr]

    with torch.no_grad():
        output = _model.generate(  # type: ignore[union-attr]
            **inputs,
            max_new_tokens=40,
            do_sample=True,
            temperature=0.85,
            top_p=0.9,
            repetition_penalty=1.2,
            pad_token_id=_tokenizer.eos_token_id,  # type: ignore[union-attr]
        )

    decoded  = _tokenizer.decode(output[0], skip_special_tokens=True)  # type: ignore[union-attr]
    response = decoded.split("### Response:")[-1].strip()
    return response.split("\n")[0].strip()


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API  (same signatures as before — pet.py needs no changes)
# ══════════════════════════════════════════════════════════════════════════════

def generate_cat_message(
    instruction: str,
    context: str,
    temperature: float = 0.85,
    max_new_tokens: int = 40,
) -> str:
    """
    Generate a cat message.
    Uses the LLM if available, otherwise falls back to the synthesis engine.
    `instruction` is used by the LLM path; the synthesis path derives style from it.
    """
    if _try_load_llm():
        try:
            return _generate_llm(instruction, context)
        except Exception as exc:
            log.warning("cat_model: LLM inference failed (%s) — falling back to synthesis", exc)

    # Map instruction back to a style key for synthesis
    reverse = {v: k for k, v in _STYLE_INSTRUCTIONS.items()}
    style = reverse.get(instruction, "affection")
    return _synthesize(style)


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
    return random.choice(["affection", "play", "boredom", "food", "sleep"])


def build_check_in_message(
    pet_name: str,
    happiness: int,
    hunger: int,
    toy_style: str,
    owner_context: str = "I haven't heard from you in a while",
) -> str:
    """
    Build a formatted check-in message for a pet.
    Automatically uses the best available generation method.
    """
    style       = pick_style(happiness, hunger, toy_style)
    instruction = _STYLE_INSTRUCTIONS[style]
    message     = generate_cat_message(instruction, owner_context)
    return f"**{pet_name}:** {message}"
