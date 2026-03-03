# Chat P1 Data Ingestion Pipeline

This module provides a complete data ingestion pipeline for loading F1 knowledge base into Pinecone vector store.

## Components

### 1. DataLoader (`data_loader.py`)
Loads and validates data from CSV and JSON sources.

**Features:**
- CSV and JSON file loading
- Pydantic schema validation
- Incremental loading (only reload modified files)
- Multiple file pattern support
- Flexible validation modes

**Schemas:**
- `RaceResultSchema`: Race results from historical_features.csv
- `DriverSchema`: Driver information from drivers.json
- `RaceSchema`: Race information from races.json

### 2. DocumentProcessor (`document_processor.py`)
Processes raw data into LangChain documents with chunking.

**Features:**
- Semantic text chunking with overlap
- Metadata extraction from source data
- Document deduplication
- Content cleaning and normalization
- Support for race results, drivers, and race info

### 3. MetadataEnricher (`metadata_enricher.py`)
Enriches document metadata with normalized F1 entities.

**Features:**
- Date extraction and normalization
- Driver name identification
- Team/constructor identification
- Circuit identification
- Category classification
- Source tracking

### 4. IngestionPipeline (`pipeline.py`)
Orchestrates the end-to-end ingestion workflow.

**Features:**
- Full ingestion of all data sources
- Incremental updates
- Progress tracking and logging
- Error recovery
- Batch processing for efficiency

## CLI Usage

The ingestion pipeline can be run via the CLI:

```bash
# Install dependencies first
poetry install

# Check configuration and vector store connection
poetry run f1-ingest check-config

# Ingest all data sources
poetry run f1-ingest ingest-all

# Ingest with custom files
poetry run f1-ingest ingest-all \
  --race-results historical_features.csv \
  --drivers drivers.json \
  --races races.json \
  --batch-size 100

# Incremental ingestion (only modified files)
poetry run f1-ingest ingest-incremental data/*.json data/*.csv

# Ingest a single file
poetry run f1-ingest ingest-file \
  --file drivers.json \
  --file-type drivers

# Custom data directory
poetry run f1-ingest --data-dir /path/to/data ingest-all

# Debug mode
poetry run f1-ingest --log-level DEBUG ingest-all
```

## Programmatic Usage

```python
import asyncio
from src.config.settings import get_settings
from src.ingestion.pipeline import IngestionPipeline

async def main():
    # Initialize pipeline
    config = get_settings()
    pipeline = IngestionPipeline(config=config, data_dir="data")
    
    # Ingest all data
    stats = await pipeline.ingest_all(
        race_results_file="historical_features.csv",
        drivers_file="drivers.json",
        races_file="races.json",
        batch_size=100,
        show_progress=True,
    )
    
    print(f"Ingested {stats['documents_ingested']} documents")
    
    # Cleanup
    await pipeline.close()

asyncio.run(main())
```

## Data Format Requirements

### Race Results CSV
Required columns:
- `race_id`: Unique race identifier (e.g., "2010_1_bahrain")
- `driver_id`: Driver identifier
- `constructor_id`: Team identifier
- `season`: Year (integer)
- `round`: Round number (integer)
- `circuit_id`: Circuit identifier

Optional columns:
- `quali_pos`, `grid_pos`, `finish_position`: Positions (integer)
- `points`: Points scored (float)
- `podium_finish`, `top_10_finish`: Flags (0/1)

### Drivers JSON
Required fields:
- `id`: Driver identifier
- `code`: 3-letter driver code
- `name`: Full name

Optional fields:
- `number`: Driver number
- `constructor`: Current team
- `nationality`: Nationality

### Races JSON
Required fields:
- `id`: Race identifier
- `name`: Race name

Optional fields:
- `circuit`: Circuit name
- `country`: Country
- `date`: Race date
- `season`: Year
- `round`: Round number

## Configuration

Set these environment variables in `.env`:

```bash
# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=f1-knowledge
PINECONE_DIMENSION=1536

# OpenAI Configuration (for embeddings)
OPENAI_API_KEY=your_openai_api_key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Ingestion Configuration
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

## Pipeline Flow

```
1. Load Data
   ├── CSV files (race results)
   ├── JSON files (drivers, races)
   └── Validate with Pydantic schemas

2. Process Documents
   ├── Convert to narrative text
   ├── Chunk long documents
   └── Deduplicate

3. Enrich Metadata
   ├── Extract dates
   ├── Identify drivers, teams, circuits
   ├── Classify categories
   └── Track sources

4. Embed & Upsert
   ├── Generate embeddings (OpenAI)
   ├── Batch processing
   └── Upsert to Pinecone
```

## Error Handling

The pipeline includes comprehensive error handling:

- **File not found**: Logs warning and continues with other files
- **Validation errors**: Logs error details and skips invalid records
- **Vector store errors**: Retries with exponential backoff
- **Batch failures**: Continues with next batch instead of failing completely

All errors are logged and included in the final statistics.

## Performance

- **Batch processing**: Configurable batch size (default: 100)
- **Parallel operations**: Async/await for I/O operations
- **Deduplication**: In-memory hash tracking
- **Progress tracking**: Real-time logging of progress

## Monitoring

The pipeline provides detailed statistics:

```python
stats = {
    "files_processed": 3,
    "total_documents": 1500,
    "documents_ingested": 1450,
    "errors": [],
    "processor_stats": {
        "unique_documents_seen": 1450,
        "chunk_size": 1000,
        "chunk_overlap": 200,
    },
    "enricher_stats": {
        "documents_enriched": 1450,
        "dates_extracted": 1200,
        "drivers_identified": 800,
        "teams_identified": 600,
        "circuits_identified": 400,
    }
}
```

## Troubleshooting

### "Vector store not initialized"
Run `check-config` to verify Pinecone connection:
```bash
poetry run f1-ingest check-config
```

### "Validation failed"
Check data format matches schemas. Use `validate=False` for flexible validation:
```python
data = loader.load_csv("file.csv", validate=False)
```

### "Rate limit exceeded"
Reduce batch size or add delays:
```bash
poetry run f1-ingest ingest-all --batch-size 50
```

### "Out of memory"
Process files individually:
```bash
poetry run f1-ingest ingest-file --file drivers.json --file-type drivers
```

## Development

Run tests:
```bash
poetry run pytest tests/test_ingestion.py -v
```

Format code:
```bash
poetry run black src/ingestion/
poetry run ruff check src/ingestion/
```

Type checking:
```bash
poetry run mypy src/ingestion/
```
