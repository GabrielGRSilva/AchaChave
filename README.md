# 🔑 AchaChave

**Extrator de Chave de Acesso de DANFE** — Aplicação desktop que extrai automaticamente as Chaves de Acesso (44 dígitos) de documentos fiscais eletrônicos brasileiros (NF-e, NFC-e, CT-e, MDF-e e outros) a partir de PDFs e imagens.

![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Plataforma-Windows-0078D4?logo=windows)
![License](https://img.shields.io/badge/Licença-Proprietária-gray)

---

## ✨ Funcionalidades

- **Extração inteligente** de Chaves de Acesso com pipeline de 4 camadas
- **Leitura de PDFs** com texto embutido ou escaneados (via OCR)
- **Leitura de imagens** (PNG, JPG, JPEG, BMP, TIFF)
- **Decodificação de código de barras** (CODE-128C) via `zxing-cpp`
- **Validação com dígito verificador** (Módulo 11 — padrão SEFAZ)
- **Reparo automático de OCR** — corrige confusões comuns como `O↔0`, `I↔1`, `S↔5`
- **Processamento em lote** com indicador de progresso por arquivo
- **Exportação** para TXT e cópia para área de transferência

## 📦 Instalação

### Pelo Instalador (recomendado)
Execute `AchaChave_Instalador.exe` — o Tesseract OCR será instalado automaticamente.

### Manual (desenvolvimento)
```bash
pip install -r requirements.txt
python achachave.py
```

### Dependências
| Pacote | Versão | Uso |
|--------|--------|-----|
| `pypdf` | ≥ 4.0.0 | Extração de texto de PDFs |
| `pytesseract` | ≥ 0.3.10 | Interface com Tesseract OCR |
| `Pillow` | ≥ 10.0.0 | Processamento de imagens |
| `zxing-cpp` | ≥ 2.2.0 | Decodificação de códigos de barras |

> **Nota:** O [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) deve estar instalado no sistema para leitura de imagens e PDFs escaneados.

## 🏗️ Build

```powershell
# Gera AchaChave.exe (arquivo único) na pasta dist/
.\build.ps1
```

## 🗂️ Estrutura do Projeto

```
AchaChave/
├── achachave.py        # Interface gráfica e ponto de entrada
├── chave_parser.py     # Pipeline de extração de Chave de Acesso (4 camadas)
├── validators.py       # Validação mod-11, códigos UF/modelo, reparo OCR
├── ocr_utils.py        # Pipeline de OCR e pré-processamento de imagem
├── requirements.txt    # Dependências Python
├── build.ps1           # Script de build (PyInstaller --onefile)
├── installer.iss       # Script do instalador (Inno Setup 6)
└── .gitignore
```

---

## 📋 Patch Notes

### v1.2 — 19/08/2026

#### 🔧 Correções de Extração (Parser)

- **Corrigido:** Chaves formatadas com pontos (`3526.0308.9431...`) agora são extraídas corretamente
- **Corrigido:** Chaves na mesma linha do rótulo (`CHAVE DE ACESSO 3526 0308...`) não eram detectadas
- **Corrigido:** Falsos positivos — sequências de 44 dígitos que não eram chaves válidas (telefones, CNPJs concatenados) eram aceitas indevidamente
- **Corrigido:** Caracteres trocados pelo OCR (`O` por `0`, `I` por `1`, `S` por `5`, etc.) causavam falha total na extração
- **Corrigido:** PDFs escaneados sem imagens extraíveis não acionavam o OCR
- **Corrigido:** Chaves separadas por hifens, pipes ou dois-pontos não eram reconhecidas
- **Corrigido:** Chaves quebradas em múltiplas linhas (comum em NFC-e) não eram reconstruídas

#### 🚀 Novas Funcionalidades

- **Pipeline de 4 camadas** para extração — da mais confiável à mais genérica:
  1. Busca por proximidade de âncora textual (`"CHAVE DE ACESSO"`)
  2. Padrão canônico de 11 blocos de 4 dígitos
  3. Varredura linha a linha com janela deslizante
  4. Reparo fuzzy de OCR com revalidação
- **Validação Módulo 11** — dígito verificador oficial da SEFAZ, eliminando falsos positivos
- **Decodificação de código de barras** (CODE-128C) via `zxing-cpp` — extração de altíssima confiabilidade
- **Reparo automático de OCR** — mapeamento de 20 caracteres comumente confundidos pelo Tesseract
- **Suporte expandido** a modelos fiscais: NF-e (55), NFC-e (65), CT-e (57), MDF-e (58), CF-e-SAT (59), CF-e-ECF (60), NFCom (62), BP-e (63), NF3e (66), CT-e OS (67)
- **UF 91** (Ambiente Nacional) adicionada à validação
- **Novos formatos de imagem**: BMP e TIFF/TIF agora são aceitos
- **Botão "Limpar"** para resetar a área de resultados
- **Indicador de progresso** por arquivo (`Processando 3/10: arquivo.pdf`)
- **Status por arquivo** com indicadores visuais (`✓` sucesso / `✗` falha com motivo)
- **Scrollbar** na área de resultados

#### 🏗️ Arquitetura

- Projeto refatorado de arquivo único (264 linhas) para **arquitetura modular** (4 módulos, 695 linhas)
- Comunicação entre threads via `queue.Queue` (thread-safe) em vez de mutação direta de lista
- Logging via módulo `logging` em vez de `print()` (que era silenciado em modo `--windowed`)
- Regex pré-compiladas no nível de módulo para melhor desempenho
- Build alterado de `--onedir` para `--onefile` — gera um único executável

#### 🔒 Segurança

- **pyzbar removido** — continha CVE-2023-40889 (heap buffer overflow, CVSS 9.8) via dependência ZBar, substituído por `zxing-cpp` (mantido ativamente, sem CVEs conhecidos)
- **Proteção contra decompression bomb** — limite de pixels configurado para imagens (`Image.MAX_IMAGE_PIXELS`)
- **Caminhos absolutos removidos** do script de build (expunham nome de usuário do sistema)
- **Código-fonte não é mais embutido** na distribuição (removido `--add-data` desnecessário)
- **`except:` genérico eliminado** — todas as exceções agora são tipadas (`except Exception`)
- **`.gitignore` abrangente** — exclui DANFEs de exemplo (dados fiscais reais / LGPD), binários (135MB+), artefatos de build, e ferramentas do instalador
- **`requirements.txt` corrigido** — continha anotações pessoais de outro projeto em vez de dependências Python

---

### v1.0.1

- Versão inicial com extração básica de Chave de Acesso
- Suporte a PDF (texto direto + OCR em imagens embutidas)
- Suporte a imagens (PNG, JPG, JPEG)
- Cópia para área de transferência e exportação TXT

---

## 👤 Autor

**Gabriel G. R. Silva**
