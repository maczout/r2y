# r2y — response-yolo

Python reimplementation of Response-2000, a structural engineering program for sectional analysis of reinforced concrete beams and columns using the Modified Compression Field Theory (MCFT).

## Setup

```bash
pip install -e ".[dev]"
```

## Usage

```bash
# Validate an input file
python cli.py validate examples/rect_beam.json

# Print section summary
python cli.py info examples/rect_beam.json

# Print layer breakdown
python cli.py layers examples/rect_beam.json

# Export material stress-strain curves
python cli.py material-curves examples/rect_beam.json --output curves.json
```

## Testing

```bash
pytest tests/ -v
```

## Project structure

- `r2y/schema.py` — Pydantic v2 models for the consolidated JSON schema
- `r2y/materials/` — Concrete and steel constitutive models
- `r2y/section/` — Cross-section geometry and layer generation
- `cli.py` — CLI entry point
- `examples/` — Example input JSON files
- `tests/` — Unit tests
