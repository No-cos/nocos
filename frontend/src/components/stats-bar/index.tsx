"use client";

/**
 * StatsBar — live platform statistics displayed between the hero and marquee.
 *
 * Three stats in a horizontal row:
 *   Open Tasks · Active Projects · Contribution Types
 *
 * Numbers animate from 0 to their final value (ease-out, 1.5 s) the first
 * time the component scrolls into view, using useInView + requestAnimationFrame.
 * Falls back to "—" if the API call fails — never shows 0 or NaN.
 */

import { useEffect, useRef, useState } from "react";
import { fetchStats } from "@/lib/api";
import { useInView } from "@/hooks/use-in-view";

interface StatItem {
  value: number | null;   // null = loading/error → show "—"
  suffix: string;
  label: string;
}

/** Ease-out cubic: fast start, decelerates to 1. */
function easeOut(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

function useCountUp(target: number | null, active: boolean, duration = 1500) {
  const [display, setDisplay] = useState<string>("—");
  const rafRef = useRef<number>();
  const startRef = useRef<number | null>(null);

  useEffect(() => {
    if (!active || target === null || target === undefined) return;
    const finalTarget = target;

    startRef.current = null;

    function tick(now: number) {
      if (startRef.current === null) startRef.current = now;
      const elapsed = now - startRef.current;
      const progress = Math.min(elapsed / duration, 1);
      const value = Math.round(easeOut(progress) * finalTarget);
      setDisplay(value.toLocaleString());
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick);
      }
    }

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current !== undefined) cancelAnimationFrame(rafRef.current);
    };
  }, [target, active, duration]);

  return display;
}

function StatBlock({
  value,
  suffix,
  label,
  animate,
}: StatItem & { animate: boolean }) {
  const count = useCountUp(value, animate);
  const displayValue = value === null ? "—" : count;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      <span
        style={{
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          fontWeight: 800,
          fontSize: "clamp(2rem, 4vw, 2.75rem)",
          color: "var(--color-text-primary)",
          lineHeight: 1.1,
          letterSpacing: "-0.02em",
        }}
      >
        {displayValue}{value !== null ? suffix : ""}
      </span>
      <span
        style={{
          fontFamily: "'Inter', sans-serif",
          fontWeight: 400,
          fontSize: "0.8125rem",
          color: "var(--color-text-secondary)",
          marginTop: "6px",
        }}
      >
        {label}
      </span>
    </div>
  );
}

export function StatsBar() {
  const { ref, inView } = useInView<HTMLDivElement>({ threshold: 0.3 });
  const [stats, setStats] = useState<{
    open_tasks: number | null;
    projects: number | null;
    contribution_types: number | null;
  }>({ open_tasks: null, projects: null, contribution_types: null });

  useEffect(() => {
    fetchStats()
      .then((data) =>
        setStats({
          open_tasks: data.open_tasks,
          projects: data.projects,
          contribution_types: data.contribution_types,
        })
      )
      .catch(() => {
        // Leave nulls — StatBlock will show "—"
      });
  }, []);

  const items: StatItem[] = [
    { value: stats.open_tasks, suffix: "+", label: "Open Tasks" },
    { value: stats.projects, suffix: "+", label: "Active Projects" },
    { value: stats.contribution_types, suffix: "", label: "Contribution Types" },
  ];

  return (
    <div
      ref={ref}
      style={{
        backgroundColor: "var(--color-bg)",
        width: "100%",
      }}
    >
      <div
        style={{
          maxWidth: "var(--content-max-width)",
          margin: "0 auto",
          padding: "48px 24px",
          display: "flex",
          justifyContent: "center",
          gap: "clamp(40px, 8vw, 120px)",
        }}
      >
        {items.map((item) => (
          <StatBlock key={item.label} {...item} animate={inView} />
        ))}
      </div>
    </div>
  );
}
