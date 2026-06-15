/**
 * GrapesJS editor wrapper.
 *
 * Mounts a GrapesJS instance into a container div.  Registers the 5 core
 * GXP component blocks in the block manager so drag-and-drop produces
 * typed GXP component nodes.
 *
 * The caller receives updates via onChange (called on every commandStack change)
 * and can retrieve the full project JSON via the `getProject()` handle.
 */
import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import grapesjs from "grapesjs";

export interface GrapesEditorHandle {
  getProject: () => object;
}

interface Props {
  initialData?: object;
  onChange?: (project: object) => void;
}

const GXP_BLOCKS = [
  {
    id: "gxp-text", label: "Text", category: "GXP",
    content: { type: "gxp-text", attributes: { text: "Enter text here", tag: "p" } },
  },
  {
    id: "gxp-button", label: "Button", category: "GXP",
    content: { type: "gxp-button", attributes: { label: "Click me", variant: "primary" } },
  },
  {
    id: "gxp-card", label: "Card", category: "GXP",
    content: { type: "gxp-card", attributes: { title: "Card Title" }, components: [] },
  },
  {
    id: "gxp-form", label: "Form", category: "GXP",
    content: {
      type: "gxp-form",
      attributes: {
        fields: [
          { name: "field1", label: "Field 1", type: "text", required: true },
        ],
        submitLabel: "Submit",
      },
    },
  },
  {
    id: "gxp-table", label: "Table", category: "GXP",
    content: {
      type: "gxp-table",
      attributes: {
        columns: [
          { key: "id", label: "ID" },
          { key: "name", label: "Name" },
        ],
        data: [{ id: "1", name: "Example" }],
      },
    },
  },
  {
    id: "gxp-container", label: "Container", category: "GXP",
    content: { type: "gxp-container", attributes: { layout: "column", gap: 12 }, components: [] },
  },
];

const GrapesEditor = forwardRef<GrapesEditorHandle, Props>(function GrapesEditor(
  { initialData, onChange },
  ref
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<ReturnType<typeof grapesjs.init> | null>(null);

  useImperativeHandle(ref, () => ({
    getProject() {
      return editorRef.current?.getProjectData() ?? {};
    },
  }));

  useEffect(() => {
    if (!containerRef.current) return;

    const editor = grapesjs.init({
      container: containerRef.current,
      height: "100%",
      width: "auto",
      storageManager: false,
      panels: { defaults: [] },
      blockManager: {
        appendTo: "#gxp-blocks",
        blocks: GXP_BLOCKS,
      },
    });

    // Register custom component types so GrapesJS renders them with their GXP type
    GXP_BLOCKS.forEach(({ id }) => {
      editor.Components.addType(id, {
        model: {
          defaults: { tagName: "div", attributes: { "data-gxp-type": id } },
        },
      });
    });

    if (initialData && Object.keys(initialData).length > 0) {
      editor.loadProjectData(initialData);
    }

    if (onChange) {
      editor.on("change:changesCount", () => {
        onChange(editor.getProjectData());
      });
    }

    editorRef.current = editor;
    return () => {
      editor.destroy();
      editorRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>
      {/* Block panel */}
      <div
        id="gxp-blocks"
        style={{
          width: 180, borderRight: "1px solid #e5e7eb", overflowY: "auto",
          background: "#f9fafb", padding: 8, flexShrink: 0,
        }}
      />
      {/* Canvas */}
      <div ref={containerRef} style={{ flex: 1, height: "100%" }} />
    </div>
  );
});

export default GrapesEditor;
