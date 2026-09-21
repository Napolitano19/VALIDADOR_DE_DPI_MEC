import os
import sys
import json
import datetime
import re
import fitz  # PyMuPDF
import pytesseract
import subprocess
from PIL import Image
import webview

# ReportLab para geração de laudos em PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# ==============================================================================
# CONFIGURAÇÃO DE CAMINHOS LOCAIS E PORTÁTEIS
# ==============================================================================
def obter_caminho_base():
    """Retorna o caminho base do projeto, suportando execução direta e PyInstaller."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = obter_caminho_base()

# Configuração do Tesseract OCR
TESSERACT_LOCAL = os.path.join(BASE_DIR, "Tesseract-OCR", "tesseract.exe")
if os.path.exists(TESSERACT_LOCAL):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_LOCAL
else:
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Configuração do ExifTool
EXIFTOOL_LOCAL = os.path.join(BASE_DIR, "ExifTool", "exiftool.exe")
if not os.path.exists(EXIFTOOL_LOCAL):
    EXIFTOOL_LOCAL = "exiftool"


# ==============================================================================
# FUNÇÃO AUXILIAR DE SANITIZAÇÃO
# ==============================================================================
def limpar_string_metadado(val):
    """
    Sanitiza strings de metadados removendo caracteres binários/corrompidos.
    Exibe apenas caracteres legíveis ASCII/Unicode válidos ou 'N/A'.
    """
    if not val or val == "N/A":
        return "N/A"
    
    s = str(val).strip()
    s_limpa = re.sub(r'[^\x20-\x7E]', '', s).strip()
    
    if not s_limpa or len(s_limpa) < 2:
        return "N/A"
        
    return s_limpa


# ==============================================================================
# CLASSE DE LÓGICA DA APLICAÇÃO (API PYWEBVIEW)
# ==============================================================================
class ApiValidador:
    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def selecionar_arquivos(self):
        """Abre o diálogo de seleção de ficheiros PDF (compatível com versões novas do pywebview)."""
        try:
            # Compatibilidade com a versão atual do pywebview (FileDialog)
            file_type = webview.FileDialog.OPEN if hasattr(webview, 'FileDialog') else webview.OPEN_DIALOG
            ficheiros = self._window.create_file_dialog(
                file_type, 
                allow_multiple=True, 
                file_types=('Arquivos PDF (*.pdf)',)
            )
            return list(ficheiros) if ficheiros else []
        except Exception as e:
            print(f"Erro ao abrir janela de arquivos: {str(e)}")
            return []

    def _extrair_metadados_exiftool(self, caminho_pdf):
        """Extrai metadados completos do PDF utilizando o ExifTool."""
        try:
            cmd = [EXIFTOOL_LOCAL, "-j", caminho_pdf]
            resultado = subprocess.run(cmd, capture_output=True, text=True, check=True)
            dados = json.loads(resultado.stdout)
            if dados and isinstance(dados, list):
                return dados[0]
        except Exception as e:
            print(f"Erro ao ler metadados com ExifTool: {str(e)}")
        return {}

    def analisar_documentos(self, caminhos, auditar_softwares=False, exigir_pdfa=False, dpi_minimo=300):
        """Executa a verificação técnica completa em cada ficheiro PDF fornecido."""
        resultados = []

        softwares_suspeitos = ["PHOTOSHOP", "CANVA", "ILLUSTRATOR", "CORELDRAW", "GIMP", "INKSCAPE"]

        for caminho in caminhos:
            nome_arquivo = os.path.basename(caminho)
            erros = []
            
            try:
                doc = fitz.open(caminho)
                total_paginas = len(doc)
                
                eh_nato_digital = False
                dpi_minimo_encontrado = 9999
                colorido_detectado = False
                tipo_documento = "Geral / Desconhecido"
                texto_completo_ocr = ""

                # 1. Análise das páginas
                for num_pag in range(total_paginas):
                    pagina = doc[num_pag]
                    rotacao = pagina.rotation
                    
                    if rotacao != 0:
                        erros.append(f"Página {num_pag + 1} está rotacionada ({rotacao}°). Fundamento Legal: Anexo I do Decreto nº 10.278/2020.")

                    texto_pagina = pagina.get_text()
                    if texto_pagina and len(texto_pagina.strip()) > 50:
                        eh_nato_digital = True
                        texto_completo_ocr += f" {texto_pagina}"

                    lista_imagens = pagina.get_images()
                    
                    if not lista_imagens and not eh_nato_digital:
                        erros.append(f"Página {num_pag + 1} não contém imagem nem texto legível.")
                        continue

                    for img in lista_imagens:
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        
                        dpi_x = round((pix.width / pagina.rect.width) * 72) if pagina.rect.width > 0 else 0
                        dpi_y = round((pix.height / pagina.rect.height) * 72) if pagina.rect.height > 0 else 0
                        dpi_efetivo = min(dpi_x, dpi_y)

                        if dpi_efetivo < dpi_minimo_encontrado and dpi_efetivo > 0:
                            dpi_minimo_encontrado = dpi_efetivo

                        if pix.colorspace and pix.colorspace.n >= 3:
                            colorido_detectado = True

                        if not eh_nato_digital and len(texto_pagina.strip()) <= 50:
                            try:
                                img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                texto_ocr = pytesseract.image_to_string(img_pil, lang='por+eng')
                                texto_completo_ocr += f" {texto_ocr}"
                            except Exception as err_ocr:
                                print(f"Aviso no OCR da pág {num_pag + 1}: {str(err_ocr)}")

                # 2. Resolução DPI utilizando o valor dinâmico passado pela interface
                dpi_final_str = "Nativo (Vetor)" if eh_nato_digital else str(dpi_minimo_encontrado if dpi_minimo_encontrado != 9999 else "N/A")
                
                if not eh_nato_digital and dpi_minimo_encontrado < dpi_minimo:
                    erros.append(f"Resolução insuficiente ({dpi_minimo_encontrado} DPI encontrado vs {dpi_minimo} DPI exigido). Fundamento Legal: Anexo I do Decreto nº 10.278/2020.")

                # 3. Classificação por tipo
                txt_lower = texto_completo_ocr.lower()
                if "vacina" in txt_lower or "rubéola" in txt_lower or "imunização" in txt_lower:
                    tipo_documento = "Comprovante / Carteira de Vacinação de Rubéola"
                elif "historico escolar" in txt_lower or "histórico escolar" in txt_lower:
                    tipo_documento = "Histórico Escolar"
                elif "diploma" in txt_lower or "certificado" in txt_lower:
                    tipo_documento = "Certificado / Diploma"
                elif "quitação eleitoral" in txt_lower or "quitacao eleitoral" in txt_lower:
                    tipo_documento = "Quitação Eleitoral"
                elif "carteira nacional de habilitação" in txt_lower or "cnh" in txt_lower or "identidade" in txt_lower:
                    tipo_documento = "Carteira de Identidade / CNH"
                elif "militar" in txt_lower or "reservista" in txt_lower:
                    tipo_documento = "Comprovante Militar"

                # 4. Metadados e verificação de PDF/A
                metadados_exif = self._extrair_metadados_exiftool(caminho)
                
                eh_pdfa = False
                if "pdfa" in str(metadados_exif.get("GTS_PDFAConformance", "")).lower() or \
                   "pdfa" in str(metadados_exif.get("PDFVersion", "")).lower() or \
                   metadados_exif.get("pdfaid:part") is not None:
                    eh_pdfa = True

                if exigir_pdfa and not eh_pdfa:
                    erros.append("O ficheiro não está no formato preservado PDF/A. Fundamento Legal: Decreto nº 10.278/2020.")

                autor = str(metadados_exif.get("Author", "")).upper()
                criador = str(metadados_exif.get("Creator", "")).upper()
                
                if "CAMSCANNER" in txt_lower or "CAMSCANNER" in autor or "CAMSCANNER" in criador:
                    erros.append("Marca d'água / aplicativo de terceiro detectado ('CAMSCANNER'). Fundamento Legal: Art. 4º do Decreto nº 10.278/2020.")

                if auditar_softwares:
                    software_usado = str(metadados_exif.get("Software", "")).upper() or str(metadados_exif.get("Producer", "")).upper()
                    for sw in softwares_suspeitos:
                        if sw in software_usado:
                            erros.append(f"Uso de editor gráfico/software não autorizado detectado ({sw}). Fundamento Legal: Art. 4º do Decreto nº 10.278/2020.")

                doc.close()

                resultados.append({
                    "nome": nome_arquivo,
                    "caminho": caminho,
                    "origem": "Nato-Digital" if eh_nato_digital else "Escaneado",
                    "tipo_doc": tipo_documento,
                    "paginas": total_paginas,
                    "dpi": dpi_final_str,
                    "pdfa": eh_pdfa,
                    "colorido": colorido_detectado,
                    "aprovado": len(erros) == 0,
                    "erros": erros,
                    "metadados": {
                        "meta_completo": metadados_exif
                    }
                })

            except Exception as e:
                resultados.append({
                    "nome": nome_arquivo,
                    "caminho": caminho,
                    "origem": "Erro",
                    "tipo_doc": "Indefinido",
                    "paginas": 0,
                    "dpi": "N/A",
                    "pdfa": False,
                    "colorido": False,
                    "aprovado": False,
                    "erros": [f"Falha ao processar o ficheiro PDF: {str(e)}"],
                    "metadados": {}
                })

        return resultados

    def gerar_laudo_pdf(self, resultados):
        """Gera o laudo oficial em PDF."""
        try:
            file_type = webview.FileDialog.SAVE if hasattr(webview, 'FileDialog') else webview.SAVE_DIALOG
            local_salvar = self._window.create_file_dialog(
                file_type, 
                save_filename="Laudo_Conformidade_MEC.pdf",
                file_types=('Arquivos PDF (*.pdf)',)
            )
            if not local_salvar:
                return False

            if isinstance(local_salvar, tuple):
                local_salvar = local_salvar[0]

            doc = SimpleDocTemplate(
                local_salvar, 
                pagesize=letter, 
                rightMargin=28, 
                leftMargin=28, 
                topMargin=28, 
                bottomMargin=28
            )
            story = []
            styles = getSampleStyleSheet()

            COR_BORDO = colors.HexColor("#4A1525")
            COR_VERMELHO = colors.HexColor("#D33833")
            COR_TEXTO = colors.HexColor("#2D3748")
            COR_FUNDO_ALT = colors.HexColor("#F8FAFC")

            title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=14, textColor=COR_BORDO, spaceAfter=2)
            sub_title = ParagraphStyle('SubTitle', parent=styles['Heading2'], fontSize=11, textColor=COR_BORDO, spaceBefore=10, spaceAfter=6)
            sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=8, textColor=COR_TEXTO, spaceAfter=8)
            
            cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=7.5, leading=9.5, textColor=COR_TEXTO)
            cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontSize=7.5, leading=9.5, fontName="Helvetica-Bold", textColor=COR_TEXTO)
            cell_header = ParagraphStyle('CellHeader', parent=styles['Normal'], fontSize=7.5, leading=9.5, fontName="Helvetica-Bold", textColor=colors.white)
            error_style = ParagraphStyle('ErrorStyle', parent=styles['Normal'], fontSize=7.5, leading=9.5, textColor=COR_VERMELHO)

            data_hora = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
            story.append(Paragraph("LAUDO TÉCNICO DE CONFORMIDADE REGULATÓRIA - MEC", title_style))
            story.append(Paragraph(f"<b>Data da Auditoria:</b> {data_hora} | <b>Embasamento Legal:</b> Decreto Federal nº 10.278/2020", sub_style))

            total = len(resultados)
            aprovados = sum(1 for r in resultados if r['aprovado'])
            reprovados = total - aprovados

            summary_data = [
                [Paragraph("<b>TOTAL ANALISADO</b>", cell_bold), Paragraph("<b>APROVADOS</b>", cell_bold), Paragraph("<b>REPROVADOS</b>", cell_bold)],
                [Paragraph(str(total), cell_bold), Paragraph(f"<font color='#2f855a'>{aprovados}</font>", cell_bold), Paragraph(f"<font color='#D33833'>{reprovados}</font>", cell_bold)]
            ]
            t_summary = Table(summary_data, colWidths=[180, 180, 180])
            t_summary.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COR_FUNDO_ALT),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_summary)
            story.append(Spacer(1, 8))

            table_data = [[
                Paragraph("Documento / Origem", cell_header),
                Paragraph("DPI", cell_header),
                Paragraph("Cor", cell_header),
                Paragraph("Resultado", cell_header),
                Paragraph("Parecer Técnico & Enquadramento Legal", cell_header)
            ]]

            for r in resultados:
                status_txt = "<font color='#2f855a'><b>APROVADO</b></font>" if r['aprovado'] else "<font color='#D33833'><b>REPROVADO</b></font>"
                cor_txt = "Colorido" if r['colorido'] else "P&B / Cinza"
                detalhe_parecer = "<font color='#2f855a'>Conforme padrões técnicos de fidelidade e integridade.</font>"
                if r['erros']:
                    detalhe_parecer = "<br/>".join([f"• {e}" for e in r['erros']])

                doc_info = f"<b>{r['nome']}</b><br/><font color='#64748B'>{r['origem']} • {r['tipo_doc']}</font>"

                table_data.append([
                    Paragraph(doc_info, cell_style),
                    Paragraph(str(r['dpi']), cell_style),
                    Paragraph(cor_txt, cell_style),
                    Paragraph(status_txt, cell_style),
                    Paragraph(detalhe_parecer, error_style if not r['aprovado'] else cell_style)
                ])

            t_details = Table(table_data, colWidths=[140, 40, 50, 66, 260])
            estilo_tabela = [
                ('BACKGROUND', (0, 0), (-1, 0), COR_BORDO),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('PADDING', (0, 0), (-1, -1), 4),
                ('ALIGN', (1, 1), (2, -1), 'CENTER'),
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),
            ]

            for i in range(1, len(table_data)):
                if i % 2 == 0:
                    estilo_tabela.append(('BACKGROUND', (0, i), (-1, i), COR_FUNDO_ALT))

            t_details.setStyle(TableStyle(estilo_tabela))
            story.append(t_details)

            story.append(Spacer(1, 12))
            story.append(Paragraph("Anexo: Ficha Técnica de Metadados Completos (ExifTool)", sub_title))

            for r in resultados:
                if r.get("metadados") and r["metadados"].get("meta_completo"):
                    meta = r["metadados"]["meta_completo"]
                    
                    rows_meta = [
                        [
                            Paragraph("Tag de Metadado", cell_header), 
                            Paragraph("Valor Registrado no Cabeçalho do PDF", cell_header)
                        ],
                        [
                            Paragraph("Software / Gerador", cell_bold), 
                            Paragraph(limpar_string_metadado(meta.get("Software") or meta.get("Producer") or meta.get("Creator")), cell_style)
                        ],
                        [
                            Paragraph("Data de Criação", cell_bold), 
                            Paragraph(limpar_string_metadado(meta.get("CreateDate")), cell_style)
                        ],
                        [
                            Paragraph("Data de Modificação", cell_bold), 
                            Paragraph(limpar_string_metadado(meta.get("ModifyDate")), cell_style)
                        ],
                        [
                            Paragraph("Versão do PDF", cell_bold), 
                            Paragraph(limpar_string_metadado(meta.get("PDFVersion")), cell_style)
                        ],
                        [
                            Paragraph("Autor / Usuário", cell_bold), 
                            Paragraph(limpar_string_metadado(meta.get("Author")), cell_style)
                        ],
                        [
                            Paragraph("Criptografia / Proteção", cell_bold), 
                            Paragraph(limpar_string_metadado(meta.get("Encryption") or "Nenhuma"), cell_style)
                        ],
                    ]

                    story.append(Spacer(1, 4))
                    story.append(Paragraph(f"<b>Arquivo: {r['nome']}</b>", cell_style))
                    story.append(Spacer(1, 2))
                    
                    t_meta = Table(rows_meta, colWidths=[150, 406])
                    t_meta.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), COR_BORDO),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('PADDING', (0, 0), (-1, -1), 3),
                    ]))
                    story.append(t_meta)

            doc.build(story)
            return True
        except Exception as e:
            print(f"Erro ao gerar laudo PDF: {str(e)}")
            return False


# ==============================================================================
# PONTO DE ENTRADA E INICIALIZAÇÃO DA INTERFACE
# ==============================================================================
if __name__ == '__main__':
    api = ApiValidador()
    caminho_html = os.path.join(BASE_DIR, 'index.html')

    window = webview.create_window(
        'Validador de Conformidade MEC - Decreto 10.278/2020',
        url=caminho_html,
        js_api=api,
        width=1100,
        height=750,
        resizable=True
    )
    api.set_window(window)
    webview.start(debug=False)