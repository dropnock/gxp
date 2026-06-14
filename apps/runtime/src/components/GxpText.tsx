interface Props { text?: string; tag?: "p" | "h1" | "h2" | "h3" | "span"; value?: unknown; [k: string]: unknown }

export function GxpText({ text, tag = "p", value }: Props) {
  const Tag = tag;
  return <Tag style={{ margin: "0 0 8px" }}>{value != null ? String(value) : (text ?? "")}</Tag>;
}
