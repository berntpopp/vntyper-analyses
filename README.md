# VNtyper Joint Cohort Analyses (vntyper-analyses)

**Repository for Pseudonymized Results and Standard Operating Procedures (SOPs) from Joint Cohort Analyses using VNtyper**

---

## Table of Contents

1.  [Overview](#overview)
2.  [Relationship to VNtyper Tool](#relationship-to-vntyper-tool)
3.  [Repository Contents](#repository-contents)
    *   [Pseudonymized Results](#pseudonymized-results)
    *   [Standard Operating Procedures (SOPs)](#standard-operating-procedures-sops)
    *   [Analysis Scripts & Documentation](#analysis-scripts--documentation)
4.  [Navigating This Repository](#navigating-this-repository)
5.  [Data Usage and Ethics](#data-usage-and-ethics)
6.  [How to Contribute](#how-to-contribute)
7.  [Citing VNtyper](#citing-vntyper)
8.  [Contact](#contact)

---

## 1. Overview

This repository, `vntyper-analyses`, serves as a central hub for the MUC1-VNTR genotyping project utilizing the **VNtyper 2.0** tool. As we analyze thousands of samples across different research centers, this space is dedicated to:

*   **Storing pseudonymized, aggregated results** from joint cohort analyses.
*   **Documenting and sharing Standard Operating Procedures (SOPs)** to ensure consistency and reproducibility in data generation, processing, and analysis across participating centers.
*   **Facilitating collaborative interpretation and reporting** of findings related to MUC1 VNTRs in Autosomal Dominant Tubulointerstitial Kidney Disease (ADTKD-MUC1) and other relevant cohorts.

The primary goal is to provide a transparent and accessible resource for all collaborators involved in the VNtyper joint cohort studies.

---

## 2. Relationship to VNtyper Tool

The analyses and results contained herein are generated using **VNtyper 2.0**, an advanced pipeline designed to genotype MUC1 coding Variable Number Tandem Repeats (VNTR) in Autosomal Dominant Tubulointerstitial Kidney Disease (ADTKD-MUC1) using Short-Read Sequencing (SRS) data.

*   **Main VNtyper Tool Repository:** [https://github.com/hassansaei/vntyper](https://github.com/hassansaei/vntyper)
*   **VNtyper Online Web Server:** [https://vntyper.org/](https://vntyper.org/)

This `vntyper-analyses` repository does **not** contain the VNtyper software itself, but rather the outputs, methodologies, and collaborative documents related to its application in large-scale cohort studies. For information on installing and running VNtyper, please refer to the main tool repository.

---

## 3. Repository Contents

This repository is structured to hold the following key components:

### Pseudonymized Results

*   **Aggregated Genotyping Data:** Combined MUC1 VNTR genotyping calls from multiple cohorts and centers. Data will typically be in summary tables.
*   **Variant Frequency Data:** Allele frequencies and characteristics of VNTRs observed across the studied populations.
*   **Statistical Summaries:** Key metrics, quality control reports, and comparative analyses derived from the joint dataset.
*   **Data Dictionaries:** Descriptions of the fields and formats used in the results files.

**All patient-level data shared in this repository will be strictly pseudonymized according to agreed-upon protocols to protect patient privacy.**

### Standard Operating Procedures (SOPs)

A collection of documents detailing the standardized methods used in the joint cohort analysis, including but not limited to:

*   **Sample Inclusion/Exclusion Criteria:** Guidelines for samples included in the analyses.
*   **Data Generation and QC:** Recommended parameters for running VNtyper, quality control checks for raw sequencing data and VNtyper outputs.
*   **Data Pseudonymization and Sharing:** Protocols for preparing and submitting data to this central repository.
*   **Joint Analysis Plans:** Statistical methods and approaches for combined analysis of data from multiple centers.
*   **Variant Annotation and Interpretation Guidelines:** Framework for interpreting novel or rare VNTR alleles.

### Analysis Scripts & Documentation

*   **Scripts:** (e.g., R, Python) used for meta-analysis, data visualization, or specific sub-analyses performed on the joint cohort data. These are distinct from the core VNtyper pipeline scripts.
*   **Reports and Summaries:** Interim or finalized reports from specific working groups or analysis efforts.

---

## 4. Navigating This Repository

We aim to maintain a clear and organized structure. Key directories you might find include:

*   `/results/`: Contains subdirectories for different analysis batches or specific cohort summaries, holding pseudonymized data files.
    *   e.g., `/results/cohort_A_YYYYMMDD/`, `/results/joint_analysis_v1/`
*   `/sops/`: Contains SOP documents, categorized by their purpose.
    *   e.g., `/sops/data_submission/`, `/sops/vntyper_execution/`
*   `/scripts/`: Contains analysis scripts used for post-VNtyper processing of joint data.
*   `/documentation/`: General documentation, data dictionaries, and project-specific information.

Please refer to the specific README files within each directory for more detailed information about its contents.

---

## 5. Data Usage and Ethics

*   The data and SOPs in this repository are primarily intended for **research use by contributing members of the VNtyper joint cohort analysis consortium.**
*   Use of any data should adhere to the collaborative agreements and data sharing policies established for this project.
*   All users are expected to respect patient privacy and the ethical guidelines governing human subjects research.
*   If you intend to use data from this repository for publications or presentations, please ensure appropriate acknowledgments and co-authorship are discussed with the project coordinators and data contributors.

---

## 6. How to Contribute

Contributions to this repository (e.g., submitting new pseudonymized results, updating SOPs, proposing analysis scripts) are welcome from participating centers and researchers. Please follow these general guidelines:

1.  **Contact Project Coordinators:** Before contributing new datasets or major SOP revisions, please discuss with the designated project coordinators ([see Contact section](#8-contact)).
2.  **Follow SOPs:** Ensure any data submitted adheres to the established SOPs for data formatting, pseudonymization, and quality control.
3.  **Use Pull Requests:** For changes to documents or scripts, please fork the repository, create a new branch for your changes, and submit a Pull Request.
4.  **Provide Clear Documentation:** Accompany any new data or scripts with clear descriptions, context, and (if applicable) a data dictionary.

More detailed contribution guidelines may be provided in the `/documentation/` directory.

---
