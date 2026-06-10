"""Metadata enrichment for F1 documents."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import structlog
from langchain_core.documents import Document

from src.exceptions import ChatFormula1Error

logger = structlog.get_logger(__name__)


class MetadataEnrichmentError(ChatFormula1Error):
    """Exception raised when metadata enrichment fails."""

    pass


class MetadataEnricher:
    """Enrich document metadata with normalized F1 entities.

    Handles:
    - Date extraction and normalization
    - Driver name normalization
    - Team/constructor name normalization
    - Race and circuit identification
    - Category classification
    - Source tracking
    """

    # Known F1 drivers (can be extended)
    KNOWN_DRIVERS = {
        "verstappen",
        "max verstappen",
        "hamilton",
        "lewis hamilton",
        "leclerc",
        "charles leclerc",
        "perez",
        "sergio perez",
        "sainz",
        "carlos sainz",
        "norris",
        "lando norris",
        "alonso",
        "fernando alonso",
        "russell",
        "george russell",
        "piastri",
        "oscar piastri",
        "gasly",
        "pierre gasly",
        "vettel",
        "sebastian vettel",
        "ricciardo",
        "daniel ricciardo",
        "bottas",
        "valtteri bottas",
        "stroll",
        "lance stroll",
        "ocon",
        "esteban ocon",
        "albon",
        "alexander albon",
        "zhou",
        "zhou guanyu",
        "magnussen",
        "kevin magnussen",
        "hulkenberg",
        "nico hulkenberg",
        "tsunoda",
        "yuki tsunoda",
        "sargeant",
        "logan sargeant",
        "de vries",
        "nyck de vries",
        "lawson",
        "liam lawson",
        "bearman",
        "oliver bearman",
        # Historical drivers
        "schumacher",
        "michael schumacher",
        "senna",
        "ayrton senna",
        "prost",
        "alain prost",
        "lauda",
        "niki lauda",
        "button",
        "jenson button",
        "rosberg",
        "nico rosberg",
        "raikkonen",
        "kimi raikkonen",
        "massa",
        "felipe massa",
        "webber",
        "mark webber",
        "barrichello",
        "rubens barrichello",
    }

    # Known F1 teams/constructors
    KNOWN_TEAMS = {
        "red bull",
        "red_bull",
        "redbull",
        "red bull racing",
        "ferrari",
        "scuderia ferrari",
        "mercedes",
        "mercedes-amg",
        "mercedes amg",
        "mclaren",
        "mclaren racing",
        "alpine",
        "alpine f1",
        "aston martin",
        "aston_martin",
        "alfa romeo",
        "alfa_romeo",
        "sauber",
        "haas",
        "haas f1",
        "alphatauri",
        "alpha tauri",
        "toro rosso",
        "toro_rosso",
        "williams",
        "williams racing",
        "racing point",
        "racing_point",
        "force india",
        "force_india",
        "renault",
        "lotus",
        "lotus_racing",
    }

    # Known F1 circuits
    KNOWN_CIRCUITS = {
        "monaco",
        "monza",
        "silverstone",
        "spa",
        "suzuka",
        "bahrain",
        "jeddah",
        "melbourne",
        "imola",
        "miami",
        "barcelona",
        "montreal",
        "austria",
        "paul ricard",
        "hungaroring",
        "zandvoort",
        "singapore",
        "austin",
        "mexico",
        "interlagos",
        "las vegas",
        "abu dhabi",
        "yas marina",
        "albert park",
        "circuit de barcelona-catalunya",
        "circuit of the americas",
        "autodromo nazionale di monza",
        "nurburgring",
        "hockenheim",
        "sepang",
        "shanghai",
    }

    # Category keywords
    CATEGORY_KEYWORDS = {
        "race_result": ["finished", "points", "podium", "grid", "qualifying"],
        "driver_info": ["driver", "nationality", "team", "number"],
        "race_info": ["grand prix", "circuit", "round", "season"],
        "technical": ["regulation", "technical", "aerodynamic", "engine"],
        "statistics": ["championship", "standings", "points", "wins"],
        "news": ["announced", "confirmed", "reported", "breaking"],
    }

    def __init__(self):
        """Initialize MetadataEnricher."""
        self.logger = logger.bind(component="metadata_enricher")
        self._enrichment_stats = {
            "documents_enriched": 0,
            "dates_extracted": 0,
            "drivers_identified": 0,
            "teams_identified": 0,
            "circuits_identified": 0,
            "categories_classified": 0,
        }

    def enrich_document(self, doc: Document) -> Document:
        """Enrich a single document's metadata.

        Args:
            doc: Document to enrich

        Returns:
            Document with enriched metadata
        """
        # Create a copy to avoid modifying original
        enriched_metadata = doc.metadata.copy()
        content = doc.page_content.lower()

        # Extract and normalize dates
        if "date" not in enriched_metadata or "year" not in enriched_metadata:
            date_info = self._extract_dates(doc.page_content, enriched_metadata)
            enriched_metadata.update(date_info)
            if date_info:
                self._enrichment_stats["dates_extracted"] += 1

        # Identify drivers
        if "driver_id" not in enriched_metadata:
            drivers = self._identify_drivers(content)
            if drivers:
                enriched_metadata["drivers"] = list(drivers)
                enriched_metadata["driver_id"] = list(drivers)[0]  # Primary driver
                self._enrichment_stats["drivers_identified"] += 1

        # Identify teams
        if "constructor_id" not in enriched_metadata:
            teams = self._identify_teams(content)
            if teams:
                enriched_metadata["teams"] = list(teams)
                enriched_metadata["constructor_id"] = list(teams)[0]  # Primary team
                self._enrichment_stats["teams_identified"] += 1

        # Identify circuits
        if "circuit_id" not in enriched_metadata:
            circuits = self._identify_circuits(content)
            if circuits:
                enriched_metadata["circuits"] = list(circuits)
                enriched_metadata["circuit_id"] = list(circuits)[0]  # Primary circuit
                self._enrichment_stats["circuits_identified"] += 1

        # Classify category if not already set
        if "category" not in enriched_metadata:
            category = self._classify_category(content, enriched_metadata)
            if category:
                enriched_metadata["category"] = category
                self._enrichment_stats["categories_classified"] += 1

        # Add enrichment timestamp
        enriched_metadata["enriched_at"] = datetime.now().isoformat()

        # Track source if not present
        if "source" not in enriched_metadata:
            enriched_metadata["source"] = "unknown"

        self._enrichment_stats["documents_enriched"] += 1

        return Document(page_content=doc.page_content, metadata=enriched_metadata)

    def enrich_documents(self, documents: List[Document]) -> List[Document]:
        """Enrich multiple documents' metadata.

        Args:
            documents: List of documents to enrich

        Returns:
            List of documents with enriched metadata
        """
        self.logger.info("enriching_documents", total_documents=len(documents))

        enriched_docs = [self.enrich_document(doc) for doc in documents]

        self.logger.info(
            "documents_enriched",
            total_documents=len(documents),
            stats=self._enrichment_stats,
        )

        return enriched_docs

    def _extract_dates(
        self, text: str, existing_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract and normalize dates from text and metadata.

        Args:
            text: Document text
            existing_metadata: Existing metadata that may contain date info

        Returns:
            Dictionary with date-related metadata
        """
        date_info: Dict[str, Any] = {}

        # Check existing metadata for season/year
        if "season" in existing_metadata:
            date_info["year"] = existing_metadata["season"]
            date_info["season"] = existing_metadata["season"]

        # Try to extract year from text (4-digit number between 1950-2100)
        year_pattern = r"\b(19[5-9]\d|20\d{2}|21[0-4]\d)\b"
        year_matches = re.findall(year_pattern, text)
        if year_matches and "year" not in date_info:
            # Use the most recent year found
            years = [int(y) for y in year_matches]
            date_info["year"] = max(years)

        # Try to extract full dates (various formats)
        date_patterns = [
            r"\b(\d{4})-(\d{2})-(\d{2})\b",  # YYYY-MM-DD
            r"\b(\d{2})/(\d{2})/(\d{4})\b",  # DD/MM/YYYY
            r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b",
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Store the first match as the date
                date_info["date_extracted"] = str(matches[0])
                break

        return date_info

    def _identify_drivers(self, text: str) -> Set[str]:
        """Identify driver names in text.

        Args:
            text: Document text (lowercase)

        Returns:
            Set of identified driver IDs
        """
        identified = set()

        for driver in self.KNOWN_DRIVERS:
            if driver in text:
                # Normalize to ID format (last name or code)
                driver_id = driver.split()[-1]  # Get last name
                identified.add(driver_id)

        return identified

    def _identify_teams(self, text: str) -> Set[str]:
        """Identify team/constructor names in text.

        Args:
            text: Document text (lowercase)

        Returns:
            Set of identified team IDs
        """
        identified = set()

        for team in self.KNOWN_TEAMS:
            if team in text:
                # Normalize to ID format (remove spaces, use underscores)
                team_id = team.replace(" ", "_").replace("-", "_")
                identified.add(team_id)

        return identified

    def _identify_circuits(self, text: str) -> Set[str]:
        """Identify circuit names in text.

        Args:
            text: Document text (lowercase)

        Returns:
            Set of identified circuit IDs
        """
        identified = set()

        for circuit in self.KNOWN_CIRCUITS:
            if circuit in text:
                # Normalize to ID format
                circuit_id = circuit.replace(" ", "_").replace("-", "_")
                identified.add(circuit_id)

        return identified

    def _classify_category(self, text: str, metadata: Dict[str, Any]) -> Optional[str]:
        """Classify document category based on content and metadata.

        Args:
            text: Document text (lowercase)
            metadata: Document metadata

        Returns:
            Category string or None
        """
        # Check metadata first
        if "finish_position" in metadata or "grid_pos" in metadata:
            return "race_result"

        if "driver_id" in metadata and "constructor_id" not in metadata:
            return "driver_info"

        if "race_id" in metadata or "circuit_id" in metadata:
            return "race_info"

        # Check content for category keywords
        category_scores: Dict[str, int] = {}

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                category_scores[category] = score

        if category_scores:
            # Return category with highest score
            return max(category_scores, key=category_scores.get)  # type: ignore

        return None

    def add_custom_driver(self, driver_name: str) -> None:
        """Add a custom driver to the known drivers list.

        Args:
            driver_name: Driver name to add (will be normalized to lowercase)
        """
        normalized = driver_name.lower()
        self.KNOWN_DRIVERS.add(normalized)
        self.logger.info("custom_driver_added", driver=normalized)

    def add_custom_team(self, team_name: str) -> None:
        """Add a custom team to the known teams list.

        Args:
            team_name: Team name to add (will be normalized to lowercase)
        """
        normalized = team_name.lower()
        self.KNOWN_TEAMS.add(normalized)
        self.logger.info("custom_team_added", team=normalized)

    def add_custom_circuit(self, circuit_name: str) -> None:
        """Add a custom circuit to the known circuits list.

        Args:
            circuit_name: Circuit name to add (will be normalized to lowercase)
        """
        normalized = circuit_name.lower()
        self.KNOWN_CIRCUITS.add(normalized)
        self.logger.info("custom_circuit_added", circuit=normalized)

    def get_stats(self) -> Dict[str, Any]:
        """Get enrichment statistics.

        Returns:
            Dictionary containing enrichment stats
        """
        return self._enrichment_stats.copy()

    def reset_stats(self) -> None:
        """Reset enrichment statistics."""
        self._enrichment_stats = {
            "documents_enriched": 0,
            "dates_extracted": 0,
            "drivers_identified": 0,
            "teams_identified": 0,
            "circuits_identified": 0,
            "categories_classified": 0,
        }
        self.logger.info("enrichment_stats_reset")
