import base64
import urllib.parse
import codecs
import re
import string
import binascii

MORSE_CODE = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.',
    'F': '..-.', 'G': '--.', 'H': '....', 'I': '..', 'J': '.---',
    'K': '-.-', 'L': '.-..', 'M': '--', 'N': '-.', 'O': '---',
    'P': '.--.', 'Q': '--.-', 'R': '.-.', 'S': '...', 'T': '-',
    'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-', 'Y': '-.--',
    'Z': '--..',
    '0': '-----', '1': '.----', '2': '..---', '3': '...--', '4': '....-',
    '5': '.....', '6': '-....', '7': '--...', '8': '---..', '9': '----.',
    ' ': '/', '.': '.-.-.-', ',': '--..--', '?': '..--..', "'": '.----.',
    '!': '-.-.--', '/': '-..-.', '(': '-.--.', ')': '-.--.-', '&': '.-...',
    ':': '---...', ';': '-.-.-.', '=': '-...-', '+': '.-.-.', '-': '-....-',
    '_': '..--.-', '"': '.-..-.', '$': '...-..-', '@': '.--.-.'
}
MORSE_CODE_REVERSE = {v: k for k, v in MORSE_CODE.items()}

NATO_PHONETIC = {
    'A': 'Alfa', 'B': 'Bravo', 'C': 'Charlie', 'D': 'Delta', 'E': 'Echo',
    'F': 'Foxtrot', 'G': 'Golf', 'H': 'Hotel', 'I': 'India', 'J': 'Juliett',
    'K': 'Kilo', 'L': 'Lima', 'M': 'Mike', 'N': 'November', 'O': 'Oscar',
    'P': 'Papa', 'Q': 'Quebec', 'R': 'Romeo', 'S': 'Sierra', 'T': 'Tango',
    'U': 'Uniform', 'V': 'Victor', 'W': 'Whiskey', 'X': 'Xray', 'Y': 'Yankee',
    'Z': 'Zulu',
    '0': 'Zero', '1': 'One', '2': 'Two', '3': 'Three', '4': 'Four',
    '5': 'Five', '6': 'Six', '7': 'Seven', '8': 'Eight', '9': 'Nine',
    ' ': '/'
}
NATO_PHONETIC_REVERSE = {v.upper(): k for k, v in NATO_PHONETIC.items()}


async def encode_text(text: str, fmt: str = 'binary', encoding: str = 'utf-8') -> str:
    """
    Encode text into various cypher/encoding formats.

    Args:
        text (str): The text to encode.
        fmt (str): The output format. One of:
            'binary', 'hex', 'base64', 'base32', 'morse', 'rot13',
            'url', 'reverse'.
        encoding (str): Byte encoding used before conversion
            (default 'utf-8'). Only relevant for binary/hex/base64/base32.
    """
    raw = text.encode(encoding)

    if fmt == 'binary':
        return ' '.join(format(byte, '08b') for byte in raw)

    elif fmt == 'hex':
        return raw.hex()

    elif fmt == 'base64':
        return base64.b64encode(raw).decode('ascii')

    elif fmt == 'base32':
        return base64.b32encode(raw).decode('ascii')

    elif fmt == 'morse':
        return ' '.join(MORSE_CODE.get(char.upper(), '?') for char in text)

    elif fmt == 'nato':
        return ' '.join(NATO_PHONETIC.get(char.upper(), '?') for char in text)

    elif fmt == 'rot13':
        return codecs.encode(text, 'rot_13')

    elif fmt == 'url':
        return urllib.parse.quote(text)

    elif fmt == 'reverse':
        return text[::-1]

    else:
        raise ValueError(
            f"Unknown format '{fmt}'. Choose from: binary, hex, base64, "
            "base32, morse, nato, rot13, url, reverse"
        )


# Formats ordered from most rigid/distinctive charset to least — checked
# in this order so we commit to the first format whose charset actually
# matches, rather than guessing blind.
_ALL_FORMATS = ['binary', 'morse', 'nato', 'hex', 'url', 'base32', 'base64', 'rot13', 'reverse']


def _looks_like(data: str, fmt: str) -> bool:
    """Cheap structural check: does `data`'s charset match what `fmt` would produce?"""
    stripped = data.strip()
    compact = re.sub(r'\s+', '', stripped)

    if fmt == 'binary':
        return bool(compact) and set(compact) <= set('01') and len(compact) % 8 == 0

    elif fmt == 'morse':
        return bool(compact) and set(stripped) <= set('.-/ \n\t')

    elif fmt == 'nato':
        words = [w for w in stripped.split(' ') if w]
        return bool(words) and all(w.upper() in NATO_PHONETIC_REVERSE or w == '/' for w in words)

    elif fmt == 'hex':
        return bool(compact) and len(compact) % 2 == 0 and all(c in string.hexdigits for c in compact)

    elif fmt == 'url':
        return '%' in stripped and bool(re.search(r'%[0-9A-Fa-f]{2}', stripped))

    elif fmt == 'base32':
        return bool(compact) and set(compact.upper()) <= set(string.ascii_uppercase + '234567=')

    elif fmt == 'base64':
        return bool(compact) and set(compact) <= set(string.ascii_letters + string.digits + '+/=')

    # rot13 and reverse have no distinctive charset — always "match" structurally,
    # they're tried last as best-effort fallbacks
    return True


async def auto_decode(data: str, encoding: str = 'utf-8') -> tuple[str, str]:
    """
    Try to detect the format `data` is encoded in and decode it.

    Checks formats in order from most structurally distinctive (binary, morse,
    hex, url, base32, base64) to least (rot13, reverse — which have no
    telltale charset and are only tried once nothing else fits).

    Returns:
        (format_used, decoded_text) — raises ValueError if nothing works.
    """
    for fmt in _ALL_FORMATS:
        if not _looks_like(data, fmt):
            continue
        try:
            result = await decode_text(data, fmt, encoding)
        except (ValueError, binascii.Error, UnicodeDecodeError):
            continue

        # rot13/reverse always "decode" successfully even on garbage input,
        # so only accept them if the output is clean printable text
        if fmt in ('rot13', 'reverse') and not all(
            ch in string.printable for ch in result
        ):
            continue

        return fmt, result

    raise ValueError("Couldn't detect the encoding format — try specifying it manually.")


async def decode_text(data: str, fmt: str = 'binary', encoding: str = 'utf-8') -> str:
    """
    Reverse encode_text — decode a cyphered string back to plain text.

    Args:
        data (str): The encoded string to decode.
        fmt (str): The format `data` is currently in (same options as encode_text).
        encoding (str): Byte encoding to decode back into (default 'utf-8').
    """
    if fmt == 'binary':
        raw = bytes(int(chunk, 2) for chunk in data.split())
        return raw.decode(encoding)

    elif fmt == 'hex':
        return bytes.fromhex(data).decode(encoding)

    elif fmt == 'base64':
        return base64.b64decode(data).decode(encoding)

    elif fmt == 'base32':
        return base64.b32decode(data).decode(encoding)

    elif fmt == 'morse':
        return ''.join(MORSE_CODE_REVERSE.get(chunk, '?') for chunk in data.split(' '))

    elif fmt == 'nato':
        return ''.join(NATO_PHONETIC_REVERSE.get(word.upper(), '?') for word in data.split(' '))

    elif fmt == 'rot13':
        return codecs.decode(data, 'rot_13')

    elif fmt == 'url':
        return urllib.parse.unquote(data)

    elif fmt == 'reverse':
        return data[::-1]

    else:
        raise ValueError(
            f"Unknown format '{fmt}'. Choose from: binary, hex, base64, "
            "base32, morse, nato, rot13, url, reverse"
        )
