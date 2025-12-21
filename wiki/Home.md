# F1 Season Calculator Wiki

Welcome to the F1 Season Calculator wiki! This documentation will help you understand, use, and contribute to the project.

## Quick Links

| Page | Description |
|------|-------------|
| [[Getting Started]] | Quick setup and first steps |
| [[Installation]] | Detailed installation guide |
| [[Features]] | Complete feature overview |
| [[API Reference]] | REST API documentation |
| [[Architecture]] | Technical architecture overview |
| [[Contributing]] | How to contribute |
| [[FAQ]] | Frequently asked questions |

## What is F1 Season Calculator?

F1 Season Calculator is a Python-based tool that analyzes Formula 1 championship scenarios. It calculates standings for every possible combination of races, revealing fascinating "what-if" scenarios that show how different race selections would affect the championship outcome.

### Key Capabilities

- **Championship Analysis**: Calculate standings for any subset of races
- **Statistical Insights**: Head-to-head comparisons, position distributions, driver statistics
- **Visual Analytics**: Interactive charts showing season progression and performance trends
- **REST API**: Programmatic access to all calculations
- **Swagger Documentation**: Built-in API explorer at `/apidocs/`

## Supported Seasons

The calculator supports Formula 1 seasons from **1950 to present**, with automatic data fetching from the Ergast API.

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.10+, Flask |
| Database | SQLite |
| Frontend | HTML5, CSS3, JavaScript, Chart.js |
| API Docs | Flasgger (Swagger UI) |
| Testing | pytest |

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/NikoKiru/F1_Season_Calculator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/NikoKiru/F1_Season_Calculator/discussions)
- **Contributing**: See [[Contributing]] guide

## License

This project is licensed under the MIT License. See [LICENSE](https://github.com/NikoKiru/F1_Season_Calculator/blob/main/LICENSE) for details.
