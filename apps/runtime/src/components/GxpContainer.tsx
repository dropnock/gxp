interface Props {
  children?: React.ReactNode;
  layout?: "row" | "column";
  gap?: number;
  [k: string]: unknown;
}

export function GxpContainer({ children, layout = "column", gap = 12 }: Props) {
  return (
    <div style={{ display: "flex", flexDirection: layout, gap, flexWrap: "wrap" }}>
      {children}
    </div>
  );
}
