/**
 * CategoryMarquee component — infinite horizontal scroll of contribution type tags.
 *
 * Two rows scroll in opposite directions using a pure CSS keyframe animation —
 * no JavaScript library required. The animation pauses on hover so users
 * can read the tags comfortably.
 *
 * Implementation detail: each row duplicates the tag list so the scroll
 * appears seamless. The duplicate is aria-hidden so screen readers don't
 * read the labels twice.
 */

import { Tag, ALL_CONTRIBUTION_TYPES } from "@/components/ui/tag";

export function CategoryMarquee() {
  // Convert the tuple to a mutable array for map()
  const types = [...ALL_CONTRIBUTION_TYPES];

  return (
    <section
      aria-label="Contribution types available on Nocos"
      style={{
        padding: "32px 0 40px",
        overflow: "hidden",
        backgroundColor: "var(--color-bg)",
        // Fade the left and right edges into the background using a CSS mask.
        // This gives the marquee the appearance of emerging from and dissolving
        // into the page — purely CSS, no extra elements needed.
        WebkitMaskImage:
          "linear-gradient(to right, transparent 0%, transparent 22%, black 25%, black 60%, transparent 63%, transparent 100%)",
        maskImage:
          "linear-gradient(to right, transparent 0%, transparent 22%, black 25%, black 60%, transparent 63%, transparent 100%)",
      }}
    >
      {/* Row 1 — scrolls left */}
      <MarqueeRow types={types} direction="left" />

      {/* Row 2 — scrolls right, offset by half to feel different */}
      <div style={{ marginTop: "12px" }}>
        <MarqueeRow types={[...types].reverse()} direction="right" />
      </div>

    </section>
  );
}

// ─── Internal sub-component ────────────────────────────────────────────────────

interface MarqueeRowProps {
  types: string[];
  direction: "left" | "right";
}

/**
 * MarqueeRow — a single scrolling row of Tag pills.
 *
 * The tag list is rendered twice side-by-side. At 50% translateX the
 * first copy has scrolled fully off-screen, and the animation resets —
 * creating a seamless loop without JavaScript.
 *
 * @param types     - Array of contribution type strings to display
 * @param direction - Scroll direction ("left" or "right")
 */
function MarqueeRow({ types, direction }: MarqueeRowProps) {
  return (
    <div
      className="marquee-row"
      style={{ overflow: "hidden", width: "100%" }}
    >
      <div
        className={`marquee-track marquee-track--${direction}`}
        aria-hidden="true"
      >
        {/* First copy */}
        {types.map((type) => (
          <Tag key={`a-${type}`} type={type} size="md" />
        ))}
        {/* Duplicate — makes the loop seamless */}
        {types.map((type) => (
          <Tag key={`b-${type}`} type={type} size="md" />
        ))}
      </div>

      {/* Accessible version: visually hidden, read once by screen readers */}
      <p className="sr-only">
        Contribution types: {types.join(", ")}
      </p>
    </div>
  );
}
