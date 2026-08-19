import re
import os
import io
import logging
from PIL import Image
from pypdf import PdfReader

from validators import validate_chave_acesso, repair_ocr_text, UF_CODES
from ocr_utils import is_tesseract_available, run_ocr_general

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
RE_CANONICAL = re.compile(r'(\d{4}[\s.\-]*){10}\d{4}')
RE_ANCHOR = re.compile(r'CHAVE\s+DE\s+ACESSO', re.IGNORECASE)
RE_NON_DIGIT = re.compile(r'\D')
RE_SEPARATORS = re.compile(r'[.\-()/ |:;,]')
RE_NON_ALPHANUM = re.compile(r'[^a-zA-Z0-9]')

def _decode_barcode(img: Image.Image) -> str | None:
    """
    Decodifica código de barras da imagem e valida como chave de acesso.
    
    Args:
        img: Objeto PIL Image.
        
    Returns:
        A chave de acesso como string ou None se não encontrada.
    """
    try:
        import zxingcpp
    except ImportError:
        return None

    try:
        results = zxingcpp.read_barcodes(img)
        for result in results:
            digits = RE_NON_DIGIT.sub('', result.text)
            if len(digits) == 44 and validate_chave_acesso(digits):
                return digits
    except Exception as e:
        logger.debug(f"Erro ao decodificar código de barras: {e}")
    
    return None

def _try_barcode_from_image(img: Image.Image) -> str | None:
    """
    Tenta extrair código de barras de uma imagem.
    
    Args:
        img: Objeto PIL Image.
        
    Returns:
        A chave de acesso ou None.
    """
    return _decode_barcode(img)

def _try_barcode_from_pdf(reader: PdfReader) -> str | None:
    """
    Itera pelas páginas e imagens do PDF tentando ler código de barras.
    
    Args:
        reader: Objeto PdfReader.
        
    Returns:
        A chave de acesso ou None.
    """
    try:
        for page in reader.pages:
            for image_file_object in page.images:
                try:
                    img = Image.open(io.BytesIO(image_file_object.data))
                    chave = _decode_barcode(img)
                    if chave:
                        return chave
                except Exception as e:
                    logger.debug(f"Erro ao processar imagem para código de barras no PDF: {e}")
    except Exception as e:
        logger.debug(f"Erro ao iterar imagens do PDF: {e}")
        
    return None

def find_chave_in_text(text: str) -> str | None:
    """
    Procura uma chave de acesso em um texto usando um pipeline de 4 camadas.
    
    Args:
        text: O texto extraído para ser analisado.
        
    Returns:
        A chave de acesso de 44 dígitos se encontrada, caso contrário None.
    """
    if not text:
        return None

    # Layer 1 - Anchor proximity
    anchor_match = RE_ANCHOR.search(text)
    if anchor_match:
        proximity_text = text[anchor_match.end():anchor_match.end() + 300]
        digits_only = RE_NON_DIGIT.sub('', proximity_text)
        if len(digits_only) >= 44:
            possible_chave = digits_only[:44]
            if validate_chave_acesso(possible_chave):
                return possible_chave

    # Layer 2 - Canonical 4-digit groups
    canonical_matches = RE_CANONICAL.finditer(text)
    for match in canonical_matches:
        digits_only = RE_NON_DIGIT.sub('', match.group())
        if len(digits_only) == 44 and validate_chave_acesso(digits_only):
            return digits_only

    # Layer 3 - Line-by-line scan
    clean_text = RE_SEPARATORS.sub('', text)
    for line in clean_text.splitlines():
        digits_only = RE_NON_DIGIT.sub('', line)
        if len(digits_only) == 44:
            if validate_chave_acesso(digits_only):
                return digits_only
        elif len(digits_only) > 44:
            for i in range(len(digits_only) - 43):
                possible_chave = digits_only[i:i+44]
                if validate_chave_acesso(possible_chave):
                    return possible_chave

    # Layer 4 - OCR fuzzy repair fallback
    repaired_text = repair_ocr_text(text)
    alphanumeric_only = RE_NON_ALPHANUM.sub('', repaired_text)
    digits_only = RE_NON_DIGIT.sub('', alphanumeric_only)
    if len(digits_only) >= 44:
        for i in range(len(digits_only) - 43):
            possible_chave = digits_only[i:i+44]
            if validate_chave_acesso(possible_chave):
                return possible_chave

    return None

def _extract_from_pdf(pdf_path: str) -> str | None:
    """
    Extrai chave de acesso de um arquivo PDF.
    
    Args:
        pdf_path: Caminho para o arquivo PDF.
        
    Returns:
        A chave de acesso ou None se não encontrada ou houver erro.
    """
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                chave = find_chave_in_text(text)
                if chave:
                    return chave
            
            # Se não encontrar no texto e OCR estiver disponível, tentar nas imagens da página
            if is_tesseract_available():
                for image_file_object in page.images:
                    try:
                        img = Image.open(io.BytesIO(image_file_object.data))
                        ocr_text = run_ocr_general(img)
                        chave_ocr = find_chave_in_text(ocr_text)
                        if chave_ocr:
                            return chave_ocr
                    except Exception as e:
                        logger.debug(f"Erro no OCR da imagem do PDF: {e}")
                        
        # Após todas as páginas, tenta ler código de barras
        chave_barcode = _try_barcode_from_pdf(reader)
        if chave_barcode:
            return chave_barcode
            
    except Exception as e:
        logger.error(f"Erro ao processar PDF {pdf_path}: {e}")
        
    return None

def _extract_from_image(img_path: str) -> str | None:
    """
    Extrai chave de acesso de um arquivo de imagem.
    
    Args:
        img_path: Caminho para o arquivo de imagem.
        
    Returns:
        A chave de acesso ou None se não encontrada.
    """
    if not is_tesseract_available():
        logger.warning("Tesseract não disponível para processamento de imagem.")
        
    try:
        with Image.open(img_path) as img:
            # Tentar OCR
            if is_tesseract_available():
                ocr_text = run_ocr_general(img)
                chave = find_chave_in_text(ocr_text)
                if chave:
                    return chave
                    
            # Tentar código de barras
            chave_barcode = _try_barcode_from_image(img)
            if chave_barcode:
                return chave_barcode
    except Exception as e:
        logger.error(f"Erro ao processar imagem {img_path}: {e}")
        
    return None

def extract_chave(filepath: str) -> str | None:
    """
    Tenta extrair uma chave de acesso válida do arquivo especificado.
    
    Args:
        filepath: Caminho completo para o arquivo.
        
    Returns:
        A chave de acesso como string de 44 dígitos ou None se falhar.
    """
    try:
        file_size = os.path.getsize(filepath)
        if file_size == 0 or file_size > MAX_FILE_SIZE:
            logger.error(f"Tamanho de arquivo inválido: {file_size} bytes")
            return None
    except OSError as e:
        logger.error(f"Erro ao acessar arquivo {filepath}: {e}")
        return None

    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    
    if ext == '.pdf':
        return _extract_from_pdf(filepath)
    elif ext in ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'):
        return _extract_from_image(filepath)
    else:
        logger.warning(f"Formato de arquivo não suportado: {ext}")
        return None
