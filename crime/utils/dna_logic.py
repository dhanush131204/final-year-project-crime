def encode_to_dna(text):
    """
    Simulated DNA encoding.
    In a real forensic system, this would map bits to base pairs (A, T, C, G).
    """
    dna_map = {'00': 'A', '01': 'C', '10': 'G', '11': 'T'}
    binary = ''.join(format(ord(c), '08b') for c in text)
    dna = ''
    for i in range(0, len(binary), 2):
        dna += dna_map[binary[i:i+2]]
    return dna

def decode_from_dna(dna):
    """
    Simulated DNA decoding.
    """
    dna_map = {'A': '00', 'C': '01', 'G': '10', 'T': '11'}
    binary = ''.join(dna_map[base] for base in dna)
    chars = []
    for i in range(0, len(binary), 8):
        byte = binary[i:i+8]
        if len(byte) == 8:
            chars.append(chr(int(byte, 2)))
    return ''.join(chars)
