export interface DatasourceConfig {
  id: string;
  type: "rest" | "workflow" | "document" | "case";
  config: {
    endpoint: string;
    method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
    headers?: Record<string, string>;
  };
}

export interface ComponentNode {
  type: string;
  id: string;
  attributes: Record<string, unknown>;
  datasourceBinding: { datasourceId: string; field: string } | null;
  children: ComponentNode[];
}

export interface Page {
  id: string;
  name: string;
  route: string;
  components: ComponentNode[];
  styles: Record<string, Record<string, string>>;
}

export interface AppSchema {
  schemaVersion: "1.0";
  appId: string;
  metadata: {
    name: string;
    description: string;
    version: number;
    theme: string;
  };
  datasources: DatasourceConfig[];
  pages: Page[];
  permissions: {
    viewRoles: string[];
    editRoles: string[];
  };
}
