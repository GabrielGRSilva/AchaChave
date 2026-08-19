"""
Módulo de validação e reparo de Chaves de Acesso de Documentos Fiscais Eletrônicos (NFe, CTe, etc).
Projeto AchaChave v1.2.
"""

from typing import Set

UF_CODES: Set[str] = {
    '11', '12', '13', '14', '15', '16', '17',  # Norte
    '21', '22', '23', '24', '25', '26', '27', '28', '29',  # Nordeste
    '31', '32', '33', '35',  # Sudeste
    '41', '42', '43',  # Sul
    '50', '51', '52', '53',  # Centro-Oeste
    '91',  # Ambiente Nacional
}

VALID_MODELS: Set[str] = {
    '55',  # NF-e
    '65',  # NFC-e
    '57',  # CT-e
    '58',  # MDF-e
    '59',  # CF-e-SAT
    '60',  # CF-e-ECF
    '62',  # NFCom
    '63',  # BP-e
    '66',  # NF3e
    '67',  # CT-e OS
}

# Mapeamento para corrigir erros comuns de OCR em dígitos
OCR_CHAR_MAP = str.maketrans(
    "OoQDIl|!ZzSsBbGgqAhT",
    "00001111225588669447"
)

def calculate_check_digit(key_43: str) -> int:
    """
    Calcula o dígito verificador de uma chave de acesso de 43 posições
    usando o algoritmo módulo 11 da SEFAZ.

    Args:
        key_43: String contendo os 43 primeiros dígitos da chave de acesso.

    Returns:
        O dígito verificador calculado (0-9).

    Raises:
        ValueError: Se a string não contiver exatamente 43 dígitos.
    """
    if not isinstance(key_43, str) or len(key_43) != 43 or not key_43.isdigit():
        raise ValueError("A chave deve conter exatamente 43 dígitos numéricos.")

    weights = [2, 3, 4, 5, 6, 7, 8, 9]
    total = 0
    for i, digit in enumerate(reversed(key_43)):
        weight = weights[i % 8]
        total += int(digit) * weight

    remainder = total % 11
    return 0 if remainder < 2 else 11 - remainder

def validate_chave_acesso(chave: str) -> bool:
    """
    Valida uma Chave de Acesso de documento fiscal.

    Verifica:
    - Comprimento exato de 44 caracteres numéricos
    - Código da UF válido
    - Modelo do documento válido
    - Dígito verificador correto (módulo 11)

    Args:
        chave: A string contendo a chave de acesso de 44 dígitos.

    Returns:
        True se a chave for válida, False caso contrário.
    """
    if not isinstance(chave, str) or len(chave) != 44 or not chave.isdigit():
        return False

    uf_code = chave[0:2]
    model = chave[20:22]

    if uf_code not in UF_CODES:
        return False

    if model not in VALID_MODELS:
        return False

    key_43 = chave[:43]
    expected_dv = int(chave[43])
    
    try:
        calculated_dv = calculate_check_digit(key_43)
    except ValueError:
        return False

    return expected_dv == calculated_dv

def repair_ocr_text(text: str) -> str:
    """
    Corrige problemas comuns de leitura OCR (caracteres trocados por outros visualmente similares).

    Aplica a substituição definida em OCR_CHAR_MAP para restaurar os dígitos originais.

    Args:
        text: Texto bruto lido pelo OCR.

    Returns:
        O texto com os caracteres corrigidos.
    """
    if not isinstance(text, str):
        return str(text)
    return text.translate(OCR_CHAR_MAP)
