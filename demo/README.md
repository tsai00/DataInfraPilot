# Demo Project (Scraping ETL)

This demo project includes a simple ETL pipeline designed to gather real estate data from 2 sources.

The pipeline consists from the following steps:
1. Scrape data from the source and store it into Azure Data Lake Storage (ADLS)
2. Download raw data from ADLS, transform it and upload back to ADLS
3. Download transformed data from ADLS and upload it to PostgreSQL DB

## High-level overview

![image info](images/project-overview.png)
