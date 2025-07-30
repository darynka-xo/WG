# PDF Document Analysis Project

OCR and AI-powered part extraction system designed for processing technical documents, part catalogs, and specification sheets.

## 🚀 Features

### Core Capabilities
- **Advanced OCR Processing**: High-accuracy text extraction from PDF documents using DocTR
- **AI-Powered Data Extraction**: GPT-4 powered intelligent parsing of part specifications
- **Dual Analysis Modes**: 
  - Part Extraction Analysis (structured data extraction)
  - Interactive OCR Viewer (visual confidence analysis)
- **Multiple Output Formats**: Excel, JSON, Markdown, and plain text
- **Real-time Processing**: Live status updates and progress tracking
- **Batch Processing**: Handle multiple documents efficiently

### Technical Features
- **Containerized Deployment**: Docker-based for easy deployment and scaling
- **RESTful API**: Complete API for integration with external systems
- **Automatic Cleanup**: Configurable file cleanup to manage storage
- **Error Recovery**: Robust error handling and retry mechanisms
- **Performance Optimized**: Efficient processing with background task management

## 📋 Prerequisites

- **Docker & Docker Compose** (recommended)
- **Python 3.11+** (for local development)
- **OpenAI API Key** (required for AI processing)

## 🛠 Quick Start

### Option 1: Docker Deployment (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/darynka-xo/WG.git
   cd WG
   ```

2. **Configure environment**
   ```bash
   cp env.example .env
   # Edit .env file with your OpenAI API key
   ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Web Interface: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Option 2: Local Development

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

3. **Run the application**
   ```bash
   python main.py
   ```

## 📖 Usage Guide

### Web Interface

#### Part Extraction Analysis
1. Select "Part Extraction Analysis" mode
2. Upload a PDF document (technical drawings, part catalogs)
3. Wait for processing to complete (progress shown in real-time)
4. Download results in multiple formats:
   - **Excel (.xlsx)**: Structured part data for analysis
   - **Text (.txt)**: Plain text extraction
   - **Markdown (.md)**: Formatted text with structure
   - **JSON**: Raw OCR data for debugging

#### Interactive OCR Viewer
1. Select "Interactive OCR Viewer" mode
2. Upload a PDF document
3. View detailed OCR results with confidence scores
4. Analyze text recognition quality and accuracy

### API Usage

#### Upload and Process Document
```bash
curl -X POST "http://localhost:8000/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@document.pdf"
```

#### Check Processing Status
```bash
curl -X GET "http://localhost:8000/status/{upload_id}"
```

#### Download Results
```bash
curl -X GET "http://localhost:8000/results/{upload_id}"
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key for AI processing | - | ✅ |
| `CLEANUP_HOURS` | Hours before files are auto-deleted | 1 | ❌ |
| `CLEANUP_INTERVAL` | Cleanup check interval (seconds) | 300 | ❌ |

### Docker Volumes

The application uses persistent volumes for data storage:

```yaml
volumes:
  - ./docker-volumes/uploads:/app/uploads      # Uploaded files
  - ./docker-volumes/results:/app/results      # Processing results
  - ./docker-volumes/temp:/app/temp           # Temporary files
  - ./docker-volumes/static:/app/static       # Static assets
```

## 📁 Project Structure

```
WG/
├── main.py                    # FastAPI application entry point
├── logic.py                   # Core processing logic
├── utils.py                   # Utility functions
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container configuration
├── docker-compose.yml         # Multi-container setup
├── env.example               # Environment template
├── services/                 # Core processing modules
│   ├── pdfToText.py          # OCR text extraction
│   ├── fulltest.py           # AI part extraction
│   ├── openai_loop.py        # OpenAI API handling
│   ├── prompts.py            # AI prompt templates
│   └── text_constructor.py   # Text formatting
├── templates/                # HTML templates
│   ├── index.html            # Main web interface
│   └── ocr_viewer.html       # OCR visualization
├── static/                   # Static web assets
├── uploads/                  # Uploaded PDF files
├── results/                  # Processing results
└── temp/                     # Temporary files
```

## 🔄 Processing Pipeline

1. **PDF Upload**: Document uploaded via web interface or API
2. **OCR Extraction**: DocTR extracts text and structure from PDF
3. **AI Processing**: GPT-4 analyzes text and extracts structured part data
4. **Output Generation**: Multiple formats generated (Excel, JSON, etc.)
5. **Result Delivery**: Files available for download or API retrieval
6. **Cleanup**: Automatic file cleanup after configured time period

## 📊 Supported Document Types

- Technical drawings and blueprints
- Parts catalogs and specification sheets
- Engineering documentation
- Manufacturing specifications
- Component datasheets
- Assembly instructions

## 🔌 API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web interface |
| `POST` | `/upload` | Upload and process PDF |
| `GET` | `/status/{id}` | Check processing status |
| `GET` | `/results/{id}` | Get processing results |
| `GET` | `/download/{id}/{type}/{filename}` | Download specific file |
| `GET` | `/download-all/{id}` | Download all results as ZIP |
| `GET` | `/health` | Health check |

### OCR Viewer Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/process-pdf-ocr` | Upload for OCR viewer |
| `GET` | `/ocr-viewer/{id}` | Interactive OCR viewer |

### Management Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `DELETE` | `/cleanup/{id}` | Clean up specific upload |
| `GET` | `/cleanup/status` | Get cleanup statistics |
| `POST` | `/reprocess/{id}` | Reprocess with different settings |


### Debug Commands

```bash
# Check application logs
docker-compose logs -f ocr-app

# Check container status
docker-compose ps

# Monitor resource usage
docker stats pdf-ocr-extractor

# Test API connectivity
curl http://localhost:8000/health

# Check file cleanup status
curl http://localhost:8000/cleanup/status
```

## 🔄 Updates & Maintenance

### Updating the Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Backup Data

```bash
# Backup processed results
tar -czf backup-$(date +%Y%m%d).tar.gz docker-volumes/results/

# Backup configuration
cp .env .env.backup
```

## 📈 Performance Optimization

### For High-Volume Usage
- Implement Redis for status tracking
- Add database persistence for processing history
- Configure load balancing for multiple instances
- Implement queuing system for batch processing

### Memory Management
- Monitor OCR model memory usage
- Implement model unloading for idle periods
- Configure garbage collection settings
- Use smaller Docker base images

## 🤝 Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run in development mode
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```