// types.ts
// TypeScript types for the Navbar component.

export interface NavLink {
  label: string;
  href: string;
}

export interface NavbarProps {
  /** Override the default nav links (useful for testing). */
  links?: NavLink[];
}
