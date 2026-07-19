import discord
import random
import re
from discord.ext import commands

CUSTOM_EMOJI_RE = re.compile(r'<a?:(\w+):\d+>')
UNICODE_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "\U00002B50-\U00002B55"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "]+", flags=re.UNICODE
)
MENTION_RE = re.compile(r'<@!?(\d+)>')
ROLE_MENTION_RE = re.compile(r'<@&(\d+)>')
CHANNEL_RE = re.compile(r'<#(\d+)>')


def normalize_custom_emojis(text):
    return CUSTOM_EMOJI_RE.sub(lambda m: f'[{m.group(1)}]', text)

def mention_to_name(text: str, bot: commands.Bot | None = None, interaction: discord.Interaction | None = None) -> str:
    """Replace <@id>, <#id>, <@&id> mentions in text with @name / #name."""
    guild = interaction.guild if interaction else None

    def user_name(user_id: int) -> str | None:
        if guild:
            member = guild.get_member(user_id)
            if member:
                return member.display_name
        if bot:
            user = bot.get_user(user_id)
            return user.name if user else None
        return None

    def channel_name(channel_id: int) -> str | None:
        if guild:
            channel = guild.get_channel(channel_id)
            if channel:
                return channel.name
        if bot:
            channel = bot.get_channel(channel_id)
            return channel.name if channel else None
        return None

    def role_name(role_id: int) -> str | None:
        if guild:
            role = guild.get_role(role_id)
            if role:
                return role.name
        if bot:
            for g in bot.guilds:
                role = g.get_role(role_id)
                if role:
                    return role.name
        return None

    text = MENTION_RE.sub(lambda m: f'@{user_name(int(m.group(1))) or m.group(0)}', text)
    text = CHANNEL_RE.sub(lambda m: f'#{channel_name(int(m.group(1))) or m.group(0)}', text)
    text = ROLE_MENTION_RE.sub(lambda m: f'@{role_name(int(m.group(1))) or m.group(0)}', text)
    return text

async def pretty_text(interaction: discord.Interaction, bot: commands.Bot, text: str, emoji_to_text: bool = True) -> str:
    """
    use it to clean text from mention 
    to images or other stuff that need the mention to be name!
    """
    if emoji_to_text:
        text = normalize_custom_emojis(text)
    text = mention_to_name(interaction=interaction, bot=bot, text=text)
    return text

# ── UwU-ify ───────────────────────────────────────────────────────────────

_UWU_FACES = ["UwU", "OwO", ">w<", "^w^", "owo", "uwu~", ":3", "nya~"]

_UWU_WORD_SWAPS = {
    "you": "uwu", "love": "wuv", "small": "smol", "cute": "kawaii~",
    "meow": "nya~", "world": "wowld", "please": "pwease",
    "stupid": "baka", "what": "nani",
}


def uwuify(text: str, stutter_chance: float = 0.1, face_chance: float = 0.3,
           word_swaps: bool = False) -> str:
    """
    Convert text into uwu-speak using the standard documented algorithm:
      - l/L, r/R -> w/W
      - n/N or m/M followed by o/O gets a 'y' inserted (nyo/myo nasalization)
    Optional extras layered on top:
      - stutter_chance: probability (0-1) each word's first letter repeats, e.g. "p-pinky"
      - face_chance: probability (0-1) of appending a kaomoji face at the end
      - word_swaps: if True, swaps common words (you -> uwu, love -> wuv, etc.)
    """
    if word_swaps:
        def swap(match):
            word = match.group(0)
            lower = word.lower()
            if lower in _UWU_WORD_SWAPS:
                replacement = _UWU_WORD_SWAPS[lower]
                return replacement.capitalize() if word[0].isupper() else replacement
            return word
        text = re.sub(r"\b\w+\b", swap, text)

    output = []
    for i, char in enumerate(text):
        prev_char = text[i - 1] if i > 0 else ""

        if char in "lLrR":
            output.append("W" if char.isupper() else "w")
        elif char in "oO" and prev_char in "nNmM":
            output.append(("Y" if char.isupper() else "y") + char)
        else:
            output.append(char)

    result = "".join(output)

    if stutter_chance > 0:
        def maybe_stutter(word):
            if word and word[0].isalpha() and random.random() < stutter_chance:
                return f"{word[0]}-{word}"
            return word
        result = " ".join(maybe_stutter(w) for w in result.split(" "))

    if face_chance > 0 and random.random() < face_chance:
        result = f"{result} {random.choice(_UWU_FACES)}"

    return result


# ── Count / Find / Replace ───────────────────────────────────────────────

def text_count(text: str, target: str | None = None, case_sensitive: bool = False) -> dict:
    """
    Count stats about `text`. If `target` is given, also counts occurrences
    of that substring/word.
    """
    stats = {
        "characters": len(text),
        "characters_no_spaces": len(text.replace(" ", "")),
        "words": len(text.split()),
        "lines": len(text.splitlines()) or 1,
    }
    if target:
        haystack = text if case_sensitive else text.lower()
        needle = target if case_sensitive else target.lower()
        stats["target"] = target
        stats["target_occurrences"] = haystack.count(needle)
    return stats


def text_find(text: str, target: str, case_sensitive: bool = False) -> list[int]:
    """Return a list of every starting index where `target` occurs in `text`."""
    haystack = text if case_sensitive else text.lower()
    needle = target if case_sensitive else target.lower()

    if not needle:
        return []

    positions = []
    start = 0
    while True:
        idx = haystack.find(needle, start)
        if idx == -1:
            break
        positions.append(idx)
        start = idx + 1
    return positions


def text_replace(text: str, target: str, replacement: str,
                  case_sensitive: bool = False, limit: int = -1) -> str:
    """
    Replace occurrences of `target` with `replacement` in `text`.
    `limit` caps the number of replacements (-1 = replace all).
    """
    if not target:
        return text

    if case_sensitive:
        return text.replace(target, replacement, limit)

    pattern = re.compile(re.escape(target), re.IGNORECASE)
    count = 0 if limit == -1 else limit
    return pattern.sub(replacement, text, count=count)

# ── Lorem Ipsum generator ─────────────────────────────────────────────────

_LOREM_WORDS = (
    "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua enim ad minim veniam "
    "quis nostrud exercitation ullamco laboris nisi aliquip ex ea commodo "
    "consequat duis aute irure in reprehenderit voluptate velit esse cillum "
    "eu fugiat nulla pariatur excepteur sint occaecat cupidatat non proident "
    "sunt culpa qui officia deserunt mollit anim id est laborum"
).split()


def generate_lorem(paragraphs: int = 1, sentences_per_paragraph: int = 5) -> str:
    """Generate placeholder Lorem Ipsum text."""
    paragraphs = max(1, min(paragraphs, 10))
    sentences_per_paragraph = max(1, min(sentences_per_paragraph, 20))

    result_paragraphs = []
    for _ in range(paragraphs):
        sentences = []
        for _ in range(sentences_per_paragraph):
            length = random.randint(6, 14)
            words = random.choices(_LOREM_WORDS, k=length)
            sentence = " ".join(words).capitalize() + "."
            sentences.append(sentence)
        result_paragraphs.append(" ".join(sentences))

    return "\n\n".join(result_paragraphs)


# ── Amberia generator (Lorem Ipsum, but everything's a variation of "amber") ─

_AMBER_NOUNS = [
    "Amber", "Ambertown", "Amberton", "Amberkin", "Ambercore", "Amberville",
    "Ambergate", "Amberholm", "Amberhall", "Amberfell", "Ambermoor",
    "Ambervale", "Amberwood", "Amberstone", "Amberford", "Amberbrook",
    "Amberridge", "Amberglen", "Amberhaven", "Ambershire", "Amberport",
    "Amberreach", "Ambersong", "Ambertide", "Amberwick", "Amberdell",
    "Amberfield", "Amberhold", "Amberkeep", "Amberlight", "Ambermere",
    "Ambernook", "Amberpeak", "Amberroot", "Ambershade", "Ambersky",
    "Ambersmith", "Ambertree", "Amberview", "Amberwatch", "Amberwell",
    "Amberwing", "Amberworth", "Amberyard", "Ambercross", "Amberdale",
    "Ambergrove", "Ambermarsh", "Ambercliff", "Amberbay", "Amberisle",
]
_AMBER_ADJECTIVES = [
    "ambery", "amberic", "amberous", "amberish", "amberesque", "amberian",
    "ambereal", "amberful", "amberless", "amberlike", "ambersome",
    "amberistic", "amberoid", "amberine", "amberate", "amberious",
    "amberacious", "ambertious", "amberical", "amberary", "amberent",
    "amberant", "amberal", "amberive", "amberescent", "amberular",
    "amberform", "ambergenic", "ambertastic", "ambertopian", "amber-kissed",
    "amber-touched", "amber-soaked", "amber-tinted", "amber-hued",
    "amber-streaked", "amber-flecked", "amber-veined", "amber-laced",
    "amber-washed", "amber-bathed", "amber-drenched", "amber-gilded",
    "amber-burnished", "amber-polished", "amber-glazed", "amber-stained",
    "amber-dusted", "amber-woven", "amber-threaded", "amber-bound",
]
_AMBER_VERBS = [
    "ambered", "ambering", "amberify", "amberifies", "amberified",
    "amberizes", "amberized", "amberizing", "amberesced", "amberescing",
    "amberweaves", "amberwove", "amberweaving", "ambershifts",
    "ambershifted", "ambershifting", "amberbinds", "amberbound",
    "amberbinding", "ambercasts", "ambercast", "ambercasting",
    "amberforges", "amberforged", "amberforging", "amberkindles",
    "amberkindled", "amberkindling", "ambermends", "ambermended",
    "ambermending", "amberspins", "amberspun", "amberspinning",
    "ambertwines", "ambertwined", "ambertwining", "amberglows",
    "amberglowed", "amberglowing", "amberdrifts", "amberdrifted",
    "amberdrifting", "ambersettles", "ambersettled", "ambersettling",
    "amberlingers", "amberlingered", "amberlingering", "ambersings",
]
_AMBER_ADVERBS = [
    "amberly", "amberishly", "amberously", "ambereally", "amberfully",
    "amberlessly", "amberistically", "amberatively", "amberiously",
    "amberically", "amberently", "amberantly", "amberescently",
    "ambergenically", "ambertastically", "amberaciously", "ambersomely",
    "amberoidally", "amberinely", "amberularly", "ambertopianly",
    "amberward", "amberwise", "ambermost", "amber-kissedly",
    "amber-touchedly", "quietly amber", "in an amber way", "amberishly still",
    "with amber intent", "as amber does", "amberly enough", "half-amberly",
    "amberly at last", "amberly again", "amberly once more", "amberly still",
    "in the amber sense", "amberly, if briefly", "amberly, as always",
    "amberly, without pause", "in an ambereal manner", "amberly and slow",
    "amberly, at length", "with a slight amber lilt", "amberly, more or less",
    "in more amber terms", "amberly, all the same", "amberly beyond words",
]


# ── Combinatorial sentence grammar ────────────────────────────────────────
# Independent pools of subject/predicate/clause fragments, combined at random
# rather than picking whole pre-baked sentences — this multiplies variety
# instead of just cycling through a handful of fixed shapes.

_SUBJECT_PATTERNS = [
    "{noun}", "the {adj} {noun}", "every {adj} {noun}", "{noun}'s {noun2}",
    "the {noun} of {noun2}", "a lone {adj} {noun}", "the great {noun}",
    "a {adj} {noun} from {noun2}", "the last {adj} {noun}",
    "{noun} and {noun2}", "the {noun2} beneath {noun}",
]

_PREDICATE_PATTERNS = [
    "{verb} {adverb}", "{verb} through {noun2}", "{verb} beyond the {adj} {noun2}",
    "{verb} beneath {noun2}", "{verb} {adverb}, unlike {noun2}",
    "{verb} toward {noun2}", "quietly {verb}", "{verb} against the {adj} {noun2}",
    "{verb} where {noun2} once stood", "{verb} without {noun2}",
]

_CLAUSE_PATTERNS = [
    "though {noun2} {verb} {adverb}", "as {noun2} watched",
    "while the {adj} {noun2} waited", "since the days of {noun2}",
    "or so the {adj} ones say", "long after {noun2} {verb}",
    "even as {noun2} {verb} {adverb}", None, None,  # None = no trailing clause
]


def _amberia_words() -> dict:
    """One fresh random pick per word-category, reused across a sentence's fragments."""
    return {
        "noun": random.choice(_AMBER_NOUNS),
        "noun2": random.choice(_AMBER_NOUNS),
        "adj": random.choice(_AMBER_ADJECTIVES),
        "verb": random.choice(_AMBER_VERBS),
        "adverb": random.choice(_AMBER_ADVERBS),
    }


def _generate_amberia_sentence() -> str:
    subject = random.choice(_SUBJECT_PATTERNS).format(**_amberia_words())
    predicate = random.choice(_PREDICATE_PATTERNS).format(**_amberia_words())
    clause_template = random.choice(_CLAUSE_PATTERNS)

    sentence = f"{subject} {predicate}"
    if clause_template:
        sentence += ", " + clause_template.format(**_amberia_words())

    return sentence[0].upper() + sentence[1:] + "."


def generate_amberia(sentences: int = 5) -> str:
    """Generate grammatical-sounding placeholder text where every word
    is some variation of 'amber' — a themed Lorem Ipsum. Sentences are
    built from independently-randomized subject/predicate/clause fragments
    rather than a fixed set of full templates, so the structure varies
    each time instead of visibly repeating."""
    sentences = max(1, min(sentences, 20))
    return " ".join(_generate_amberia_sentence() for _ in range(sentences))


# ── Old-TV-style ad generator ────────────────────────────────────────────

_AD_PROBLEMS = [
    "tangled cables", "boring lunches", "slow wifi", "messy desks",
    "cold coffee", "losing your keys", "bad haircuts", "squeaky doors",
    "wrinkled shirts", "lost TV remotes", "sticky drawers", "burnt toast",
    "flat soda", "foggy mirrors", "static socks", "cluttered garages",
    "stubborn stains", "greasy pans", "dull knives", "clogged sinks",
    "frizzy hair", "flabby arms", "cluttered closets", "soggy leftovers",
    "unpeeled potatoes", "cracked phone screens", "leaky pipes",
    "itchy scalp", "wobbly furniture", "dying houseplants",
    "foggy car windows", "burnt popcorn", "dusty blinds",
    "heavy grocery bags", "slow blenders", "dead batteries",
    "cold showers", "noisy neighbors", "lost socks in the dryer",
    "overgrown lawns", "flat tires", "broken zippers", "callused feet",
    "tangled headphones", "peeling wallpaper", "rusty tools",
    "spilled glitter", "expired coupons", "creaky floorboards",
]
_AD_PRODUCTS = [
    "Sock Vacuum 3000", "Mega Blender X", "The Cable Untangler",
    "SnackMaster Pro", "The WiFi Booster Deluxe", "KeyFinder 9000",
    "The Toast-Saver 2000", "QuickPress Shirt Wand", "The Drawer Genie",
    "SodaFizz Sealer", "The Remote Rescuer", "MirrorClear Max",
    "The Absorb-All Towel", "The Snug Wrap", "The Stain Vanisher",
    "The Patch-It Sealant Tape", "The Chop-It-All Bullet",
    "The Multi-Rod Fishing Wonder", "The Veg-Slicer 5000",
    "The Wonder Blade Knife Set", "The Thigh Toner Max",
    "The Shake-N-Tone Bar", "The Sprout Buddy", "The Clap Switch",
    "The Peeling Gloves", "The Home Haircut Wand", "The Forehead Fixer Stick",
    "The Callus Zapper", "The Ab Firmer 3000", "The Home Gym Flex Bar",
    "The Rotisserie Wonder Oven", "The Grease-Away Pan Scraper",
    "The Pipe Patch Kit", "The Leaf-Free Gutter Guard",
    "The Instant Plant Reviver", "The Zipper Fixer Pro",
    "The Glitter-Be-Gone Roller", "The Coupon Organizer Wallet",
]

_AD_OPENERS = [
    "Tired of {problem}? SAY NO MORE!",
    "Sick of {problem}? We've got you covered!",
    "Are you STILL dealing with {problem}?!",
    "Struggling with {problem} every single day? Not anymore!",
    "{problem}? There's finally a fix!",
]
_AD_INTROS = [
    "Introducing the ALL-NEW **{product}**!",
    "Say hello to **{product}** — the future is here!",
    "Meet **{product}**, the last thing you'll ever need!",
    "Presenting **{product}**, as seen on TV!",
]
_AD_BENEFITS = [
    "It's fast", "It's affordable", "It practically works itself",
    "Your neighbors will be jealous", "Guaranteed results in minutes",
    "As seen on late-night TV", "No tools required", "Works while you sleep",
    "Kids and adults love it", "One size fits all", "Batteries included",
    "Made from 100% amberium-grade materials",
]
_AD_TESTIMONIALS = [
    '"I couldn\'t believe the results!" — a totally real customer',
    '"My life has changed forever!" — satisfied buyer',
    '"I use it every single day now." — happy customer',
    '"Why didn\'t I buy this sooner?" — thrilled user',
]
_AD_GUARANTEES = [
    "100% money-back guarantee, no questions asked!",
    "If you're not satisfied, send it back for a full refund!",
    "Tested by real people, backed by our promise!",
]
_AD_URGENCY = [
    "But wait — there's more! Call in the next 10 minutes and we'll DOUBLE your order — just pay separate processing and handling!",
    "Supplies are running out FAST — don't wait!",
    "This offer won't last! Order before midnight!",
    "The first 100 callers get a free bonus gift!",
]
_AD_PRICES = ["$19.99", "$29.95", "$9.99", "4 easy payments of $9.99"]


def generate_ad(subject: str | None = None) -> str:
    """Generate a random or given-subject ad in old TV infomercial style.
    Built from independent sections (opener, intro, benefits, optional
    testimonial/guarantee, urgency, closer) so the shape varies between
    calls instead of always following one fixed skeleton."""
    problem = random.choice(_AD_PROBLEMS)
    product = subject if subject else random.choice(_AD_PRODUCTS)
    phone_suffix = random.randint(100, 999)

    opener = random.choice(_AD_OPENERS).format(problem=problem)
    if opener and opener[0].islower():
        opener = opener[0].upper() + opener[1:]

    sections = [
        opener,
        random.choice(_AD_INTROS).format(product=product),
    ]

    benefit_count = random.randint(2, 4)
    benefits = random.sample(_AD_BENEFITS, benefit_count)
    sections.append("! ".join(benefits) + "!")

    if random.random() < 0.5:
        sections.append(random.choice(_AD_TESTIMONIALS))

    if random.random() < 0.4:
        sections.append(f"Only {random.choice(_AD_PRICES)}!")

    if random.random() < 0.4:
        sections.append(random.choice(_AD_GUARANTEES))

    sections.append(random.choice(_AD_URGENCY))
    sections.append(
        f"Call now: 1-800-{phone_suffix}-AMBR\n"
        f"Operators are standing by! **{product}** is not sold in stores!"
    )

    return "\n\n".join(sections)
