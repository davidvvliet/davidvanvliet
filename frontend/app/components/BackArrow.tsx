// The "back" arrow before links like "explore" and "models". Drawn rather than the
// "←" character, whose head is small on a long stem and sits at lowercase height.
// As tall as a capital letter and resting on the baseline, so it lines up with the
// titles beside it; stroked in the text's colour.
export default function BackArrow() {
  return (
    <svg viewBox="0 0 10 8" aria-hidden="true"
      style={{ display: "inline-block", height: "0.72em", width: "0.9em", marginRight: "0.5em", overflow: "visible", flex: "none" }}>
      <path d="M4.6 0.6 L0.8 4 L4.6 7.4 M0.8 4 H9.4" fill="none" stroke="currentColor" strokeWidth="1.1" />
    </svg>
  );
}
