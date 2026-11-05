// Every missing page, including an unknown /writing post: just "404", in the site's font and colours.
export default function NotFound() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#0a0a0a",
        color: "#ededed",
        fontFamily: "var(--font-roboto-mono), ui-monospace, monospace",
        fontSize: "1rem",
      }}
    >
      404
    </main>
  );
}
