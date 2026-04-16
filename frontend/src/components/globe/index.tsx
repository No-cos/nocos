"use client";

/**
 * GlobeAnimation — decorative ASCII globe that rotates continuously.
 *
 * Features:
 * - Auto-spins left-to-right at a constant rate
 * - Follows the mouse cursor with lerp-smoothed yaw + pitch offsets
 *   (max ±30° influence; mouse adds on top of auto-spin, does not replace it)
 * - pointer-events: none — never blocks hero buttons
 * - aria-hidden: true — decorative, ignored by screen readers
 * - Transparent background — page background shows through
 * - cancelAnimationFrame + removeEventListener cleanup on unmount
 */

import { useEffect, useRef } from "react";

const WORLD_MAP = [
  "                                                                                                                            ",
  "                                                ...,,,....                                                                  ",
  "                                             ...::::::::::...           ...,..                                              ",
  "                           ......           ..:::***:::***:::..      ..:::::..                                              ",
  "                         ..::::::..        ..::::***:::***::::..    .:::::**:..                                             ",
  "                       ..:::::***::.      .:::::***:::***::::::.   .:::::***:..                                             ",
  "                      .:::::*****:::..    .::::****:::***:::::.    ::::*****:..                                             ",
  "                      .::::*****:::::.     ..::****:::***::::..     ..:*****:..                                             ",
  "                      ..::*****:::::.        ..:***:::***:..           ..:**:..                                             ",
  "                        ..:::***:::..          ..:***:::..               ....                                               ",
  "                          ..:::::..              ......                                                                     ",
  "                            .....                                                                                           ",
  "                                              ..::|--|--|::..                                                              ",
  "               .·.             .·.           ..:::|--|--|:::..         .·.                                                  ",
  "              ·:::·           ·:::·         .:::::|--|--|:::::.       ·:::·                                                 ",
  "             ·::*::·         ·::*::·        ::::**|--|--|**::::      ·::*::·                                                ",
  "             :::*:::         :::*:::        ::::**|--|--|**::::      :::*:::                                                ",
  "             ·::*::·         ·::*::·        ::::**|--|--|**::::      ·::*::·                                                ",
  "              ·:::·           ·:::·         .:::::|--|--|:::::.       ·:::·                                                 ",
  "               ·.·             ·.·           ..:::|--|--|:::..         ·.·                                                  ",
  "                                              ..::|--|--|::..                                                              ",
  "                                                                                                                            ",
  "                                                                                                                            ",
  "     .·.                                                                                    .·.                             ",
  "    ·:::·                           ......                                                 ·:::·                            ",
  "   ·::*::·                        ..::::::..                                              ·::*::·                           ",
  "   :::*:::                       .::****:::..                                             :::*:::                           ",
  "   ·::*::·                      ..::***:::...                                             ·::*::·                           ",
  "    ·:::·                        ..::::::..                                                ·:::·                            ",
  "     .·.                           ......                                                   .·.                             ",
  "                                                                                                                            ",
  "                                                                                                                            ",
  "                                             ..:::::::..                                                                    ",
  "                                           ..:::::::::..                                                                    ",
  "                                          .:::::::::::..                                                                    ",
  "                                          :::::::::::::.                                                                    ",
  "                                          .:::::::::::..                                                                    ",
  "                                           ..:::::::::..                                                                    ",
  "                                             ..:::::::..                                                                    ",
  "                                                                                                                            ",
  "                                                                                                                            ",
];

export function GlobeAnimation() {
  const elRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = elRef.current;
    if (!el) return;

    // Skip the animation on touch/mobile devices — the rAF loop doing
    // 8,820-char textContent mutations every frame competes with the
    // browser's scroll compositor and causes visible lag on mobile.
    // Touch devices get no mouse-follow benefit, so this is zero visual loss.
    if (window.matchMedia("(pointer: coarse)").matches) return;

    // ── Globe constants ───────────────────────────────────────────────
    const WIDTH = 140;
    const HEIGHT = Math.floor(WIDTH * 0.45); // ~63 rows — monospace aspect ratio
    const ROTATION_SPEED = (2 * Math.PI) / 9000; // full auto-spin ≈ 9 s
    const SHADE_RAMP = "@#MWo*|=~-.· ";
    const MAP_H = WORLD_MAP.length;
    const MAP_W = WORLD_MAP[0].length;

    // ── Mouse-follow state ────────────────────────────────────────────
    // Max ±30° (π/6 rad) of mouse influence on top of the auto-spin
    const MAX_MOUSE_ANGLE = Math.PI / 6;
    const LERP = 0.05; // damping — lower = smoother / lazier follow

    const mouse = {
      targetYaw: 0,
      targetPitch: 0,
      currentYaw: 0,
      currentPitch: 0,
    };

    function handleMouseMove(e: MouseEvent) {
      // Normalise cursor to [-0.5, 0.5] across the viewport
      const cx = e.clientX / window.innerWidth - 0.5;
      const cy = e.clientY / window.innerHeight - 0.5;
      // Right cursor → rotate globe right; up cursor → tilt globe up (negative cy → positive pitch)
      mouse.targetYaw = cx * 2 * MAX_MOUSE_ANGLE;
      mouse.targetPitch = -cy * 2 * MAX_MOUSE_ANGLE;
    }

    window.addEventListener("mousemove", handleMouseMove, { passive: true });

    // ── Render loop ───────────────────────────────────────────────────
    const startTime = performance.now();
    let rafId: number;

    function render() {
      // Smooth mouse values toward their targets
      mouse.currentYaw += (mouse.targetYaw - mouse.currentYaw) * LERP;
      mouse.currentPitch += (mouse.targetPitch - mouse.currentPitch) * LERP;

      const elapsed = performance.now() - startTime;
      // Auto-spin angle + mouse yaw offset
      const angle = -(elapsed * ROTATION_SPEED) + mouse.currentYaw;

      // Precompute pitch rotation factors (rotation around X axis)
      const cosPitch = Math.cos(mouse.currentPitch);
      const sinPitch = Math.sin(mouse.currentPitch);

      let output = "";

      for (let y = 0; y < HEIGHT; y++) {
        // ny: screen-space vertical normal, flipped so +1 = top of sphere
        const ny = -(2 * y / (HEIGHT - 1) - 1);

        for (let x = 0; x < WIDTH; x++) {
          const nx = 2 * x / (WIDTH - 1) - 1;

          if (nx * nx + ny * ny <= 1) {
            const nz = Math.sqrt(1 - nx * nx - ny * ny);

            // Apply pitch rotation (around X axis) to ny/nz before projection
            const ny_r = ny * cosPitch - nz * sinPitch;
            const nz_r = ny * sinPitch + nz * cosPitch;

            const lat = Math.asin(Math.max(-1, Math.min(1, ny_r)));
            let lon = Math.atan2(nx, nz_r) + angle;
            lon = ((lon % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);

            const mapX = Math.floor((lon / (2 * Math.PI)) * (MAP_W - 1));
            const mapY = Math.floor(((Math.PI / 2 - lat) / Math.PI) * (MAP_H - 1));

            if (mapY >= 0 && mapY < MAP_H && mapX >= 0 && mapX < MAP_W) {
              const char = WORLD_MAP[mapY][mapX];
              if (char === " ") {
                output += " ";
              } else {
                const shadeIndex = Math.floor((1 - nz) * (SHADE_RAMP.length - 1));
                output += SHADE_RAMP[shadeIndex];
              }
            } else {
              output += " ";
            }
          } else {
            output += " ";
          }
        }
        output += "\n";
      }

      if (!el) return;
      el.textContent = output;
      rafId = requestAnimationFrame(render);
    }

    rafId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  return (
    <div
      ref={elRef}
      aria-hidden="true"
      className="globe-ascii"
      style={{
        fontFamily: '"Courier New", Courier, "Roboto Mono", monospace',
        fontWeight: "bold",
        lineHeight: 1.0,
        whiteSpace: "pre",
        userSelect: "none",
        pointerEvents: "none",
        color: "var(--color-cta-primary)",
      }}
    />
  );
}
