# Validador de Documentos - Exigências MEC

Aplicação em Python com interface em HTML/JS (via `pywebview`) para auditoria automatizada de documentos em PDF de acordo com o Decreto Federal nº 10.278/2020.

---

## 🛠️ Pré-requisitos no Novo PC

### 1. Instalar o Tesseract OCR (Dependência de Sistema)
Para que a extração por OCR e a validação de rotação funcionem no ambiente de desenvolvimento:
1. Baixe o instalador do Tesseract OCR para Windows (ex: `tesseract-ocr-w64-setup-....exe`).
2. Instale no caminho padrão do sistema (`C:\Program Files\Tesseract-OCR`) **OU** coloque os arquivos da pasta portátil dentro da pasta `Tesseract-OCR/` na raiz deste projeto.
3. Certifique-se de incluir o suporte ao idioma português (`por.traineddata`).

---

## 🚀 Como Rodar o Projeto

1. **Clonar o repositório:**
   ```bash
   git clone [https://github.com/Napolitano19/VALIDADOR_DE_DPI_MEC.git](https://github.com/Napolitano19/VALIDADOR_DE_DPI_MEC.git)
   cd VALIDADOR_DE_DPI_MEC
   ```

2. **Criar e ativar um ambiente virtual (recomendado):**
   ```bash
   python -m venv venv
   # No Windows:
   .\venv\Scripts\activate
   ```

3. **Instalar as dependências do Python:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Executar a aplicação:**
   ```bash
   python validador_dpi.py
   ```

---

## 📦 Como Compilar para Executável (.exe)

Se desejar gerar novamente o executável contendo a pasta do Tesseract e a interface Web embutidas:

```bash
pyinstaller --noconfirm --onedir --windowed ^
  --add-data "index.html;." ^
  --add-data "Tesseract-OCR;Tesseract-OCR" ^
  --name "Validador_MEC" ^
  validador_dpi.py
```