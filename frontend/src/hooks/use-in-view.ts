"use client";

import { useEffect, useRef, useState } from "react";

/**
 * useInView — scroll-triggered visibility hook using IntersectionObserver.
 *
 * Returns a ref to attach to the target element and a boolean that flips to
 * true once the element enters the viewport. With triggerOnce: true (the
 * default) the observer disconnects after first intersection so the element
 * never re-animates on scroll-up.
 *
 * @param options.threshold  - Fraction of element visible to trigger (default 0.15)
 * @param options.triggerOnce - Disconnect after first intersection (default true)
 */
export function useInView<T extends Element = HTMLElement>(options?: {
  threshold?: number;
  triggerOnce?: boolean;
}) {
  const { threshold = 0.15, triggerOnce = true } = options ?? {};
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          if (triggerOnce) observer.disconnect();
        }
      },
      { threshold }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold, triggerOnce]);

  return { ref, inView };
}
