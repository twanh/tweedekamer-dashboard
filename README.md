# Tweede Kamer Dashboard

A dashboard for visualizing data from the Dutch parliament (Tweede Kamer), powered by GraphDB and Flask.

## Setup

### Prerequisites

- Docker and Docker Compose installed
- Python 3.x (for running scripts)

### 1. Start Docker Services

Start all services using Docker Compose:

```bash
docker-compose up -d
```

This will start three services:
- **GraphDB**: Knowledge graph database running on port `7200`
- **Web App**: Flask dashboard running on port `5001`
- **Scraper**: Service for scraping Tweede Kamer data

Check that all services are running:

```bash
docker-compose ps
```

### 2. Configure GraphDB Repository

1. Open GraphDB Workbench in your browser:
   ```
   http://localhost:7200
   ```

2. Navigate to **Setup** → **Repositories** → **New repository**

3. Create a repository with the following settings:
   - **Repository ID**: `tk_kb`
   - **Repository title**: `Tweede Kamer Knowledge Base`
   - Select **GraphDB repository type**
   - Under **Ruleset**: Choose **OWL2RL (Optimized)**
   - Click **Create**

### 3. Upload the Ontology

Once the repository is created, upload the ontology using the provided script:

```bash
python scripts/add_ontology.py http://localhost:7200/repositories/tk_kb kb/tweedekamer-ontology.ttl
```

This will load the ontology definitions into GraphDB.

### 4. Import Data

You have two options for importing data:

#### Option A: Run the Scraper

Run the scraper to fetch data from the Tweede Kamer API and populate the knowledge base:

```bash
docker-compose exec scraper python scraper/src/main.py
```

You can also specify custom date ranges:

```bash
docker-compose exec scraper python scraper/src/main.py \
  --start-date 2025-01-01 \
  --end-date 2025-12-31
```

#### Option B: Upload Existing Data

Upload a exesting data file to the repository. The datafile will be made public in a later stage.

## Accessing the Web App

Once everything is set up, access the web dashboard at:

**http://localhost:5001**

## Service Ports

- **GraphDB**: `http://localhost:7200`
- **Web Dashboard**: `http://localhost:5001`

## Stopping Services

To stop all services:

```bash
docker-compose down
```

To stop and remove all data (including GraphDB storage):

```bash
docker-compose down -v
```
