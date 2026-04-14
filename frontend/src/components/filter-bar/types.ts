// types.ts — FilterBar component props

export interface FilterBarProps {
  /** Currently active filter type(s). Empty array = "All". */
  activeTypes: string[];
  /** Called when a tag is toggled or "All" is clicked. */
  onChange: (types: string[]) => void;
}
