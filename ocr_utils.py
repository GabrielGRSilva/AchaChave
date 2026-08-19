"""
Módulo de utilitários de OCR para AchaChave v1.2.

Este módulo lida com a inicialização do Tesseract OCR,
o pré-processamento de imagens para otimizar os resultados e
a execução do OCR.
"""

import os
import logging
from PIL import Image, ImageEnhance

logger = logging.getLogger(__name__)

try:
    import pytesseract
    _PYTESSERACT_AVAILABLE = True
except ImportError:
    logger.warning("pytesseract não está instalado. Funcionalidades de OCR não estarão disponíveis.")
    _PYTESSERACT_AVAILABLE = False
    pytesseract = None

# Proteção contra ataques de descompressão (Decompression Bomb)
Image.MAX_IMAGE_PIXELS = 178956970

_TESSERACT_SEARCH_PATHS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Tesseract-OCR', 'tesseract.exe'),
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
]

_tesseract_available = None

def find_tesseract() -> str | None:
    """
    Procura o executável do Tesseract nos caminhos padrão.
    Se não encontrar, tenta verificar se está disponível no PATH.
    """
    if not _PYTESSERACT_AVAILABLE:
        return None

    # Verifica os caminhos predefinidos
    for path in _TESSERACT_SEARCH_PATHS:
        if os.path.exists(path):
            return path
    
    # Fallback para verificar se já está no PATH
    try:
        pytesseract.get_tesseract_version()
        return 'tesseract'
    except Exception:
        return None

def init_tesseract() -> bool:
    """
    Inicializa o Tesseract OCR, configurando o caminho do executável se necessário.
    Armazena o resultado no cache _tesseract_available.
    """
    global _tesseract_available
    
    if not _PYTESSERACT_AVAILABLE:
        _tesseract_available = False
        return False

    tess_path = find_tesseract()
    if tess_path:
        if tess_path != 'tesseract':
            pytesseract.pytesseract.tesseract_cmd = tess_path
        logger.info(f"Tesseract OCR encontrado e inicializado via: {tess_path}")
        _tesseract_available = True
        return True
    else:
        logger.error("Executável do Tesseract não foi encontrado. Instale o Tesseract-OCR.")
        _tesseract_available = False
        return False

def is_tesseract_available() -> bool:
    """
    Retorna a disponibilidade do Tesseract OCR usando cache.
    Se ainda não foi verificado, chama init_tesseract().
    """
    global _tesseract_available
    if _tesseract_available is None:
        init_tesseract()
    return _tesseract_available

def preprocess_image(img: Image.Image) -> Image.Image:
    """
    Realiza o pré-processamento de uma imagem para melhorar a precisão do OCR.
    Inclui conversão para tons de cinza, redimensionamento se a imagem for muito pequena,
    aumento de contraste e binarização.
    """
    processed = img.convert('L')
    
    min_dim = min(processed.width, processed.height)
    if min_dim < 1000:
        scale_factor = max(2, 1000 // min_dim)
        new_size = (processed.width * scale_factor, processed.height * scale_factor)
        processed = processed.resize(new_size, Image.Resampling.LANCZOS)
        
    enhancer = ImageEnhance.Contrast(processed)
    processed = enhancer.enhance(2.0)
    
    processed = processed.point(lambda p: 255 if p > 128 else 0)
    
    if processed.mode != 'L':
        processed = processed.convert('L')
        
    return processed

def run_ocr(img: Image.Image, digits_only: bool = False) -> str | None:
    """
    Executa o OCR em uma imagem, após aplicar pré-processamento.
    Permite restringir a saída apenas para dígitos.
    """
    if not is_tesseract_available():
        logger.warning("Tesseract OCR não está disponível. Não é possível rodar o OCR.")
        return None

    try:
        processed_img = preprocess_image(img)
        
        config = '--psm 6'
        if digits_only:
            config += ' -c tessedit_char_whitelist=0123456789'
            
        text = pytesseract.image_to_string(processed_img, config=config)
        
        if text and text.strip():
            return text.strip()
        return None
    except Exception as e:
        logger.error(f"Erro ao executar OCR na imagem: {e}")
        return None

def run_ocr_general(img: Image.Image) -> str | None:
    """
    Executa o OCR em uma imagem (modo geral, sem restrição de caracteres).
    """
    return run_ocr(img, digits_only=False)

def run_ocr_digits(img: Image.Image) -> str | None:
    """
    Executa o OCR em uma imagem (modo apenas dígitos).
    """
    return run_ocr(img, digits_only=True)
