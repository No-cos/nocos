"use client";

/**
 * GlobeAnimation — decorative ASCII globe that rotates continuously.
 *
 * Extracted from ascii_globe_hero.html. Renders into a <div> using
 * requestAnimationFrame; cleaned up with cancelAnimationFrame on unmount.
 *
 * Design constraints:
 * - pointer-events: none — never blocks hero CTA clicks
 * - aria-hidden: true — purely decorative, ignored by screen readers
 * - Transparent background — page background shows through
 */

import { useEffect, useRef } from "react";

// Landmask lookup — simplified equirectangular world map
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

    const WIDTH = 140;
    const HEIGHT = Math.floor(WIDTH * 0.45); // ~63 rows — monospace aspect ratio
    const ROTATION_SPEED = (2 * Math.PI) / 9000; // full rotation ≈ 9 s
    const SHADE_RAMP = "@#MWo*|=~-.· ";

    const MAP_H = WORLD_MAP.length;
    const MAP_W = WORLD_MAP[0].length;

    const startTime = performance.now();
    let rafId: number;

    function render() {
      const elapsed = performance.now() - startTime;
      const angle = -(elapsed * ROTATION_SPEED);

      let output = "";

      for (let y = 0; y < HEIGHT; y++) {
        const ny = -(2 * y / (HEIGHT - 1) - 1);

        for (let x = 0; x < WIDTH; x++) {
          const nx = 2 * x / (WIDTH - 1) - 1;

          if (nx * nx + ny * ny <= 1) {
            const nz = Math.sqrt(1 - nx * nx - ny * ny);

            const lat = Math.asin(ny);
            let lon = Math.atan2(nx, nz) + angle;
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
