"""
AchaChave v1.2 — Extrator de Chave de Acesso de DANFE
Aplicação desktop para extração de Chaves de Acesso de documentos fiscais
eletrônicos (NF-e, NFC-e, CT-e, MDF-e) a partir de PDFs e imagens.

Autor: Gabriel G. R. Silva
"""

__version__ = "1.2"

import tkinter as tk
from tkinter import filedialog, messagebox
import os
import logging
import queue
import threading

from chave_parser import extract_chave
from ocr_utils import is_tesseract_available, init_tesseract

# ---------------------------------------------------------------------------
# Configuração de logging
# Em modo --windowed (sem console), os logs vão apenas para arquivo se
# configurado. Em desenvolvimento, são exibidos no terminal.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("AchaChave")


class AchaChaveApp:
    """Interface gráfica principal do AchaChave."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AchaChave - Extrator de DANFE")
        self.root.geometry("700x500")
        self.root.minsize(600, 400)
        self.root.configure(bg="#f0f0f0")

        # Estado interno
        self.extracted_keys: list[tuple[str, str, str]] = []  # (filename, data, status)
        self.result_queue: queue.Queue = queue.Queue()
        self._total_files = 0
        self._processed_count = 0

        # Monta a interface
        self._setup_ui()

        # Inicializa Tesseract em background
        init_tesseract()
        self.ocr_available = is_tesseract_available()
        if not self.ocr_available:
            logger.info("Tesseract OCR não encontrado — OCR indisponível.")

    # -----------------------------------------------------------------------
    # Interface gráfica
    # -----------------------------------------------------------------------
    def _setup_ui(self):
        """Constrói todos os widgets da interface."""

        # Título
        tk.Label(
            self.root,
            text="Extrator de Chave de Acesso (DANFE)",
            font=("Segoe UI", 16, "bold"),
            bg="#f0f0f0",
            fg="#333",
        ).pack(pady=10)

        # Botão de seleção de arquivos
        self.btn_select = tk.Button(
            self.root,
            text="Selecionar DANFEs (PDFs e Imagens)",
            command=self._on_select_files,
            font=("Segoe UI", 11),
            bg="#0078D7",
            fg="white",
            relief=tk.FLAT,
            padx=15,
            pady=5,
        )
        self.btn_select.pack(pady=5)

        # Área de texto com scrollbar
        frame_text = tk.Frame(self.root)
        frame_text.pack(pady=10, fill=tk.BOTH, expand=True, padx=15)

        scrollbar = tk.Scrollbar(frame_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_area = tk.Text(
            frame_text,
            height=12,
            width=75,
            font=("Consolas", 10),
            bd=1,
            relief=tk.SOLID,
            yscrollcommand=scrollbar.set,
        )
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text_area.yview)

        # Botões de ação
        frame_actions = tk.Frame(self.root, bg="#f0f0f0")
        frame_actions.pack(pady=5)

        tk.Button(
            frame_actions,
            text="Copiar Todas",
            command=self._on_copy_all,
            font=("Segoe UI", 10),
            bg="#28a745",
            fg="white",
            relief=tk.FLAT,
            padx=10,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            frame_actions,
            text="Exportar para TXT",
            command=self._on_export_txt,
            font=("Segoe UI", 10),
            bg="#6c757d",
            fg="white",
            relief=tk.FLAT,
            padx=10,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            frame_actions,
            text="Limpar",
            command=self._on_clear,
            font=("Segoe UI", 10),
            bg="#dc3545",
            fg="white",
            relief=tk.FLAT,
            padx=10,
        ).pack(side=tk.LEFT, padx=5)

        # Barra de status
        self.status_var = tk.StringVar(value="Aguardando arquivos...")
        tk.Label(
            self.root,
            textvariable=self.status_var,
            bg="#f0f0f0",
            fg="#555",
            font=("Segoe UI", 9),
        ).pack(side=tk.BOTTOM, pady=10)

        # Rodapé: versão e autor (canto inferior direito)
        tk.Label(
            self.root,
            text=f"Versão {__version__} — Criado por Gabriel G. R. Silva",
            font=("Segoe UI", 7),
            bg="#f0f0f0",
            fg="#aaa",
        ).place(relx=1.0, rely=1.0, anchor="se", x=-6, y=-6)

    # -----------------------------------------------------------------------
    # Seleção e processamento de arquivos
    # -----------------------------------------------------------------------
    def _on_select_files(self):
        """Abre diálogo de seleção e inicia processamento em background."""
        files = filedialog.askopenfilenames(
            title="Selecione as DANFEs",
            filetypes=[
                ("Arquivos Suportados", "*.pdf *.png *.jpg *.jpeg *.bmp *.tiff *.tif"),
                ("PDFs", "*.pdf"),
                ("Imagens", "*.png *.jpg *.jpeg *.bmp *.tiff *.tif"),
            ],
        )
        if not files:
            return

        # Prepara a interface
        self.btn_select.config(state=tk.DISABLED)
        self.text_area.delete(1.0, tk.END)
        self.extracted_keys.clear()
        self._total_files = len(files)
        self._processed_count = 0
        self.status_var.set("Iniciando processamento...")

        # Aviso de OCR ausente
        if not self.ocr_available:
            messagebox.showwarning(
                "OCR Indisponível",
                "O Tesseract OCR não foi encontrado.\n"
                "Arquivos de imagem e PDFs escaneados não poderão ser lidos.\n"
                "Para suporte completo, instale o Tesseract OCR.",
            )

        # Inicia worker thread
        threading.Thread(
            target=self._worker_process_files,
            args=(files,),
            daemon=True,
        ).start()

        # Inicia polling da fila de resultados na thread principal
        self.root.after(100, self._poll_results)

    def _worker_process_files(self, files: tuple[str, ...]):
        """
        Worker thread: processa cada arquivo e envia resultados para a UI
        via Queue (thread-safe).
        """
        for filepath in files:
            filename = os.path.basename(filepath)
            try:
                key = extract_chave(filepath)
                if key:
                    self.result_queue.put(("success", filename, key))
                else:
                    self.result_queue.put(("fail", filename, "Chave não encontrada"))
            except Exception as e:
                logger.error("Erro ao processar %s: %s", filename, e)
                self.result_queue.put(("error", filename, f"Erro: {e}"))

        # Sinaliza fim do processamento
        self.result_queue.put(("done", "", ""))

    def _poll_results(self):
        """
        Consome a fila de resultados e atualiza a UI.
        Executa na thread principal do Tkinter (thread-safe).
        """
        try:
            while True:
                msg_type, filename, data = self.result_queue.get_nowait()

                if msg_type == "done":
                    total = len(self.extracted_keys)
                    successes = sum(
                        1 for _, _, status in self.extracted_keys if status == "success"
                    )
                    self.status_var.set(
                        f"Concluído: {successes}/{total} chaves extraídas com sucesso."
                    )
                    self.btn_select.config(state=tk.NORMAL)
                    return  # Para o polling

                self._processed_count += 1
                self.status_var.set(
                    f"Processando {self._processed_count}/{self._total_files}: {filename}"
                )

                if msg_type == "success":
                    self.extracted_keys.append((filename, data, "success"))
                    self.text_area.insert(tk.END, f"✓ {data}\n")
                else:
                    self.extracted_keys.append((filename, data, "fail"))
                    self.text_area.insert(tk.END, f"✗ {filename}: {data}\n")

        except queue.Empty:
            pass

        # Continua polling enquanto o worker estiver ativo
        self.root.after(100, self._poll_results)

    # -----------------------------------------------------------------------
    # Ações do usuário
    # -----------------------------------------------------------------------
    def _on_clear(self):
        """Limpa os resultados e reseta o estado."""
        self.text_area.delete(1.0, tk.END)
        self.extracted_keys.clear()
        self.status_var.set("Aguardando arquivos...")

    def _on_copy_all(self):
        """Copia todas as chaves válidas para a área de transferência."""
        keys_only = [
            data for _, data, status in self.extracted_keys if status == "success"
        ]
        if keys_only:
            text_to_copy = "\n".join(keys_only)
            self.root.clipboard_clear()
            self.root.clipboard_append(text_to_copy)
            messagebox.showinfo(
                "Sucesso", "Chaves copiadas para a área de transferência!"
            )
        else:
            messagebox.showwarning("Aviso", "Nenhuma chave válida para copiar.")

    def _on_export_txt(self):
        """Exporta as chaves válidas para um arquivo TXT."""
        keys_only = [
            data for _, data, status in self.extracted_keys if status == "success"
        ]
        if not keys_only:
            messagebox.showwarning("Aviso", "Nenhuma chave válida para exportar.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Arquivo de Texto", "*.txt")],
            title="Salvar Chaves",
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(keys_only))
            messagebox.showinfo("Sucesso", "Chaves exportadas com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar arquivo:\n{e}")


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = AchaChaveApp(root)
    root.mainloop()
