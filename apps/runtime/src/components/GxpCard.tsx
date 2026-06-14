interface Props {
  title?: string;
  children?: React.ReactNode;
  [k: string]: unknown;
}

export function GxpCard({ title, children }: Props) {
  return (
    <div style={{
      border: "1px solid #e5e7eb", borderRadius: 8,
      padding: 20, background: "#fff", marginBottom: 16,
    }}>
      {title && <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700 }}>{title}</h3>}
      {children}
    </div>
  );
}
