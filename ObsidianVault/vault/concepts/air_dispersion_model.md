---
title: Air Dispersion Model
type: Concept
source_document: soe_report.pdf
source_location: pp. 22-23
extraction_date: '2026-08-11'
tags: []
---

# Air Dispersion Model


## Summary
A customized software model designed to run in conjunction with a low-cost sensor network. It processes meteorological parameters and traffic emissions to generate hourly, high-resolution continuous air quality maps.

## Key Data / Findings

| Verification Parameter | Value Range | Benchmark |
|---|---|---|
| Model Accuracy ($R^2$) | 0.70 to 0.97 | US EPA Recommended standard (≥ 0.7) |
| Model Error (RMSE) | 1.80 to 3.70 µg/m³ | US EPA Recommended standard (≤ 7 µg/m³) |

## Relationships
- **COMPUTED_FROM** → [[Low-Cost Air Quality Sensors]]
- **BENCHMARKED_AGAINST** → [[US Environmental Protection Agency (US EPA)]]

## Source Excerpt
> The model integrates measurement data from the low-cost sensor with other data sources such as real-time meteorological data, traffic emissions, background concentration from nearby air monitoring station... to generate hourly air quality heat maps...
 — soe_report.pdf, pp. 22-23
