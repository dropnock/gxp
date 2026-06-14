interface Props {
  label?: string;
  variant?: "primary" | "secondary" | "danger";
  datasourceAction?: string;
  [k: string]: unknown;
}

const STYLES: Record<string, React.CSSProperties> = {
  primary:   { background: "#2563eb", color: "#fff", border: "none" },
  secondary: { background: "#f3f4f6", color: "#374151", border: "1px solid #d1d5db" },
  danger:    { background: "#dc2626", color: "#fff", border: "none" },
};

export function GxpButton({ label = "Button", variant = "primary" }: Props) {
  return (
    <button
      style={{
        padding: "8px 16px", borderRadius: 4, cursor: "pointer", fontSize: 14,
        ...STYLES[variant] ?? STYLES.primary,
      }}
    >
      {label}
    </button>
  );
}
