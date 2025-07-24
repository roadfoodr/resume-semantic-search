## Objective

To convert resumes into structured JSON records optimized for **semantic, fuzzy search**—favoring high-quality summaries over rigid field-by-field extraction. The goal is to enable more flexible, intent-based matching between candidate profiles and job descriptions.

---

## Design Philosophy

During extraction, we intentionally **transform** each document into a compact, meaningful **representation** of a candidate’s experience and skills by creating LLM-generated summaries of the candidate's overall profile, skills, work history, project history, and education. This representation is tailored for semantic similarity retrieval, allowing us to compare candidates and job descriptions at the level of meaning rather than just keywords.

---

## What We Built

1. **Defined a Focused Resume Schema:**

   * Key fields: `id`, `name`, `summary`, `work_history`, `project_history`, `skills`, `education`, `links`, and `raw_text`.
   * The schema prioritizes fields that capture the candidate's experience in a condensed, semantically meaningful form, ready for downstream search and filtering.

2. **Created a Resume Parsing Pipeline:**

   * Extracts raw text from PDFs using `PyMuPDF`.
   * Identifies and extracts links (LinkedIn, GitHub, personal websites) using simple regex patterns.
   * Leverages `Instructor` with OpenAI to populate a structured `pydantic` model via natural language understanding.

3. **Enabled Fuzzy Matching and Semantic Retrieval:**

   * Fields like `summary`, `skills`, and `work_history` are designed to be embedded and compared using vector similarity.
   * This allows for matching queries like "senior software engineer with ML experience" even if exact terms don’t appear in the text.

---

## Why We Use LLMs to construct Summary Fields

Resumes vary widely in structure, terminology, and verbosity. Using LLMs allows us to:

* Interpret and normalize unstructured text into concise summaries
* Extract implied skills, responsibilities, and impact
* Avoid brittle rules or template-specific logic

This LLM-based summarization yields consistent, high-signal outputs that improve downstream retrieval and ranking.

---

## Summary

* **Concise, useful schema:** Only the most relevant, queryable fields.
* **LLM-assisted structure:** Reliable and consistent summaries using `Instructor`.
* **Search-ready output:** Fields are designed for embedding-based retrieval.
* **Scalable and robust:** Simple to extend, works across diverse resume formats.

Let me know if you'd like this packaged as documentation, implementation notes, or team onboarding material.
