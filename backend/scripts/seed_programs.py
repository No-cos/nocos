#!/usr/bin/env python3
# scripts/seed_programs.py
# Seed the programs table with current paid stipend programs.
#
# Run once after the first deploy (or whenever you want to reset to the
# canonical program list). Safe to re-run — it checks for existing rows
# by name before inserting so duplicates are never created.
#
# Usage (from backend/):
#   python scripts/seed_programs.py

import sys
import os
from datetime import date

# Ensure the backend root is on the path so all modules resolve correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import config
from models.base import Base
from models.program import Program

# ─── Canonical program data ────────────────────────────────────────────────────
# Status reflects the state as of April 2026.
# Update status, dates, and stipend_range as new cohorts are announced.

PROGRAMS: list[dict] = [
    {
        "name": "Google Summer of Code 2026",
        "organisation": "Google",
        "logo_url": "https://summerofcode.withgoogle.com/static/img/og-image.png",
        "description": (
            "GSoC is a global, online program focused on bringing new contributors into "
            "open source software development. Contributors work on a 3-month programming "
            "project with the guidance of mentors from open source organisations."
        ),
        "stipend_range": "$1,500 – $6,600",
        "application_open": date(2026, 3, 24),
        "application_deadline": date(2026, 4, 8),
        "program_start": date(2026, 5, 26),
        "tags": ["open-source", "mentorship", "coding", "google"],
        "application_url": "https://summerofcode.withgoogle.com/",
        "status": "closed",
    },
    {
        "name": "Google Season of Docs 2026",
        "organisation": "Google",
        "logo_url": None,
        "description": (
            "Season of Docs brings together open source projects and technical writers to "
            "improve open source documentation. Projects receive a stipend to pay technical "
            "writers for creating or improving project documentation."
        ),
        "stipend_range": "$3,000 – $15,000",
        "application_open": date(2026, 3, 10),
        "application_deadline": date(2026, 4, 22),
        "program_start": date(2026, 5, 20),
        "tags": ["documentation", "technical-writing", "open-source", "google"],
        "application_url": "https://developers.google.com/season-of-docs",
        "status": "open",
    },
    {
        "name": "Outreachy May – August 2026",
        "organisation": "Software Freedom Conservancy",
        "logo_url": None,
        "description": (
            "Outreachy provides internships in open source and open science. Internships are "
            "open to people subject to systemic bias and underrepresentation in tech. "
            "Interns work remotely with experienced mentors for three months."
        ),
        "stipend_range": "$7,000",
        "application_open": date(2026, 1, 13),
        "application_deadline": date(2026, 2, 3),
        "program_start": date(2026, 5, 27),
        "tags": ["diversity", "open-source", "mentorship", "remote"],
        "application_url": "https://www.outreachy.org/",
        "status": "closed",
    },
    {
        "name": "Outreachy December 2026 – March 2027",
        "organisation": "Software Freedom Conservancy",
        "logo_url": None,
        "description": (
            "Outreachy provides internships in open source and open science. Internships are "
            "open to people subject to systemic bias and underrepresentation in tech. "
            "Applications for the December cohort open in August 2026."
        ),
        "stipend_range": "$7,000",
        "application_open": date(2026, 8, 11),
        "application_deadline": date(2026, 9, 1),
        "program_start": date(2026, 12, 2),
        "tags": ["diversity", "open-source", "mentorship", "remote"],
        "application_url": "https://www.outreachy.org/",
        "status": "upcoming",
    },
    {
        "name": "LFX Mentorship Term 1 2026",
        "organisation": "Linux Foundation",
        "logo_url": None,
        "description": (
            "The Linux Foundation LFX Mentorship programme helps developers — especially "
            "those from non-traditional backgrounds — gain exposure to open source development "
            "under the guidance of experienced mentors across LF-hosted projects."
        ),
        "stipend_range": "$3,000 – $6,600",
        "application_open": date(2026, 1, 14),
        "application_deadline": date(2026, 2, 6),
        "program_start": date(2026, 3, 2),
        "tags": ["linux", "cloud", "open-source", "mentorship"],
        "application_url": "https://mentorship.lfx.linuxfoundation.org/",
        "status": "closed",
    },
    {
        "name": "LFX Mentorship Term 2 2026",
        "organisation": "Linux Foundation",
        "logo_url": None,
        "description": (
            "The second LFX Mentorship term of 2026 accepts applications for cloud-native, "
            "security, and networking projects across the Linux Foundation ecosystem. "
            "Mentees work full-time for three months with a dedicated stipend."
        ),
        "stipend_range": "$3,000 – $6,600",
        "application_open": date(2026, 5, 13),
        "application_deadline": date(2026, 6, 5),
        "program_start": date(2026, 7, 1),
        "tags": ["linux", "cloud", "open-source", "mentorship"],
        "application_url": "https://mentorship.lfx.linuxfoundation.org/",
        "status": "upcoming",
    },
    {
        "name": "MLH Fellowship Summer 2026",
        "organisation": "Major League Hacking",
        "logo_url": None,
        "description": (
            "The MLH Fellowship is a remote internship alternative for software engineers. "
            "Fellows contribute to open source projects used by companies worldwide, "
            "build their portfolio, and earn a living stipend — no office required."
        ),
        "stipend_range": "$5,000",
        "application_open": date(2026, 2, 1),
        "application_deadline": date(2026, 5, 1),
        "program_start": date(2026, 6, 1),
        "tags": ["open-source", "networking", "mentorship", "software-engineering"],
        "application_url": "https://fellowship.mlh.io/",
        "status": "open",
    },
    {
        "name": "Semester of Code 2026",
        "organisation": "openSUSE",
        "logo_url": None,
        "description": (
            "The openSUSE Semester of Code is a European programme that gives students "
            "the opportunity to work on open source projects over one semester while "
            "receiving academic credit and a stipend from their university."
        ),
        "stipend_range": "€ varies by university",
        "application_open": date(2026, 3, 1),
        "application_deadline": date(2026, 4, 30),
        "program_start": date(2026, 5, 15),
        "tags": ["open-source", "linux", "europe", "students"],
        "application_url": "https://en.opensuse.org/openSUSE:Season_of_Code",
        "status": "open",
    },
]


def seed(db_url: str) -> None:
    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionLocal() as session:
        inserted = 0
        skipped = 0

        for data in PROGRAMS:
            # Check by name — if a program with this exact name already exists, skip it.
            existing = session.query(Program).filter(Program.name == data["name"]).first()
            if existing:
                print(f"  SKIP  {data['name']}")
                skipped += 1
                continue

            program = Program(**data)
            session.add(program)
            print(f"  INSERT {data['name']} ({data['status']})")
            inserted += 1

        session.commit()
        print(f"\nDone — {inserted} inserted, {skipped} skipped.")


if __name__ == "__main__":
    db_url = config.DATABASE_URL
    if not db_url:
        print("ERROR: DATABASE_URL is not set. Export it before running this script.")
        sys.exit(1)

    print(f"Seeding programs into {db_url[:db_url.index('@') + 1]}... (credentials hidden)\n")
    seed(db_url)
