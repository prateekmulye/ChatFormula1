"""CLI interface for running data ingestion pipeline."""

import asyncio
import sys
import time

import click
import structlog

from chatf1_agent.logging import setup_logging
from chatf1_agent.settings import get_settings
from ingestion.pipeline import IngestionPipeline

logger = structlog.get_logger(__name__)


@click.group()
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    help="Logging level",
)
@click.option(
    "--data-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default="data",
    help="Base directory for data files",
)
@click.pass_context
def cli(ctx: click.Context, log_level: str, data_dir: str) -> None:
    """ChatFormula1 Data Ingestion CLI.

    Ingest F1 data into Pinecone vector store for RAG pipeline.
    """
    # Setup logging (pretty console output for CLI use)
    setup_logging(log_level, json_output=False)

    # Store in context
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level
    ctx.obj["data_dir"] = data_dir

    logger.info("cli_initialized", log_level=log_level, data_dir=data_dir)


@cli.command()
@click.option(
    "--race-results",
    type=str,
    default="historical_features.csv",
    help="Race results CSV file",
)
@click.option(
    "--drivers",
    type=str,
    default="drivers.json",
    help="Drivers JSON file",
)
@click.option(
    "--races",
    type=str,
    default="races.json",
    help="Races JSON file",
)
@click.option(
    "--batch-size",
    type=int,
    default=100,
    help="Batch size for vector store ingestion",
)
@click.option(
    "--no-progress",
    is_flag=True,
    help="Disable progress logging",
)
@click.pass_context
def ingest_all(
    ctx: click.Context,
    race_results: str,
    drivers: str,
    races: str,
    batch_size: int,
    no_progress: bool,
) -> None:
    """Ingest all F1 data sources into vector store.

    This will load race results, driver data, and race information,
    process them into documents, and upsert to Pinecone.
    """
    data_dir = ctx.obj["data_dir"]

    click.echo("🏎️  ChatFormula1 Data Ingestion")
    click.echo("=" * 50)
    click.echo(f"Data directory: {data_dir}")
    click.echo(f"Race results: {race_results}")
    click.echo(f"Drivers: {drivers}")
    click.echo(f"Races: {races}")
    click.echo(f"Batch size: {batch_size}")
    click.echo("=" * 50)

    async def run_ingestion() -> None:
        try:
            # Get settings
            config = get_settings()

            # Initialize pipeline
            pipeline = IngestionPipeline(config=config, data_dir=data_dir)

            # Run ingestion
            click.echo("\n📥 Starting ingestion...")
            stats = await pipeline.ingest_all(
                race_results_file=race_results,
                drivers_file=drivers,
                races_file=races,
                batch_size=batch_size,
                show_progress=not no_progress,
            )

            # Display results
            click.echo("\n✅ Ingestion complete!")
            click.echo("\n📊 Statistics:")
            click.echo(f"  Files processed: {stats['files_processed']}")
            click.echo(f"  Total documents: {stats['total_documents']}")
            click.echo(f"  Documents ingested: {stats['documents_ingested']}")

            if stats["errors"]:
                click.echo(f"\n⚠️  Errors: {len(stats['errors'])}")
                for error in stats["errors"]:
                    click.echo(f"    - {error}")

            # Cleanup
            await pipeline.close()

        except Exception as e:
            click.echo(f"\n❌ Ingestion failed: {e}", err=True)
            logger.error("ingestion_failed", error=str(e))
            sys.exit(1)

    # Run async function
    asyncio.run(run_ingestion())


@cli.command()
@click.argument("files", nargs=-1, type=str, required=True)
@click.option(
    "--batch-size",
    type=int,
    default=100,
    help="Batch size for vector store ingestion",
)
@click.pass_context
def ingest_incremental(
    ctx: click.Context,
    files: tuple,
    batch_size: int,
) -> None:
    """Ingest only modified files (incremental update).

    Checks modification timestamps and only ingests files that have
    been updated since the last ingestion.

    Example:
        python -m ingestion.cli ingest-incremental data/*.json data/*.csv
    """
    data_dir = ctx.obj["data_dir"]

    click.echo("🏎️  ChatFormula1 Incremental Ingestion")
    click.echo("=" * 50)
    click.echo(f"Data directory: {data_dir}")
    click.echo(f"Files to check: {len(files)}")
    click.echo("=" * 50)

    async def run_ingestion() -> None:
        try:
            # Get settings
            config = get_settings()

            # Initialize pipeline
            pipeline = IngestionPipeline(config=config, data_dir=data_dir)

            # Run incremental ingestion
            click.echo("\n📥 Checking for updates...")
            stats = await pipeline.ingest_incremental(
                file_paths=list(files),
                batch_size=batch_size,
            )

            # Display results
            click.echo("\n✅ Incremental ingestion complete!")
            click.echo("\n📊 Statistics:")
            click.echo(f"  Files updated: {stats.get('files_updated', 0)}")
            click.echo(f"  Files processed: {stats['files_processed']}")
            click.echo(f"  Total documents: {stats['total_documents']}")
            click.echo(f"  Documents ingested: {stats['documents_ingested']}")

            if stats["errors"]:
                click.echo(f"\n⚠️  Errors: {len(stats['errors'])}")
                for error in stats["errors"]:
                    click.echo(f"    - {error}")

            # Cleanup
            await pipeline.close()

        except Exception as e:
            click.echo(f"\n❌ Ingestion failed: {e}", err=True)
            logger.error("incremental_ingestion_failed", error=str(e))
            sys.exit(1)

    # Run async function
    asyncio.run(run_ingestion())


@cli.command()
@click.option(
    "--file",
    type=str,
    required=True,
    help="File to ingest",
)
@click.option(
    "--file-type",
    type=click.Choice(["race_results", "drivers", "races"], case_sensitive=False),
    required=True,
    help="Type of data in the file",
)
@click.option(
    "--batch-size",
    type=int,
    default=100,
    help="Batch size for vector store ingestion",
)
@click.pass_context
def ingest_file(
    ctx: click.Context,
    file: str,
    file_type: str,
    batch_size: int,
) -> None:
    """Ingest a single file.

    Useful for testing or ingesting specific data sources.
    """
    data_dir = ctx.obj["data_dir"]

    click.echo("🏎️  ChatFormula1 Single File Ingestion")
    click.echo("=" * 50)
    click.echo(f"Data directory: {data_dir}")
    click.echo(f"File: {file}")
    click.echo(f"Type: {file_type}")
    click.echo("=" * 50)

    async def run_ingestion() -> None:
        try:
            # Get settings
            config = get_settings()

            # Initialize pipeline
            pipeline = IngestionPipeline(config=config, data_dir=data_dir)
            await pipeline.initialize_vector_store()

            # Ingest based on type
            click.echo(f"\n📥 Ingesting {file_type}...")

            if file_type == "race_results":
                docs = await pipeline._ingest_race_results(file)
            elif file_type == "drivers":
                docs = await pipeline._ingest_drivers(file)
            elif file_type == "races":
                docs = await pipeline._ingest_races(file)
            else:
                raise ValueError(f"Unknown file type: {file_type}")

            # Upsert to vector store
            click.echo(f"\n📤 Upserting {len(docs)} documents...")
            assert pipeline.vector_store is not None
            ids = await pipeline.vector_store.add_documents(
                documents=docs,
                batch_size=batch_size,
                show_progress=True,
            )

            # Display results
            click.echo("\n✅ File ingestion complete!")
            click.echo(f"  Documents created: {len(docs)}")
            click.echo(f"  Documents ingested: {len(ids)}")

            # Cleanup
            await pipeline.close()

        except Exception as e:
            click.echo(f"\n❌ File ingestion failed: {e}", err=True)
            logger.error("file_ingestion_failed", error=str(e))
            sys.exit(1)

    # Run async function
    asyncio.run(run_ingestion())


@cli.command()
@click.pass_context
def check_config(ctx: click.Context) -> None:
    """Check configuration and vector store connection.

    Validates that all required API keys are set and the vector
    store is accessible.
    """
    click.echo("🏎️  ChatFormula1 Configuration Check")
    click.echo("=" * 50)

    async def run_check() -> None:
        try:
            # Get settings
            config = get_settings()

            click.echo("✅ Configuration loaded successfully")
            click.echo(f"  Environment: {config.environment}")
            click.echo(f"  Log level: {config.log_level}")

            click.echo("\n🤖 LLM provider")
            click.echo(f"  Provider: {config.llm_provider}")
            click.echo(f"  Base URL: {config.llm_base_url or '(provider default)'}")
            click.echo(f"  Generation model: {config.llm_model}")
            click.echo(f"  Analysis model: {config.analysis_model}")
            click.echo(f"  Function calling: {config.supports_function_calling}")

            click.echo("\n🧬 Embeddings")
            click.echo(f"  Provider: {config.resolved_embedding_provider}")
            click.echo(
                f"  Base URL: {config.embedding_base_url or '(provider default)'}"
            )
            click.echo(f"  Model: {config.embedding_model}")
            # Raises with remediation when the dimension is unresolvable.
            expected_dimension = config.resolved_embedding_dimension
            click.echo(f"  Dimension: {expected_dimension}")

            click.echo("\n📚 Ingestion")
            click.echo(f"  Pinecone index: {config.pinecone_index_name}")
            click.echo(f"  Chunk size: {config.chunk_size}")
            click.echo(f"  Chunk overlap: {config.chunk_overlap}")

            # Test vector store connection (validates the index dimension
            # against the configured embeddings and fails loudly on drift).
            click.echo("\n🔌 Testing vector store connection...")
            data_dir = ctx.obj["data_dir"]
            pipeline = IngestionPipeline(config=config, data_dir=data_dir)
            await pipeline.initialize_vector_store()

            assert pipeline.vector_store is not None
            health = await pipeline.vector_store.health_check()

            if health["status"] == "healthy":
                click.echo("✅ Vector store connection successful")
                click.echo(f"  Index: {health['index_name']}")
                click.echo(
                    f"  Dimension: {health['dimension']} "
                    f"(matches configured {expected_dimension} ✅)"
                )
                click.echo(f"  Vectors: {health['total_vector_count']}")
            else:
                click.echo(
                    f"❌ Vector store unhealthy: {health.get('error')}", err=True
                )
                sys.exit(1)

            await pipeline.close()

        except Exception as e:
            click.echo(f"\n❌ Configuration check failed: {e}", err=True)
            logger.error("config_check_failed", error=str(e))
            sys.exit(1)

    # Run async function
    asyncio.run(run_check())


@cli.command()
@click.option(
    "--yes",
    is_flag=True,
    help="Skip the confirmation prompt (CI / scripted use).",
)
def reindex(yes: bool) -> None:
    """Delete and recreate the Pinecone index (destroys ALL vectors).

    Run this BEFORE re-ingesting whenever the embedding provider, model,
    or dimension changes — vectors from different embedding models are
    not interchangeable. Repopulate afterwards with `make ingest`.
    """
    from pinecone import Pinecone, ServerlessSpec

    click.echo("🏎️  ChatFormula1 Index Rebuild")
    click.echo("=" * 50)

    try:
        config = get_settings()
        config.require("pinecone_api_key")
        dimension = config.resolved_embedding_dimension
        name = config.pinecone_index_name

        click.echo(f"Index: {name}")
        click.echo(f"Embedding provider: {config.resolved_embedding_provider}")
        click.echo(f"Embedding model: {config.embedding_model}")
        click.echo(f"Dimension: {dimension}")

        pc = Pinecone(api_key=config.pinecone_api_key)
        existing = [idx.name for idx in pc.list_indexes()]

        if name in existing:
            stats = pc.Index(name).describe_index_stats()
            count = stats.total_vector_count
            if not yes:
                click.confirm(
                    f"\n⚠️  Delete index '{name}' ({count} vectors)? "
                    "This cannot be undone",
                    abort=True,
                )
            click.echo(f"🗑️  Deleting index '{name}'...")
            pc.delete_index(name)

            # Deletion is asynchronous server-side; wait until it is gone.
            deadline = time.monotonic() + 60
            while name in [idx.name for idx in pc.list_indexes()]:
                if time.monotonic() > deadline:
                    raise TimeoutError(
                        f"Index '{name}' was not deleted within 60s; "
                        "retry once Pinecone finishes the deletion."
                    )
                time.sleep(2)
        else:
            click.echo(f"Index '{name}' does not exist yet; creating it fresh.")

        click.echo(f"🆕 Creating index '{name}' ({dimension}-dim, cosine)...")
        pc.create_index(
            name=name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

        click.echo("\n✅ Index rebuilt and EMPTY. Re-ingest with: make ingest")
        logger.info("reindex_complete", index_name=name, dimension=dimension)

    except click.Abort:
        raise
    except Exception as e:
        click.echo(f"\n❌ Reindex failed: {e}", err=True)
        logger.error("reindex_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    cli()
