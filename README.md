# Validador de Documentos - Exigências MEC

Aplicação desktop desenvolvida em Python, com interface dinâmica em **HTML/CSS/JavaScript** utilizando `pywebview`, destinada à auditoria automatizada de documentos em PDF, considerando requisitos relacionados à digitalização e preservação de documentos.

---

## 🚀 Funcionalidades

- 🔍 **Validação de DPI Efetivo Ajustável**  
  Verifica se a resolução das imagens contidas no documento atende ao limite mínimo configurado (ex.: **300 DPI**).

- 🧬 **Classificação de Origem do Documento**  
  Distingue automaticamente documentos **Nato-Digitais** (texto/vetores nativos) de documentos **Escaneados**.

- 🏷️ **Reconhecimento e Classificação de Documentos**  
  Utiliza OCR para identificar e classificar diferentes tipos de documentos, como:
  - Comprovantes de Vacinação de Rubéola
  - Históricos Escolares
  - Diplomas
  - CNH
  - Quitação Eleitoral
  - Outros documentos acadêmicos e pessoais

- 📜 **Auditoria do Padrão PDF/A**  
  Verifica se os arquivos atendem às especificações relacionadas ao padrão **PDF/A**, utilizado para preservação digital de longo prazo.

- 🕵️ **Auditoria de Metadados e Marcas d'Água**  
  Analisa os metadados dos arquivos utilizando o **ExifTool**, permitindo identificar:
  - Marcas d'água de aplicativos de digitalização, como CamScanner;
  - Rastros de softwares gráficos, como Photoshop, Illustrator e Canva;
  - Informações relacionadas à origem e processamento do arquivo.

- 📊 **Análise Multi-Documento em Lote**  
  Permite processar vários arquivos simultaneamente, apresentando os resultados em uma tabela detalhada na interface.

- 📄 **Exportação de Laudo Técnico**  
  Gera um laudo técnico em PDF contendo o resultado da auditoria e o parecer de conformidade de cada documento analisado.

---

## 🛠️ Pré-requisitos

### 1. Python

Recomenda-se utilizar uma versão recente do Python compatível com as dependências listadas em `requirements.txt`.

### 2. Tesseract OCR

O **Tesseract OCR** é necessário para os recursos de extração de texto e validação de rotação dos documentos.

#### Instalação no Windows

1. Baixe e instale o Tesseract OCR para Windows.

2. Instale preferencialmente no caminho padrão:

   ```text
   C:\Program Files\Tesseract-OCR
   ```

3. Alternativamente, os arquivos da instalação portátil podem ser colocados na pasta:

   ```text
   Tesseract-OCR/
   ```

   na raiz do projeto.

4. Certifique-se de que o pacote de idioma português esteja disponível:

   ```text
   por.traineddata
   ```

---

## 🚀 Como Rodar o Projeto

### 1. Clonar o repositório

```bash
git clone https://github.com/Napolitano19/VALIDADOR_DE_DPI_MEC.git
cd VALIDADOR_DE_DPI_MEC
```

### 2. Criar o ambiente virtual

```bash
python -m venv venv
```

### 3. Ativar o ambiente virtual no Windows

```powershell
.\venv\Scripts\activate
```

### 4. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 5. Executar a aplicação

```bash
python validador_dpi.py
```

---

## 🧪 Teste do Ambiente

Após instalar todas as dependências, é possível executar o script de verificação do ambiente:

```bash
python test_environment.py
```

Esse teste pode ser utilizado para verificar se as principais dependências e recursos necessários para execução estão disponíveis.

---

## 📦 Gerando o Executável

Para gerar uma versão distribuível da aplicação utilizando **PyInstaller**, execute:

```powershell
pyinstaller --noconfirm --onedir --windowed `
  --add-data "index.html;." `
  --add-data "Tesseract-OCR;Tesseract-OCR" `
  --name "Validador_MEC" `
  validador_dpi.py
```

O executável será gerado dentro da pasta:

```text
dist/Validador_MEC/
```

### Estrutura esperada

Após a compilação, a estrutura deverá conter os principais arquivos e diretórios necessários para execução da aplicação, incluindo:

```text
Validador_MEC/
├── index.html
├── Tesseract-OCR/
├── validador_dpi.exe
└── ...
```

> **Observação:** a presença da pasta `Tesseract-OCR` no pacote final permite que a aplicação utilize o mecanismo OCR sem depender necessariamente de uma instalação global do Tesseract no computador.

---

## 📁 Estrutura do Projeto

Uma estrutura típica do projeto é:

```text
VALIDADOR_DE_DPI_MEC/
├── Tesseract-OCR/
├── index.html
├── validador_dpi.py
├── test_environment.py
├── requirements.txt
├── README.md
└── ...
```

---

## 🔎 Fluxo de Auditoria

De forma geral, o processo de validação segue o seguinte fluxo:

```text
Documento PDF
      │
      ▼
Leitura e análise do PDF
      │
      ├──► Origem do documento
      │      ├── Nato-Digital
      │      └── Escaneado
      │
      ├──► Análise de imagens
      │      └── DPI efetivo
      │
      ├──► OCR
      │      └── Reconhecimento do conteúdo
      │
      ├──► Metadados
      │      └── ExifTool
      │
      ├──► PDF/A
      │      └── Validação do padrão
      │
      └──► Regras de conformidade
             │
             ▼
        Resultado da Auditoria
             │
             ▼
       Laudo Técnico em PDF
```

---

## ⚙️ Tecnologias Utilizadas

- **Python**
- **PyWebView**
- **HTML / CSS / JavaScript**
- **Tesseract OCR**
- **ExifTool**
- **PyInstaller**
- **PDF/A**
- **OCR**

---

## 📄 Referência Normativa

O projeto foi desenvolvido com foco na auditoria de documentos digitalizados e nos requisitos aplicáveis à digitalização, integridade, autenticidade e preservação de documentos.

> **Importante:** os resultados apresentados pela aplicação devem ser considerados como apoio técnico à conferência documental. A validação final de conformidade deve considerar os procedimentos institucionais e os requisitos normativos aplicáveis.

---

## 👨‍💻 Execução Rápida

Para um ambiente Windows já configurado:

```powershell
git clone https://github.com/Napolitano19/VALIDADOR_DE_DPI_MEC.git
cd VALIDADOR_DE_DPI_MEC

python -m venv venv
.\venv\Scripts\activate

pip install -r requirements.txt

python test_environment.py
python validador_dpi.py
```

---

## 📌 Repositório

**GitHub:**  
https://github.com/Napolitano19/VALIDADOR_DE_DPI_MEC