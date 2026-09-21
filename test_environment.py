import os
import sys
import subprocess

def testar_ambiente():
    print("=" * 60)
    print("🔍 DIAGNÓSTICO DE DEPENDÊNCIAS - VALIDADOR MEC")
    print("=" * 60)
    
    erros = 0

    # 1. Teste das Importações
    pacotes = {
        "webview": "pywebview (Interface)",
        "fitz": "PyMuPDF (Processamento de PDF)",
        "PIL": "Pillow (Manipulação de Imagem)",
        "pytesseract": "pytesseract (Integração OCR)",
        "reportlab": "reportlab (Geração de Laudo PDF)"
    }

    print("\n[1/4] Testando bibliotecas do Python...")
    for mod, nome in pacotes.items():
        try:
            __import__(mod)
            print(f"  ✅ {nome}: OK")
        except ImportError:
            print(f"  ❌ {nome}: NÃO INSTALADO")
            erros += 1

    # 2. Teste de Acesso ao Tesseract OCR
    print("\n[2/4] Testando integração com o Tesseract OCR...")
    try:
        import pytesseract

        base_path = os.path.dirname(os.path.abspath(__file__))
        caminho_local = os.path.join(base_path, 'Tesseract-OCR', 'tesseract.exe')
        caminho_sistema = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        if os.path.exists(caminho_local):
            pytesseract.pytesseract.tesseract_cmd = caminho_local
            print(f"  ℹ️ Tesseract local encontrado em: {caminho_local}")
        elif os.path.exists(caminho_sistema):
            pytesseract.pytesseract.tesseract_cmd = caminho_sistema
            print(f"  ℹ️ Tesseract do sistema encontrado em: {caminho_sistema}")

        versao = pytesseract.get_tesseract_version()
        print(f"  ✅ Motor Tesseract ativo (Versão {versao})")
    except Exception as e:
        print(f"  ❌ Falha no Tesseract OCR: {str(e)}")
        erros += 1

    # 3. Teste do PyMuPDF (fitz)
    print("\n[3/4] Testando engine de PDFs (PyMuPDF)...")
    try:
        import fitz
        doc = fitz.open()
        doc.new_page()
        doc.close()
        print("  ✅ Leitor/Criador de PDFs funcionando com sucesso")
    except Exception as e:
        print(f"  ❌ Falha na engine de PDF: {str(e)}")
        erros += 1

    # 4. Teste do ExifTool
    print("\n[4/4] Testando utilitário de Metadados (ExifTool)...")
    exif_path = os.path.join(os.getcwd(), "ExifTool", "exiftool.exe")
    if os.path.exists(exif_path):
        try:
            res = subprocess.run([exif_path, "-ver"], capture_output=True, text=True, check=True)
            print(f"  ✅ ExifTool encontrado (Versão {res.stdout.strip()})")
        except Exception as e:
            print(f"  ⚠️ ExifTool localizado, mas falhou ao executar: {e}")
            erros += 1
    else:
        print("  ⚠️ ExifTool não localizado na pasta 'ExifTool/'")
        erros += 1

    # Resultado Final
    print("\n" + "=" * 60)
    if erros == 0:
        print("🚀 TUDO CERTO! O ambiente está pronto para rodar a aplicação.")
    else:
        print(f"⚠️ ATENÇÃO: Foram encontrados {erros} problema(s). Verifique as pendências acima.")
    print("=" * 60)

if __name__ == "__main__":
    testar_ambiente()