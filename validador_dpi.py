import os
import io
import sys
import datetime
import unicodedata
import webview
import fitz  # PyMuPDF
from PIL import Image, ImageStat
import pytesseract

# Importações da biblioteca ReportLab para geração do Laudo PDF
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO DINÂMICA DO TESSERACT (EMBUTIDO / PORTABLE)
# ---------------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    # Execução compilada (.exe via PyInstaller)
    base_path = sys._MEIPASS
else:
    # Execução em modo script (.py)
    base_path = os.path.dirname(os.path.abspath(__file__))

caminho_tesseract = os.path.join(base_path, 'Tesseract-OCR', 'tesseract.exe')

if os.path.exists(caminho_tesseract):
    pytesseract.pytesseract.tesseract_cmd = caminho_tesseract
    os.environ['TESSDATA_PREFIX'] = os.path.join(base_path, 'Tesseract-OCR', 'tessdata')
else:
    # Fallback para o caminho padrão do sistema no Windows caso a pasta local fale
    caminho_sistema = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(caminho_sistema):
        pytesseract.pytesseract.tesseract_cmd = caminho_sistema


def remover_acentos(texto):
    """Remove acentos e caracteres especiais para facilitar as buscas."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).upper()


# Mapeamento de Regras do MEC por Tipo de Documento
REGRAS_DOCUMENTOS = {
    "QUITACAO_ELEITORAL": {
        "rotulo": "Quitação Eleitoral",
        "keywords": ["QUITACAO ELEITORAL", "CERTIDAO DE QUITACAO", "JUSTICA ELEITORAL", "TRIBUNAL SUPERIOR ELEITORAL", "QUITACAO"],
        "exige_cor": False
    },
    "IDENTIDADE_RG_CNH": {
        "rotulo": "Carteira de Identidade / CNH",
        "keywords": ["CNH", "CNH-E", "HABILITACAO", "CARTEIRA DE IDENTIDADE", "REGISTRO GERAL", "CARTEIRA NACIONAL DE HABILITACAO", "DETRAN", "SSP", "IDENTIDADE"],
        "exige_cor": True
    },
    "CERTIFICADO_DIPLOMA": {
        "rotulo": "Certificado / Diploma",
        "keywords": ["CERTIFICADO DE CONCLUSAO", "DIPLOMA", "ENSINO MEDIO", "SECRETARIA DE EDUCACAO", "CERTIFICADO", "CONCLUSAO DE ENSINO"],
        "exige_cor": True
    },
    "HISTORICO_ESCOLAR": {
        "rotulo": "Histórico Escolar",
        "keywords": ["HISTORICO ESCOLAR", "COMPONENTES CURRICULARES", "MATRICULA", "HISTORICO"],
        "exige_cor": False
    },
    "CERTIDAO": {
        "rotulo": "Certidão (Nascimento/Casamento)",
        "keywords": ["CERTIDAO DE NASCIMENTO", "CERTIDAO DE CASAMENTO", "REGISTRO CIVIL", "NASCIMENTO", "CASAMENTO"],
        "exige_cor": True
    },
    "SERVICO_MILITAR": {
        "rotulo": "Comprovante Militar",
        "keywords": ["SERVICO MILITAR", "CERTIFICADO DE RESERVISTA", "MINISTERIO DA DEFESA", "EXERCITO BRASILEIRO", "CAM", "MILITAR", "RESERVISTA"],
        "exige_cor": False
    }
}


class ValidadorAPI:
    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def selecionar_arquivos(self):
        """Abre a janela nativa para seleção de PDFs."""
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG, 
            allow_multiple=True, 
            file_types=('Arquivos PDF (*.pdf)',)
        )
        return result if result else []

    def validar_documentos(self, caminhos, dpi_minimo=300, exigir_pdfa=False):
        """Método invocado pela interface Web em JavaScript."""
        resultados = []
        for caminho in caminhos:
            res = self.validar_pdf(caminho, dpi_minimo=int(dpi_minimo), exigir_pdfa=exigir_pdfa)
            resultados.append(res)
        return resultados

    def _obter_texto_completo(self, doc):
        """Renderiza a página a 300 DPI para extrair texto via OCR Tesseract e rastrear marcas d'água."""
        texto_nativo = ""
        texto_ocr_visual = ""
        
        try:
            page = doc[0]
            # 1. Extrai texto vetorial/nativo da camada do PDF
            texto_nativo = page.get_text("text") or ""
            
            # 2. Renderiza a página em 300 DPI e aplica o OCR visual
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes()))
            
            try:
                texto_ocr_visual = pytesseract.image_to_string(img, lang='por')
            except Exception:
                texto_ocr_visual = pytesseract.image_to_string(img)
        except Exception as e:
            print(f"Erro no processamento OCR: {str(e)}")

        return remover_acentos(f"{texto_nativo} {texto_ocr_visual}")

    def _identificar_tipo_documento(self, texto_analise, nome_arquivo):
        texto_unificado = remover_acentos(texto_analise + " " + nome_arquivo)
        for chave, regra in REGRAS_DOCUMENTOS.items():
            if any(kw in texto_unificado for kw in regra["keywords"]):
                return chave, regra["rotulo"], regra["exige_cor"]
        return "DESCONHECIDO", "Geral / Desconhecido", False

    def _verificar_pdfa(self, doc):
        try:
            xml_data = ""
            if hasattr(doc, "get_xml_metadata"):
                xml_data = doc.get_xml_metadata() or ""
            elif hasattr(doc, "metadata_xmp"):
                xml_data = doc.metadata_xmp or ""
            
            xmp_lower = str(xml_data).lower()
            if "pdfaid:conformance" in xmp_lower or "pdfaid:part" in xmp_lower:
                return True
            
            meta = doc.metadata or {}
            for v in meta.values():
                if v and "pdf/a" in str(v).lower():
                    return True
            return False
        except Exception:
            return False

    def _checar_variacao_cor(self, img):
        if img.mode != "RGB":
            img = img.convert("RGB")
        stat = ImageStat.Stat(img)
        return abs(stat.var[0] - stat.var[1]) > 10 or abs(stat.var[1] - stat.var[2]) > 10

    def validar_pdf(self, caminho_arquivo, dpi_minimo=300, exigir_pdfa=False):
        try:
            doc = fitz.open(caminho_arquivo)
            nome_arquivo = os.path.basename(caminho_arquivo)
            
            total_paginas = len(doc)
            menor_dpi_encontrado = 9999
            tem_cor = False
            erros = []

            # Alerta preventivo se o motor OCR não for localizado
            if not os.path.exists(pytesseract.pytesseract.tesseract_cmd):
                erros.append("ERRO DE SISTEMA: Motor Tesseract OCR não encontrado para verificação de marcas d'água.")

            # 1. EXTRAÇÃO UNIFICADA DE TEXTO
            texto_analise_unificado = self._obter_texto_completo(doc)
            _, rotulo_doc, exige_cor = self._identificar_tipo_documento(texto_analise_unificado, nome_arquivo)

            # 2. CHECAGEM DE MARCA D'ÁGUA / APLICATIVOS TERCEIROS
            texto_completo_busca = remover_acentos((texto_analise_unificado + " " + nome_arquivo).upper())
            padroes_apps = [
                "CAMSCANNER", "ADOBE SCAN", "TAPSCANNER", "CLEAR SCANNER", 
                "GENIUS SCAN", "SIMPLE SCANNER", "VFLAT", "OFFICE LENS", 
                "MICROSOFT LENS", "SCANNED WITH", "DIGITALIZADO COM"
            ]
            
            marcas_detectadas = [app for app in padroes_apps if app in texto_completo_busca]
            if marcas_detectadas:
                app_encontrado = ", ".join(set(marcas_detectadas))
                erros.append(
                    f"Marca d'água / aplicativo de terceiro detectado ('{app_encontrado}'). "
                    f"Fundamento Legal: Art. 4º do Decreto nº 10.278/2020."
                )

            # 3. VERIFICAÇÃO DE PDF/A
            e_pdfa = self._verificar_pdfa(doc)
            if exigir_pdfa and not e_pdfa:
                erros.append("Arquivo não atende ao padrão PDF/A. Fundamento Legal: Art. 5º do Decreto nº 10.278/2020.")

            # 4. CHECAGEM DE RESOLUÇÃO (DPI), ROTAÇÃO E COR
            for index, page in enumerate(doc):
                image_list = page.get_images(full=True)
                texto_pagina = page.get_text("text").strip()
                page_area = page.rect.width * page.rect.height
                
                # Validação de Rotação por OSD
                try:
                    pix = page.get_pixmap(dpi=150)
                    img_pag = Image.open(io.BytesIO(pix.tobytes()))
                    osd = pytesseract.image_to_osd(img_pag)
                    for line in osd.split('\n'):
                        if "Rotate:" in line:
                            angulo = int(line.split(':')[1].strip())
                            if angulo != 0:
                                erros.append(f"Página {index + 1} está rotacionada ({angulo}°). Fundamento Legal: Anexo I do Decreto nº 10.278/2020.")
                            break
                except Exception:
                    pass

                if not image_list:
                    if len(texto_pagina) > 20:
                        if 300 < menor_dpi_encontrado:
                            menor_dpi_encontrado = 300
                        continue
                    else:
                        erros.append(f"Página {index + 1} não contém imagem nem texto legível.")
                        continue

                for img_info in image_list:
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    img = Image.open(io.BytesIO(base_image["image"]))
                    width, height = img.size
                    
                    rects = page.get_image_rects(xref)
                    if rects:
                        rect = rects[0]
                        if page_area > 0 and ((rect.width * rect.height) / page_area) < 0.20:
                            continue

                        w_inches = rect.width / 72.0
                        h_inches = rect.height / 72.0
                        dpi_efetivo = round(min(width / w_inches if w_inches > 0 else 0, height / h_inches if h_inches > 0 else 0))
                        
                        if dpi_efetivo < menor_dpi_encontrado:
                            menor_dpi_encontrado = dpi_efetivo

                    if img.mode in ("RGB", "CMYK") and self._checar_variacao_cor(img):
                        tem_cor = True

            if menor_dpi_encontrado == 9999:
                menor_dpi_encontrado = 300 if any(len(p.get_text("text").strip()) > 20 for p in doc) else 0

            if menor_dpi_encontrado < dpi_minimo:
                erros.append(f"Resolução insuficiente ({menor_dpi_encontrado} DPI encontrado vs {dpi_minimo} DPI exigido). Fundamento Legal: Anexo I do Decreto nº 10.278/2020.")

            tem_texto_nativo = any(len(p.get_text("text").strip()) > 50 for p in doc)
            if exige_cor and not tem_cor and not tem_texto_nativo:
                erros.append(f"O documento '{rotulo_doc}' exige captura colorida (RGB). Fundamento Legal: Anexo I do Decreto nº 10.278/2020.")

            return {
                "nome": nome_arquivo,
                "caminho": caminho_arquivo,
                "tipo_doc": rotulo_doc,
                "dpi": menor_dpi_encontrado if menor_dpi_encontrado > 0 else "N/A",
                "colorido": tem_cor,
                "pdfa": e_pdfa,
                "paginas": total_paginas,
                "aprovado": len(erros) == 0,
                "erros": erros
            }

        except Exception as e:
            return {
                "nome": os.path.basename(caminho_arquivo),
                "caminho": caminho_arquivo,
                "tipo_doc": "Erro no processamento",
                "dpi": 0,
                "colorido": False,
                "pdfa": False,
                "paginas": 0,
                "aprovado": False,
                "erros": [f"Erro ao processar arquivo: {str(e)}"]
            }

    def gerar_laudo_pdf(self, resultados):
        try:
            local_salvar = self._window.create_file_dialog(
                webview.SAVE_DIALOG, 
                save_filename="Laudo_Conformidade_MEC.pdf",
                file_types=('Arquivos PDF (*.pdf)',)
            )
            if not local_salvar:
                return False

            if isinstance(local_salvar, tuple):
                local_salvar = local_salvar[0]

            doc = SimpleDocTemplate(local_salvar, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
            story = []
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1a365d'), spaceAfter=6)
            sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#4a5568'), spaceAfter=12)
            cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=8, leading=10)
            cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontSize=8, leading=10, fontName="Helvetica-Bold")
            error_style = ParagraphStyle('ErrorStyle', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#c53030'))

            data_hora = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
            story.append(Paragraph("LAUDO TÉCNICO DE CONFORMIDADE REGULATÓRIA - MEC", title_style))
            story.append(Paragraph(f"<b>Data da Auditoria:</b> {data_hora} | <b>Embasamento Legal:</b> Decreto Federal nº 10.278/2020", sub_style))

            total = len(resultados)
            aprovados = sum(1 for r in resultados if r['aprovado'])
            reprovados = total - aprovados

            summary_data = [
                [Paragraph("<b>TOTAL ANALISADO</b>", cell_bold), Paragraph("<b>APROVADOS</b>", cell_bold), Paragraph("<b>REPROVADOS</b>", cell_bold)],
                [Paragraph(str(total), cell_bold), Paragraph(f"<font color='#2f855a'>{aprovados}</font>", cell_bold), Paragraph(f"<font color='#c53030'>{reprovados}</font>", cell_bold)]
            ]
            t_summary = Table(summary_data, colWidths=[180, 180, 180])
            t_summary.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf2f7')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(t_summary)
            story.append(Spacer(1, 12))

            table_data = [[
                Paragraph("<b>Documento / Tipo</b>", cell_bold),
                Paragraph("<b>DPI</b>", cell_bold),
                Paragraph("<b>Cor</b>", cell_bold),
                Paragraph("<b>Resultado</b>", cell_bold),
                Paragraph("<b>Parecer Técnico & Enquadramento Legal</b>", cell_bold)
            ]]

            for r in resultados:
                status_txt = "<font color='#2f855a'><b>APROVADO</b></font>" if r['aprovado'] else "<font color='#c53030'><b>REPROVADO</b></font>"
                cor_txt = "Colorido" if r['colorido'] else "P&B / Cinza"
                detalhe_parecer = "<font color='#2f855a'>Conforme padrões técnicos de fidelidade e integridade.</font>"
                if r['erros']:
                    detalhe_parecer = "<br/>".join([f"• {e}" for e in r['erros']])

                doc_info = f"<b>{r['nome']}</b><br/><font color='#718096'>Tipo: {r['tipo_doc']}</font>"

                table_data.append([
                    Paragraph(doc_info, cell_style),
                    Paragraph(str(r['dpi']), cell_style),
                    Paragraph(cor_txt, cell_style),
                    Paragraph(status_txt, cell_style),
                    Paragraph(detalhe_parecer, error_style if not r['aprovado'] else cell_style)
                ])

            t_details = Table(table_data, colWidths=[130, 40, 55, 65, 250])
            t_details.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2b6cb0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('PADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(t_details)

            doc.build(story)
            return True
        except Exception as e:
            print(f"Erro ao gerar laudo PDF: {str(e)}")
            return False


def obter_caminho_html():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'index.html')
    return os.path.abspath('index.html')


def iniciar_app():
    api = ValidadorAPI()
    html_path = obter_caminho_html()

    window = webview.create_window(
        title='Validador de Documentos MEC',
        url=f'file:///{html_path}' if os.path.isabs(html_path) else html_path,
        js_api=api,
        width=1120,
        height=820,
        resizable=True
    )
    api.set_window(window)
    webview.start(debug=False)


if __name__ == '__main__':
    iniciar_app()