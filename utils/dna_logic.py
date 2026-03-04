# DNA Cryptography mapping for ASCII characters to DNA bases
# Simple reversible scheme for demonstration: 2-bit to base mapping
# 00->A, 01->T, 10->C, 11->G
# Each byte -> 4 bases

BIT_TO_BASE = {
    "00": "A",
    "01": "T",
    "10": "C",
    "11": "G",
}
BASE_TO_BIT = {v: k for k, v in BIT_TO_BASE.items()}


def encode_to_dna(text: str) -> str:
    dna = []
    for ch in text.encode("utf-8"):
        bits = f"{ch:08b}"
        dna.extend(BIT_TO_BASE[bits[i : i + 2]] for i in range(0, 8, 2))
    return "".join(dna)


def decode_from_dna(dna: str) -> str:
    # Validate length multiple of 4
    if len(dna) % 4 != 0:
        raise ValueError("Invalid DNA length for decoding")
    out = bytearray()
    for i in range(0, len(dna), 4):
        quartet = dna[i : i + 4]
        bits = "".join(BASE_TO_BIT.get(base, "00") for base in quartet)
        out.append(int(bits, 2))
    return out.decode("utf-8", errors="ignore")
