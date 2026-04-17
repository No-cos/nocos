"use client";

/**
 * usePrograms.ts
 *
 * Custom hook for fetching paid stipend programs from the Nocos API.
 * Mirrors the useIssues pattern: centralised data fetching, dev fallback
 * to mock data, and a clean { data, isLoading, error } interface.
 */

import { useState, useEffect } from "react";
import { fetchPrograms, type Program, type ProgramListResponse } from "@/lib/api";

const IS_DEV = process.env.NODE_ENV === "development";

interface UseProgramsOptions {
  status?: "upcoming" | "open" | "closed";
}

interface UseProgramsResult {
  data: ProgramListResponse | null;
  isLoading: boolean;
  error: string | null;
}

/** Minimal mock data used in development when the backend is not running. */
function getMockPrograms(): ProgramListResponse {
  const now = new Date();
  const future = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000);
  const past = new Date(now.getTime() - 10 * 24 * 60 * 60 * 1000);

  const mock: Program[] = [
    {
      id: "mock-1",
      name: "Google Season of Docs 2026",
      organisation: "Google",
      logo_url: null,
      description:
        "Season of Docs brings together open source projects and technical writers to improve open source documentation.",
      stipend_range: "$3,000 – $15,000",
      application_open: past.toISOString().slice(0, 10),
      application_deadline: future.toISOString().slice(0, 10),
      program_start: null,
      tags: ["documentation", "technical-writing", "open-source"],
      application_url: "https://developers.google.com/season-of-docs",
      status: "open",
      is_active: true,
      created_at: now.toISOString(),
      updated_at: now.toISOString(),
    },
    {
      id: "mock-2",
      name: "Google Summer of Code 2026",
      organisation: "Google",
      logo_url: null,
      description:
        "GSoC is a global, online program focused on bringing new contributors into open source software development.",
      stipend_range: "$1,500 – $6,600",
      application_open: past.toISOString().slice(0, 10),
      application_deadline: past.toISOString().slice(0, 10),
      program_start: null,
      tags: ["open-source", "mentorship", "coding"],
      application_url: "https://summerofcode.withgoogle.com/",
      status: "closed",
      is_active: true,
      created_at: now.toISOString(),
      updated_at: now.toISOString(),
    },
    {
      id: "mock-3",
      name: "Outreachy December 2026 – March 2027",
      organisation: "Software Freedom Conservancy",
      logo_url: null,
      description:
        "Outreachy provides internships in open source and open science for people subject to systemic bias in tech.",
      stipend_range: "$7,000",
      application_open: null,
      application_deadline: null,
      program_start: null,
      tags: ["diversity", "open-source", "mentorship"],
      application_url: "https://www.outreachy.org/",
      status: "upcoming",
      is_active: true,
      created_at: now.toISOString(),
      updated_at: now.toISOString(),
    },
  ];

  return { success: true, data: mock, meta: { total: mock.length } };
}

export function usePrograms(options: UseProgramsOptions = {}): UseProgramsResult {
  const { status } = options;

  const [data, setData] = useState<ProgramListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);

      try {
        const result = await fetchPrograms(status);
        if (!cancelled) setData(result);
      } catch (err) {
        if (cancelled) return;

        if (IS_DEV) {
          console.warn(
            "[Nocos dev] Backend unavailable — using mock program data."
          );
          setData(getMockPrograms());
        } else {
          console.error("Failed to fetch programs:", err);
          setError("Failed to load programs. Please try again.");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [status]);

  return { data, isLoading, error };
}
