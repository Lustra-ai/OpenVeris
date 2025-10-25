# OpenVeris

An automated anomaly detection system for Ukrainian public officials' asset declarations.

## Overview

OpenVeris is a machine learning project designed to automatically detect suspicious patterns in asset declarations submitted by Ukrainian government officials. The system analyzes declarations from public databases to identify discrepancies between reported income, assets, and official positions.

## Problem Statement

Manual review of public official declarations is extremely time-consuming, as highlighted in investigative journalism reports. This creates a significant bottleneck in transparency and anti-corruption efforts. OpenVeris aims to automate this process, enabling faster identification of potentially problematic declarations.

## Data Sources

The project extracts declarations from the following portals:

- [NAZK (National Agency on Corruption Prevention)](https://public.nazk.gov.ua/)
- [YouControl - Individual Catalog](https://youcontrol.com.ua/catalog/individuals/)

## Solution

The end goal is an anomaly detection algorithm that flags declarations as suspicious when:
- Reported income doesn't match the official's position (either too low or too high)
- Asset holdings are inconsistent with declared income
- Other unusual patterns emerge from the data

## Project Scope

This project covers the complete ML lifecycle, making it an excellent learning opportunity:

1. **Data Collection** - Web scraping and data aggregation from multiple sources
2. **Data Analysis & Preprocessing** - Cleaning, normalization, handling missing values
3. **Feature Engineering** - Designing relevant features for anomaly detection
4. **Data Labeling** - Creating training datasets with normal and anomalous examples
5. **Model Training & Experimentation** - Algorithm selection, hyperparameter tuning, validation
6. **Model Deployment** - Production deployment with logging and model versioning
7. **Monitoring** - Detection of data drift and domain shifts

## Getting Started

*Coming soon*

## Installation

*Coming soon*

## Usage

*Coming soon*

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

*To be determined*

## Status

Project is in early development stage.
