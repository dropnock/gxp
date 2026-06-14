import type { ComponentNode, DatasourceConfig } from "@gxp/ts-shared/gxp-schema";
import { registry } from "./component-registry";

interface RenderContext {
  datasourceData: Record<string, unknown>;
}

export function renderComponentTree(
  nodes: ComponentNode[],
  ctx: RenderContext = { datasourceData: {} },
): React.ReactNode {
  return nodes.map((node) => {
    const Component = registry[node.type];
    if (!Component) return null;

    // Resolve datasource binding → inject `value` prop
    let extraProps: Record<string, unknown> = {};
    if (node.datasourceBinding) {
      const { datasourceId, field } = node.datasourceBinding;
      const dsData = ctx.datasourceData[datasourceId];
      if (dsData !== undefined) {
        extraProps.value = field
          ? (dsData as Record<string, unknown>)[field]
          : dsData;
      }
    }

    return (
      <Component key={node.id} {...node.attributes} {...extraProps}>
        {node.children.length > 0
          ? renderComponentTree(node.children, ctx)
          : null}
      </Component>
    );
  });
}
