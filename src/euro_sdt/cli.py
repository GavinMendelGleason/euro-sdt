"""Unified CLI for the euro-sdt pipeline.

Usage:
    euro-sdt scrape commission     # Scrape VdL II commissioner list
    euro-sdt scrape meps           # Scrape current MEP list
    euro-sdt scrape cvs            # Fetch Wikidata CV data
    euro-sdt scrape declarations   # Parse declarations ZIP
    euro-sdt scrape sources        # Extract source texts
    euro-sdt extract orgs          # LLM org membership extraction
    euro-sdt extract verify        # LLM fact verification
    euro-sdt extract validate      # LLM entity validation
    euro-sdt extract dedup-edu     # Education institution dedup
    euro-sdt render wiki           # Generate Obsidian wiki
    euro-sdt render analytics      # Generate time-series charts
    euro-sdt status                # DB coverage report
    euro-sdt check-citations       # Verify paper citations
"""

import typer

app = typer.Typer(name="euro-sdt", help="EU institutional elite research pipeline")

# ── Subcommand groups ────────────────────────────────────────────────────────

scrape_group = typer.Typer(name="scrape", help="Data acquisition")
app.add_typer(scrape_group)

extract_group = typer.Typer(name="extract", help="LLM extraction & verification")
app.add_typer(extract_group)

render_group = typer.Typer(name="render", help="Output generation")
app.add_typer(render_group)


# ── Scrape commands ─────────────────────────────────────────────────────────

@scrape_group.command(name="commission")
def scrape_commission():
    """Scrape VdL II commissioner list from Wikipedia."""
    from euro_sdt.scrape.commission import main
    main()


@scrape_group.command(name="meps")
def scrape_meps():
    """Scrape current MEP list from Wikipedia."""
    from euro_sdt.scrape.meps import main
    main()


@scrape_group.command(name="cvs")
def scrape_cvs():
    """Fetch CV data from Wikidata SPARQL for MEPs and commissioners."""
    from euro_sdt.scrape.cvs import main
    main()


@scrape_group.command(name="declarations")
def scrape_declarations():
    """Parse EC machine-readable declarations ZIP."""
    from euro_sdt.scrape.declarations import main
    main()


@scrape_group.command(name="sources")
def scrape_sources():
    """Extract plain text and phrase indices from all source documents."""
    from euro_sdt.scrape.sources import main
    main()


# ── Extract commands ────────────────────────────────────────────────────────

@extract_group.command(name="orgs")
def extract_orgs(
    dry_run: bool = typer.Option(False, "--dry-run"),
    limit: int = typer.Option(0, "--limit", "-n"),
):
    """LLM phrase-level org membership extraction from bios."""
    from euro_sdt.extract.orgs import main
    main(dry_run=dry_run, limit=limit)


@extract_group.command(name="verify")
def extract_verify():
    """LLM fact verification against source quotes."""
    from euro_sdt.extract.verify import main
    main()


@extract_group.command(name="validate")
def extract_validate():
    """LLM entity name validation (VALID/STRIP/INVALID)."""
    from euro_sdt.extract.validate import main
    main()


@extract_group.command(name="dedup-edu")
def extract_dedup_edu():
    """LLM education institution deduplication."""
    from euro_sdt.extract.dedup_edu import main
    main()


# ── Render commands ─────────────────────────────────────────────────────────

@render_group.command(name="wiki")
def render_wiki():
    """Generate Obsidian wiki from the database."""
    from euro_sdt.render.wiki import main
    main()


@render_group.command(name="analytics")
def render_analytics():
    """Generate time-series charts and analytics."""
    from euro_sdt.render.analytics import main
    main()


# ── Top-level commands ──────────────────────────────────────────────────────

@app.command(name="status")
def show_status():
    """Show database coverage and confidence status."""
    from euro_sdt.status import main
    main()


@app.command(name="check-citations")
def check_citations():
    """Cross-check paper citations against local PDFs."""
    from euro_sdt.check_citations import main
    main()


if __name__ == "__main__":
    app()
