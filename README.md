# IT Helpdesk Ticket Categorisation and Triage — MSIT 5910 Capstone

[![tests](https://github.com/saikatsunilganguly-cpu/msit5910-helpdesk-capstone/actions/workflows/tests.yml/badge.svg)](https://github.com/saikatsunilganguly-cpu/msit5910-helpdesk-capstone/actions/workflows/tests.yml)

**Portfolio:** https://saikatsunilganguly-cpu.github.io/msit5910-helpdesk-capstone/

**Author:** Saikat Sunil Ganguly · **Program:** MSIT 5910 Capstone, University of the People · **Supervisor:** Dr. Stella Whyte

## Project Summary

This capstone investigates how a simplified ticket categorisation model and a
structured triage workflow can improve routing consistency and reduce avoidable
delays in IT helpdesk environments.

It began as a tool-agnostic workflow design: six modules, a security and
governance layer, and seven functional requirements. With the supervisor's
approval, it then added a deliberately small working prototype of the core
logic. The prototype is a Flask application with rule-based categorisation,
role-based access control that masks security-sensitive tickets, and an audit
log.

## Key Results

| Measure | Result |
|---|---|
| Categorisation accuracy | 98.0% (49 of 50 independently written tickets) |
| Mean response time (single user) | 15.3 ms over 60 requests |
| Automated tests | 55: 52 pass, 3 documented limitations (expected failures) |
| Statement coverage (`app`, `categorization`, `models`) | 98% |
| Stability (10 concurrent users) | 300/300 submissions stored, no records lost |

The prototype implements three of the six modules. Of the seven functional
requirements, six are partly implemented and one (reporting) is not built. See
the report for details.

## Repository Structure

```
msit5910-helpdesk-capstone/
├── README.md
├── .github/workflows/tests.yml   # runs all tests on every push
├── docs/                         # GitHub Pages portfolio and design notes
│   ├── index.html
│   ├── assets/                   # report PDF, demo video, figures
│   ├── literature-review/
│   ├── problem-statement/
│   ├── design/
│   └── progress/
├── diagrams/                     # architecture (Mermaid source + PNG)
├── requirements/                 # functional and non-functional requirements
├── workflow/                     # triage workflow
└── prototype/                    # Flask app, tests, evaluation scripts and results
```

## Run the Prototype

```
cd prototype
pip install -r requirements.txt
python app.py        # http://127.0.0.1:5000  (log in as agent1 or idmgmt1)
python -m pytest     # all 55 tests
```

## Branching and Releases

- **development:** active work, tested automatically on every push.
- **main:** reviewed, stable state; each milestone merged here is tagged.

Releases follow Semantic Versioning: v0.1.0 (first prototype), v0.2.0 (unit
tests and keyword fix), v1.0.0 (tested prototype), v1.1.0 (evaluation),
v1.2.0 (system testing and fixes).
