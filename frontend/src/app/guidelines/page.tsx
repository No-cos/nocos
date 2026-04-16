import Link from "next/link";
import { Navbar } from "@/components/navbar";

export const metadata = {
  title: "Contribution Guidelines — Nocos",
  description:
    "What Nocos accepts and what we don't — guidelines for submitting non-code open source tasks.",
};

export default function GuidelinesPage() {
  return (
    <>
      <Navbar />
      <div
        style={{
          minHeight: "100vh",
          backgroundColor: "var(--color-bg)",
          paddingTop: "var(--navbar-height)",
        }}
      >
        <div
          style={{
            maxWidth: "720px",
            margin: "0 auto",
            padding: "80px 24px 96px",
          }}
        >
          {/* Page heading */}
          <h1
            style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontWeight: 800,
              fontSize: "clamp(1.75rem, 4vw, 2.5rem)",
              color: "var(--color-text-primary)",
              margin: "0 0 12px",
              lineHeight: 1.2,
            }}
          >
            Contribution Guidelines
          </h1>
          <p
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "1rem",
              color: "var(--color-text-secondary)",
              margin: "0 0 32px",
              lineHeight: 1.6,
            }}
          >
            What we accept and what we don&apos;t
          </p>

          {/* Divider */}
          <hr
            style={{
              border: "none",
              borderTop: "1px solid var(--color-border)",
              margin: "0 0 48px",
            }}
          />

          {/* Sections */}
          <div
            style={{ display: "flex", flexDirection: "column", gap: "40px" }}
          >
            <Section heading="What we accept">
              <BulletList
                items={[
                  "Issues requiring design, documentation, translation, research, community management, marketing, social media, project management, data analytics, or PR review.",
                  "Issues from public repositories with a recognised open source license (MIT, Apache, GPL, Creative Commons, etc.).",
                  "Issues that are currently open and actively seeking contributors.",
                  "Issues with enough context for a contributor to understand what is needed.",
                ]}
              />
            </Section>

            <Section heading="What we do not accept">
              <BulletList
                items={[
                  "Code-related issues — bug fixes, feature requests, refactoring, performance improvements, or anything requiring programming.",
                  "Issues from private, archived, or unlicensed repositories.",
                  "Duplicate issues already listed on Nocos.",
                  "Issues with no description or insufficient detail for a contributor to act on.",
                  "Issues from projects that are no longer actively maintained.",
                  "Spam, promotional content, or issues unrelated to open source contribution.",
                ]}
              />
            </Section>

            <Section heading="Tips for a successful submission">
              <BulletList
                items={[
                  "Make sure your issue title clearly describes the non-code work needed.",
                  "Include enough detail so a contributor knows exactly what to do.",
                  "Confirm the repository has an open source license before submitting.",
                  "Only submit issues that are genuinely open and welcoming contributors.",
                ]}
              />
            </Section>
          </div>

          {/* Divider */}
          <hr
            style={{
              border: "none",
              borderTop: "1px solid var(--color-border)",
              margin: "48px 0 40px",
            }}
          />

          {/* Return link */}
          <Link
            href="/"
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "0.9375rem",
              fontWeight: 500,
              color: "var(--color-cta-primary)",
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            ← Return to Home
          </Link>
        </div>
      </div>
    </>
  );
}

// ── Section ───────────────────────────────────────────────────────────────────

function Section({
  heading,
  children,
}: {
  heading: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2
        style={{
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          fontWeight: 700,
          fontSize: "1.125rem",
          color: "var(--color-text-primary)",
          margin: "0 0 16px",
        }}
      >
        {heading}
      </h2>
      {children}
    </section>
  );
}

// ── BulletList ────────────────────────────────────────────────────────────────

function BulletList({ items }: { items: string[] }) {
  return (
    <ul
      style={{
        margin: 0,
        padding: 0,
        listStyle: "none",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
      }}
    >
      {items.map((item, i) => (
        <li
          key={i}
          style={{
            display: "flex",
            gap: "12px",
            alignItems: "flex-start",
          }}
        >
          <span
            aria-hidden="true"
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              backgroundColor: "var(--color-cta-primary)",
              flexShrink: 0,
              marginTop: "9px",
            }}
          />
          <span
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "0.9375rem",
              color: "var(--color-text-primary)",
              lineHeight: 1.7,
            }}
          >
            {item}
          </span>
        </li>
      ))}
    </ul>
  );
}
